#!/usr/bin/env python3
"""Debug script to test search_inventory and see actual return structure"""

import sys

sys.path.append(".")

from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

# Initialize the ingestion system with the default embedding model
print("Initializing Excel Inventory Ingestion...")
# Use all-MiniLM-L6-v2 which matches the existing collection
ingestion = ExcelInventoryIngestion(embedding_model="all-MiniLM-L6-v2")

# Test search with a sample query
test_query = "blue cotton tag"
print(f"\nSearching for: '{test_query}'")

# Call search_inventory and inspect the result
search_result = ingestion.search_inventory(query=test_query, limit=1)

print(f"\nResult type: {type(search_result)}")
print(
    f"Result length: {len(search_result) if isinstance(search_result, list) else 'N/A'}"
)
print("\nFull result structure:")
print(search_result)

if search_result and isinstance(search_result, list):
    print("\nFirst result details:")
    first_result = search_result[0]
    print(f"Keys in first result: {first_result.keys()}")
    print("\nFirst result content:")
    for key, value in first_result.items():
        print(f"  {key}: {value}")
