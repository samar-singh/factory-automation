#!/usr/bin/env python3
"""Verify search functionality with the updated data"""

from factory_automation.factory_rag.enhanced_search import EnhancedRAGSearch
from factory_automation.factory_database.vector_db import ChromaDBClient

def test_searches():
    """Test various searches to verify data completeness"""
    
    print("\n" + "="*70)
    print("Testing Search Functionality with Updated Data")
    print("="*70 + "\n")
    
    # Initialize search
    search = EnhancedRAGSearch()
    
    # Test queries
    test_queries = [
        "AS RELAXED CROP WB size 36",
        "ALLEN SOLLY size 28",
        "FM STOCK items",
        "tags with size 32",
        "PETER ENGLAND formal tags"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-"*50)
        
        results = search.search_with_reranking(query, k=5)
        
        if results:
            for i, result in enumerate(results[:3], 1):
                metadata = result.get('metadata', {})
                print(f"{i}. {metadata.get('tag_name', metadata.get('trim_name', 'N/A'))}")
                print(f"   Code: {metadata.get('tag_code', 'N/A')}")
                print(f"   Size: {metadata.get('size', 'N/A')}")
                print(f"   Qty: {metadata.get('quantity', metadata.get('QTY', 'N/A'))}")
                print(f"   Sheet: {metadata.get('sheet', 'N/A')}")
                print(f"   Score: {result.get('score', 0):.3f}")
        else:
            print("No results found")
    
    # Specific test for AS RELAXED CROP WB sizes
    print("\n" + "="*70)
    print("Verifying AS RELAXED CROP WB All Sizes")
    print("="*70 + "\n")
    
    client = ChromaDBClient()
    
    # Check specific tag codes
    tag_codes = [f"TBALTAG0{i}N" for i in range(392, 402)]
    found_sizes = []
    
    for code in tag_codes:
        results = client.collection.get(
            where={"tag_code": code},
            limit=1
        )
        
        if results and results.get('ids'):
            metadata = results['metadatas'][0]
            size = metadata.get('size', 'N/A')
            qty = metadata.get('quantity', metadata.get('QTY', 'N/A'))
            found_sizes.append((code, size, qty))
            print(f"✅ {code}: Size {size}, Qty {qty}")
        else:
            print(f"❌ {code}: Not found")
    
    print(f"\n📊 Found {len(found_sizes)}/10 AS RELAXED CROP WB sizes")
    
    print("\n✅ Search verification complete!")

if __name__ == "__main__":
    test_searches()