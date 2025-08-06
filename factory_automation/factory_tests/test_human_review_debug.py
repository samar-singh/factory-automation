#!/usr/bin/env python3
"""Debug human review request creation"""

import asyncio
import json
from datetime import datetime

from factory_automation.factory_agents.orchestrator_with_human import (
    OrchestratorWithHuman,
)
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_order_processing():
    """Test order processing with the provided email"""

    # The email chain provided by user
    email_body = """Dear Sir/Madam,
As per phone discussion had with you, we have revised to VOGUE COLLECTIONS for billing & delivery address & change in your records.

On Wednesday 9 July, 2025 at 05:43:26 pm IST, Nair <blroffice@stl-hk.net> wrote:

Dear Riaz 

As per our telecom this order we have peroceeded with Interface. 


Thanks & Regards
V.K.NAIR
Email: blroffice@stl-hk.net
OUR NEW ADDRESS:
M.L. ENTERPRISES
2ND FLOOR, Survey No.76/1A -76/1B,
Govind Swamy Layout,
Tharabanhalli Jala Hobli, 
Landmark - Behind ITC Factory, KIA Road,
Bangalore - 562157, Karanataka.


Note: IF YOU ARE NOT GETTING OUR REPLY IN 24 HOURS PLEASE RE-SEND YOUR EMAILS / ORDERS.





On 05-Jul-2025, at 10:23 AM, interface <trimsblr@yahoo.co.in> wrote:

Dear Sir/Madam,
Resending/ this Tags with trims code only our supplies & confirm the order for production & revert back ASAP.



----- Forwarded message -----
From: M.L.E Accounts <mlenterprises28@gmail.com>
To: interface <trimsblr@yahoo.co.in>
Cc: NAIR MLE NEW <blroffice@stl-hk.net>; Riaz Uddin Bhuiyan <riaz@lyricbd.com>; rabi <rabi@lyricbd.com>; meena.interfacedirect@gmail.com <meena.interfacedirect@gmail.com>; idban.acct@gmail.com <idban.acct@gmail.com>; Shilpy Mahani <shilpy@riyuv.com>; Ganapathy K <ganapathy.k@abfrl.adityabirla.com>; ganapathy.k@ablbl.adityabirla.com <ganapathy.k@ablbl.adityabirla.com>; Lalit <lalit@stl-hk.net>; zzaha@lyricbd.com <zzaha@lyricbd.com>
Sent: Friday 4 July, 2025 at 08:21:01 pm IST
Subject: Re: Re sending 02Performa invoice # 1032 /ML ENTERPRISES/BOOKING / ITEM : TBPRTAG0082N / PETER ENGLAND

Hi Interface team 

There are 3 items customer sent order please send us revised PI 

Also please issue the PI in the name of our below company and not in the name of ML Enterprises

Vogue Collections
3rd Floor, Survey No.76/1A -76/1B, 
Govind Swamy Layout,
Tharabanhalli Jala Hobli, Yelanhanka Taluk,
Landmark - Behind ITC Factory, KIA Road,
Bangalore - 562157
Karanataka
GSTIN: 29AABPB6937A1Z3


On 3 Jul 2025, at 15:24, interface <trimsblr@yahoo.co.in> wrote:

Dear Sir/Madam,
Re sending the order & confirm the order for our supplies of tag for production purpose & revert back ASAP.


On Thursday 3 July, 2025 at 10:48:39 am IST, Riaz Uddin Bhuiyan <riaz@lyricbd.com> wrote:

Dear Inter face Team ,
 
 
Would you pls response on previous order & here added a new item

Pls confirm goods Ready date & provide PI in USD .

 
 
PI ADDRESS ,

Lyric Industries (Pvt.) Ltd.

Cha Bagan Road, East Mouchak, Kaliakair,

GAZIPUR-1751,BANGLADESH.

BIN NO: 000362165-0103

 
 
 
USE AREA

TRIM CODE

ORDER QTY

PETER ENGLAND MENS

TBPRTAG0082N

31570

PETER ENGLANG REVERSIBLE

TBPCTAG0532N

8750

ALLEN SOLLY REVEISIBLE

 
5200

 
 
Best Regards

Riaz


 
From: interface <trimsblr@yahoo.co.in>
Sent: Friday, June 20, 2025 4:54 PM
To: Riaz Uddin Bhuiyan <riaz@lyricbd.com>; NAIR MLE NEW <blroffice@stl-hk.net>
Cc: 'rabi' <rabi@lyricbd.com>; meena.interfacedirect@gmail.com; idban.acct@gmail.com; LALIT RUPANI <lalit@stl-hk.net>
Subject: Performa invoice # 1032 /ML ENTERPRISES/BOOKING / ITEM : TBPRTAG0082N / PETER ENGLAND

 
Dear ML ENTERPRISES- our export division for $ rate quote.

PFA Performa invoice # 1032 & please approve the order with PO for production purposes. & Kindly  do the needful.

With warm Regards,

PUSHPARAJ. A/Interface Direct/ Tag supplier / trimsblr@yahoo.co.in
NEW-GSTIN:  29AAKFI9058A1Z6
Dispatches Team / PH/998000 9355 /KAMAKSHI-8310636489.

 
On Friday 20 June, 2025 at 12:19:04 pm IST, Riaz Uddin Bhuiyan <riaz@lyricbd.com> wrote:

 
 
Dear Concern,

 
 
Below qty is final

TBPRTAG0082N – (Perer England Red trim codes ) – 31570pcs

TBPCTAG0532N ( PE REVERSIBLE)- 8750 pcs

 
PI ADDRESS ,

Lyric Industries (Pvt.) Ltd.

Cha Bagan Road, East Mouchak, Kaliakair,

GAZIPUR-1751,BANGLADESH.

BIN NO: 000362165-0103

 
 
 
Best Regards

Riaz


 
"""

    print("=== Testing Order Processing with Email Chain ===\n")

    # Initialize orchestrator
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)

    # Create email data structure
    email_data = {
        "message_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from": "riaz@lyricbd.com",
        "subject": "Re: Re sending 02Performa invoice # 1032 /ML ENTERPRISES/BOOKING / ITEM : TBPRTAG0082N / PETER ENGLAND",
        "body": email_body,
        "email_type": "order",
    }

    print(f"Processing email from: {email_data['from']}")
    print(f"Subject: {email_data['subject'][:80]}...")

    # Process the email
    print("\n🔄 Processing order...")
    result = await orchestrator.process_email(email_data)

    print("\n📊 Processing Result:")
    print(json.dumps(result, indent=2))

    # Check if human review was created
    if "tool_calls" in result:
        for tool_call in result["tool_calls"]:
            if tool_call.get("tool") == "create_human_review":
                print("\n✅ Human review request was created!")
                break
        else:
            print("\n❌ No human review request found in tool calls")

    # Check the review queue
    print("\n📋 Checking review queue...")
    human_manager = orchestrator.human_manager

    # Get pending reviews
    pending_reviews = await human_manager.get_pending_reviews()

    print(f"\nTotal pending reviews: {len(pending_reviews)}")

    if pending_reviews:
        print("\nPending Reviews:")
        for review in pending_reviews[:5]:  # Show first 5
            print(f"  - ID: {review.request_id}")
            print(f"    Customer: {review.customer_email}")
            print(f"    Confidence: {review.confidence_score:.1f}%")
            print(f"    Priority: {review.priority.value}")
            print(f"    Status: {review.status.value}")
            print(f"    Created: {review.created_at}")
            print()
    else:
        print("  No pending reviews found!")

    # Get review statistics
    stats = human_manager.get_review_statistics()
    print("\n📈 Review Statistics:")
    print(json.dumps(stats, indent=2))

    # Also check if the review was stored in memory
    print(f"\n🧠 In-memory review count: {len(human_manager.review_requests)}")
    if human_manager.review_requests:
        latest_review = list(human_manager.review_requests.values())[-1]
        print(f"Latest review ID: {latest_review.request_id}")
        print(f"Latest review confidence: {latest_review.confidence_score}")


if __name__ == "__main__":
    asyncio.run(test_order_processing())
