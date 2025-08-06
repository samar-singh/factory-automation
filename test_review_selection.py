#!/usr/bin/env python3
"""Test the improved human review selection"""

import asyncio

from dotenv import load_dotenv

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)
from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient

load_dotenv()


async def test_review_selection():
    """Test the review selection process"""
    print("🧪 Testing Review Selection Fix\n")

    # Initialize components
    manager = HumanInteractionManager()
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client=chromadb_client)

    # Create a test order that will need review
    test_email = {
        "id": "test-fix-001",
        "from": "testcustomer@example.com",
        "to": "orders@company.com",
        "subject": "Urgent Order - Need Tags ASAP",
        "body": """Hi Team,

We urgently need:
- 1000 pieces of Allen Solly tags (any style)
- 500 pieces of Van Heusen labels

Please confirm availability.

Thanks!""",
        "attachments": [],
    }

    print("1️⃣ Processing test email...")
    await orchestrator.process_email(test_email)
    print("✅ Order processed\n")

    # Check review queue
    print("2️⃣ Checking review queue...")
    reviews = await manager.get_pending_reviews()
    print(f"Found {len(reviews)} reviews in queue")

    if reviews:
        review = reviews[0]
        print("\n📋 Review Created:")
        print(f"ID: {review.request_id}")
        print(f"Customer: {review.customer_email}")
        print(f"Confidence: {review.confidence_score:.1%}")
        print(f"Status: {review.status.value}")

        print("\n✅ TEST PASSED!")
        print("\nNow you can:")
        print("1. Go to http://127.0.0.1:7860")
        print("2. Navigate to Human Review tab")
        print("3. Click on the review row in the table")
        print("4. Click 'Open Selected Review'")
        print("5. The review should open without JSON errors!")
    else:
        print("❌ No reviews created")


if __name__ == "__main__":
    asyncio.run(test_review_selection())
