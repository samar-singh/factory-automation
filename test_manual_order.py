"""Manually test order processing with human review"""


def test_manual_order():
    """Test order processing through the Gradio interface"""

    base_url = "http://localhost:7860"

    print("=== MANUAL TESTING INSTRUCTIONS ===")
    print(f"\n1. Open your browser to: {base_url}")
    print("\n2. You should see 3 tabs:")
    print("   - 🤖 Order Processing")
    print("   - 👤 Human Review")
    print("   - 📊 System Status")

    print("\n3. In the Order Processing tab, paste this email:")
    print("-" * 60)

    email_content = """From: interface.scs02@gmail.com
Subject: Fwd: PURCHASE ORDER FOR FIT TAG 31570 QTY & REVERSIBLE TAG 8750 QTY. FROM NISHA
Date: Mon, Aug 5, 2024 at 7:42 PM

---------- Forwarded message ---------
From: Interface Direct <interface.scs02@gmail.com>
Subject: PURCHASE ORDER FOR FIT TAG 31570 QTY & REVERSIBLE TAG 8750 QTY. FROM NISHA
To: Sreeja Rajmohan <sreejarajmohan1234@gmail.com>

Dear Sreeja,

Good evening.

Please process the order and share the proforma attached.

PEC FIT TAG. 31570 QTY.
And
PEC reversible tag 8750 qty.

Details from Excel attachment:
- PETER ENGLAND SPORT COLLECTION TAG (TBPRTAG0082N) - 31,570 pieces @ Rs.1.31
- PEC reversible Hang tag-Navy SWING TAGS (TBPCTAG0532N) - 8,750 pieces @ Rs.0.40

Customer: NAIR
Invoice No: 1032-2025-26

Thanks and regards
Nisha"""

    print(email_content)
    print("-" * 60)

    print("\n4. Click the '📧 Process Order' button")
    print("\n5. You should see:")
    print("   - Processing Result (JSON)")
    print("   - Extracted Information showing customer email")

    print("\n6. Go to the Human Review tab")
    print("\n7. Click 'Refresh Queue' button")
    print("\n8. You should see pending reviews from the mock emails")
    print("   - The system already created 5 reviews from mock emails")
    print("   - Your new order should appear as well")

    print("\n9. Select a review from the dropdown")
    print("\n10. You can:")
    print("    - See the order details")
    print("    - View search results")
    print("    - Choose a decision (Approve/Reject/Clarify/Alternative/Defer)")
    print("    - Add notes")
    print("    - Submit decision")

    print("\n=== CURRENT SYSTEM STATE ===")
    print("The system has already processed 5 mock emails and created reviews:")
    print("- REV-20250805-201448-0001 through REV-20250805-201451-0005")
    print("- One is marked as URGENT priority")
    print("- All are waiting for human review")

    print("\n=== TESTING THE 90% THRESHOLD ===")
    print("Since we don't have exact inventory matches for TBPRTAG0082N,")
    print("the confidence will be <90%, triggering human review as expected.")


if __name__ == "__main__":
    test_manual_order()
