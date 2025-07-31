#!/usr/bin/env python3
"""Show what's currently in the inventory database"""

from collections import defaultdict

import chromadb
from chromadb.config import Settings


def main():
    print("=" * 70)
    print("INVENTORY DATABASE CONTENTS")
    print("=" * 70)

    # Connect to ChromaDB
    client = chromadb.PersistentClient(
        path="./chroma_data", settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_collection("tag_inventory")

    # Get all items
    all_items = collection.get(limit=1000)

    print(f"\nTotal items in database: {len(all_items['ids'])}")

    # Organize by brand
    brands = defaultdict(list)
    total_stock = 0

    for i, (id, meta) in enumerate(zip(all_items["ids"], all_items["metadatas"])):
        brand = meta.get("brand", "Unknown")
        brands[brand].append(
            {
                "name": meta.get("trim_name", "N/A"),
                "code": meta.get("trim_code", "N/A"),
                "stock": meta.get("stock", 0),
                "source": meta.get("excel_source", "N/A"),
            }
        )
        total_stock += meta.get("stock", 0)

    print(f"Total stock units: {total_stock:,}")
    print(f"Number of brands: {len(brands)}")

    # Show items by brand
    for brand in sorted(brands.keys()):
        items = brands[brand]
        brand_stock = sum(item["stock"] for item in items)

        print(f"\n{'='*70}")
        print(f"BRAND: {brand}")
        print(f"Items: {len(items)} | Total Stock: {brand_stock:,}")
        print(f"Source: {items[0]['source']}")
        print("-" * 70)

        # Show first 5 items
        for i, item in enumerate(items[:5]):
            print(f"{i+1}. {item['name']}")
            print(f"   Code: {item['code']} | Stock: {item['stock']}")

        if len(items) > 5:
            print(f"   ... and {len(items)-5} more items")

    # Show sample searches
    print(f"\n{'='*70}")
    print("SAMPLE SEARCHES YOU CAN TRY")
    print("=" * 70)

    # Pick some real items from inventory
    sample_items = []
    for brand, items in brands.items():
        if items and items[0]["stock"] > 0:
            sample_items.append(
                f"{brand} {items[0]['name'].split()[0] if items[0]['name'] != 'N/A' else 'tags'}"
            )
        if len(sample_items) >= 5:
            break

    for item in sample_items:
        print(f"- {item}")

    print("\nRun 'python test_interactive.py' to search these items!")


if __name__ == "__main__":
    main()
