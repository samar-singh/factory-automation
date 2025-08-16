"""Visual similarity search using CLIP embeddings for image-to-image matching"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import clip
import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)


class VisualSimilaritySearch:
    """Search for visually similar images using CLIP embeddings"""

    def __init__(self, chromadb_client):
        """Initialize visual search with CLIP model"""
        self.chromadb_client = chromadb_client

        # Load CLIP model
        logger.info("Loading CLIP model for visual similarity search...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        logger.info(f"CLIP model loaded on {self.device}")

        # Collection names for different embedding types
        # Now we have a dedicated CLIP collection with 512-dim embeddings
        self.inventory_collection = "tag_inventory_clip"  # CLIP embeddings (512 dim)
        self.customer_collection = "tag_images_full"  # Customer uploaded images

    def extract_image_embedding(self, image_path: str) -> Optional[List[float]]:
        """Extract CLIP embedding from an image file

        Args:
            image_path: Path to the image file

        Returns:
            CLIP embedding as list of floats, or None if error
        """
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

            # Extract features
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                # Normalize the features
                image_features = image_features / image_features.norm(
                    dim=-1, keepdim=True
                )

            # Convert to list for ChromaDB
            embedding = image_features.cpu().numpy().flatten().tolist()

            logger.debug(
                f"Extracted CLIP embedding of dimension {len(embedding)} from {image_path}"
            )
            return embedding

        except Exception as e:
            logger.error(f"Failed to extract embedding from {image_path}: {e}")
            return None

    async def search_similar_inventory_images(
        self, query_image_path: str, limit: int = 10, min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for similar images in inventory using CLIP embeddings

        Args:
            query_image_path: Path to the query image
            limit: Maximum number of results to return
            min_similarity: Minimum similarity score (0-1)

        Returns:
            List of similar images with metadata and similarity scores
        """
        try:
            # Extract embedding from query image
            query_embedding = self.extract_image_embedding(query_image_path)
            if not query_embedding:
                logger.error(f"Could not extract embedding from {query_image_path}")
                return []

            # Search in inventory collection using embedding
            collection = self.chromadb_client.client.get_collection(
                self.inventory_collection
            )

            # Query by embedding (not text!)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=["metadatas", "distances", "documents"],
            )

            # Process results
            similar_images = []
            if results["ids"][0]:
                for i, item_id in enumerate(results["ids"][0]):
                    # Convert distance to similarity (1 - distance for cosine)
                    similarity = 1 - results["distances"][0][i]

                    if similarity >= min_similarity:
                        metadata = results["metadatas"][0][i]

                        similar_images.append(
                            {
                                "item_id": item_id,
                                "similarity_score": similarity,
                                "tag_code": metadata.get("tag_code", "Unknown"),
                                "brand": metadata.get("brand", "Unknown"),
                                "tag_type": metadata.get("tag_type", "Unknown"),
                                "image_path": metadata.get("image_path", ""),
                                "metadata": metadata,
                                "distance": results["distances"][0][i],
                            }
                        )

                # Sort by similarity score
                similar_images.sort(key=lambda x: x["similarity_score"], reverse=True)

                logger.info(f"Found {len(similar_images)} similar images in inventory")
                for match in similar_images[:3]:  # Log top 3
                    logger.info(
                        f"  - {match['tag_code']}: {match['similarity_score']:.3f} similarity"
                    )

            return similar_images

        except Exception as e:
            logger.error(f"Error in visual similarity search: {e}")
            return []

    async def compare_images(self, image_path1: str, image_path2: str) -> float:
        """Compare two images directly using CLIP embeddings

        Args:
            image_path1: Path to first image
            image_path2: Path to second image

        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Extract embeddings for both images
            emb1 = self.extract_image_embedding(image_path1)
            emb2 = self.extract_image_embedding(image_path2)

            if not emb1 or not emb2:
                return 0.0

            # Calculate cosine similarity
            emb1_np = np.array(emb1)
            emb2_np = np.array(emb2)

            similarity = np.dot(emb1_np, emb2_np) / (
                np.linalg.norm(emb1_np) * np.linalg.norm(emb2_np)
            )

            return float(similarity)

        except Exception as e:
            logger.error(f"Error comparing images: {e}")
            return 0.0

    async def find_best_matches_for_order(
        self,
        customer_image_paths: List[str],
        order_items: List[Any],
        limit_per_item: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Find best visual matches for all items in an order

        Args:
            customer_image_paths: List of paths to customer's images
            order_items: List of order items to match
            limit_per_item: Max matches per item

        Returns:
            Dictionary mapping item IDs to their visual matches
        """
        item_matches = {}

        for image_path in customer_image_paths:
            logger.info(f"Searching inventory for image: {Path(image_path).name}")

            # Search for similar images in inventory
            matches = await self.search_similar_inventory_images(
                image_path,
                limit=limit_per_item * len(order_items),  # Get more to distribute
            )

            # Group matches by relevance to order items
            for item in order_items:
                item_id = item.item_id
                if item_id not in item_matches:
                    item_matches[item_id] = []

                # Filter matches relevant to this item (by brand, tag type, etc.)
                for match in matches:
                    # Check if match is relevant to this item
                    brand_match = (
                        item.brand.lower() in match["brand"].lower()
                        or match["brand"].lower() in item.brand.lower()
                        or item.brand == "Unknown"
                    )

                    if brand_match:
                        # Check if this match (by tag_code) is already in the list
                        # to avoid duplicates from multiple customer images
                        tag_code = match.get("tag_code", "")
                        already_exists = any(
                            existing.get("tag_code") == tag_code
                            for existing in item_matches[item_id]
                        )

                        if not already_exists:
                            # Add image source info
                            match["source_image"] = Path(image_path).name
                            item_matches[item_id].append(match)
                        else:
                            # Update existing match if this one has better similarity
                            for i, existing in enumerate(item_matches[item_id]):
                                if existing.get("tag_code") == tag_code:
                                    if match.get("similarity_score", 0) > existing.get(
                                        "similarity_score", 0
                                    ):
                                        match["source_image"] = Path(image_path).name
                                        item_matches[item_id][i] = match
                                    break

        # Sort and limit matches per item
        for item_id in item_matches:
            # Sort by similarity score
            item_matches[item_id].sort(
                key=lambda x: x["similarity_score"], reverse=True
            )
            # Keep only top matches
            item_matches[item_id] = item_matches[item_id][:limit_per_item]

        return item_matches
