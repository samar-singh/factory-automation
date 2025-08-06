#!/usr/bin/env python3
"""Direct test of AI-powered order extraction"""

import asyncio
import json

from openai import AsyncOpenAI

from factory_automation.factory_config.settings import settings


async def extract_order_with_ai(email_body: str):
    """Extract order items using OpenAI GPT-4"""

    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Prepare the prompt
    extraction_prompt = f"""
    You are an expert at extracting order information from emails for a garment price tag manufacturing factory.
    
    Analyze the following email and extract ALL order items with their specifications.
    
    Email Content:
    {email_body}
    
    Extract the following information for EACH item ordered:
    1. Item type (e.g., price tags, hang tags, care labels, barcode stickers, etc.)
    2. Quantity (number of pieces/units)
    3. Brand/Customer name
    4. Color specifications if mentioned
    5. Size specifications (dimensions if provided)
    6. Material type if mentioned (paper, plastic, fabric, etc.)
    7. Special requirements (printing, embossing, special finishes)
    8. Any product codes or SKUs mentioned
    9. Delivery timeline if mentioned
    
    Return the extracted information as a JSON object with this structure:
    {{
        "customer_name": "extracted customer/brand name",
        "order_items": [
            {{
                "item_type": "type of tag/label",
                "quantity": number,
                "brand": "brand name if different from customer",
                "color": "color if specified",
                "size": "dimensions if specified",
                "material": "material type",
                "special_requirements": ["list of special requirements"],
                "product_code": "code if mentioned",
                "description": "full description combining all details"
            }}
        ],
        "delivery_timeline": "urgency or deadline if mentioned",
        "additional_notes": "any other important information",
        "confidence_level": "high/medium/low based on clarity of requirements",
        "missing_information": ["list of important missing details"]
    }}
    """

    try:
        # Call GPT-4
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured order information from unstructured text. Always return valid JSON.",
                },
                {"role": "user", "content": extraction_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000,
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {"error": str(e), "extraction_method": "failed"}


async def main():
    """Test the extraction with sample emails"""

    test_emails = [
        {
            "name": "Myntra Urgent Order",
            "body": """
            Hi Team,
            
            We need an urgent order for Myntra:
            - 5000 pieces of price tags in black color
            - Size: 2x3 inches
            - Material: Premium cardboard with matte finish
            - Special requirement: Gold foil embossing for logo
            - Product codes: MYN-2024-BLK-001 to MYN-2024-BLK-5000
            
            Additionally, we need:
            - 2000 hang tags with strings
            - Color: White with red text
            - Size: 3x4 inches
            
            Please deliver by next Monday.
            
            Thanks,
            Myntra Procurement Team
            """,
        },
        {
            "name": "Allen Solly Labels",
            "body": """
            Dear Supplier,
            
            Please process our order:
            1. Care labels - 10,000 units
            2. Brand labels - 10,000 units  
            3. Size labels (S, M, L, XL) - 2,500 each size
            
            All labels should be in standard Allen Solly branding.
            Fabric material preferred.
            
            Regards,
            Allen Solly
            """,
        },
        {
            "name": "Quick Requirement",
            "body": """
            Need 500 tags urgently. Black color preferred.
            Send quotation ASAP.
            """,
        },
    ]

    print("=" * 70)
    print("AI-POWERED ORDER EXTRACTION TEST")
    print("=" * 70)

    for email in test_emails:
        print(f"\n📧 Testing: {email['name']}")
        print("-" * 60)

        result = await extract_order_with_ai(email["body"])

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            continue

        print(f"✅ Customer: {result.get('customer_name', 'Not identified')}")
        print(f"📊 Confidence: {result.get('confidence_level', 'Unknown')}")

        items = result.get("order_items", [])
        if items:
            print(f"\n📦 Extracted {len(items)} items:")
            for i, item in enumerate(items, 1):
                print(f"\n  Item {i}:")
                print(f"    • Type: {item.get('item_type', 'Unknown')}")
                print(f"    • Quantity: {item.get('quantity', 'Unknown')}")
                if item.get("color"):
                    print(f"    • Color: {item['color']}")
                if item.get("size"):
                    print(f"    • Size: {item['size']}")
                if item.get("material"):
                    print(f"    • Material: {item['material']}")
                if item.get("special_requirements"):
                    print(f"    • Special: {', '.join(item['special_requirements'])}")
                if item.get("product_code"):
                    print(f"    • Code: {item['product_code']}")
        else:
            print("  ⚠️ No items extracted")

        if result.get("delivery_timeline"):
            print(f"\n⏰ Delivery: {result['delivery_timeline']}")

        if result.get("missing_information"):
            print(f"\n❓ Missing: {', '.join(result['missing_information'])}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
