#!/usr/bin/env python3
"""Test script to verify correct customer identification from email threads"""

import asyncio
import logging
from datetime import datetime
from factory_automation.factory_agents.order_processor_agent import OrderProcessorAgent
from factory_automation.factory_database.connection import get_db
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# The sample email provided by the user
SAMPLE_EMAIL_BODY = """Dear Sir/Madam
Order received with thanks & Greetings from Interface Direct.   
PFA Pro-Forma Invoice # 1542 & please check the description of the tag image & approve the order & do the needful. Please let us know if you need any more help.

 

With warm Regards,

PUSHPARAJ.A/ Interface Direct/ Tag supplier / trimsblr@yahoo.co.in
Dispatches Team / PH/998000 9355.


On Monday 28 July, 2025 at 07:00:31 pm IST, Rajlaxmi Home Products Pvt ltd <storerhppl@gmail.com> wrote:


Dear Meena ji,

See attached Allen Solly (E-com) brand bulk tag po copy for order confirmation .We need the bulk tag materials delivery date  

Fit    FIT TAG    Main Tag    Main Tag Remark
Bootcut    TBALWBL0009N/10N/11N/12N/13N/14N/15N/16N    TBALHGT0033N    Sustainability hangtag
Classic straight    TBALWBL0001N/02N/03N/04N/05N/06N/07N/08N    TBALHGT0033N    Sustainability hangtag
Skinny    TBALTAG0363N/364N/365N/366N/367N/368N/369N    TBALHGT0033N    Sustainability hangtag
Slim    TBALWBL0060N/61N/62N/63N/64N/65N/66N/67N/68N    TBALHGT0033N    Sustainability hangtag

Pls confirm the receipt and revert back .

Thanks & Regards,
Vijay kapse
RAJLAXMI  HOME PRODUCTS PVT. LTD
Gala No. 5, Anjani Kumar Indi. Estate ,
Datta Mandir Road, Bhandup ( W)
Mumbai-400078
Contact No. 8655233004"""

async def test_customer_extraction():
    """Test that the system correctly identifies the customer from the email thread"""
    
    print("\n" + "="*80)
    print("TESTING CUSTOMER IDENTIFICATION FROM EMAIL THREAD")
    print("="*80 + "\n")
    
    # Initialize ChromaDB client (required for OrderProcessorAgent)
    from factory_automation.factory_database.vector_db import ChromaDBClient
    chromadb_client = ChromaDBClient()
    
    # Initialize order processor
    order_processor = OrderProcessorAgent(
        chromadb_client=chromadb_client,
        human_manager=None,     # Not needed for this test
    )
    
    # Test extraction
    print("📧 Processing email from: trimsblr@yahoo.co.in")
    print("📋 Subject: Pro-Forma Invoice # 1542")
    print("\n" + "-"*40 + "\n")
    
    try:
        # Process the email using the full processing pipeline
        result = await order_processor.process_order_email(
            email_subject="Pro-Forma Invoice # 1542",
            email_body=SAMPLE_EMAIL_BODY,
            email_date=datetime.now(),
            sender_email="trimsblr@yahoo.co.in",
            attachments=[]
        )
        
        # Check the results
        print("🔍 EXTRACTION RESULTS:")
        print("-"*40)
        
        if result and result.order and result.order.customer:
            customer_email = result.order.customer.email
            customer_company = result.order.customer.company_name
            
            print(f"✉️  Customer Email: {customer_email}")
            print(f"🏢 Customer Company: {customer_company}")
            
            # Verify correct extraction
            if customer_email == "storerhppl@gmail.com":
                print("\n✅ SUCCESS: Correctly identified customer email!")
            elif customer_email == "trimsblr@yahoo.co.in":
                print("\n❌ FAILED: Incorrectly identified supplier as customer")
            else:
                print(f"\n⚠️  Extracted different email: {customer_email}")
            
            if "Rajlaxmi" in str(customer_company):
                print("✅ SUCCESS: Correctly identified customer company!")
            elif "Interface Direct" in str(customer_company):
                print("❌ FAILED: Incorrectly identified supplier as customer")
            else:
                print(f"⚠️  Extracted different company: {customer_company}")
                
        else:
            print("❌ No customer information extracted")
            
        # Also show order items if extracted
        if result and result.order and result.order.items:
            print(f"\n📦 Found {len(result.order.items)} order items")
            for item in result.order.items[:3]:  # Show first 3 items
                print(f"   - {item.tag_specification.tag_code}: {item.quantity_ordered} units")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_customer_extraction())