"""Test the complete order processing with email and Excel attachment including images"""

import asyncio
from datetime import datetime

from factory_automation.factory_agents.excel_image_extractor import (
    enhance_excel_processing,
)
from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)
from factory_automation.factory_agents.order_processor_agent import OrderProcessorAgent

# Import our components
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_order_processing():
    # Initialize components
    chromadb_client = ChromaDBClient()
    human_manager = HumanInteractionManager()
    order_processor = OrderProcessorAgent(chromadb_client, human_manager)

    # Enhance Excel processing to handle images
    enhance_excel_processing(order_processor)

    # The email you provided
    email_subject = "Fwd: PURCHASE ORDER FOR FIT TAG 31570 QTY & REVERSIBLE TAG 8750 QTY. FROM NISHA"
    email_body = """
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

Attached file for your reference

Thanks and regards
Nisha
"""

    # Read the Excel attachment
    excel_path = "/Users/samarsingh/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/4C7D8FC2-7A28-468A-8CE3-EF6B878FA056/ML ENTERPRISES_VOGUE COLLECTIONS 1032.xlsx"

    with open(excel_path, "rb") as f:
        excel_content = f.read()

    # Prepare attachment data
    attachments = [
        {
            "filename": "ML ENTERPRISES_VOGUE COLLECTIONS 1032.xlsx",
            "content": excel_content,
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
    ]

    # Process the order
    print("=== PROCESSING ORDER WITH ATTACHMENTS ===")
    result = await order_processor.process_order_email(
        email_subject=email_subject,
        email_body=email_body,
        email_date=datetime.now(),
        sender_email="interface.scs02@gmail.com",
        attachments=attachments,
    )

    # Display results
    print("\n=== ORDER PROCESSING RESULT ===")
    print(f"Order ID: {result.order.order_id}")
    print(f"Customer: {result.order.customer.company_name}")
    print(f"Extraction Confidence: {result.order.extraction_confidence:.2%}")
    print(f"Recommended Action: {result.recommended_action}")

    print("\n=== EXTRACTED ITEMS ===")
    for item in result.order.items[:5]:  # Show first 5 items
        print(
            f"- {item.tag_specification.tag_code}: {item.tag_specification.tag_type.value}"
        )
        print(f"  Quantity: {item.quantity_ordered}")
        print(
            f"  Match Score: {item.inventory_match_score:.2%}"
            if item.inventory_match_score
            else "  No match found"
        )

    print("\n=== CONFIDENCE SCORES ===")
    for item_id, score in result.confidence_scores.items():
        print(f"- {item_id}: {score:.2%}")

    # Check if human review was created
    print("\n=== HUMAN REVIEW STATUS ===")
    pending_reviews = await human_manager.get_pending_reviews()
    if pending_reviews:
        print(f"Pending reviews: {len(pending_reviews)}")
        for review in pending_reviews:
            print(f"- Review ID: {review.request_id}")
            print(f"  Customer: {review.customer_email}")
            print(f"  Confidence: {review.confidence_score:.2%}")
            print(f"  Priority: {review.priority.value}")
            print(f"  Status: {review.status.value}")
    else:
        print("No pending reviews - order may have been auto-approved")

    # Show attachment processing results
    if result.order.attachments:
        print("\n=== PROCESSED ATTACHMENTS ===")
        for att in result.order.attachments:
            print(f"- {att.filename} ({att.type.value})")
            if att.extracted_data:
                if (
                    att.type.value == "excel"
                    and "embedded_images" in att.extracted_data
                ):
                    print(
                        f"  Found {att.extracted_data.get('embedded_image_count', 0)} embedded images"
                    )
                    if att.extracted_data.get("embedded_images"):
                        for img in att.extracted_data["embedded_images"]:
                            print(f"    - {img['filename']}: Analyzed with Qwen2.5VL")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_order_processing())
