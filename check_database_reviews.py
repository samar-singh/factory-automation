#!/usr/bin/env python3
"""Check review decisions in the database"""

import json

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)
from factory_automation.factory_database.connection import get_db_session
from factory_automation.factory_database.models import ReviewDecision


def check_database_reviews():
    """Display all review decisions from the database"""

    print("📋 REVIEW DECISIONS IN DATABASE")
    print("=" * 50)

    session = get_db_session()

    try:
        # Get all review decisions
        reviews = session.query(ReviewDecision).all()

        if reviews:
            print(f"\nTotal reviews in database: {len(reviews)}")

            for review in reviews:
                print(f"\n📌 Review: {review.review_id}")
                print(f"   Customer: {review.customer_email}")
                print(f"   Subject: {review.subject}")
                print(f"   Confidence: {review.confidence_score:.1%}")
                print(f"   Decision: {review.decision}")
                print(f"   Status: {review.status}")
                print(f"   Reviewed at: {review.reviewed_at}")
                print(
                    f"   Review duration: {review.review_duration_seconds:.1f} seconds"
                )
                print(f"   Notes: {review.review_notes}")

                if review.items:
                    print(f"   Items requested: {len(review.items)}")

                if review.alternative_items:
                    print(
                        f"   Alternatives: {json.dumps(review.alternative_items, indent=6)}"
                    )
        else:
            print("\n❌ No review decisions found in database")

        # Also check from HumanInteractionManager
        print("\n\n📋 REVIEW HISTORY FROM MANAGER (DB METHOD)")
        print("=" * 50)

        manager = HumanInteractionManager()
        db_history = manager.get_review_history_from_db(limit=10)

        if db_history:
            print(f"\nRetrieved {len(db_history)} reviews from database")
            for review in db_history[:3]:  # Show first 3
                print(
                    f"\n- {review['review_id']}: {review['decision']} ({review['status']})"
                )
                print(f"  Customer: {review['customer_email']}")
                print(f"  Reviewed: {review['reviewed_at']}")
        else:
            print("\n❌ No reviews retrieved via manager method")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    check_database_reviews()
