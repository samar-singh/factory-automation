#!/usr/bin/env python3
"""Test ChromaDB setup with direct chromadb usage."""

import chromadb
from chromadb.config import Settings


def test_chromadb():
    print("Testing ChromaDB setup...")

    # Create persistent client
    client = chromadb.PersistentClient(
        path="./chroma_data",
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )
    print("✓ ChromaDB client created")

    # Create or get a test collection
    collection = client.get_or_create_collection(
        name="test_inventory", metadata={"hnsw:space": "cosine"}
    )
    print("✓ Created/retrieved test collection")

    # Add a test document
    collection.add(
        documents=["Blue cotton tag, 2x3 inches, product code: BLU-CTN-23"],
        metadatas=[
            {"type": "tag", "color": "blue", "material": "cotton", "size": "2x3"}
        ],
        ids=["test_1"],
    )
    print("✓ Added test document")

    # Query the collection
    results = collection.query(query_texts=["blue cotton tag"], n_results=1)
    print("✓ Query successful")
    if results["documents"] and results["documents"][0]:
        print(f"  Found: {results['documents'][0][0]}")
        print(f"  Metadata: {results['metadatas'][0][0]}")

    # Check persistent directory
    import os

    if os.path.exists("./chroma_data"):
        print("✓ Persistent directory created at ./chroma_data")

    # List all collections
    collections = client.list_collections()
    print(f"✓ Total collections: {len(collections)}")
    for col in collections:
        print(f"  - {col.name}")

    print("\nChromaDB is fully functional!")


if __name__ == "__main__":
    test_chromadb()
