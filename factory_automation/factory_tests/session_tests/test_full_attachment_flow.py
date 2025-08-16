#!/usr/bin/env python3
"""
Complete test of attachment processing flow
Tests the full pipeline from UI to order processor
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set specific loggers to debug
logging.getLogger("factory_automation.factory_agents.orchestrator_v3_agentic").setLevel(
    logging.DEBUG
)
logging.getLogger("factory_automation.factory_agents.order_processor_agent").setLevel(
    logging.DEBUG
)


async def test_complete_flow():
    """Test the complete attachment processing flow"""

    print("\n" + "=" * 60)
    print("COMPLETE ATTACHMENT FLOW TEST")
    print("=" * 60 + "\n")

    # Step 1: Create test files
    print("1. Creating test files...")

    # Create CSV file
    csv_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    csv_file.write("Item,Quantity,Brand,Price\n")
    csv_file.write("Blue Shirt Tag,500,Peter England,2.50\n")
    csv_file.write("Red Polo Tag,300,Allen Solly,3.00\n")
    csv_file.close()

    # Create PDF file (simple text file renamed to .pdf for testing)
    pdf_file = tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False)
    pdf_file.write("Purchase Order #12345\n")
    pdf_file.write("Date: 2025-01-08\n")
    pdf_file.write("Items: See attached CSV\n")
    pdf_file.close()

    print(f"   ✓ CSV: {csv_file.name}")
    print(f"   ✓ PDF: {pdf_file.name}")

    # Step 2: Initialize system
    print("\n2. Initializing system...")
    from factory_automation.factory_agents.orchestrator_with_human import (
        OrchestratorWithHuman,
    )
    from factory_automation.factory_database.vector_db import ChromaDBClient

    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client, use_mock_gmail=False)
    print("   ✓ Orchestrator initialized")

    # Step 3: Simulate what the UI does
    print("\n3. Preparing email data (simulating UI)...")

    email_body = """
From: customer@example.com
Subject: Urgent Order - Blue and Red Tags
Date: Wednesday, 8 January 2025

Dear Team,

Please process our urgent order for:
- 500 Blue Shirt Tags for Peter England
- 300 Red Polo Tags for Allen Solly

Order details are in the attached CSV file.
Purchase order document is also attached.

Best regards,
Customer
"""

    # This is exactly what run_factory_automation.py does
    attachment_list = [
        {
            "filename": os.path.basename(csv_file.name),
            "filepath": os.path.abspath(csv_file.name),
            "mime_type": "text/csv",
        },
        {
            "filename": os.path.basename(pdf_file.name),
            "filepath": os.path.abspath(pdf_file.name),
            "mime_type": "application/pdf",
        },
    ]

    email_data = {
        "message_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from": "customer@example.com",
        "subject": "Urgent Order - Blue and Red Tags",
        "body": email_body,
        "email_type": "order",
        "attachments": attachment_list,
    }

    print(f"   ✓ Email with {len(attachment_list)} attachments")
    for att in attachment_list:
        print(f"     - {att['filename']}: {att['filepath']}")
        print(f"       Exists: {os.path.exists(att['filepath'])}")

    # Step 4: Process the email
    print("\n4. Processing email through orchestrator...")

    try:
        result = await orchestrator.process_email(email_data)

        print("\n5. Results:")
        print(f"   - Success: {result.get('success', False)}")
        print(f"   - Email ID: {result.get('email_id', 'N/A')}")

        if result.get("success"):
            print("   ✅ Email processed successfully")

            # Check if attachments were processed
            if "attachment" in str(result).lower() or "csv" in str(result).lower():
                print("   ✅ Attachments were processed")
            else:
                print("   ⚠️  Check if attachments were processed")
        else:
            print(f"   ❌ Processing failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback

        traceback.print_exc()

    # Step 5: Clean up
    print("\n6. Cleaning up...")
    os.unlink(csv_file.name)
    os.unlink(pdf_file.name)
    print("   ✓ Test files deleted")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set")
        print("   The orchestrator will fail when trying to use AI")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        print()

    asyncio.run(test_complete_flow())
