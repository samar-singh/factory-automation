"""Test the enhanced UI by adding more test data and showing available features"""

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)
from factory_automation.factory_models.order_models import (
    OrderPriority,
    QueuedRecommendation,
    RecommendationType,
)


def add_test_recommendations():
    """Add test recommendations to demonstrate UI features"""

    print("\n=== Adding Test Recommendations for UI Demo ===\n")

    manager = HumanInteractionManager()

    # Create diverse test recommendations
    test_data = [
        {
            "customer": "AllenSolly@example.com",
            "type": RecommendationType.EMAIL_RESPONSE,
            "data": {
                "email_draft": {
                    "subject": "Re: Urgent Order - Allen Solly Tags",
                    "body": "Thank you for your order. We have the following tags available:\n"
                    "- TBAL001: Main Tag (500 units)\n"
                    "- TBAL002: Fit Tag (300 units)\n"
                    "Please confirm if you'd like to proceed.",
                },
                "inventory_matches": [
                    {
                        "tag_code": "TBAL001",
                        "name": "Allen Solly Main Tag",
                        "quantity": 500,
                        "price": 25,
                    },
                    {
                        "tag_code": "TBAL002",
                        "name": "Allen Solly Fit Tag",
                        "quantity": 300,
                        "price": 15,
                    },
                ],
                "order_details": {
                    "total_quantity": 800,
                    "estimated_amount": 17000,
                    "delivery_date": "2025-01-20",
                },
            },
            "confidence": 0.88,
            "priority": OrderPriority.URGENT,
        },
        {
            "customer": "PeterEngland@retail.com",
            "type": RecommendationType.DOCUMENT_GENERATION,
            "data": {
                "document_type": "proforma_invoice",
                "invoice_number": "PI-2025-001234",
                "items": [
                    {
                        "tag_code": "TPPE001",
                        "name": "Peter England Main Tag",
                        "quantity": 1000,
                        "price": 22,
                        "amount": 22000,
                    },
                    {
                        "tag_code": "TPPE002",
                        "name": "Peter England Care Label",
                        "quantity": 1000,
                        "price": 8,
                        "amount": 8000,
                    },
                ],
                "total_amount": 30000,
                "customer_details": {
                    "name": "Peter England Retail Pvt Ltd",
                    "address": "Mumbai, Maharashtra",
                    "gst": "27AAACT2345K1Z5",
                },
                "payment_terms": "50% advance, 50% on delivery",
            },
            "confidence": 0.95,
            "priority": OrderPriority.HIGH,
        },
        {
            "customer": "VanHeusen@corporate.com",
            "type": RecommendationType.INVENTORY_UPDATE,
            "data": {
                "reason": "Low stock alert for popular items",
                "updates": [
                    {
                        "tag_code": "TVHS001",
                        "field": "quantity",
                        "old_value": 50,
                        "new_value": 0,
                        "action": "reorder",
                    },
                    {
                        "tag_code": "TVHS002",
                        "field": "price",
                        "old_value": 30,
                        "new_value": 32,
                        "action": "price_update",
                    },
                ],
                "recommended_action": "Order 500 units of TVHS001 from supplier",
                "urgency": "high",
            },
            "confidence": 0.72,
            "priority": OrderPriority.HIGH,
        },
        {
            "customer": "LouisPhilippe@premium.com",
            "type": RecommendationType.CUSTOMER_FOLLOW_UP,
            "data": {
                "reason": "Pending payment for previous order",
                "order_reference": "ORD-20250105-LP001",
                "amount_pending": 45000,
                "days_overdue": 7,
                "suggested_message": "Dear Louis Philippe team, this is a gentle reminder about the pending payment...",
                "follow_up_actions": [
                    "Send reminder email",
                    "Call customer",
                    "Hold new orders",
                ],
            },
            "confidence": 0.65,
            "priority": OrderPriority.MEDIUM,
        },
        {
            "customer": "ColorPlus@fashion.com",
            "type": RecommendationType.NEW_ITEM_ADDITION,
            "data": {
                "reason": "Customer requesting new tag design",
                "item_details": {
                    "tag_code": "TCP001-NEW",
                    "description": "ColorPlus Premium Woven Label",
                    "material": "Satin",
                    "size": "3x2 inches",
                    "minimum_order": 1000,
                    "estimated_price": 35,
                },
                "customer_requirements": "Gold foiling with embossed logo",
                "feasibility": "Possible with 10-day lead time",
            },
            "confidence": 0.78,
            "priority": OrderPriority.MEDIUM,
        },
        {
            "customer": "test@lowconfidence.com",
            "type": RecommendationType.EMAIL_RESPONSE,
            "data": {
                "email_draft": {
                    "subject": "Clarification Needed",
                    "body": "We need more information to process your order...",
                },
                "issues": [
                    "Unclear specifications",
                    "Missing quantity",
                    "Unknown tag codes",
                ],
                "action_needed": "human_clarification",
            },
            "confidence": 0.35,
            "priority": OrderPriority.LOW,
        },
    ]

    queue_ids = []
    for item in test_data:
        rec = QueuedRecommendation(
            order_id=None,
            customer_email=item["customer"],
            recommendation_type=item["type"],
            recommendation_data=item["data"],
            confidence_score=item["confidence"],
            priority=item["priority"],
        )

        queue_id = manager.add_to_recommendation_queue(rec)
        queue_ids.append(queue_id)

        print(f"✅ Added: {item['type'].value}")
        print(f"   Customer: {item['customer']}")
        print(f"   Confidence: {item['confidence']*100:.1f}%")
        print(f"   Priority: {item['priority'].value}")
        print(f"   Queue ID: {queue_id}")
        print()

    print("\n📊 Summary:")
    print(f"   Total recommendations added: {len(queue_ids)}")
    print("   Ready for review in UI at: http://localhost:7862")
    print()
    print("🎯 UI Features to Test:")
    print("   1. Database Queue tab - See all pending recommendations")
    print("   2. Select multiple items with checkboxes for batch processing")
    print("   3. Create batches with custom names")
    print("   4. Review batch items with email templates")
    print("   5. Preview documents (Proforma Invoice, Quotation, etc.)")
    print("   6. Choose which databases to update (PostgreSQL, ChromaDB, Excel)")
    print("   7. Filter by priority (Urgent, High, Medium, Low)")
    print("   8. View queue metrics and statistics")

    return queue_ids


if __name__ == "__main__":
    queue_ids = add_test_recommendations()

    print("\n✨ Test data added successfully!")
    print("📱 Open http://localhost:7862 in your browser")
    print("🔍 Navigate to the 'Database Queue' tab to see all recommendations")
