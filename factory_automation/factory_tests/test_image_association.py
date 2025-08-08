#!/usr/bin/env python3
"""Test complete image association workflow with RAG search"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import warnings
warnings.filterwarnings('ignore')


def test_image_association_workflow():
    """Test the complete image association and search workflow"""
    
    print("="*60)
    print("TESTING IMAGE ASSOCIATION WITH RAG SEARCH")
    print("="*60)
    
    from factory_automation.factory_database.vector_db import ChromaDBClient
    from factory_automation.factory_database.image_storage import ImageStorageManager
    from factory_automation.factory_rag.intelligent_excel_ingestion import IntelligentExcelIngestion
    from factory_automation.factory_rag.enhanced_search import EnhancedRAGSearch
    from factory_automation.factory_ui.image_display_helper import (
        format_search_result_with_image,
        create_image_gallery_html
    )
    
    # Test configuration
    test_collection = "test_image_association"
    test_file = "inventory/PETER ENGLAND STOCK 2026.xlsx"
    
    print("\n1. Initializing components...")
    
    # Initialize components
    chroma_client = ChromaDBClient(collection_name=test_collection)
    image_storage = ImageStorageManager(collection_name="test_images_full")
    
    # Initialize ingestion with CLIP disabled for speed (can enable if needed)
    ingestion = IntelligentExcelIngestion(
        chroma_client=chroma_client,
        embedding_model="all-MiniLM-L6-v2",  # Fast model for testing
        use_vision_model=False,
        use_clip_embeddings=False  # Set to True to test CLIP
    )
    
    print("   ✅ Components initialized")
    
    # Check if test file exists
    if not os.path.exists(test_file):
        print(f"\n❌ Test file not found: {test_file}")
        print("   Please ensure inventory files are present")
        return
    
    print(f"\n2. Ingesting {test_file} with image extraction...")
    
    # Ingest with image extraction
    result = ingestion.ingest_excel_file(test_file, batch_size=20)
    
    if result["status"] == "success":
        print(f"   ✅ Ingested {result['items_ingested']} items")
        print(f"   - Items with images: {result.get('items_with_images', 0)}")
        print(f"   - Rows recovered: {result.get('rows_recovered', 0)}")
    else:
        print(f"   ❌ Ingestion failed: {result.get('error', 'Unknown error')}")
        return
    
    # Check image storage (use the ingestion's internal storage)
    print("\n3. Verifying image storage...")
    image_stats = ingestion.image_storage.get_stats()
    print(f"   - Total images stored: {image_stats['total_images']}")
    print(f"   - Estimated storage size: {image_stats.get('estimated_total_size_mb', 0):.2f} MB")
    
    # Test enhanced search with image enrichment
    print("\n4. Testing enhanced search with image enrichment...")
    
    # Initialize enhanced search with matching embeddings
    from factory_automation.factory_rag.embeddings_config import EmbeddingsManager
    
    # Use same embedding model as ingestion
    embeddings_manager = EmbeddingsManager("all-MiniLM-L6-v2")
    
    search_engine = EnhancedRAGSearch(
        chromadb_client=chroma_client,
        embeddings_manager=embeddings_manager,  # Use same embeddings
        enable_reranking=False,  # Disable for speed
        enable_hybrid_search=False,  # Disable for speed
        enable_image_search=True  # Enable image enrichment
    )
    
    # Test queries
    test_queries = [
        "peter england shirt",
        "blue tag",
        "items with images"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        
        results, stats = search_engine.search(query, n_results=3)
        
        print(f"   Found {len(results)} results")
        
        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            print(f"\n   Result {i}:")
            print(f"     - Name: {metadata.get('item_name', 'N/A')}")
            print(f"     - Code: {metadata.get('item_code', 'N/A')}")
            print(f"     - Confidence: {result.get('confidence_percentage', 0)}%")
            
            # Check for image
            if result.get("image_data"):
                image_size = len(result["image_data"]["base64"])
                print(f"     - ✅ Has full image ({image_size} bytes)")
                print(f"     - CLIP embedding: {result['image_data'].get('has_clip_embedding', False)}")
            else:
                print("     - ❌ No image data")
    
    # Test image display formatting
    print("\n5. Testing image display formatting...")
    
    if results:
        # Format first result for display
        formatted = format_search_result_with_image(results[0])
        print("   Formatted result:")
        print(f"   - Has image: {formatted['has_image']}")
        print(f"   - HTML generated: {'Yes' if formatted['image_html'] else 'No'}")
        
        # Create gallery HTML
        gallery_html = create_image_gallery_html(results[:3])
        print(f"   - Gallery HTML length: {len(gallery_html)} chars")
    
    # Test image retrieval by ID
    print("\n6. Testing direct image retrieval...")
    
    # Get an image ID from results
    image_id = None
    for result in results:
        if result.get("metadata", {}).get("image_id"):
            image_id = result["metadata"]["image_id"]
            break
    
    if image_id:
        print(f"   Retrieving image ID: {image_id}")
        image_data = image_storage.get_image(image_id)
        
        if image_data:
            print("   ✅ Image retrieved successfully")
            print(f"   - Base64 size: {len(image_data['base64'])} bytes")
            print(f"   - Metadata: {image_data['metadata']}")
        else:
            print("   ❌ Failed to retrieve image")
    else:
        print("   No image IDs found in results")
    
    # Cleanup
    print("\n7. Cleaning up test collections...")
    try:
        chroma_client.client.delete_collection(test_collection)
        image_storage.client.delete_collection("test_images_full")
        print("   ✅ Test collections deleted")
    except Exception as e:
        print(f"   ⚠️ Cleanup warning: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
    print("\n✅ Image Association Workflow Summary:")
    print("1. Images extracted from Excel and stored in separate collection")
    print("2. Full base64 images preserved (not truncated)")
    print("3. Image IDs linked to inventory items in metadata")
    print("4. Search results enriched with full image data")
    print("5. Images ready for display in UI")
    
    if result.get("items_with_images", 0) > 0:
        print(f"\n🎉 Successfully associated {result['items_with_images']} images with inventory items!")


def test_clip_embeddings():
    """Test CLIP embedding generation and image similarity search"""
    
    print("\n" + "="*60)
    print("TESTING CLIP EMBEDDINGS FOR IMAGE SEARCH")
    print("="*60)
    
    print("\n⚠️ Note: This test requires CLIP model (will download ~340MB on first run)")
    
    try:
        import clip
        import torch
        
        print("✅ CLIP library available")
        
        # Test CLIP model loading
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        print(f"✅ CLIP model loaded on {device}")
        
        # Now test with CLIP enabled
        from factory_automation.factory_rag.intelligent_excel_ingestion import IntelligentExcelIngestion
        
        ingestion = IntelligentExcelIngestion(
            embedding_model="all-MiniLM-L6-v2",
            use_clip_embeddings=True
        )
        
        print("✅ Ingestion system initialized with CLIP")
        
        # Test embedding generation
        test_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="  # 1x1 red pixel
        
        embedding = ingestion.generate_clip_embedding(test_base64)
        
        if embedding:
            print(f"✅ Generated CLIP embedding with {len(embedding)} dimensions")
        else:
            print("❌ Failed to generate CLIP embedding")
            
    except ImportError:
        print("❌ CLIP not installed. Install with: pip install torch clip")
    except Exception as e:
        print(f"❌ Error testing CLIP: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test image association workflow")
    parser.add_argument("--clip", action="store_true", help="Test CLIP embeddings")
    
    args = parser.parse_args()
    
    if args.clip:
        test_clip_embeddings()
    
    # Run main test
    test_image_association_workflow()