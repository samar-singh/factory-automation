#!/usr/bin/env python3
"""Reset ChromaDB and ingest with Google Gemini embeddings for superior accuracy."""

import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run ingestion
from factory_automation.factory_database.vector_db import ChromaDBClient  # noqa: E402
from factory_automation.factory_rag.excel_ingestion import (  # noqa: E402
    ExcelInventoryIngestion,
)


def main():
    print("🚀 Resetting ChromaDB and ingesting with Google Gemini embeddings...")
    print("=" * 60)

    # Check for API key
    import os

    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: Google API key not found!")
        print("   Please set GOOGLE_API_KEY or GEMINI_API_KEY in your .env file")
        print("   Get your API key from: https://makersuite.google.com/app/apikey")
        return

    # Delete existing ChromaDB data
    chroma_path = Path("./chroma_data")
    if chroma_path.exists():
        print(f"🗑️  Removing existing ChromaDB data at {chroma_path}")
        shutil.rmtree(chroma_path)

    # Initialize ChromaDB fresh with a collection for Gemini
    # We'll use a specific collection name for Gemini embeddings
    chroma_client = ChromaDBClient(collection_name="tag_inventory_gemini")

    # Use Gemini embeddings (768 dimensions, superior multilingual support)
    print("✨ Using Google Gemini embeddings (768 dimensions)")
    print("   • Better multilingual support")
    print("   • Improved semantic understanding")
    print("   • Longer context window (2048 tokens)")

    try:
        ingestion = ExcelInventoryIngestion(
            chroma_client=chroma_client, embedding_model="gemini"
        )
    except Exception as e:
        print(f"❌ Error initializing Gemini embeddings: {e}")
        return

    # Ingest all Excel files
    inventory_folder = Path("inventory")
    if not inventory_folder.exists():
        print(f"❌ Error: {inventory_folder} folder not found!")
        return

    print(f"\n📂 Ingesting from {inventory_folder}...")
    results = ingestion.ingest_inventory_folder(str(inventory_folder))

    # Summary
    total_ingested = sum(
        r.get("items_ingested", 0) for r in results if r["status"] == "success"
    )
    failed_files = [r["file"] for r in results if r["status"] == "error"]

    print("\n" + "=" * 60)
    print("✅ Ingestion Complete with Gemini Embeddings!")
    print(f"📊 Total items ingested: {total_ingested}")
    print(
        f"✅ Successful files: {len([r for r in results if r['status'] == 'success'])}"
    )
    print(f"❌ Failed files: {len(failed_files)}")

    if failed_files:
        print("\n⚠️  Failed files:")
        for f in failed_files:
            print(f"  - {f}")

    # Show collection info
    collection = chroma_client.collection
    print(
        f"\n🗄️  ChromaDB collection '{collection.name}' now has {collection.count()} items"
    )
    print("   • Embedding model: Google Gemini (text-embedding-004)")
    print("   • Dimensions: 768")
    print("\n🎯 Ready to use with improved accuracy!")

    # Update the vector_db.py default collection to use Gemini
    print("\n💡 To use Gemini embeddings by default, update:")
    print("   factory_automation/factory_database/vector_db.py")
    print("   Change: collection_name='tag_inventory_stella'")
    print("   To:     collection_name='tag_inventory_gemini'")


if __name__ == "__main__":
    main()
