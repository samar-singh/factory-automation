#!/usr/bin/env python3
"""Test the complete factory automation flow with human review"""

import json
import time

import requests

# Test email content
test_email = """From: testing@interface-direct.com
To: orders@yourcompany.com
Subject: PEC FIT TAG ORDER - Urgent

Dear Team,

We need the following reversible tags urgently:

1. PEC Bootcut - 500 pieces  
2. PEC Slim Fit - 300 pieces
3. PEC Regular - 200 pieces

All tags should be reversible with our standard pricing.

Thanks,
Test Customer
Interface Direct Ltd."""


def test_order_processing():
    """Test the order processing endpoint"""
    print("📧 Testing Order Processing...")

    # Call the order processing endpoint
    response = requests.post(
        "http://127.0.0.1:7861/run/process_order",
        json={"data": [test_email]},
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        result = response.json()
        print("✅ Order processed successfully!")
        print(f"Response: {json.dumps(result, indent=2)}")
        return True
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return False


def check_review_queue():
    """Check the human review queue"""
    print("\n👀 Checking Human Review Queue...")

    # Wait a bit for processing
    time.sleep(3)

    # Refresh the queue
    response = requests.post(
        "http://127.0.0.1:7861/run/refresh_queue",
        json={"data": ["All"]},  # Priority filter
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        result = response.json()
        data = result.get("data", [])

        if data and len(data) > 0:
            queue_data = data[0]  # First item is the queue dataframe
            data[1] if len(data) > 1 else {}  # Second item is stats

            print(f"✅ Found {len(queue_data)} items in review queue")

            # Display queue items
            if queue_data:
                print("\nReview Queue:")
                for item in queue_data:
                    print(
                        f"- ID: {item[0]}, Customer: {item[1]}, Confidence: {item[3]}"
                    )

                return (
                    queue_data[0][0] if queue_data else None
                )  # Return first review ID
            else:
                print("⚠️  Queue is empty")
        else:
            print("⚠️  No data returned")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

    return None


def open_review(review_id):
    """Open a specific review"""
    print(f"\n📂 Opening Review: {review_id}")

    response = requests.post(
        "http://127.0.0.1:7861/run/open_review",
        json={"data": [review_id]},
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        result = response.json()
        data = result.get("data", [])

        if data and len(data) >= 6:
            print("✅ Review opened successfully!")
            print(f"Customer: {data[1]}")
            print(f"Subject: {data[2]}")
            print(f"Confidence: {data[3]}")

            # Check items
            if data[4]:
                print(f"\nRequested Items: {json.dumps(data[4], indent=2)}")

            # Check search results
            if data[5]:
                print(f"\nSearch Results: {json.dumps(data[5], indent=2)}")

            return True
        else:
            print("⚠️  No review data returned")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

    return False


def main():
    """Run the complete test flow"""
    print("🏭 Factory Automation Complete Flow Test")
    print("=" * 50)

    # Test 1: Process an order
    if test_order_processing():

        # Test 2: Check review queue
        review_id = check_review_queue()

        if review_id:
            # Test 3: Open the review
            if open_review(review_id):
                print("\n✅ All tests passed! The system is working correctly.")
                print("\n📋 Next Steps:")
                print("1. Go to http://127.0.0.1:7861")
                print("2. Navigate to the Human Review tab")
                print("3. Click 'Open Review' and make a decision")
                print("4. Monitor the logs for processing")
            else:
                print("\n❌ Failed to open review")
        else:
            print("\n❌ No reviews found in queue")
    else:
        print("\n❌ Order processing failed")


if __name__ == "__main__":
    main()
