#!/usr/bin/env python3
"""Simple verification of AS RELAXED CROP WB data"""

from factory_automation.factory_database.vector_db import ChromaDBClient

print("\nVerifying AS RELAXED CROP WB sizes in ChromaDB...")
print("="*50)

client = ChromaDBClient()

# Check specific tag codes for AS RELAXED CROP WB
tag_codes = [f"TBALTAG0{i}N" for i in range(392, 402)]
found_count = 0

for code in tag_codes:
    results = client.collection.get(
        where={"tag_code": code},
        limit=1
    )
    
    if results and results.get('ids'):
        metadata = results['metadatas'][0]
        size = metadata.get('size', 'N/A')
        qty = metadata.get('quantity', metadata.get('QTY', 'N/A'))
        sheet = metadata.get('sheet', 'N/A')
        found_count += 1
        print(f"✅ {code}: Size {size}, Qty {qty}, Sheet: {sheet}")
    else:
        print(f"❌ {code}: Not found")

print(f"\n📊 Summary: {found_count}/10 sizes found")

# Also check total Sheet2 items
sheet2_results = client.collection.get(
    where={"sheet": "Sheet2"},
    limit=1000
)

if sheet2_results and sheet2_results.get('ids'):
    print(f"📑 Total Sheet2 items: {len(sheet2_results['ids'])}")
    
    # Count by brand
    brands = {}
    for metadata in sheet2_results['metadatas']:
        brand = metadata.get('brand', 'Unknown')
        if brand not in brands:
            brands[brand] = 0
        brands[brand] += 1
    
    print("\n📦 Sheet2 items by brand:")
    for brand, count in sorted(brands.items()):
        print(f"   - {brand}: {count} items")