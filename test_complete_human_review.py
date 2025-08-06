"""Complete test of order processing with human review flow"""

import asyncio
import json
from datetime import datetime

from factory_automation.factory_agents.orchestrator_with_human import (
    OrchestratorWithHuman,
)

# Import our components
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_human_review_flow():
    # Initialize orchestrator with human interaction
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)

    # The email content
    email_data = {
        "message_id": "test-001",
        "from": "interface.scs02@gmail.com",
        "subject": "Fwd: PURCHASE ORDER FOR FIT TAG 31570 QTY & REVERSIBLE TAG 8750 QTY. FROM NISHA",
        "body": """---------- Forwarded message ---------
From: Interface Direct <interface.scs02@gmail.com>
Date: Mon, Aug 5, 2024 at 7:42 PM
Subject: PURCHASE ORDER FOR FIT TAG 31570 QTY & REVERSIBLE TAG 8750 QTY. FROM NISHA
To: Sreeja Rajmohan <sreejarajmohan1234@gmail.com>

Dear Sreeja,

Good evening.

Please process the order and share the proforma attached.

PEC FIT TAG. 31570 QTY.
And
PEC reversible tag 8750 qty.

Attached file shows the following items:
- PETER ENGLAND SPORT COLLECTION TAG (TBPRTAG0082N) - 31,570 pieces @ Rs.1.31
- PEC reversible Hang tag-Navy SWING TAGS (TBPCTAG0532N) - 8,750 pieces @ Rs.0.40

Customer: NAIR
Invoice No: 1032-2025-26

Thanks and regards
Nisha""",
        "received_at": datetime.now().isoformat(),
    }

    # Use the orchestrator's process_complete_order tool
    print("=== PROCESSING ORDER THROUGH ORCHESTRATOR ===")

    # Create the tool function that would be called by the agent
    process_order_tool = None
    for tool in orchestrator.tools:
        if hasattr(tool, "_name") and tool._name == "process_complete_order":
            process_order_tool = tool
            break

    if process_order_tool:
        # Call the tool directly
        result = await process_order_tool(json.dumps(email_data))
        print(f"\nTool Result: {result}")

        # Parse the result
        if "Error" not in result:
            result_data = json.loads(result)

            print("\n=== EXTRACTED ORDER DETAILS ===")
            print(f"Order ID: {result_data.get('order_id', 'N/A')}")
            print(f"Customer: {result_data.get('customer_name', 'N/A')}")
            print(f"Confidence: {result_data.get('overall_confidence', 0):.2%}")
            print(f"Action: {result_data.get('action_taken', 'N/A')}")

            # Since confidence will be low, it should create a human review
            if result_data.get("action_taken") == "Created human review request":
                print("\n✅ Human review request created!")
                print("Reason: Orders with <90% confidence require human review")

    # Check human review queue
    print("\n=== CHECKING HUMAN REVIEW QUEUE ===")
    pending_reviews = await orchestrator.human_manager.get_pending_reviews()

    if pending_reviews:
        print(f"Found {len(pending_reviews)} pending reviews:")
        for review in pending_reviews:
            print(f"\n--- Review: {review.request_id} ---")
            print(f"Customer: {review.customer_email}")
            print(f"Subject: {review.subject}")
            print(f"Confidence: {review.confidence_score:.2%}")
            print(f"Priority: {review.priority.value}")
            print(f"Status: {review.status.value}")
            print(f"Items: {len(review.items)} extracted")

            # Show what options are available for human reviewer
            print("\nHuman reviewer can choose:")
            print("  1. Approve - Process the order as-is")
            print("  2. Reject - Decline the order")
            print("  3. Clarify - Request more information from customer")
            print("  4. Alternative - Suggest alternative products")
            print("  5. Defer - Push to back of queue for later review")

            # Simulate human decision
            print("\n=== SIMULATING HUMAN DECISION ===")
            decision_result = await orchestrator.human_manager.submit_review_decision(
                request_id=review.request_id,
                decision="approve",
                notes="Tags match our inventory. Quantities confirmed. Proceed with order.",
            )

            print(f"Decision submitted: {json.dumps(decision_result, indent=2)}")
    else:
        print("❌ No reviews found in queue - this suggests an issue with the flow")

    # Check final statistics
    stats = orchestrator.get_review_statistics()
    print("\n=== REVIEW STATISTICS ===")
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_human_review_flow())
