#!/usr/bin/env python3
"""Enable vision model for automatic tag name generation from images"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.intelligent_excel_ingestion import (
    IntelligentExcelIngestion,
)


def test_vision_model_connection():
    """Test if Together.ai API is configured and working"""
    import requests

    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ TOGETHER_API_KEY not found in environment")
        print("   Please add to .env file:")
        print("   TOGETHER_API_KEY=your-api-key-here")
        return False

    # Test API connection
    try:
        response = requests.get(
            "https://api.together.xyz/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
        )

        if response.status_code == 200:
            print("✅ Together.ai API connection successful")

            # Check if Qwen2.5VL model is available
            models = response.json()
            qwen_available = any(
                "Qwen2.5-VL" in model.get("name", "") for model in models
            )

            if qwen_available:
                print("✅ Qwen2.5VL-72B model available")
            else:
                print("⚠️ Qwen2.5VL model might not be available")

            return True
        else:
            print(f"❌ Together.ai API error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error connecting to Together.ai: {e}")
        return False


def run_vision_enhanced_ingestion():
    """Run ingestion with vision model enabled for tag name generation"""

    print("=" * 60)
    print("VISION-ENHANCED INTELLIGENT INGESTION")
    print("=" * 60)

    # Test API first
    if not test_vision_model_connection():
        print("\n⚠️ Vision model requires Together.ai API key")
        print("Proceeding with CLIP-only ingestion...")
        use_vision = False
    else:
        use_vision = True

    # Configuration
    collection_name = "tag_inventory_vision_enhanced"
    embedding_model = "stella-400m"

    print("\nConfiguration:")
    print(f"  Collection: {collection_name}")
    print(f"  Text Embeddings: {embedding_model}")
    print("  CLIP Embeddings: Enabled")
    print(f"  Vision Model: {'Enabled (Qwen2.5VL-72B)' if use_vision else 'Disabled'}")
    print(f"  Auto Tag Name Generation: {'Yes' if use_vision else 'No'}")

    # Initialize ChromaDB
    print("\n1. Initializing ChromaDB...")
    chroma_client = ChromaDBClient(collection_name=collection_name)

    # Clear existing if any
    try:
        chroma_client.client.delete_collection(collection_name)
        print("   Cleared existing collection")
    except:
        pass

    # Re-initialize
    chroma_client = ChromaDBClient(collection_name=collection_name)
    print(f"   Created new collection: {collection_name}")

    # Initialize ingestion with vision model
    print("\n2. Initializing vision-enhanced ingestion...")
    ingestion = IntelligentExcelIngestion(
        chroma_client=chroma_client,
        embedding_model=embedding_model,
        use_vision_model=use_vision,  # Enable vision model if API available
    )

    # Find test files with missing tag names
    test_files = [
        "inventory/PETER ENGLAND STOCK 2026.xlsx",  # Has rows with images but no tag names
        "inventory/OTHERS STOCK 2026.xlsx",  # Has many missing tag names
        "inventory/THREAD 2.xlsx",  # Has thread images without names
    ]

    print("\n3. Processing files with vision model...")

    total_generated = 0
    total_items = 0

    for file_path in test_files:
        if not Path(file_path).exists():
            print(f"\n   ⚠️ File not found: {file_path}")
            continue

        print(f"\n   Processing: {Path(file_path).name}")
        print("   " + "-" * 40)

        try:
            result = ingestion.ingest_excel_file(file_path)

            if result["status"] == "success":
                items = result["items_ingested"]
                generated = result.get("items_with_generated_names", 0)
                images = result.get("items_with_images", 0)
                recovered = result.get("rows_recovered", 0)

                total_items += items
                total_generated += generated

                print(f"   ✅ Ingested: {items} items")
                print(f"      Images found: {images}")
                print(
                    f"      Names generated: {generated} {'🤖' if generated > 0 else ''}"
                )
                print(f"      Rows recovered: {recovered}")

                # Show some generated names if any
                if generated > 0 and use_vision:
                    print("      Sample generated names:")
                    # Query for items with generated names
                    results = chroma_client.collection.query(
                        query_texts=["generated tag name"],
                        n_results=3,
                        where={"name_generated": True},
                    )

                    if results["metadatas"]:
                        for meta in results["metadatas"][0][:3]:
                            print(f"        - {meta.get('item_name', 'Unknown')}")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")

    # Summary
    print("\n" + "=" * 60)
    print("VISION INGESTION SUMMARY")
    print("=" * 60)

    print(f"\nTotal items ingested: {total_items}")
    print(f"Tag names generated: {total_generated}")

    if use_vision and total_generated > 0:
        print(f"Generation rate: {total_generated/total_items*100:.1f}%")
        print("\n✅ Vision model successfully generated tag names from images!")
    elif use_vision:
        print("\n⚠️ Vision model enabled but no names generated")
        print("   This might be due to:")
        print("   - Images already having tag names")
        print("   - Vision model not recognizing text in images")
    else:
        print("\n⚠️ Vision model disabled - no automatic tag name generation")

    # Test search with generated names
    if total_generated > 0:
        print("\n4. Testing search with generated names...")

        test_queries = ["generated tag", "vision processed item", "auto named product"]

        for query in test_queries:
            results = chroma_client.search(query, n_results=2)
            if results["documents"][0]:
                print(f"\n   Query: '{query}'")
                meta = results["metadatas"][0][0]
                print(f"   Found: {meta.get('item_name', 'Unknown')}")
                if meta.get("name_generated"):
                    print("   ✅ This name was auto-generated!")

    return total_generated > 0 if use_vision else True


def main():
    """Main entry point"""
    print("Vision Model Setup for Automatic Tag Name Generation")
    print("=" * 60)

    # Check environment
    print("\n1. Checking environment...")

    together_key = os.getenv("TOGETHER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    print(f"   OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Missing'}")
    print(f"   TOGETHER_API_KEY: {'✅ Set' if together_key else '❌ Missing'}")

    if not together_key:
        print("\n📝 To enable vision model, add to .env:")
        print("   TOGETHER_API_KEY=your-api-key-here")
        print("\n   Get your API key from: https://api.together.xyz/")
        print("   The Qwen2.5VL-72B model costs ~$0.90 per 1M tokens")
        print("\n   Proceeding without vision model...")

    # Run ingestion
    print("\n2. Starting vision-enhanced ingestion...")
    success = run_vision_enhanced_ingestion()

    if success:
        print("\n✅ Vision-enhanced ingestion complete!")
        if together_key:
            print("   Tag names were automatically generated from images")
        else:
            print("   Add Together.ai API key to enable automatic tag name generation")
    else:
        print("\n❌ Vision-enhanced ingestion failed")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
