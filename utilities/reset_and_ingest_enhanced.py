#!/usr/bin/env python3
"""Reset ChromaDB and ingest using enhanced intelligent ingestion with image extraction"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.intelligent_excel_ingestion import (
    IntelligentExcelIngestion,
)


def reset_and_ingest_enhanced():
    """Reset ChromaDB and ingest all Excel files using enhanced ingestion"""

    print("=" * 60)
    print("ENHANCED INTELLIGENT INGESTION WITH IMAGE EXTRACTION")
    print("=" * 60)

    # Use production settings from config
    collection_name = "tag_inventory_stella_smart"  # From config.yaml - main collection
    embedding_model = (
        "stella-400m"  # From config.yaml - primary model (1024 dims, better accuracy)
    )

    print("\nConfiguration:")
    print(f"  Collection: {collection_name}")
    print(f"  Embedding Model: {embedding_model}")
    print("  Image Extraction: Enabled")
    print("  Data Recovery: Enabled")

    # Reset ChromaDB
    print("\n1. Resetting ChromaDB...")
    try:
        chroma_client = ChromaDBClient(collection_name=collection_name)
        chroma_client.client.delete_collection(collection_name)
        print(f"   Deleted existing collection: {collection_name}")
    except:
        print("   No existing collection to delete")

    # Re-initialize with fresh collection
    chroma_client = ChromaDBClient(collection_name=collection_name)
    print(f"   Created new collection: {collection_name}")

    # Initialize enhanced ingestion system with config-based settings
    print("\n2. Initializing enhanced ingestion system...")

    # CLIP settings from config.yaml
    use_clip = True  # config.yaml: rag.use_clip_embeddings = true
    use_vision = (
        False  # config.yaml: rag.use_vision_model = false (requires Together.ai API)
    )

    print(f"  CLIP Embeddings: {'Enabled' if use_clip else 'Disabled'}")
    print(f"  Vision Model: {'Enabled' if use_vision else 'Disabled'}")

    ingestion = IntelligentExcelIngestion(
        chroma_client=chroma_client,
        embedding_model=embedding_model,
        use_vision_model=use_vision,  # From config - requires Together.ai for tag name generation
    )

    # Find all Excel files
    inventory_path = Path("inventory")
    excel_files = list(inventory_path.glob("*.xlsx"))
    excel_files = [
        f for f in excel_files if not f.name.startswith("~$")
    ]  # Skip temp files

    print(f"\n3. Found {len(excel_files)} Excel files to ingest")

    # Track overall statistics
    total_items = 0
    total_images = 0
    total_recovered = 0
    total_generated = 0
    successful_files = 0
    failed_files = []

    # Ingest each file
    for idx, file_path in enumerate(excel_files, 1):
        print(f"\n4.{idx} Processing: {file_path.name}")
        print("-" * 40)

        try:
            result = ingestion.ingest_excel_file(str(file_path))

            if result["status"] == "success":
                successful_files += 1
                items = result["items_ingested"]
                images = result.get("items_with_images", 0)
                recovered = result.get("rows_recovered", 0)
                generated = result.get("items_with_generated_names", 0)

                total_items += items
                total_images += images
                total_recovered += recovered
                total_generated += generated

                print(f"   ✅ Success: {items} items ingested")
                print(f"      - Items with images: {images}")
                print(f"      - Rows recovered: {recovered}")
                print(f"      - Names generated: {generated}")
                print(f"      - Column mapping: {result.get('column_mapping', {})}")
            else:
                failed_files.append(file_path.name)
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            failed_files.append(file_path.name)
            print(f"   ❌ Error: {str(e)[:100]}")

    # Print summary
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)

    print("\nFiles Processed:")
    print(f"  ✅ Successful: {successful_files}/{len(excel_files)}")
    if failed_files:
        print(f"  ❌ Failed: {', '.join(failed_files)}")

    print("\nItems Ingested:")
    print(f"  Total items: {total_items}")
    print(
        f"  Items with images: {total_images} ({total_images/total_items*100:.1f}%)"
        if total_items > 0
        else ""
    )
    print(
        f"  Rows recovered: {total_recovered} ({total_recovered/total_items*100:.1f}%)"
        if total_items > 0
        else ""
    )
    print(f"  Names generated: {total_generated}")

    print("\nCollection Info:")
    collection = chroma_client.collection
    print(f"  Name: {collection.name}")
    print(f"  Total documents: {collection.count()}")

    # Test search
    print("\n5. Testing search functionality...")
    test_queries = [
        "peter england blue shirt",
        "myntra tag",
        "allen solly",
        "items with images",
        "recovered items",
    ]

    for query in test_queries[:3]:
        results = chroma_client.search(query, n_results=2)
        print(f"\n   Query: '{query}'")
        if results["documents"][0]:
            print(f"   Found {len(results['documents'][0])} results")
            meta = results["metadatas"][0][0]
            print(
                f"   Top result: {meta.get('item_name', 'N/A')} ({meta.get('brand', 'N/A')})"
            )

    print("\n" + "=" * 60)
    print("ENHANCED INGESTION COMPLETE!")
    print("=" * 60)

    improvements = []
    if total_recovered > 0:
        improvements.append(
            f"🎉 Recovered {total_recovered} rows that would have been lost"
        )
    if total_images > 0:
        improvements.append(f"📷 Extracted {total_images} embedded images")
    if total_generated > 0:
        improvements.append(f"🤖 Generated {total_generated} tag names from images")

    if improvements:
        print("\nKey Improvements:")
        for improvement in improvements:
            print(f"  {improvement}")

    print("\nNext Steps:")
    print(
        "1. Install CLIP if not already: pip install git+https://github.com/openai/CLIP.git"
    )
    print(
        "2. Enable vision model (use_vision_model=True) to generate tag names from images"
    )
    print("3. Test the enhanced search with image-based queries")
    print("4. Integrate with the main factory automation pipeline")
    print("5. Monitor recovery rates and adjust thresholds as needed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Reset and ingest with enhanced ingestion"
    )
    parser.add_argument(
        "--collection",
        default="tag_inventory_stella_smart",
        help="Collection name (production default)",
    )
    parser.add_argument("--model", default="stella-400m", help="Embedding model")
    parser.add_argument("--vision", action="store_true", help="Enable vision model")

    args = parser.parse_args()

    if args.vision:
        print("Note: Vision model enabled - requires Together.ai API key")

    reset_and_ingest_enhanced()
