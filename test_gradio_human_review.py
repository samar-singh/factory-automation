"""Test human review through Gradio interface"""

import requests


def test_gradio_human_review():
    """Test order processing and human review through Gradio API"""

    # Gradio API endpoint
    base_url = "http://127.0.0.1:7860"

    # Check if Gradio is running
    try:
        response = requests.get(base_url)
        if response.status_code != 200:
            print("❌ Gradio interface not running. Please start it first.")
            return
    except:
        print("❌ Cannot connect to Gradio. Please start the interface first.")
        return

    print("✅ Gradio interface is running")

    # Test email content
    email_content = """
Subject: Fwd: PURCHASE ORDER FOR FIT TAG 31570 QTY & REVERSIBLE TAG 8750 QTY. FROM NISHA

---------- Forwarded message ---------
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

The order includes:
- PETER ENGLAND SPORT COLLECTION TAG (TBPRTAG0082N) - 31,570 pieces
- PEC reversible Hang tag-Navy SWING TAGS (TBPCTAG0532N) - 8,750 pieces

Customer: NAIR
Invoice No: 1032-2025-26

Thanks and regards
Nisha
"""

    print("\n=== STEP 1: Process Order ===")
    print("Processing order email...")

    # Note: Since we're testing with the live Gradio app, we'll simulate the interaction
    # In real usage, users would paste this into the Order Processing tab

    print("\nEmail content to paste in Order Processing tab:")
    print("-" * 50)
    print(email_content)
    print("-" * 50)

    print("\n=== STEP 2: Check Human Review Queue ===")
    print("After processing, check the Human Review tab")
    print("Expected: 1 pending review with ~70% confidence")

    print("\n=== STEP 3: Human Decision Options ===")
    print("In the Human Review tab, you can:")
    print("1. Select the review from dropdown")
    print("2. Choose decision: Approve/Reject/Clarify/Alternative/Defer")
    print("3. Add notes")
    print("4. Submit decision")

    print("\n=== MANUAL TEST INSTRUCTIONS ===")
    print("1. Go to http://127.0.0.1:7860")
    print("2. Click on 'Order Processing' tab")
    print("3. Paste the email content above")
    print("4. Click 'Process Order'")
    print("5. Go to 'Human Review' tab")
    print("6. Refresh the queue")
    print("7. Select the review and make a decision")

    # Check if we can access the API endpoints
    print("\n=== CHECKING API ENDPOINTS ===")

    # Try to get the Gradio config
    try:
        config_response = requests.get(f"{base_url}/config")
        if config_response.status_code == 200:
            print("✅ Gradio API accessible")
            config = config_response.json()
            print(f"Components: {len(config.get('components', []))}")
        else:
            print("⚠️  Gradio API not fully accessible")
    except Exception as e:
        print(f"⚠️  Error accessing API: {e}")


if __name__ == "__main__":
    test_gradio_human_review()
