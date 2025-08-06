"""Simulate order processing to debug duplicate reviews"""

import asyncio


async def simulate_order():
    """Simulate processing an order through the Gradio API"""

    # Wait for system to fully start
    print("Waiting for system to initialize...")
    await asyncio.sleep(3)

    # Test email

    print("\n=== SIMULATING ORDER PROCESSING ===")
    print("Email from: test@example.com")
    print("Subject: Test Order for Debugging")

    # Monitor logs for 30 seconds after submission
    print("\nMonitoring for duplicate review creation...")

    # Since we can't directly call Gradio API, let's check what's happening
    print("\nTo manually test:")
    print("1. Go to http://127.0.0.1:7861")
    print("2. Paste the email above in Order Processing")
    print("3. Click Process Order")
    print("4. Watch the logs for duplicate reviews")

    # Check logs
    await asyncio.sleep(5)

    print("\n=== CHECKING LOGS ===")
    with open("factory_debug.log", "r") as f:
        lines = f.readlines()
        review_lines = [
            line for line in lines if "REV-" in line and "review request" in line
        ]

        print(f"Found {len(review_lines)} review creation entries:")
        for line in review_lines:
            print(f"  - {line.strip()}")


if __name__ == "__main__":
    asyncio.run(simulate_order())
