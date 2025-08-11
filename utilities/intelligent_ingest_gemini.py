#!/usr/bin/env python3
"""Intelligent Excel ingestion with automatic header detection and Gemini embeddings"""

import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.intelligent_excel_ingestion import (
    IntelligentExcelIngestion,
)


def main():
    print("🧠 Intelligent Excel Ingestion with Gemini Embeddings")
    print("=" * 60)

    # Check for API key
    import os

    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: Google API key not found!")
        print("   Please set GOOGLE_API_KEY or GEMINI_API_KEY in your .env file")
        return

    print("✨ Features:")
    print("   • Automatic header detection")
    print("   • Intelligent column mapping")
    print("   • Handles any Excel format")
    print("   • Learns patterns across files")
    print("   • Gemini embeddings for best accuracy")
    print()

    # Clean ChromaDB
    chroma_path = Path("./chroma_data")
    if chroma_path.exists():
        print("🗑️  Cleaning existing ChromaDB data...")
        shutil.rmtree(chroma_path)

    # Initialize ChromaDB with Gemini collection
    print("📊 Initializing ChromaDB with Gemini collection...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_gemini_smart")

    # Initialize intelligent ingestion
    print("🤖 Initializing intelligent ingestion system...")
    try:
        ingestion = IntelligentExcelIngestion(
            chroma_client=chroma_client, embedding_model="gemini"
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Ingest all Excel files
    inventory_folder = Path("inventory")
    if not inventory_folder.exists():
        print(f"❌ Error: {inventory_folder} folder not found!")
        return

    print(f"\n📂 Processing Excel files from {inventory_folder}...")
    print("-" * 60)

    results = ingestion.ingest_folder(str(inventory_folder))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Ingestion Summary")
    print("=" * 60)

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]
    total_items = sum(r.get("items_ingested", 0) for r in successful)

    print(f"\n✅ Successful files: {len(successful)}")
    for result in successful:
        print(f"   • {Path(result['file']).name}")
        print(f"     - Items: {result['items_ingested']}")
        print(f"     - Brand: {result['brand']}")
        print(f"     - Columns: {', '.join(result['column_mapping'].values())}")

    if failed:
        print(f"\n❌ Failed files: {len(failed)}")
        for result in failed:
            print(f"   • {Path(result['file']).name}: {result['error']}")

    print(f"\n📈 Total items ingested: {total_items}")

    # Show learned patterns
    print("\n🧠 Learned Column Patterns:")
    patterns = ingestion.get_learned_mappings()
    for col_type, patterns_list in patterns.items():
        if patterns_list:
            print(f"   {col_type}: {', '.join(patterns_list[:5])}")

    # Collection info
    collection = chroma_client.collection
    print(
        f"\n🗄️  ChromaDB collection '{collection.name}' has {collection.count()} items"
    )
    print("\n✅ Intelligent ingestion complete!")

    # Update instructions
    print("\n💡 To use this in production:")
    print("   1. Update factory_database/vector_db.py")
    print("      Change: collection_name='tag_inventory_stella'")
    print("      To:     collection_name='tag_inventory_gemini_smart'")
    print()
    print("   2. The system will now handle ANY Excel format automatically!")


if __name__ == "__main__":
    main()
