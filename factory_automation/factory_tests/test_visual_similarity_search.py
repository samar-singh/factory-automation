#!/usr/bin/env python3
"""Test visual similarity search with CLIP embeddings"""

import base64
import logging
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory_automation.factory_database.image_storage import ImageStorageManager
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.enhanced_search import EnhancedRAGSearch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisualSimilarityTester:
    """Test visual similarity search capabilities"""
    
    def __init__(self):
        """Initialize test components"""
        self.chroma_client = ChromaDBClient(collection_name="tag_inventory_stella_smart")
        self.image_storage = ImageStorageManager()
        self.search_engine = EnhancedRAGSearch(
            chromadb_client=self.chroma_client,
            enable_image_search=True,
            enable_reranking=True
        )
        
        # Check if CLIP is available
        self.clip_available = self._check_clip()
    
    def _check_clip(self) -> bool:
        """Check if CLIP is available"""
        try:
            import clip
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model, self.preprocess = clip.load("ViT-B/32", device=self.device)
            logger.info(f"CLIP loaded successfully on {self.device}")
            return True
        except Exception as e:
            logger.warning(f"CLIP not available: {e}")
            return False
    
    def generate_clip_embedding(self, image_base64: str) -> List[float]:
        """Generate CLIP embedding for an image"""
        if not self.clip_available:
            return None
        
        try:
            import torch
            from io import BytesIO
            
            # Decode base64 to PIL Image
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data)).convert("RGB")
            
            # Preprocess and encode
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                # Normalize
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
            return image_features.cpu().numpy().flatten().tolist()
            
        except Exception as e:
            logger.error(f"Error generating CLIP embedding: {e}")
            return None
    
    def test_image_to_image_search(self) -> Tuple[bool, str]:
        """Test searching for similar images using an image query"""
        logger.info("\n=== Testing Image-to-Image Search ===")
        
        try:
            # Get a sample image from storage
            sample_results = self.image_storage.collection.get(limit=5, include=["metadatas"])
            
            if not sample_results.get("ids"):
                return False, "No images found in storage"
            
            # Use first image as query
            query_image_id = sample_results["ids"][0]
            query_metadata = sample_results["metadatas"][0]
            
            logger.info(f"Using image {query_image_id} as query")
            logger.info(f"Query image: {query_metadata.get('item_name', 'Unknown')}")
            
            # Get the full image
            query_image = self.image_storage.get_image(query_image_id)
            
            if not query_image or not query_image.get("embedding"):
                # Generate embedding if missing
                if query_image and query_image.get("base64") and self.clip_available:
                    logger.info("Generating CLIP embedding for query image...")
                    embedding = self.generate_clip_embedding(query_image["base64"])
                    if embedding:
                        # Search by embedding
                        similar_images = self.image_storage.search_by_embedding(
                            query_embedding=embedding,
                            n_results=5
                        )
                    else:
                        return False, "Could not generate embedding"
                else:
                    return False, "Query image has no embedding and CLIP not available"
            else:
                # Use existing embedding
                embedding = query_image["embedding"]
                similar_images = self.image_storage.search_by_embedding(
                    query_embedding=embedding,
                    n_results=5
                )
            
            logger.info(f"\nFound {len(similar_images)} similar images:")
            for i, img in enumerate(similar_images, 1):
                logger.info(f"{i}. {img['metadata'].get('item_name', 'Unknown')}")
                logger.info(f"   Brand: {img['metadata'].get('brand', 'N/A')}")
                logger.info(f"   Similarity: {img['similarity']:.3f}")
            
            return True, f"Successfully found {len(similar_images)} similar images"
            
        except Exception as e:
            logger.error(f"Image search test failed: {e}")
            return False, str(e)
    
    def test_text_to_image_search(self) -> Tuple[bool, str]:
        """Test finding images using text queries"""
        logger.info("\n=== Testing Text-to-Image Search ===")
        
        test_queries = [
            "blue shirt with collar",
            "myntra tag with logo",
            "thread spool image",
            "peter england formal wear"
        ]
        
        results_summary = []
        
        for query in test_queries:
            logger.info(f"\nSearching for: '{query}'")
            
            try:
                results, stats = self.search_engine.search(query, n_results=3)
                
                images_found = sum(1 for r in results if r.get("image_data"))
                logger.info(f"  Found {len(results)} results, {images_found} with images")
                
                for r in results[:3]:
                    meta = r.get("metadata", {})
                    has_image = r.get("image_data") is not None
                    logger.info(f"  - {meta.get('item_name', 'Unknown')} ({'WITH' if has_image else 'NO'} image)")
                
                results_summary.append(f"{query}: {images_found}/{len(results)} with images")
                
            except Exception as e:
                logger.error(f"  Error: {e}")
                results_summary.append(f"{query}: ERROR")
        
        return True, "\n".join(results_summary)
    
    def test_visual_diversity(self) -> Tuple[bool, str]:
        """Test diversity of visual embeddings"""
        logger.info("\n=== Testing Visual Embedding Diversity ===")
        
        try:
            # Get sample of images with embeddings
            sample = self.image_storage.collection.get(
                limit=20,
                include=["embeddings", "metadatas"],
                where={"has_full_image": True}
            )
            
            if not sample.get("embeddings") or len(sample["embeddings"]) < 2:
                return False, "Not enough images with embeddings"
            
            # Calculate pairwise similarities
            embeddings = np.array(sample["embeddings"])
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            normalized = embeddings / (norms + 1e-8)
            
            # Compute similarity matrix
            similarity_matrix = np.dot(normalized, normalized.T)
            
            # Get statistics
            np.fill_diagonal(similarity_matrix, 0)  # Exclude self-similarity
            avg_similarity = np.mean(similarity_matrix)
            max_similarity = np.max(similarity_matrix)
            min_similarity = np.min(similarity_matrix)
            
            logger.info("Embedding diversity statistics:")
            logger.info(f"  Average similarity: {avg_similarity:.3f}")
            logger.info(f"  Max similarity: {max_similarity:.3f}")
            logger.info(f"  Min similarity: {min_similarity:.3f}")
            
            # Find most similar pairs
            flat_indices = np.argpartition(similarity_matrix.flatten(), -3)[-3:]
            for idx in flat_indices:
                i, j = np.unravel_index(idx, similarity_matrix.shape)
                if i < j:  # Avoid duplicates
                    sim = similarity_matrix[i, j]
                    item1 = sample["metadatas"][i].get("item_name", "Unknown")
                    item2 = sample["metadatas"][j].get("item_name", "Unknown")
                    logger.info(f"  Similar pair: {item1} <-> {item2} (sim: {sim:.3f})")
            
            diversity_score = 1 - avg_similarity
            return True, f"Diversity score: {diversity_score:.3f} (higher is more diverse)"
            
        except Exception as e:
            logger.error(f"Diversity test failed: {e}")
            return False, str(e)
    
    def run_all_tests(self):
        """Run all visual similarity tests"""
        logger.info("Starting Visual Similarity Search Tests")
        logger.info("=" * 60)
        
        # Check prerequisites
        logger.info(f"ChromaDB items: {self.chroma_client.collection.count()}")
        logger.info(f"Stored images: {self.image_storage.count()}")
        logger.info(f"CLIP available: {self.clip_available}")
        
        results = []
        
        # Run tests
        tests = [
            ("Image-to-Image Search", self.test_image_to_image_search),
            ("Text-to-Image Search", self.test_text_to_image_search),
            ("Visual Diversity", self.test_visual_diversity)
        ]
        
        for test_name, test_func in tests:
            success, message = test_func()
            results.append({
                "test": test_name,
                "success": success,
                "message": message
            })
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            logger.info(f"{status} - {result['test']}")
            logger.info(f"      {result['message']}")
        
        all_passed = all(r["success"] for r in results)
        logger.info(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '⚠️ SOME TESTS FAILED'}")
        
        return all_passed


def main():
    """Main test runner"""
    tester = VisualSimilarityTester()
    success = tester.run_all_tests()
    
    # Performance benchmark
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("PERFORMANCE BENCHMARK")
        logger.info("=" * 60)
        
        import time
        
        # Benchmark text search
        queries = ["peter england", "allen solly", "myntra", "thread"]
        times = []
        
        for query in queries:
            start = time.time()
            results, _ = tester.search_engine.search(query, n_results=5)
            elapsed = time.time() - start
            times.append(elapsed)
            logger.info(f"Query '{query}': {elapsed:.3f}s ({len(results)} results)")
        
        avg_time = np.mean(times)
        logger.info(f"\nAverage query time: {avg_time:.3f}s")
        
        if avg_time < 1.0:
            logger.info("✅ Excellent performance (<1s)")
        elif avg_time < 2.0:
            logger.info("✅ Good performance (<2s)")
        elif avg_time < 3.0:
            logger.info("⚠️ Acceptable performance (<3s)")
        else:
            logger.info("❌ Poor performance (>3s)")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())