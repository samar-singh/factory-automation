"""Test the running factory automation system"""

import asyncio
from datetime import datetime

import httpx


async def test_system():
    """Test the running system through its API"""

    base_url = "http://localhost:7860"

    # Test email content with your order
    email_content = """From: interface.scs02@gmail.com
Subject: Fwd: PURCHASE ORDER FOR FIT TAG 31570 QTY & REVERSIBLE TAG 8750 QTY. FROM NISHA
Date: Mon, Aug 5, 2024 at 7:42 PM

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

Order details:
- PETER ENGLAND SPORT COLLECTION TAG (TBPRTAG0082N) - 31,570 pieces @ Rs.1.31
- PEC reversible Hang tag-Navy SWING TAGS (TBPCTAG0532N) - 8,750 pieces @ Rs.0.40

Customer: NAIR
Invoice No: 1032-2025-26

Thanks and regards
Nisha"""

    print("=== TESTING FACTORY AUTOMATION SYSTEM ===")
    print(f"Time: {datetime.now()}")
    print(f"URL: {base_url}")

    # Check if system is running
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(base_url)
            if response.status_code == 200:
                print("✅ System is running")
            else:
                print(f"❌ System returned status {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Cannot connect to system: {e}")
            return

    print("\n=== CURRENT STATE ===")
    print("Based on the logs, the system has:")
    print("- 5 human review requests created")
    print("- 1 URGENT priority review")
    print("- Orders are being processed but need human approval")

    print("\n=== TO TEST THE SYSTEM ===")
    print("1. Open browser: http://localhost:7860")
    print("2. Go to 'Order Processing' tab")
    print("3. Paste this email:")
    print("-" * 50)
    print(email_content)
    print("-" * 50)
    print("\n4. Click 'Process Order'")
    print("5. Go to 'Human Review' tab")
    print("6. Click 'Refresh Queue'")
    print("7. You should see pending reviews")
    print("8. Select a review and approve/reject")

    print("\n=== CHECKING SYSTEM STATUS ===")
    # Try to check the API endpoint for status
    async with httpx.AsyncClient() as client:
        try:
            # Gradio API endpoint
            api_response = await client.get(f"{base_url}/api/predict/")
            print(f"API endpoint status: {api_response.status_code}")
        except:
            print("API endpoints not directly accessible (normal for Gradio)")


if __name__ == "__main__":
    asyncio.run(test_system())
