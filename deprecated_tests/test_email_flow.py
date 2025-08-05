#!/usr/bin/env python3
"""Test the complete email flow with the provided example"""

import sys

sys.path.append(".")

from factory_automation.factory_agents.gmail_agent import GmailAgent
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

# Sample email content
email_body = """Dear Sir/Madam
Order received with thanks & Greetings from Interface Direct.
PFA Pro-Forma Invoice # 1554 & please check the description of the tag image & approve the order  & do the needful. Please let us know if you need any more help.

With warm Regards,

PUSHPARAJ.A/ Interface Direct/ Tag supplier / trimsblr@yahoo.co.in
Dispatches Team / PH/998000 9355.

On Wednesday 30 July, 2025 at 04:25:08 pm IST, Param lunagariya <paramlunagariya9@gmail.com> wrote:

Dear Interface Team ,

             Please find attached PO of hand tag of SYMBOL share Pi and delivery date of the tags.

              Always add a transport charge in the invoice.

Param Lunagariya
Senior Merchandiser
E: paramlunagariya9@gmail.com
| M: 7016996528
SURBHI TEXTILE MILL PVT LTD
Plot No- 3507 Road no.-6 Sachin GIDC,
Surat Gujarat-394230."""

print("=" * 80)
print("TESTING END-TO-END EMAIL FLOW")
print("=" * 80)

# Step 1: Parse email to extract order details
print("\n1. PARSING EMAIL")
print("-" * 50)

gmail_agent = GmailAgent()

# Create a mock email content structure
email_content = {
    "id": "test_email_001",
    "from": "Param lunagariya <paramlunagariya9@gmail.com>",
    "subject": "Order for hand tag of SYMBOL",
    "date": "2025-07-30 16:25:08",
    "body": email_body,
    "attachments": [],
}

# Parse the email using the extract_order_details method
order_data = gmail_agent.extract_order_details(email_content)
print(f"Extracted order data: {order_data}")

# Step 2: Search inventory for the extracted items
print("\n2. SEARCHING INVENTORY")
print("-" * 50)

ingestion = ExcelInventoryIngestion(embedding_model="all-MiniLM-L6-v2")

# Process each line item
if order_data and "lines" in order_data:
    for line in order_data["lines"]:
        print(f"\nSearching for: {line}")

        # Search in inventory
        results = ingestion.search_inventory(query=line, limit=3)

        if results:
            print(f"Found {len(results)} matches:")
            for i, match in enumerate(results, 1):
                metadata = match.get("metadata", {})
                print(f"  Match {i}:")
                print(f"    Brand: {metadata.get('brand', 'Unknown')}")
                print(f"    Product: {metadata.get('trim_name', 'Unknown')}")
                print(f"    Stock: {metadata.get('stock', 0)} units")
                print(f"    Confidence: {match.get('score', 0)*100:.1f}%")
                print(f"    Source: {metadata.get('excel_source', 'Unknown')}")
        else:
            print("  No matches found")

# Step 3: Decision making based on confidence
print("\n3. DECISION ROUTING")
print("-" * 50)

if order_data and "lines" in order_data:
    auto_approve_all = True

    for line in order_data["lines"]:
        results = ingestion.search_inventory(query=line, limit=1)

        if results:
            match = results[0]
            metadata = match.get("metadata", {})
            score = match.get("score", 0)
            stock = metadata.get("stock", 0)

            if score > 0.8 and stock > 0:
                decision = "AUTO-APPROVE ✅"
            elif score > 0.7 and stock > 0:
                decision = "MANUAL REVIEW 👀"
                auto_approve_all = False
            else:
                decision = "FIND ALTERNATIVE ❌"
                auto_approve_all = False

            print(f"{line}: {decision} (confidence: {score:.1%}, stock: {stock})")
        else:
            print(f"{line}: NO MATCH - MANUAL REVIEW")
            auto_approve_all = False

    print(
        f"\nFinal Decision: {'Auto-approve entire order' if auto_approve_all else 'Requires manual review'}"
    )

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
