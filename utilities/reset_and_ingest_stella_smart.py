#!/usr/bin/env python3
"""Reset ChromaDB and ingest with intelligent Excel processing using Stella embeddings."""

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
    print("🧠 Intelligent Excel Ingestion with Stella Embeddings")
    print("=" * 60)

    print("✨ Features:")
    print("   • Automatic header detection")
    print("   • Intelligent column mapping")
    print("   • Handles any Excel format")
    print("   • Learns patterns across files")
    print("   • Fast Stella embeddings (1024 dimensions)")
    print()

    # Clean ChromaDB
    chroma_path = Path("./chroma_data")
    if chroma_path.exists():
        print("🗑️  Cleaning existing ChromaDB data...")
        shutil.rmtree(chroma_path)

    # Initialize ChromaDB with intelligent collection
    print("📊 Initializing ChromaDB with intelligent collection...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella_smart")

    # Initialize intelligent ingestion with Stella for speed
    print("🤖 Initializing intelligent ingestion system with Stella...")
    ingestion = IntelligentExcelIngestion(
        chroma_client=chroma_client, embedding_model="stella-400m"
    )

    # Ingest all Excel files (skip temporary files)
    inventory_folder = Path("inventory")
    if not inventory_folder.exists():
        print(f"❌ Error: {inventory_folder} folder not found!")
        return

    print(f"\n📂 Processing Excel files from {inventory_folder}...")
    print("-" * 60)

    # Get all Excel files, excluding temporary files
    excel_files = []
    for pattern in ["*.xlsx", "*.xls"]:
        for file in inventory_folder.glob(pattern):
            # Skip temporary files (start with ~$)
            if not file.name.startswith("~$"):
                excel_files.append(file)

    excel_files = sorted(excel_files)
    print(f"Found {len(excel_files)} Excel files to process")

    # Process each file
    results = []
    for file_path in excel_files:
        result = ingestion.ingest_excel_file(str(file_path))
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Ingestion Summary")
    print("=" * 60)

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]
    total_items = sum(r.get("items_ingested", 0) for r in successful)

    print(f"\n✅ Successful files: {len(successful)}/{len(excel_files)}")
    for result in successful:
        print(f"   • {Path(result['file']).name}")
        print(f"     - Items: {result['items_ingested']}")
        print(f"     - Brand: {result['brand']}")

    if failed:
        print(f"\n❌ Failed files: {len(failed)}")
        for result in failed:
            print(f"   • {Path(result['file']).name}: {result['error'][:50]}...")

    print(f"\n📈 Total items ingested: {total_items}")

    # Show learned patterns
    print("\n🧠 Learned Column Patterns:")
    patterns = ingestion.get_learned_mappings()
    for col_type, patterns_list in patterns.items():
        if patterns_list:
            unique_patterns = list(set(patterns_list))[:5]
            print(f"   {col_type}: {', '.join(unique_patterns)}")

    # Collection info
    collection = chroma_client.collection
    print(
        f"\n🗄️  ChromaDB collection '{collection.name}' has {collection.count()} items"
    )
    print("\n✅ Intelligent ingestion complete with Stella embeddings!")

    # Test search
    print("\n🔍 Testing search functionality...")
    from factory_automation.factory_rag.embeddings_config import EmbeddingsManager

    embeddings = EmbeddingsManager("stella-400m", device="cpu")

    test_queries = [
        "Peter England blue tag",
        "Allen Solly cotton tag",
        "thread with quantity available",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")

        # Generate query embedding
        query_embedding = embeddings.encode_queries([query])[0]

        # Search
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )

        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(min(3, len(results["ids"][0]))):
                metadata = results["metadatas"][0][i]
                score = 1 - results["distances"][0][i]
                print(
                    f"   • {metadata.get('item_name', 'N/A')} (Brand: {metadata.get('brand', 'N/A')}, Score: {score:.3f})"
                )
        else:
            print("   No results found")

    print("\n" + "=" * 60)
    print("🎉 System ready with intelligent ingestion!")
    print("=" * 60)


if __name__ == "__main__":
    main()
