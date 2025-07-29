#!/usr/bin/env python3
"""Quick test to search existing inventory in ChromaDB"""

import chromadb
from chromadb.config import Settings

def test_inventory_search():
    """Test searching the already ingested inventory"""
    
    print("Factory Automation: Quick Inventory Search Test")
    print("=" * 70)
    
    # Connect to existing ChromaDB
    client = chromadb.PersistentClient(
        path="./chroma_data",
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get the inventory collection
    collection = client.get_collection("tag_inventory")
    
    print(f"\nTotal items in inventory: {collection.count()}")
    
    # Test queries
    test_queries = [
        "Allen Solly casual tags black cotton",
        "Myntra tags with thread",
        "Peter England formal blue tags",
        "lifestyle premium tags",
        "Amazon sustainable tags"
    ]
    
    print("\nTesting RAG-based inventory search:")
    print("-" * 70)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Search using ChromaDB's built-in embeddings
        results = collection.query(
            query_texts=[query],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )
        
        if results['ids'][0]:
            print("Results:")
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                score = 1 - distance  # Convert distance to similarity
                
                print(f"\n  {i+1}. {metadata.get('trim_name', 'N/A')}")
                print(f"     Code: {metadata.get('trim_code', 'N/A')}")
                print(f"     Brand: {metadata.get('brand', 'N/A')}")
                print(f"     Stock: {metadata.get('stock', 0)} units")
                print(f"     Match Score: {score:.1%}")
        else:
            print("  No results found")
    
    # Show inventory summary
    print("\n" + "="*70)
    print("INVENTORY SUMMARY")
    print("="*70)
    
    # Get all items for statistics
    all_items = collection.get(limit=1000)
    
    brands = {}
    total_stock = 0
    out_of_stock = 0
    
    for metadata in all_items['metadatas']:
        brand = metadata.get('brand', 'Unknown')
        stock = metadata.get('stock', 0)
        
        if brand not in brands:
            brands[brand] = {'count': 0, 'stock': 0}
        
        brands[brand]['count'] += 1
        brands[brand]['stock'] += stock
        total_stock += stock
        
        if stock == 0:
            out_of_stock += 1
    
    print(f"Total SKUs: {len(all_items['metadatas'])}")
    print(f"Total Stock Units: {total_stock:,}")
    print(f"Out of Stock Items: {out_of_stock}")
    
    print("\nBy Brand:")
    for brand, data in sorted(brands.items()):
        print(f"- {brand}: {data['count']} items, {data['stock']:,} units")
    
    # Show sample items
    print("\nSample Inventory Items:")
    print("-" * 70)
    for i, (doc, meta) in enumerate(zip(all_items['documents'][:5], all_items['metadatas'][:5]), 1):
        print(f"{i}. {meta.get('trim_name', 'N/A')} ({meta.get('trim_code', 'N/A')})")
        print(f"   Brand: {meta.get('brand', 'N/A')}, Stock: {meta.get('stock', 0)}")

if __name__ == "__main__":
    test_inventory_search()