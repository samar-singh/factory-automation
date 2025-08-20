#!/usr/bin/env python3
"""Simple test of inventory search functionality"""

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.embeddings_config import EmbeddingsManager
import numpy as np

# Initialize components
print("Initializing components...")
chromadb_client = ChromaDBClient()
embeddings_manager = EmbeddingsManager(model_name="stella-400m")

# Check database
print(f"\nDatabase status:")
print(f"  Collection: {chromadb_client.collection_name}")
print(f"  Total items: {chromadb_client.count()}")

# Get sample items
sample = chromadb_client.collection.get(limit=3)
if sample and sample['documents']:
    print(f"\nSample items in database:")
    for i, (doc, id_) in enumerate(zip(sample['documents'], sample['ids'])):
        print(f"  {i+1}. ID: {id_}")
        print(f"     {doc[:100]}...")

# Test search
test_queries = [
    "Allen Solly tags",
    "TBALWBL0009N",
    "black woven tags",
    "Van Heusen"
]

print(f"\nTesting search with Stella embeddings:")
for query in test_queries:
    print(f"\n  Query: '{query}'")
    try:
        # Generate embedding
        embeddings = embeddings_manager.encode_queries([query])
        print(f"    Embedding shape: {embeddings.shape}")
        
        # Convert to list
        if hasattr(embeddings, 'tolist'):
            query_embedding = embeddings[0].tolist()
        else:
            query_embedding = embeddings[0]
        
        print(f"    Embedding dimension: {len(query_embedding)}")
        
        # Search
        results = chromadb_client.search(
            query=query,
            query_embedding=query_embedding,
            n_results=3
        )
        
        if results and results.get('documents'):
            print(f"    ✅ Found {len(results['documents'][0])} matches:")
            for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0])):
                confidence = 1 - dist
                print(f"       {i+1}. {doc[:60]}... (conf: {confidence:.3f})")
        else:
            print(f"    ❌ No matches found")
            
    except Exception as e:
        print(f"    ❌ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n✅ Test complete!")