#!/usr/bin/env python3
"""Test ChromaDB setup and create collections."""

import sys
sys.path.append('./factory_automation')

from factory_automation.factory_rag.chromadb_client import ChromaDBClient

def test_chromadb():
    print("Testing ChromaDB setup...")
    
    # Initialize client
    client = ChromaDBClient()
    print("✓ ChromaDB client initialized")
    
    # Create a test collection
    collection = client.create_collection("test_inventory")
    print("✓ Created test collection")
    
    # Add a test document
    client.add_documents(
        collection_name="test_inventory",
        documents=["This is a test tag: Blue cotton tag, 2x3 inches"],
        metadatas=[{"type": "tag", "color": "blue", "material": "cotton"}],
        ids=["test_1"]
    )
    print("✓ Added test document")
    
    # Query the collection
    results = client.query_collection(
        collection_name="test_inventory",
        query_texts=["blue tag"],
        n_results=1
    )
    print("✓ Query successful")
    print(f"  Found: {results['documents'][0] if results['documents'] else 'No results'}")
    
    # List collections
    collections = client.list_collections()
    print(f"✓ Collections: {[c.name for c in collections]}")
    
    print("\nChromaDB is fully functional!")

if __name__ == "__main__":
    test_chromadb()