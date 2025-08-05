#!/usr/bin/env python3
"""Test email order processing with the provided email."""

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


def test_email_order():
    """Test processing the email order."""

    # The email content (not used directly in this test)
    # email_content = """..."""

    print("=" * 80)
    print("TESTING EMAIL ORDER PROCESSING")
    print("=" * 80)
    print("From: interface <trimsblr@yahoo.co.in>")
    print(
        "Subject: Pro-Forma Invoice # 1554/SURBHI TEXTILE/PO OF HAND TAG OF SYMBOL ST-057"
    )
    print("To: Param lunagariya <paramlunagariya9@gmail.com>")
    print("=" * 80)

    # Initialize system
    print("\n1. Initializing ChromaDB and ingestion system...")
    chroma_client = ChromaDBClient()
    ingestion = ExcelInventoryIngestion(
        chroma_client=chroma_client, embedding_model="all-MiniLM-L6-v2"
    )

    collection = chroma_client.collection
    print(f"   ✓ Connected to ChromaDB: {collection.count()} items in inventory")

    # Extract order information
    print("\n2. Analyzing email content...")
    print("   - Pro-Forma Invoice # 1554")
    print("   - Customer: SURBHI TEXTILE")
    print("   - Product: HAND TAG OF SYMBOL ST-057")

    # Key information extraction
    # order_items = []  # Not used in this version

    # From the subject and email, we know:
    # - It's about "HAND TAG OF SYMBOL ST-057"
    # - This seems to be a confirmation/approval request for an order

    # Let's search for SYMBOL tags
    search_queries = [
        "SYMBOL hand tag",
        "SYMBOL ST-057",
        "SYMBOL tag",
        "hand tag",
        "ST-057",
    ]

    print("\n3. Searching inventory for matching items...")
    all_results = []

    for query in search_queries:
        print(f"\n   Searching for: '{query}'")
        results = ingestion.search_inventory(query=query, limit=5)

        if results:
            print(f"   Found {len(results)} matches:")
            for i, result in enumerate(results[:3]):  # Show top 3
                item_name = result["metadata"].get("trim_name", "N/A")
                brand = result["metadata"].get("brand", "N/A")
                stock = result["metadata"].get("stock", 0)
                confidence = result["score"]
                print(f"   {i+1}. {item_name} (Brand: {brand})")
                print(f"      Stock: {stock} | Confidence: {confidence:.1%}")

                # Convert to the format expected by the rest of the code
                match = {
                    "item_name": item_name,
                    "item_code": result["metadata"].get("trim_code", "N/A"),
                    "brand": brand,
                    "available_stock": stock,
                    "confidence_score": confidence,
                    "metadata": result["metadata"],
                }
                all_results.append(match)
        else:
            print("   No matches found")

    # Deduplicate results by item_code
    unique_results = {}
    for result in all_results:
        key = result.get("item_code", result["item_name"])
        if (
            key not in unique_results
            or result["confidence_score"] > unique_results[key]["confidence_score"]
        ):
            unique_results[key] = result

    print("\n4. Best matches found:")
    if unique_results:
        sorted_results = sorted(
            unique_results.values(), key=lambda x: x["confidence_score"], reverse=True
        )
        for i, match in enumerate(sorted_results[:5]):
            print(f"\n   Match #{i+1}:")
            print(f"   Item: {match['item_name']}")
            print(f"   Brand: {match['brand']}")
            print(f"   Code: {match.get('item_code', 'N/A')}")
            print(f"   Stock: {match['available_stock']} units")
            print(f"   Confidence: {match['confidence_score']:.1%}")
    else:
        print("   No relevant matches found")

    print("\n5. Analysis:")
    print("   - The email appears to be a pro-forma invoice approval request")
    print("   - Product: HAND TAG OF SYMBOL ST-057")
    print("   - Customer has already placed the PO")
    print("   - They're asking for confirmation and to add transport charges")

    print("\n6. Recommendations:")
    if unique_results:
        best_match = sorted_results[0]
        if best_match["confidence_score"] > 0.7:
            print("   ✓ HIGH CONFIDENCE: Found matching SYMBOL tags in inventory")
        elif best_match["confidence_score"] > 0.5:
            print(
                "   ⚠ MEDIUM CONFIDENCE: Possible matches found, manual review recommended"
            )
        else:
            print("   ❌ LOW CONFIDENCE: No strong matches, manual search required")
    else:
        print("   ❌ NO MATCHES: Unable to find SYMBOL ST-057 tags in inventory")
        print("   - This might be a new product code")
        print("   - Manual inventory check recommended")

    print("\n7. Action Items:")
    print("   - Review the attached Pro-Forma Invoice #1554")
    print("   - Confirm product details match inventory")
    print("   - Add transport charges as requested")
    print("   - Send approval confirmation to customer")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_email_order()
