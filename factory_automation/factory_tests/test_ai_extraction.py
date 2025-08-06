#!/usr/bin/env python3
"""Test the AI-powered order extraction functionality"""

import asyncio
import json

from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_extraction():
    """Test the extract_order_items function with sample emails"""

    # Initialize components
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client)

    # Sample test emails
    test_emails = [
        {
            "subject": "Urgent Order - Myntra Tags",
            "body": """
            Hi Team,
            
            We need an urgent order for Myntra:
            - 5000 pieces of price tags in black color
            - Size: 2x3 inches
            - Material: Premium cardboard with matte finish
            - Special requirement: Gold foil embossing for logo
            - Product codes: MYN-2024-BLK-001 to MYN-2024-BLK-5000
            
            Additionally, we need:
            - 2000 hang tags with strings
            - Color: White with red text
            - Size: 3x4 inches
            
            Please deliver by next Monday.
            
            Thanks,
            Myntra Procurement Team
            """,
        },
        {
            "subject": "Order for Allen Solly Labels",
            "body": """
            Dear Supplier,
            
            Please process our order:
            1. Care labels - 10,000 units
            2. Brand labels - 10,000 units  
            3. Size labels (S, M, L, XL) - 2,500 each size
            
            All labels should be in standard Allen Solly branding.
            Fabric material preferred.
            
            Regards,
            Allen Solly
            """,
        },
        {
            "subject": "Quick requirement",
            "body": """
            Need 500 tags urgently. Black color preferred.
            Send quotation ASAP.
            """,
        },
    ]

    print("=" * 60)
    print("TESTING AI-POWERED ORDER EXTRACTION")
    print("=" * 60)

    # Get the extract_order_items tool
    tools = orchestrator._create_tools()
    extract_tool = None

    for tool in tools:
        if hasattr(tool, "__name__") and tool.__name__ == "extract_order_items":
            extract_tool = tool
            break

    if not extract_tool:
        print("❌ Could not find extract_order_items tool")
        return

    # Test each email
    for i, email in enumerate(test_emails, 1):
        print(f"\n📧 Test Email {i}: {email['subject']}")
        print("-" * 50)

        try:
            # Call the extraction function
            result = await extract_tool(email["body"], has_attachments=False)

            # Parse and display results
            extracted_data = json.loads(result)

            print(
                f"✅ Extraction Method: {extracted_data.get('extraction_method', 'unknown')}"
            )
            print(
                f"📊 Confidence Level: {extracted_data.get('confidence_level', 'unknown')}"
            )

            if "customer_name" in extracted_data:
                print(f"👤 Customer: {extracted_data['customer_name']}")

            if "order_items" in extracted_data and extracted_data["order_items"]:
                print(f"\n📦 Extracted {len(extracted_data['order_items'])} items:")
                for item in extracted_data["order_items"]:
                    print(
                        f"  • {item.get('quantity', '?')} x {item.get('item_type', 'unknown')}"
                    )
                    if item.get("color"):
                        print(f"    Color: {item['color']}")
                    if item.get("size"):
                        print(f"    Size: {item['size']}")
                    if item.get("material"):
                        print(f"    Material: {item['material']}")
                    if item.get("special_requirements"):
                        print(f"    Special: {', '.join(item['special_requirements'])}")
            else:
                print("  ⚠️ No items extracted")

            if (
                "delivery_timeline" in extracted_data
                and extracted_data["delivery_timeline"]
            ):
                print(f"\n⏰ Delivery: {extracted_data['delivery_timeline']}")

            if (
                "missing_information" in extracted_data
                and extracted_data["missing_information"]
            ):
                print(
                    f"\n❓ Missing Info: {', '.join(extracted_data['missing_information'])}"
                )

        except Exception as e:
            print(f"❌ Extraction failed: {str(e)}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_extraction())
