#!/usr/bin/env python3
"""End-to-end test: Email polling → Order extraction → Inventory matching"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent / "factory_automation"))

import logging

from factory_automation.factory_agents.gmail_agent import GmailAgent
from factory_automation.factory_agents.inventory_rag_agent import InventoryRAGAgent
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
            return True
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

    return total_items > 0


def test_manual_order_matching(order_text: str):
    """Test order matching with manual input"""
    print("\n" + "=" * 70)
    print("MANUAL ORDER TEST")
    print("=" * 70)
    print(f"Order text: {order_text}")

    # Initialize inventory RAG agent
    inventory_agent = InventoryRAGAgent()

    # Process order
    result = inventory_agent.process_order_request(order_text)

    # Display results
    print("\nOrder Analysis:")
    print(f"- Quantity needed: {result['quantity_needed']}")
    print(f"- Brand filter: {result['brand_filter'] or 'None'}")
    print(f"- Status: {result['status']}")
    print(f"- Recommended action: {result['recommended_action']}")
    print(f"\nMessage: {result['message']}")

    if result["matches"]:
        print(f"\nTop {min(3, len(result['matches']))} Matches:")
        for i, match in enumerate(result["matches"][:3], 1):
            print(f"\n{i}. {match['item_name']}")
            print(f"   Code: {match['item_code']}")
            print(f"   Brand: {match['brand']}")
            print(f"   Stock: {match['available_stock']} units")
            print(f"   Confidence: {match['confidence_score']:.1%}")
            print(f"   Sufficient stock: {'✓' if match['sufficient_stock'] else '✗'}")


def test_gmail_flow(user_email: str):
    """Test the complete Gmail → Inventory flow"""
    print("\n" + "=" * 70)
    print("GMAIL INTEGRATION TEST")
    print("=" * 70)

    # Initialize Gmail agent
    gmail_agent = GmailAgent()

    # Initialize Gmail service
    if not gmail_agent.initialize_service(user_email):
        print("Failed to initialize Gmail service")
        print("Make sure the service account has domain-wide delegation")
        print("and the email address has granted access")
        return

    print(f"Successfully connected to Gmail for: {user_email}")

    # Poll recent emails
    print("\nPolling for recent order emails...")
    orders = gmail_agent.poll_recent_orders(hours=168)  # Last 7 days

    if not orders:
        print("No order emails found")
        # Try a broader search
        print("\nTrying broader search...")
        messages = gmail_agent.list_messages("", max_results=5)
        print(f"Found {len(messages)} recent emails")
        return

    print(f"\nFound {len(orders)} order emails")

    # Initialize inventory agent
    inventory_agent = InventoryRAGAgent()

    # Process each order
    for i, order in enumerate(orders, 1):
        print(f"\n{'='*70}")
        print(f"ORDER {i}/{len(orders)}")
        print(f"{'='*70}")

        print(f"From: {order['customer_name']} ({order['customer_email']})")
        print(f"Subject: {order['subject']}")
        print(f"Date: {order['date']}")
        print(f"Urgency: {order['urgency']}")

        if order["items"]:
            print("\nExtracted items:")
            for item in order["items"]:
                print(f"  - {item}")

                # Match each item against inventory
                print(f"\n  Matching: '{item}'")
                result = inventory_agent.process_order_request(item)

                if result["matches"]:
                    best_match = result["matches"][0]
                    print(f"  Best match: {best_match['item_name']}")
                    print(f"  Confidence: {best_match['confidence_score']:.1%}")
                    print(f"  Stock: {best_match['available_stock']}")
                else:
                    print("  No matches found")


def generate_order_summary():
    """Generate a comprehensive order vs inventory summary"""
    print("\n" + "=" * 70)
    print("ORDER VS INVENTORY SUMMARY REPORT")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test various order scenarios
    test_orders = [
        "Need 500 Allen Solly casual tags black cotton",
        "Urgent requirement for 1000 Myntra tags with thread",
        "Please send 200 Peter England formal blue tags",
        "Looking for 300 lifestyle tags premium quality",
        "Required 100 Amazon tags sustainable material",
    ]

    inventory_agent = InventoryRAGAgent()

    summary = {
        "total_orders": len(test_orders),
        "auto_processable": 0,
        "needs_review": 0,
        "no_matches": 0,
        "insufficient_stock": 0,
    }

    print("\nProcessing test orders...\n")

    for order in test_orders:
        print(f"Order: {order}")
        result = inventory_agent.process_order_request(order)

        # Update summary
        if result["status"] == "matched_with_stock":
            summary["auto_processable"] += 1
            status = "✓ AUTO-PROCESS"
        elif result["status"] == "matched_no_stock":
            summary["insufficient_stock"] += 1
            status = "⚠ INSUFFICIENT STOCK"
        elif result["status"] == "needs_confirmation":
            summary["needs_review"] += 1
            status = "👁 NEEDS REVIEW"
        else:
            summary["no_matches"] += 1
            status = "✗ NO MATCH"

        print(f"Status: {status}")

        if result["matches"]:
            match = result["matches"][0]
            print(
                f"Match: {match['item_name']} (Confidence: {match['confidence_score']:.1%})"
            )
            print(f"Stock: {match['available_stock']} units")

        print("-" * 70)

    # Print summary
    print("\nSUMMARY:")
    print(f"Total Orders: {summary['total_orders']}")
    print(
        f"Auto-processable: {summary['auto_processable']} ({summary['auto_processable']/summary['total_orders']*100:.0f}%)"
    )
    print(
        f"Needs Review: {summary['needs_review']} ({summary['needs_review']/summary['total_orders']*100:.0f}%)"
    )
    print(
        f"No Matches: {summary['no_matches']} ({summary['no_matches']/summary['total_orders']*100:.0f}%)"
    )
    print(
        f"Insufficient Stock: {summary['insufficient_stock']} ({summary['insufficient_stock']/summary['total_orders']*100:.0f}%)"
    )


def main():
    """Main test function"""

    print("Factory Automation: Email to Inventory Test Flow")
    print("=" * 70)

    # Step 1: Ensure inventory is ingested
    if not ingest_inventory_if_needed():
        print("Failed to ingest inventory. Exiting.")
        return

    # Step 2: Test manual order matching
    print("\n1. Testing manual order matching...")
    test_manual_order_matching("Need 500 Allen Solly casual tags black cotton")

    # Step 3: Generate order vs inventory summary
    print("\n2. Generating order vs inventory summary...")
    generate_order_summary()

    # Step 4: Test Gmail integration (optional)
    print("\n3. Gmail Integration")
    print("-" * 70)
    user_email = input("Enter email address to poll (or press Enter to skip): ").strip()

    if user_email and "@" in user_email:
        test_gmail_flow(user_email)
    else:
        print("Skipping Gmail integration test")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
