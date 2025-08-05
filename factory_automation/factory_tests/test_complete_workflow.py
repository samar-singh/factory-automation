#!/usr/bin/env python3
"""Test complete order processing workflow with the example email"""

import asyncio
from datetime import datetime
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.order_processor_agent import OrderProcessorAgent
from factory_automation.factory_agents.human_interaction_manager import HumanInteractionManager

async def test_workflow():
    """Test the complete workflow with the provided example email"""
    
    # Initialize components
    chromadb_client = ChromaDBClient()
    human_manager = HumanInteractionManager()
    order_processor = OrderProcessorAgent(chromadb_client, human_manager)
    
    # Example email from the user
    email_subject = "Allen Solly (E-com) brand bulk tag po copy for order confirmation"
    email_date = datetime.now()
    sender_email = "storerhppl@gmail.com"
    
    email_body = """
    Dear Sir/Madam
    Order received with thanks & Greetings from Interface Direct.   
    PFA Pro-Forma Invoice # 1542 & please check the description of the tag image & approve the order & do the needful. 
    Please let us know if you need any more help.

    With warm Regards,
    PUSHPARAJ.A/ Interface Direct/ Tag supplier / trimsblr@yahoo.co.in
    Dispatches Team / PH/998000 9355.

    On Monday 28 July, 2025 at 07:00:31 pm IST, Rajlaxmi Home Products Pvt ltd <storerhppl@gmail.com> wrote:

    Dear Meena ji,

    See attached Allen Solly (E-com) brand bulk tag po copy for order confirmation.
    We need the bulk tag materials delivery date  

    Fit    FIT TAG    Main Tag    Main Tag Remark
    Bootcut    TBALWBL0009N/10N/11N/12N/13N/14N/15N/16N    TBALHGT0033N    Sustainability hangtag
    Classic straight    TBALWBL0001N/02N/03N/04N/05N/06N/07N/08N    TBALHGT0033N    Sustainability hangtag
    Skinny    TBALTAG0363N/364N/365N/366N/367N/368N/369N    TBALHGT0033N    Sustainability hangtag
    Slim    TBALWBL0060N/61N/62N/63N/64N/65N/66N/67N/68N    TBALHGT0033N    Sustainability hangtag

    Pls confirm the receipt and revert back.

    Thanks & Regards,
    Vijay kapse
    RAJLAXMI  HOME PRODUCTS PVT. LTD
    Gala No. 5, Anjani Kumar Indi. Estate,
    Datta Mandir Road, Bhandup (W)
    Mumbai-400078
    Contact No. 8655233004
    """
    
    # Simulate attachments (in real scenario, these would be actual files)
    attachments = [
        {
            "filename": "ProForma_Invoice_1542.pdf",
            "mime_type": "application/pdf",
            "content": b"PDF content here"  # Would be actual PDF bytes
        },
        {
            "filename": "Allen_Solly_Tag_Sample.jpg",
            "mime_type": "image/jpeg",
            "content": b"Image content here"  # Would be actual image bytes
        },
        {
            "filename": "Bulk_Order_Details.xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content": b"Excel content here"  # Would be actual Excel bytes
        }
    ]
    
    print("=" * 80)
    print("COMPLETE ORDER PROCESSING WORKFLOW TEST")
    print("=" * 80)
    
    print(f"\n📧 Processing order email from: {sender_email}")
    print(f"Subject: {email_subject}")
    print(f"Attachments: {len(attachments)} files")
    print("-" * 80)
    
    # Process the order
    result = await order_processor.process_order_email(
        email_subject=email_subject,
        email_body=email_body,
        email_date=email_date,
        sender_email=sender_email,
        attachments=attachments
    )
    
    # Display results
    print("\n📊 PROCESSING RESULTS:")
    print("-" * 40)
    
    if result.order:
        order = result.order
        print(f"✅ Order ID: {order.order_id}")
        print(f"📦 Customer: {order.customer.company_name}")
        print(f"📊 Extraction Confidence: {order.extraction_confidence:.1%}")
        print(f"🔍 Extraction Method: {order.extraction_method}")
        
        print(f"\n📋 Extracted Items: {len(order.items)}")
        for item in order.items:
            print(f"\n  Item {item.item_id}:")
            print(f"    • Tag Code: {item.tag_specification.tag_code}")
            print(f"    • Type: {item.tag_specification.tag_type.value}")
            print(f"    • Quantity: {item.quantity_ordered}")
            print(f"    • Brand: {item.brand}")
            if item.fit_mapping:
                print(f"    • Fit Type: {item.fit_mapping.fit_type}")
                print(f"    • Main Tag: {item.fit_mapping.main_tag_code}")
                print(f"    • Remark: {item.fit_mapping.main_tag_remark}")
            if item.inventory_match_score:
                print(f"    • Match Score: {item.inventory_match_score:.1%}")
        
        print("\n📅 Delivery:")
        print(f"    • Urgency: {order.delivery.urgency.value}")
        if order.delivery.required_date:
            print(f"    • Required Date: {order.delivery.required_date}")
        
        if order.proforma_invoice:
            print("\n💰 Proforma Invoice:")
            print(f"    • Number: {order.proforma_invoice.invoice_number}")
        
        print(f"\n🎯 Recommended Action: {result.recommended_action}")
        print(f"⚡ Processing Time: {result.processing_time_ms}ms")
        
        if result.confidence_scores:
            print("\n🔍 Item Confidence Scores:")
            for item_id, score in result.confidence_scores.items():
                print(f"    • {item_id}: {score:.1%}")
        
        if result.inventory_matches:
            print(f"\n📦 Inventory Matches Found: {len(result.inventory_matches)}")
            # Show top 3 matches
            for match in result.inventory_matches[:3]:
                print(f"    • {match.get('tag_code', 'N/A')}: {match.get('confidence', 0):.1%} confidence")
        
        if order.missing_information:
            print("\n❓ Missing Information:")
            for info in order.missing_information:
                print(f"    • {info}")
        
        print(f"\n✅ Approval Status: {order.approval_status}")
        
        if result.inventory_updates:
            print(f"\n📝 Inventory Updates: {len(result.inventory_updates)}")
            for update in result.inventory_updates:
                print(f"    • {update.tag_code}: -{update.quantity_used} units")
        
        if result.errors:
            print("\n❌ Errors:")
            for error in result.errors:
                print(f"    • {error}")
        
        if result.warnings:
            print("\n⚠️ Warnings:")
            for warning in result.warnings:
                print(f"    • {warning}")
    
    else:
        print("❌ Failed to process order")
        if result.errors:
            for error in result.errors:
                print(f"    • {error}")
    
    print("\n" + "=" * 80)
    print("WORKFLOW TEST COMPLETE")
    print("=" * 80)
    
    # Check if human review is pending
    if result.recommended_action == "human_review":
        print("\n👤 ORDER SUBMITTED FOR HUMAN REVIEW")
        print("The order has been sent to the human review queue.")
        print("A reviewer will process it based on the confidence threshold.")

if __name__ == "__main__":
    asyncio.run(test_workflow())