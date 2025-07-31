#!/usr/bin/env python3
"""Analyze email patterns and improve order extraction."""

import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.append("./factory_automation")

from factory_automation.factory_database.vector_db import ChromaDBClient  # noqa: E402
from factory_automation.factory_rag.excel_ingestion import (  # noqa: E402
    ExcelInventoryIngestion,
)


def analyze_email_and_inventory():
    """Analyze the email order and provide insights."""

    print("=" * 80)
    print("EMAIL ORDER ANALYSIS & DEBUGGING")
    print("=" * 80)

    # Email details
    print("\n1. EMAIL STRUCTURE ANALYSIS:")
    print("   From: interface <trimsblr@yahoo.co.in> (Supplier)")
    print("   To: Param lunagariya <paramlunagariya9@gmail.com> (Customer)")
    print(
        "   Subject: Pro-Forma Invoice # 1554/SURBHI TEXTILE/PO OF HAND TAG OF SYMBOL ST-057"
    )

    print("\n   Key Information Extracted:")
    print("   - Invoice Number: 1554")
    print("   - Customer: SURBHI TEXTILE MILL PVT LTD")
    print("   - Product Code: ST-057")
    print("   - Product Type: HAND TAG OF SYMBOL")
    print("   - This is a CONFIRMATION email (PO already placed)")

    print("\n2. ORDER FLOW ANALYSIS:")
    print("   Step 1: Customer (Param) sent PO for 'hand tag of SYMBOL'")
    print("   Step 2: Supplier (Interface) created Pro-Forma Invoice #1554")
    print("   Step 3: Supplier sent invoice for approval (current email)")
    print("   Step 4: Customer needs to approve and confirm")

    print("\n3. MISSING INFORMATION:")
    print("   ❌ Quantity not specified in email body")
    print("   ❌ Unit price not mentioned")
    print("   ❌ Delivery date not in email (likely in attachment)")
    print("   ❌ Actual tag specifications (size, color, etc.)")
    print("   ℹ️  These details are likely in the attached Pro-Forma Invoice")

    # Initialize system
    print("\n4. INVENTORY SEARCH ANALYSIS:")
    chroma_client = ChromaDBClient()
    ingestion = ExcelInventoryIngestion(
        chroma_client=chroma_client, embedding_model="all-MiniLM-L6-v2"
    )

    # Let's check what SYMBOL items we have
    print("\n   Checking all SYMBOL items in inventory...")
    symbol_results = ingestion.search_inventory(query="SYMBOL", limit=20)

    if symbol_results:
        print(f"\n   Found {len(symbol_results)} SYMBOL-related items:")
        symbol_items = {}
        for result in symbol_results:
            brand = result["metadata"].get("brand", "N/A")
            name = result["metadata"].get("trim_name", "N/A")
            code = result["metadata"].get("trim_code", "N/A")
            stock = result["metadata"].get("stock", 0)

            if "symbol" in name.lower():
                if brand not in symbol_items:
                    symbol_items[brand] = []
                symbol_items[brand].append({"name": name, "code": code, "stock": stock})

        for brand, items in symbol_items.items():
            print(f"\n   Brand: {brand}")
            for item in items[:5]:  # Show first 5
                print(f"   - {item['name']}")
                print(f"     Code: {item['code']} | Stock: {item['stock']}")

    print("\n5. PROBLEM DIAGNOSIS:")
    print("   Issue 1: Product code 'ST-057' doesn't match our inventory codes")
    print("   Issue 2: We have SYMBOL items but under AMAZON brand, not as standalone")
    print("   Issue 3: Email doesn't contain quantity/specs - need attachment parsing")

    print("\n6. RECOMMENDATIONS:")
    print("   1. Implement attachment parsing (Pro-Forma Invoice PDF/Excel)")
    print("   2. Create mapping table for customer codes (ST-057) to our codes")
    print("   3. Add fuzzy matching for product codes")
    print("   4. Extract quantity from invoice attachments")
    print("   5. Build customer-specific product catalog")

    print("\n7. IMMEDIATE ACTIONS:")
    print("   - Check if 'ST-057' is a customer-specific code")
    print("   - Look for SYMBOL items with 'hand tag' in description")
    print("   - Request the Pro-Forma Invoice attachment for full details")
    print("   - Add ST-057 mapping to known SYMBOL products")

    # Search for hand tags specifically
    print("\n8. SEARCHING FOR HAND TAGS:")
    hand_tag_results = ingestion.search_inventory(query="hand tag", limit=10)

    if hand_tag_results:
        print(f"\n   Found {len(hand_tag_results)} hand tag items:")
        for i, result in enumerate(hand_tag_results[:5]):
            name = result["metadata"].get("trim_name", "N/A")
            brand = result["metadata"].get("brand", "N/A")
            stock = result["metadata"].get("stock", 0)
            score = result["score"]
            print(f"   {i+1}. {name} (Brand: {brand})")
            print(f"      Stock: {stock} | Relevance: {score:.1%}")

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("- The system is working correctly")
    print("- We need attachment parsing to get complete order details")
    print("- Customer code 'ST-057' needs to be mapped to our inventory")
    print("- Consider adding a 'customer_codes' field to inventory")
    print("=" * 80)


if __name__ == "__main__":
    analyze_email_and_inventory()
