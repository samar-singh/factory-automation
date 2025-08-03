#!/usr/bin/env python3
"""Test search with Stella-400M embeddings by creating a temporary collection"""

import sys

sys.path.append(".")

import chromadb
from chromadb.config import Settings

from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion
from factory_automation.factory_rag.excel_ingestion import (
    ExcelInventoryIngestion as OriginalIngestion,
)

print("=" * 80)
print("TESTING STELLA-400M EMBEDDINGS")
print("=" * 80)

# Create a temporary ChromaDB client with a new collection
print("\n1. Creating temporary collection for Stella test...")
client = chromadb.PersistentClient(
    path="./chroma_stella_test",
    settings=Settings(anonymized_telemetry=False, allow_reset=True),
)

# Create collection with 1024 dimensions for Stella
collection = client.get_or_create_collection(
    name="inventory_stella_test", metadata={"hnsw:space": "cosine"}
)


# Mock ChromaDBClient to use our collection
class MockChromaClient:
    def __init__(self, collection):
        self.collection = collection
        self.persist_directory = "./chroma_stella_test"


mock_client = MockChromaClient(collection)

# Initialize with Stella embeddings
print("\n2. Initializing Stella-400M embeddings...")
ingestion = ExcelInventoryIngestion(
    chroma_client=mock_client, embedding_model="stella-400m"
)

# Add some test data directly
print("\n3. Adding test inventory items...")
test_items = [
    {
        "brand": "SYMBOL",
        "trim_name": "Symbol Everyday Classics Formal Main Tag (black)",
        "stock": 5300,
        "excel_source": "TEST_DATA.xlsx",
    },
    {
        "brand": "SYMBOL",
        "trim_name": "Symbol Hand Tag Premium",
        "stock": 2500,
        "excel_source": "TEST_DATA.xlsx",
    },
    {
        "brand": "ALLEN SOLLY",
        "trim_name": "Allen Solly Main Tag Work Casual",
        "stock": 1100,
        "excel_source": "TEST_DATA.xlsx",
    },
    {
        "brand": "NETPLAY",
        "trim_name": "Blue Cotton Stretch Fabric Tag",
        "stock": 10800,
        "excel_source": "TEST_DATA.xlsx",
    },
]

# Add items to collection
for i, item in enumerate(test_items):
    item_id = f"test_{i}"
    text = f"Brand: {item['brand']} | Product: {item['trim_name']} | Stock: {item['stock']} units"

    # Generate embedding
    embedding = ingestion.embeddings_manager.encode_queries([text])[0]

    # Add to collection
    collection.add(
        ids=[item_id],
        embeddings=[embedding.tolist()],
        documents=[text],
        metadatas=[item],
    )

print(f"Added {len(test_items)} test items")

# Test searches
print("\n4. Testing searches with Stella embeddings...")
print("-" * 50)

test_queries = [
    "SYMBOL tag",
    "hand tag of SYMBOL",
    "SYMBOL hand tag",
    "Allen Solly tag",
    "blue cotton tag",
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    results = ingestion.search_inventory(query=query, limit=3)

    if results:
        for j, match in enumerate(results, 1):
            metadata = match.get("metadata", {})
            score = match.get("score", 0)

            # Determine confidence level
            if score > 0.8:
                confidence = "HIGH ✅"
            elif score > 0.6:
                confidence = "MEDIUM ⚠️"
            else:
                confidence = "LOW ❌"

            print(f"  {j}. {metadata.get('brand')} - {metadata.get('trim_name')}")
            print(
                f"     Score: {score:.3f} ({confidence}) | Stock: {metadata.get('stock')}"
            )

# Compare with all-MiniLM
print("\n\n5. Comparison with all-MiniLM-L6-v2...")
print("-" * 50)

original_ingestion = OriginalIngestion(embedding_model="all-MiniLM-L6-v2")

print("\nOriginal embeddings (all-MiniLM-L6-v2) for 'SYMBOL tag':")
results = original_ingestion.search_inventory(query="SYMBOL tag", limit=3)
if results:
    for match in results[:3]:
        metadata = match.get("metadata", {})
        print(
            f"  {metadata.get('brand')} - {metadata.get('trim_name')} (Score: {match.get('score', 0):.3f})"
        )

print("\n" + "=" * 80)
print("STELLA EMBEDDING TEST COMPLETE")
print("=" * 80)
