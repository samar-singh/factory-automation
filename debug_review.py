"""Debug the human review data"""

import asyncio

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)


async def debug_reviews():
    """Check what's in the review queue"""

    manager = HumanInteractionManager()

    # Get pending reviews
    reviews = await manager.get_pending_reviews()

    print(f"Found {len(reviews)} pending reviews")

    for review in reviews:
        print(f"\n=== Review: {review.request_id} ===")
        print(f"Customer: {review.customer_email}")
        print(f"Subject: {review.subject}")
        print(f"Confidence: {review.confidence_score}")
        print(f"Items type: {type(review.items)}")
        print(f"Items: {review.items}")
        print(f"Search results type: {type(review.search_results)}")
        print(f"Search results: {review.search_results}")

        # Get full details
        full_review = await manager.get_review_details(review.request_id)
        if full_review:
            print("Full review data available: Yes")
        else:
            print("Full review data available: No")


if __name__ == "__main__":
    asyncio.run(debug_reviews())
