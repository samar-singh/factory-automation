#!/usr/bin/env python3
"""Test the complete system with Stella embeddings"""

import sys

sys.path.append(".")

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

print("=" * 80)
print("TESTING COMPLETE SYSTEM WITH STELLA-400M")
print("=" * 80)

# Initialize with Stella collection
print("\n1. Connecting to Stella collection...")
chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
total_items = chroma_client.collection.count()
print(f"✓ Connected to ChromaDB (Stella): {total_items} items in inventory")

# Initialize ingestion with Stella
print("\n2. Initializing Stella embeddings...")
ingestion = ExcelInventoryIngestion(
    chroma_client=chroma_client, embedding_model="stella-400m"
)
print("✓ Stella embeddings initialized")

# Test the email example queries
print("\n3. Testing with email example queries...")
print("-" * 50)

test_scenarios = [
    {
        "query": "hand tag of SYMBOL",
        "expected": "Should find SYMBOL tags with good confidence",
    },
    {
        "query": "SYMBOL hand tag",
        "expected": "Should find same results (order shouldn't matter)",
    },
    {"query": "Allen Solly main tag", "expected": "Should find Allen Solly tags"},
    {"query": "blue cotton tag", "expected": "Should find blue/cotton material tags"},
]

for scenario in test_scenarios:
    query = scenario["query"]
    print(f"\nQuery: '{query}'")
    print(f"Expected: {scenario['expected']}")

    results = ingestion.search_inventory(query=query, limit=5)

    if results:
        print(f"Found {len(results)} matches:")
        for i, match in enumerate(results, 1):
            metadata = match.get("metadata", {})
            score = match.get("score", 0)
            stock = metadata.get("stock", 0)

            # Determine action based on confidence and stock
            if score > 0.8 and stock > 0:
                action = "✅ AUTO-APPROVE"
            elif score > 0.6 and stock > 0:
                action = "⚠️  MANUAL REVIEW"
            else:
                action = "❌ FIND ALTERNATIVE"

            print(f"  {i}. {metadata.get('brand')} - {metadata.get('trim_name')}")
            print(f"     Score: {score:.3f} | Stock: {stock} | Action: {action}")
    else:
        print("  No matches found")

# Compare with old collection
print("\n\n4. Comparison with old MiniLM collection...")
print("-" * 50)

old_client = ChromaDBClient(collection_name="tag_inventory")
old_ingestion = ExcelInventoryIngestion(
    chroma_client=old_client, embedding_model="all-MiniLM-L6-v2"
)

query = "SYMBOL hand tag"
print(f"\nQuery: '{query}'")

print("\nOld (MiniLM) results:")
old_results = old_ingestion.search_inventory(query=query, limit=3)
for i, match in enumerate(old_results, 1):
    metadata = match.get("metadata", {})
    print(
        f"  {i}. {metadata.get('brand')} - {metadata.get('trim_name')} (Score: {match.get('score', 0):.3f})"
    )

print("\nNew (Stella) results:")
new_results = ingestion.search_inventory(query=query, limit=3)
for i, match in enumerate(new_results, 1):
    metadata = match.get("metadata", {})
    print(
        f"  {i}. {metadata.get('brand')} - {metadata.get('trim_name')} (Score: {match.get('score', 0):.3f})"
    )

print("\n" + "=" * 80)
print("STELLA SYSTEM TEST COMPLETE")
print("\nThe Gradio app is now using Stella-400M embeddings!")
print("Run: python -m factory_automation.factory_ui.gradio_app_live")
print("=" * 80)
