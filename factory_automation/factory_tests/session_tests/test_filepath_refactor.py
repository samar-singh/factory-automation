#!/usr/bin/env python3
"""
Test script to verify file path refactoring works correctly
"""

import asyncio
import json
import os

# Test data
EMAIL_DATA = {
    "message_id": "test_001",
    "from": "customer@example.com",
    "subject": "Order for Blue Shirt Tags",
    "body": """
    Dear Team,
    
    Please find attached our order details in the CSV file.
    We need 500 Blue Shirt Tags for Peter England brand.
    Additional 300 Red Polo Tags for Allen Solly.
    
    The CSV file contains complete order information.
    
    Best regards,
    Customer
    """,
    "email_type": "order",
    "attachments": [
        {
            "filename": "test_order.csv",
            "filepath": os.path.abspath("test_order.csv"),
            "mime_type": "text/csv",
        }
    ],
}


async def test_filepath_processing():
    """Test the file path based attachment processing"""

    print("=" * 60)
    print("FILE PATH REFACTORING TEST")
    print("=" * 60)

    # Import after environment is loaded
    from factory_automation.factory_agents.orchestrator_v3_agentic import (
        AgenticOrchestratorV3,
    )
    from factory_automation.factory_database.vector_db import ChromaDBClient

    print("\n1. Initializing orchestrator...")
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=False)

    print("\n2. Email data prepared:")
    print(f"   - Subject: {EMAIL_DATA['subject']}")
    print(f"   - From: {EMAIL_DATA['from']}")
    print(f"   - Attachments: {len(EMAIL_DATA['attachments'])} files")
    for att in EMAIL_DATA["attachments"]:
        print(f"     • {att['filename']} at {att['filepath']}")
        print(f"       File exists: {os.path.exists(att['filepath'])}")

    print("\n3. Processing email with attachments...")
    result = await orchestrator.process_email(EMAIL_DATA)

    print("\n4. Results:")
    print(f"   - Success: {result.get('success', False)}")
    print(f"   - Email ID: {result.get('email_id', 'N/A')}")
    print(f"   - Tool calls: {result.get('autonomous_actions', 0)}")

    if result.get("tool_calls"):
        print("\n5. Tool calls made:")
        for tc in result["tool_calls"]:
            print(f"   - {tc['tool']}")
            if "attachments" in str(tc.get("args", {})):
                print("     ✓ Attachments passed to tool")

    print("\n6. Summary:")
    summary = result.get("final_summary", "")
    if "processed" in summary.lower() or "attachment" in summary.lower():
        print("   ✅ Attachments were processed")
    else:
        print("   ⚠️  Check if attachments were processed")

    # Parse the summary to check for order details
    if "order_id" in summary:
        print("\n7. Order Details Extracted:")
        try:
            # Try to parse JSON from summary
            import re

            json_match = re.search(r"\{.*\}", summary, re.DOTALL)
            if json_match:
                order_data = json.loads(json_match.group())
                print(f"   - Order ID: {order_data.get('order_id', 'N/A')}")
                print(f"   - Customer: {order_data.get('customer', 'N/A')}")
                print(f"   - Items: {order_data.get('total_items', 0)}")
                print(
                    f"   - Confidence: {order_data.get('extraction_confidence', 0):.2%}"
                )
                print(f"   - Action: {order_data.get('recommended_action', 'N/A')}")
        except:
            pass

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    return result


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_filepath_processing())
