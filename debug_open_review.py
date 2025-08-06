"""Debug the Open Review error"""

import asyncio

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)


async def debug_open_review():
    """Check what data is in the review"""

    # Create a shared manager instance (should be same as in running system)
    manager = HumanInteractionManager()

    # Get pending reviews
    reviews = await manager.get_pending_reviews()

    print(f"Found {len(reviews)} pending reviews\n")

    if reviews:
        # Get the first review
        review = reviews[0]
        print(f"=== Review Details: {review.request_id} ===")
        print(f"Email ID: {review.email_id}")
        print(f"Customer: {review.customer_email}")
        print(f"Subject: {review.subject}")
        print(f"Confidence: {review.confidence_score}")

        print("\n=== Items Data ===")
        print(f"Type: {type(review.items)}")
        print(f"Content: {review.items}")

        print("\n=== Search Results Data ===")
        print(f"Type: {type(review.search_results)}")
        print(f"Content: {review.search_results}")

        # Test formatting like the UI does
        print("\n=== Testing UI Formatting ===")

        # Format items
        items_formatted = []
        if review.items:
            for item in review.items[:10]:
                if isinstance(item, dict):
                    items_formatted.append(
                        {
                            "item_id": item.get("item_id", "N/A"),
                            "tag_code": item.get("tag_code", "N/A"),
                            "quantity": item.get("quantity", 0),
                            "tag_type": item.get("tag_type", "unknown"),
                        }
                    )

        print(f"Formatted items: {items_formatted}")

        # Format search results
        search_results_formatted = []
        if review.search_results:
            for result in review.search_results[:5]:
                if isinstance(result, dict):
                    search_results_formatted.append(
                        {
                            "name": result.get(
                                "name", result.get("tag_code", "Unknown")
                            ),
                            "code": result.get("code", result.get("tag_code", "N/A")),
                            "brand": result.get("brand", "Unknown"),
                            "similarity": f"{result.get('similarity_score', result.get('confidence', 0)) * 100:.1f}%",
                            "price": result.get("price", 0),
                            "stock": result.get("stock", 0),
                        }
                    )

        print(f"Formatted search results: {search_results_formatted}")

        # Check if data would cause JSON error
        import json

        try:
            json.dumps(
                items_formatted if items_formatted else [{"message": "No items"}]
            )
            print("\n✅ Items data is JSON serializable")
        except Exception as e:
            print(f"\n❌ Items data JSON error: {e}")

        try:
            json.dumps(
                search_results_formatted
                if search_results_formatted
                else [{"message": "No results"}]
            )
            print("✅ Search results data is JSON serializable")
        except Exception as e:
            print(f"❌ Search results JSON error: {e}")


if __name__ == "__main__":
    asyncio.run(debug_open_review())
