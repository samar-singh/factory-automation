#!/usr/bin/env python3
"""Direct test of RAG search with typical order items"""

import sys

sys.path.append(".")

from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

print("=" * 80)
print("TESTING RAG SEARCH FUNCTIONALITY")
print("=" * 80)

# Initialize with correct embedding model
ingestion = ExcelInventoryIngestion(embedding_model="all-MiniLM-L6-v2")

# Test queries based on the email example
test_queries = [
    "hand tag of SYMBOL",
    "SYMBOL hand tag",
    "SYMBOL tag",
    "hand tag",
    "blue cotton tag",
    "Allen Solly tag",
    "Peter England label",
]

print("\nRunning searches...")
print("-" * 50)

for query in test_queries:
    print(f"\nQuery: '{query}'")
    results = ingestion.search_inventory(query=query, limit=3)

    if results:
        print(f"Found {len(results)} matches:")
        for i, match in enumerate(results, 1):
            metadata = match.get("metadata", {})
            score = match.get("score", 0)

            # Determine confidence level
            if score > 0.8:
                confidence = "HIGH"
            elif score > 0.6:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

            print(
                f"  {i}. {metadata.get('brand', 'Unknown')} - {metadata.get('trim_name', 'Unknown')}"
            )
            print(
                f"     Stock: {metadata.get('stock', 0)} | Score: {score:.3f} ({confidence})"
            )
            print(f"     Source: {metadata.get('excel_source', 'Unknown')}")
    else:
        print("  No matches found")

print("\n" + "=" * 80)
print("SEARCH TEST COMPLETE")
print("=" * 80)
