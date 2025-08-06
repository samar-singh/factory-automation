#!/usr/bin/env python3
"""Check review history in the system"""

import asyncio
import json

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)


async def check_review_history():
    """Display all completed reviews"""

    manager = HumanInteractionManager()

    print("📋 REVIEW HISTORY")
    print("=" * 50)

    # Get all completed reviews
    if manager.completed_reviews:
        print(f"\nTotal completed reviews: {len(manager.completed_reviews)}")

        for review_id, review in manager.completed_reviews.items():
            print(f"\n📌 Review: {review_id}")
            print(f"   Customer: {review.customer_email}")
            print(f"   Subject: {review.subject}")
            print(f"   Confidence: {review.confidence_score:.1%}")
            print(f"   Decision: {review.decision}")
            print(f"   Status: {review.status.value}")
            print(f"   Reviewed at: {review.reviewed_at}")
            print(f"   Notes: {review.review_notes}")

            if review.alternative_items:
                print(
                    f"   Alternatives: {json.dumps(review.alternative_items, indent=6)}"
                )
    else:
        print("\n❌ No completed reviews found in memory")

    # Get statistics
    stats = manager.get_review_statistics()
    print("\n📊 STATISTICS")
    print(f"   Total Pending: {stats['total_pending']}")
    print(f"   Total Completed: {stats['total_completed']}")
    print(f"   Average Review Time: {stats['average_review_time_seconds']:.1f} seconds")

    if stats["status_distribution"]:
        print("\n   Status Distribution:")
        for status, count in stats["status_distribution"].items():
            print(f"     {status}: {count}")


if __name__ == "__main__":
    asyncio.run(check_review_history())
