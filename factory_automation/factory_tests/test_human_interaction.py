"""Test script for Human Interaction System"""

import asyncio

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
    Priority
)
from factory_automation.factory_agents.orchestrator_with_human import (
    OrchestratorWithHuman
)
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_human_interaction():
    """Test the human interaction workflow"""
    
    print("=" * 50)
    print("Testing Human Interaction System")
    print("=" * 50)
    
    # Initialize components
    print("\n1. Initializing components...")
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    human_manager = orchestrator.human_manager
    
    # Test Case 1: Create review request for medium confidence order
    print("\n2. Creating test review request (65% confidence)...")
    
    test_email = {
        "message_id": "test_msg_001",
        "from": "allen.solly@example.com",
        "subject": "Urgent Order - 500 Black Woven Tags",
        "body": "We need 500 black woven tags with our logo. Size should be 2x1 inches. Need delivery ASAP.",
        "email_type": "order"
    }
    
    test_search_results = [
        {
            "item_id": "TAG001",
            "name": "Black Woven Tag Premium",
            "code": "BWP-001",
            "brand": "Allen Solly",
            "similarity_score": 0.65,
            "price": 15,
            "stock": 1000
        },
        {
            "item_id": "TAG002",
            "name": "Black Cotton Tag",
            "code": "BCT-002",
            "brand": "Generic",
            "similarity_score": 0.55,
            "price": 10,
            "stock": 500
        }
    ]
    
    test_items = [
        {
            "quantity": 500,
            "description": "black woven tags with logo",
            "specifications": {
                "size": "2x1",
                "color": "black",
                "material": "woven"
            }
        }
    ]
    
    # Create review request
    review = await human_manager.create_review_request(
        email_data=test_email,
        search_results=test_search_results,
        confidence_score=65.0,
        extracted_items=test_items
    )
    
    print(f"✅ Created review: {review.request_id}")
    print(f"   Priority: {review.priority.value}")
    print(f"   Status: {review.status.value}")
    print(f"   Confidence: {review.confidence_score}%")
    
    # Test Case 2: Check pending reviews
    print("\n3. Checking pending reviews...")
    
    pending = await human_manager.get_pending_reviews()
    print(f"   Total pending: {len(pending)}")
    
    urgent_reviews = await human_manager.get_pending_reviews(priority_filter=Priority.URGENT)
    print(f"   Urgent reviews: {len(urgent_reviews)}")
    
    # Test Case 3: Simulate human assignment
    print("\n4. Simulating reviewer assignment...")
    
    success = await human_manager.assign_review(review.request_id, "reviewer_001")
    print(f"   Assignment successful: {success}")
    
    # Test Case 4: Get review details
    print("\n5. Getting review details...")
    
    details = await human_manager.get_review_details(review.request_id)
    if details:
        print(f"   Review ID: {details.request_id}")
        print(f"   Assigned to: {details.assigned_to}")
        print(f"   Status: {details.status.value}")
    
    # Test Case 5: Simulate human decision
    print("\n6. Simulating human approval decision...")
    
    decision_result = await human_manager.submit_review_decision(
        request_id=review.request_id,
        decision="approve",
        notes="Items match requirements. Customer is regular. Approved for processing."
    )
    
    print(f"   Decision submitted: {decision_result['success']}")
    if decision_result['success']:
        print(f"   Review status: {decision_result['status']}")
        print(f"   Review time: {decision_result['review_time_seconds']:.1f} seconds")
    
    # Test Case 6: Create low confidence review needing alternatives
    print("\n7. Creating low confidence review (45%)...")
    
    test_email_2 = {
        "message_id": "test_msg_002",
        "from": "newcustomer@example.com",
        "subject": "Custom Tag Order",
        "body": "Need special holographic tags with QR codes",
        "email_type": "order"
    }
    
    review_2 = await human_manager.create_review_request(
        email_data=test_email_2,
        search_results=[],  # No good matches
        confidence_score=45.0,
        extracted_items=[{"quantity": 100, "description": "holographic tags with QR"}]
    )
    
    print(f"✅ Created low confidence review: {review_2.request_id}")
    
    # Simulate alternative suggestion
    alternative_items = [
        {"name": "Silver Holographic Tag", "code": "SHT-001", "brand": "Premium"},
        {"name": "QR Code Label", "code": "QRL-002", "brand": "Tech"}
    ]
    
    alt_decision = await human_manager.submit_review_decision(
        request_id=review_2.request_id,
        decision="alternative",
        notes="No exact match. Suggesting similar items.",
        alternative_items=alternative_items
    )
    
    print(f"   Alternative suggestion submitted: {alt_decision['success']}")
    
    # Test Case 7: Get statistics
    print("\n8. Getting review statistics...")
    
    stats = human_manager.get_review_statistics()
    print(f"   Total pending: {stats['total_pending']}")
    print(f"   Total completed: {stats['total_completed']}")
    print(f"   Status breakdown: {stats['status_breakdown']}")
    print(f"   Priority breakdown: {stats['priority_breakdown']}")
    print(f"   Avg review time: {stats['average_review_time_seconds']:.1f} seconds")
    
    # Test Case 8: Test orchestrator integration
    print("\n9. Testing orchestrator integration...")
    
    test_email_3 = {
        "message_id": "test_msg_003",
        "from": "myntra@example.com",
        "subject": "Order for eco-friendly tags",
        "body": "Need 1000 recycled paper tags",
        "attachments": []
    }
    
    # Process through orchestrator
    result = await orchestrator.process_email(test_email_3)
    
    print(f"   Processing complete: {result['success']}")
    print(f"   Tool calls made: {result.get('autonomous_actions', 0)}")
    
    # Test Case 9: Export data
    print("\n10. Exporting review data...")
    
    export_data = human_manager.export_review_data()
    print(f"   Exported {len(export_data['pending_reviews'])} pending reviews")
    print(f"   Exported {len(export_data['completed_reviews'])} completed reviews")
    
    print("\n" + "=" * 50)
    print("✅ Human Interaction System Test Complete!")
    print("=" * 50)
    
    return True


async def test_escalation():
    """Test review escalation"""
    
    print("\n" + "=" * 50)
    print("Testing Review Escalation")
    print("=" * 50)
    
    human_manager = HumanInteractionManager()
    
    # Create a low priority review
    test_email = {
        "message_id": "esc_test_001",
        "from": "customer@example.com",
        "subject": "Regular order",
        "body": "Need some tags",
        "email_type": "order"
    }
    
    review = await human_manager.create_review_request(
        email_data=test_email,
        search_results=[],
        confidence_score=70.0,
        extracted_items=[{"quantity": 50, "description": "tags"}]
    )
    
    print(f"\nCreated review: {review.request_id}")
    print(f"Initial priority: {review.priority.value}")
    
    # Escalate the review
    success = await human_manager.escalate_review(
        review.request_id,
        "Customer called - needs urgent delivery"
    )
    
    print(f"\nEscalation successful: {success}")
    
    # Check new priority
    updated = await human_manager.get_review_details(review.request_id)
    print(f"Updated priority: {updated.priority.value}")
    print(f"Notes: {updated.review_notes}")
    
    print("\n✅ Escalation test complete!")


def main():
    """Run all tests"""
    
    print("\n🚀 Starting Human Interaction System Tests\n")
    
    # Run main test
    asyncio.run(test_human_interaction())
    
    # Run escalation test
    asyncio.run(test_escalation())
    
    print("\n🎉 All tests completed successfully!")


if __name__ == "__main__":
    main()