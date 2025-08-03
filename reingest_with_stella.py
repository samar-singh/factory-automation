#!/usr/bin/env python3
"""Re-ingest inventory data using Stella-400M embeddings for better accuracy"""

import os
import sys

sys.path.append(".")

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

print("=" * 80)
print("RE-INGESTING INVENTORY WITH STELLA-400M EMBEDDINGS")
print("=" * 80)

# Create a new collection for stella embeddings
print("\n1. Creating new ChromaDB collection for Stella embeddings...")
chroma_client = ChromaDBClient(collection_name="inventory_stella")
print(f"Collection created: {chroma_client.collection.name}")

# Initialize ingestion with stella-400m
print("\n2. Initializing Stella-400M embeddings...")
ingestion = ExcelInventoryIngestion(
    chroma_client=chroma_client, embedding_model="stella-400m"
)

# Find Excel files to ingest
excel_dir = "inventory_excel_files"
if os.path.exists(excel_dir):
    excel_files = [f for f in os.listdir(excel_dir) if f.endswith(".xlsx")]
    print(f"\n3. Found {len(excel_files)} Excel files to ingest")

    # Ingest each file
    total_items = 0
    for i, file in enumerate(excel_files, 1):
        file_path = os.path.join(excel_dir, file)
        print(f"\n   [{i}/{len(excel_files)}] Ingesting {file}...")
        try:
            result = ingestion.ingest_excel_file(file_path)
            items_count = result.get("items_ingested", 0)
            total_items += items_count
            print(f"        ✓ Ingested {items_count} items")
        except Exception as e:
            print(f"        ✗ Error: {e}")

    print(f"\n4. Total items ingested: {total_items}")

    # Test search with stella embeddings
    print("\n5. Testing search with Stella embeddings...")
    test_queries = [
        "SYMBOL tag",
        "hand tag of SYMBOL",
        "Allen Solly tag",
        "blue cotton tag",
    ]

    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = ingestion.search_inventory(query=query, limit=3)
        if results:
            for j, match in enumerate(results, 1):
                metadata = match.get("metadata", {})
                score = match.get("score", 0)
                print(
                    f"   {j}. {metadata.get('brand')} - {metadata.get('trim_name')} (Score: {score:.3f})"
                )
else:
    print(f"\nError: Directory '{excel_dir}' not found!")
    print("Please ensure inventory Excel files are in the correct location.")

print("\n" + "=" * 80)
print("RE-INGESTION COMPLETE")
print("=" * 80)
