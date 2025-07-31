#!/usr/bin/env python3
"""Simplified end-to-end test without agent framework dependencies"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import logging

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ingest_inventory_if_needed():
    """Ensure inventory is ingested into ChromaDB"""
    logger.info("Checking if inventory needs to be ingested...")

    # Check if ChromaDB has data
    chroma_client = ChromaDBClient()

    # Try to get count
    try:
        count = chroma_client.collection.count()
        if count > 0:
            logger.info(f"ChromaDB already has {count} items. Skipping ingestion.")
            return chroma_client
    except Exception:
        pass  # Collection might not exist yet

    # Ingest inventory
    logger.info("Ingesting inventory from Excel files...")
    ingestion = ExcelInventoryIngestion(
        chroma_client=chroma_client, embedding_model="stella-400m"
    )

    results = ingestion.ingest_inventory_folder("inventory")

    total_items = sum(
        r.get("items_ingested", 0) for r in results if r["status"] == "success"
    )
    logger.info(f"Ingested {total_items} items into ChromaDB")

    return chroma_client


def test_order_matching():
    """Test order matching with various scenarios"""

    # Initialize ingestion system
    chroma_client = ingest_inventory_if_needed()
    ingestion = ExcelInventoryIngestion(
        chroma_client=chroma_client, embedding_model="stella-400m"
    )

    print("\n" + "=" * 70)
    print("ORDER VS INVENTORY MATCHING TEST")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test orders
    test_orders = [
        {
            "customer": "ABC Garments",
            "order": "Need 500 Allen Solly casual tags black cotton",
            "quantity": 500,
        },
        {
            "customer": "XYZ Fashion",
            "order": "Urgent requirement for 1000 Myntra tags with thread",
            "quantity": 1000,
        },
        {
            "customer": "Fashion Hub",
            "order": "Please send 200 Peter England formal blue tags",
            "quantity": 200,
        },
        {
            "customer": "Style Store",
            "order": "Looking for 300 lifestyle tags premium quality",
            "quantity": 300,
        },
        {
            "customer": "Eco Clothing",
            "order": "Required 100 Amazon tags sustainable material",
            "quantity": 100,
        },
    ]

    summary = {
        "total_orders": len(test_orders),
        "perfect_matches": 0,
        "partial_matches": 0,
        "no_matches": 0,
        "insufficient_stock": 0,
    }

    print("\nProcessing Orders:\n")

    for i, order_data in enumerate(test_orders, 1):
        print(f"{i}. Customer: {order_data['customer']}")
        print(f"   Order: {order_data['order']}")
        print(f"   Quantity Needed: {order_data['quantity']}")

        # Search inventory
        results = ingestion.search_inventory(
            query=order_data["order"], min_stock=0, limit=3
        )

        if results:
            best_match = results[0]
            confidence = best_match["score"]
            available_stock = best_match["metadata"].get("stock", 0)

            print("\n   Best Match Found:")
            print(f"   - Item: {best_match['metadata'].get('trim_name', 'N/A')}")
            print(f"   - Code: {best_match['metadata'].get('trim_code', 'N/A')}")
            print(f"   - Brand: {best_match['metadata'].get('brand', 'N/A')}")
            print(f"   - Available Stock: {available_stock}")
            print(f"   - Confidence Score: {confidence:.1%}")

            # Determine status
            if confidence > 0.85:
                if available_stock >= order_data["quantity"]:
                    status = "✓ PERFECT MATCH - Ready to fulfill"
                    summary["perfect_matches"] += 1
                else:
                    status = "⚠ INSUFFICIENT STOCK"
                    summary["insufficient_stock"] += 1
            elif confidence > 0.70:
                status = "👁 PARTIAL MATCH - Needs review"
                summary["partial_matches"] += 1
            else:
                status = "✗ WEAK MATCH - Manual intervention needed"
                summary["no_matches"] += 1

            print(f"   - Status: {status}")

            # Show alternatives if needed
            if available_stock < order_data["quantity"] and len(results) > 1:
                print("\n   Alternative Options:")
                for j, alt in enumerate(results[1:3], 1):
                    print(
                        f"   {j}. {alt['metadata'].get('trim_name', 'N/A')} "
                        f"(Stock: {alt['metadata'].get('stock', 0)}, "
                        f"Score: {alt['score']:.1%})"
                    )
        else:
            print("   Status: ✗ NO MATCHES FOUND")
            summary["no_matches"] += 1

        print("\n" + "-" * 70 + "\n")

    # Print summary
    print("SUMMARY REPORT")
    print("=" * 70)
    print(f"Total Orders Processed: {summary['total_orders']}")
    print("\nMatch Results:")
    print(
        f"- Perfect Matches (Auto-processable): {summary['perfect_matches']} "
        f"({summary['perfect_matches']/summary['total_orders']*100:.0f}%)"
    )
    print(
        f"- Partial Matches (Need Review): {summary['partial_matches']} "
        f"({summary['partial_matches']/summary['total_orders']*100:.0f}%)"
    )
    print(
        f"- No/Weak Matches: {summary['no_matches']} "
        f"({summary['no_matches']/summary['total_orders']*100:.0f}%)"
    )
    print(
        f"- Insufficient Stock: {summary['insufficient_stock']} "
        f"({summary['insufficient_stock']/summary['total_orders']*100:.0f}%)"
    )

    print("\nRECOMMENDATIONS:")
    if summary["insufficient_stock"] > 0:
        print("- Restock items with high demand but low inventory")
    if summary["no_matches"] > 0:
        print("- Review unmatched orders for new product requirements")
    if summary["partial_matches"] > 0:
        print("- Set up human review process for medium-confidence matches")

    # Show inventory statistics
    print("\n" + "=" * 70)
    print("INVENTORY STATISTICS")
    print("=" * 70)

    # Get all items to show statistics
    all_items = chroma_client.collection.get(limit=1000)

    if all_items["metadatas"]:
        brands = {}
        total_stock = 0
        out_of_stock = 0

        for metadata in all_items["metadatas"]:
            brand = metadata.get("brand", "Unknown")
            stock = metadata.get("stock", 0)

            if brand not in brands:
                brands[brand] = {"count": 0, "total_stock": 0}

            brands[brand]["count"] += 1
            brands[brand]["total_stock"] += stock
            total_stock += stock

            if stock == 0:
                out_of_stock += 1

        print(f"Total SKUs in Database: {len(all_items['metadatas'])}")
        print(f"Total Stock Units: {total_stock:,}")
        print(f"Out of Stock Items: {out_of_stock}")

        print("\nStock by Brand:")
        for brand, data in sorted(brands.items()):
            print(f"- {brand}: {data['count']} SKUs, {data['total_stock']:,} units")


def main():
    """Main test function"""
    print("Factory Automation: RAG-Based Order to Inventory Matching")
    print("=" * 70)

    test_order_matching()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    print("\nNext Steps:")
    print("1. Integrate with Gmail API to automatically pull order emails")
    print("2. Set up Gradio dashboard for human review of partial matches")
    print("3. Implement order confirmation and document generation")
    print("4. Add payment tracking functionality")


if __name__ == "__main__":
    main()
