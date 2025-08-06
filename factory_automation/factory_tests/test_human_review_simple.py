#!/usr/bin/env python3
"""Simple test to check human review creation"""

import asyncio
import json

from factory_automation.factory_agents.human_interaction_manager import Priority
from factory_automation.factory_agents.orchestrator_with_human import (
    OrchestratorWithHuman,
)
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_direct_review_creation():
    """Test creating review request directly"""

    print("=== Testing Direct Review Creation ===\n")

    # Initialize components
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    human_manager = orchestrator.human_manager

    # Create a review request directly
    print("1️⃣ Creating review request directly...")

    email_data = {
        "from": "test@example.com",
        "subject": "Test Order",
        "body": "Need 1000 Allen Solly tags",
    }

    search_results = [
        {"name": "AS Tag", "code": "AS001", "similarity_score": 0.75, "stock": 5000}
    ]

    extracted_items = [{"item": "Allen Solly tags", "quantity": 1000}]

    review = await human_manager.create_review_request(
        email_data=email_data,
        search_results=search_results,
        confidence_score=75.0,
        extracted_items=extracted_items,
        priority=Priority.HIGH,
    )

    print(f"✅ Created review: {review.request_id}")
    print(f"   Status: {review.status.value}")
    print(f"   Priority: {review.priority.value}")

    # Check if it's in the queue
    print("\n2️⃣ Checking review queue...")
    pending = await human_manager.get_pending_reviews()

    print(f"Total pending reviews: {len(pending)}")

    if pending:
        for r in pending:
            print(f"  - {r.request_id}: {r.customer_email} ({r.confidence_score}%)")

    # Test the create_human_review tool
    print("\n3️⃣ Testing create_human_review tool...")

    # Get the tool
    create_review_tool = None
    for tool in orchestrator.tools:
        if hasattr(tool, "__name__") and tool.__name__ == "create_human_review":
            create_review_tool = tool
            break

    if create_review_tool:
        # Call the tool
        result = await create_review_tool(
            email_data=json.dumps(email_data),
            search_results=json.dumps(search_results),
            confidence_score=75.0,
            extracted_items=json.dumps(extracted_items),
        )

        print(f"Tool result: {result}")
    else:
        print("❌ create_human_review tool not found!")

    # Final check
    print("\n4️⃣ Final queue check...")
    final_pending = await human_manager.get_pending_reviews()
    print(f"Total pending reviews: {len(final_pending)}")

    stats = human_manager.get_review_statistics()
    print(f"\nStatistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_direct_review_creation())
