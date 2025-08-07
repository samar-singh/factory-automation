#!/usr/bin/env python3
"""Migrate inventory data to Stella-400M embeddings"""

import os
import sys
import time

sys.path.append(".")

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion


def main():
    print("=" * 80)
    print("MIGRATING TO STELLA-400M EMBEDDINGS")
    print("=" * 80)

    # Step 1: Create new collection for Stella
    print("\n1. Creating new ChromaDB collection for Stella embeddings...")
    stella_client = ChromaDBClient(collection_name="tag_inventory_stella")
    print(f"✓ Created collection: {stella_client.collection_name}")

    # Step 2: Initialize ingestion with Stella
    print("\n2. Initializing Stella-400M embeddings...")
    start_time = time.time()
    ingestion = ExcelInventoryIngestion(
        chroma_client=stella_client, embedding_model="stella-400m"
    )
    init_time = time.time() - start_time
    print(f"✓ Stella embeddings initialized in {init_time:.2f} seconds")

    # Step 3: Find all Excel files
    print("\n3. Looking for Excel inventory files...")
    excel_dir = "inventory"

    if not os.path.exists(excel_dir):
        print(f"❌ Error: Directory '{excel_dir}' not found!")
        print("Please ensure inventory Excel files are in the correct location.")
        return

    excel_files = sorted([f for f in os.listdir(excel_dir) if f.endswith(".xlsx")])
    print(f"✓ Found {len(excel_files)} Excel files to ingest")

    # Step 4: Ingest each file
    print("\n4. Ingesting Excel files with Stella embeddings...")
    print("-" * 50)

    total_items = 0
    failed_files = []

    for i, file in enumerate(excel_files, 1):
        file_path = os.path.join(excel_dir, file)
        print(f"\n[{i}/{len(excel_files)}] Processing {file}...")

        try:
            start_time = time.time()
            result = ingestion.ingest_excel_file(file_path)
            items_count = result.get("items_ingested", 0)
            total_items += items_count
            elapsed = time.time() - start_time

            print(f"    ✓ Ingested {items_count} items in {elapsed:.2f}s")
            print(f"    ✓ Skipped {result.get('items_skipped', 0)} duplicates")

        except Exception as e:
            print(f"    ❌ Error: {e}")
            failed_files.append(file)

    # Step 5: Summary
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"\n✓ Total items ingested: {total_items}")
    print(f"✓ Collection name: {stella_client.collection_name}")
    print("✓ Embedding model: stella-400m (1024 dimensions)")

    if failed_files:
        print(f"\n⚠️  Failed files ({len(failed_files)}):")
        for file in failed_files:
            print(f"   - {file}")

    # Step 6: Test the new collection
    print("\n6. Testing search with Stella embeddings...")
    print("-" * 50)

    test_queries = ["SYMBOL hand tag", "Allen Solly tag", "blue cotton tag"]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = ingestion.search_inventory(query=query, limit=3)

        if results:
            for j, match in enumerate(results, 1):
                metadata = match.get("metadata", {})
                score = match.get("score", 0)
                print(
                    f"  {j}. {metadata.get('brand')} - {metadata.get('trim_name')[:40]}..."
                )
                print(f"     Score: {score:.3f} | Stock: {metadata.get('stock')}")

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE!")
    print("\nNext steps:")
    print("1. Update gradio_app_live.py to use 'tag_inventory_stella' collection")
    print("2. Test the complete system")
    print("3. Once verified, you can delete the old collection")
    print("=" * 80)


if __name__ == "__main__":
    main()
