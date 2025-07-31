#!/usr/bin/env python3
"""Interactive test - type your own order queries"""

import chromadb
from chromadb.config import Settings

def search_inventory(query, collection, min_stock=0):
    """Search inventory using ChromaDB"""
    results = collection.query(
        query_texts=[query],
        n_results=5,
        include=['documents', 'metadatas', 'distances']
    )
    
    matches = []
    if results['ids'][0]:
        for i in range(len(results['ids'][0])):
            stock = results['metadatas'][0][i].get('stock', 0)
            if stock >= min_stock:
                matches.append({
                    'item': results['metadatas'][0][i].get('trim_name', 'N/A'),
                    'code': results['metadatas'][0][i].get('trim_code', 'N/A'),
                    'brand': results['metadatas'][0][i].get('brand', 'N/A'),
                    'stock': stock,
                    'score': 1 - results['distances'][0][i],
                    'source': results['metadatas'][0][i].get('excel_source', 'N/A')
                })
    return matches

def main():
    print("="*70)
    print("INTERACTIVE INVENTORY SEARCH TEST")
    print("="*70)
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(
        path="./chroma_data",
        settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_collection("tag_inventory")
    print(f"Connected to inventory database: {collection.count()} items\n")
    
    print("Available brands in inventory:")
    # Get unique brands
    all_items = collection.get(limit=1000)
    brands = set()
    for meta in all_items['metadatas']:
        brands.add(meta.get('brand', 'Unknown'))
    for brand in sorted(brands):
        print(f"  - {brand}")
    
    print("\nType your order queries (or 'quit' to exit)")
    print("Examples:")
    print("  - Need 500 VH tags")
    print("  - FM linen tags with stock")
    print("  - Wotnot boys tags urgent")
    print("-"*70)
    
    while True:
        query = input("\nEnter order query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
            
        if not query:
            continue
        
        # Extract quantity if mentioned
        import re
        qty_match = re.search(r'(\d+)\s+', query)
        quantity_needed = int(qty_match.group(1)) if qty_match else 0
        
        print(f"\nSearching for: '{query}'")
        if quantity_needed:
            print(f"Quantity needed: {quantity_needed}")
        
        # Search
        matches = search_inventory(query, collection, min_stock=0)
        
        if matches:
            print(f"\nFound {len(matches)} matches:")
            for i, match in enumerate(matches, 1):
                print(f"\n{i}. {match['item']}")
                print(f"   Code: {match['code']}")
                print(f"   Brand: {match['brand']}")
                print(f"   Stock: {match['stock']} units", end="")
                
                if quantity_needed > 0:
                    if match['stock'] >= quantity_needed:
                        print(" ✓ Sufficient")
                    else:
                        print(f" ✗ Need {quantity_needed - match['stock']} more")
                else:
                    print()
                    
                print(f"   Confidence: {match['score']:.1%}")
                print(f"   Source: {match['source']}")
        else:
            print("\nNo matches found. Try different keywords.")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()