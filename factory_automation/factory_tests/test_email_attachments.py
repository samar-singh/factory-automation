#!/usr/bin/env python3
"""Test email with attachments processing"""

import os
from datetime import datetime

import pandas as pd


def create_sample_order_excel():
    """Create a sample order Excel file"""

    # Sample order data
    order_data = {
        "Item Code": [
            "AS-BLK-CTN-01",
            "MYN-SLK-THR-02",
            "PE-BLU-FRM-03",
            "LS-PRM-GLD-04",
        ],
        "Description": [
            "Allen Solly Black Cotton Tags",
            "Myntra Silk Tags with Thread",
            "Peter England Blue Formal Tags",
            "Lifestyle Premium Gold Tags",
        ],
        "Quantity": [500, 1000, 200, 300],
        "Size": ["2x3", "3x4", "2x3", "3x3"],
        "Special Instructions": [
            "With gold print",
            "Sustainable material",
            "Matte finish",
            "Embossed logo",
        ],
    }

    df = pd.DataFrame(order_data)
    filename = "sample_order_attachment.xlsx"
    df.to_excel(filename, index=False)
    print(f"Created sample Excel order: {filename}")
    return filename


def simulate_email_with_attachment():
    """Simulate what the enhanced Gmail agent would extract"""

    print("=" * 70)
    print("SIMULATED EMAIL WITH ATTACHMENT PROCESSING")
    print("=" * 70)

    # Simulated email data
    email = {
        "from": "ABC Fashion House <orders@abcfashion.com>",
        "subject": "Bulk Order - Please Process Attached",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "body": """Dear Team,

Please find attached our monthly order Excel file.

We need these items urgently for our upcoming collection.
Additionally, please include:
- 100 VH tags in Navy with gold font
- 50 FM Flex-knit denim tags

Please confirm stock availability and delivery timeline.

Best regards,
ABC Fashion House""",
        "attachments": ["sample_order_attachment.xlsx"],
    }

    print(f"From: {email['from']}")
    print(f"Subject: {email['subject']}")
    print(f"Date: {email['date']}")
    print(f"Attachments: {', '.join(email['attachments'])}")
    print("\nEmail Body:")
    print("-" * 40)
    print(email["body"])
    print("-" * 40)

    # Simulate attachment processing
    print("\nPROCESSING ATTACHMENTS...")
    print("=" * 70)

    # Read the Excel file
    df = pd.read_excel(email["attachments"][0])

    print("\nExtracted from Excel attachment:")
    print(f"Total items in attachment: {len(df)}")
    print("\nOrder Details from Attachment:")
    print("-" * 70)

    for idx, row in df.iterrows():
        print(f"\n{idx+1}. {row['Description']}")
        print(f"   Code: {row['Item Code']}")
        print(f"   Quantity: {row['Quantity']}")
        print(f"   Size: {row['Size']}")
        print(f"   Instructions: {row['Special Instructions']}")

    # Extract items from email body
    print("\n\nExtracted from Email Body:")
    print("-" * 70)
    print("1. 100 VH tags in Navy with gold font")
    print("2. 50 FM Flex-knit denim tags")

    # Combined order summary
    print("\n\nCOMBINED ORDER SUMMARY")
    print("=" * 70)
    print("Items from attachment: 4")
    print("Items from email body: 2")
    print("Total unique items: 6")
    print(f"Total quantity: {df['Quantity'].sum() + 100 + 50} units")

    # Show how it would match with inventory
    print("\n\nINVENTORY MATCHING PREVIEW")
    print("=" * 70)

    items_to_match = [
        ("Allen Solly Black Cotton Tags", 500),
        ("Myntra Silk Tags with Thread", 1000),
        ("Peter England Blue Formal Tags", 200),
        ("Lifestyle Premium Gold Tags", 300),
        ("VH tags in Navy with gold font", 100),
        ("FM Flex-knit denim tags", 50),
    ]

    for item, qty in items_to_match:
        print(f"\nSearching for: '{item}' (Qty: {qty})")
        print("   → This would be matched against ChromaDB inventory using RAG")
        print("   → Confidence score and stock availability would be checked")

    # Clean up
    if os.path.exists("sample_order_attachment.xlsx"):
        os.remove("sample_order_attachment.xlsx")
        print("\nCleaned up sample file")


def show_enhanced_capabilities():
    """Show what the enhanced Gmail agent can do"""

    print("\n\n" + "=" * 70)
    print("ENHANCED GMAIL AGENT CAPABILITIES")
    print("=" * 70)

    print("\n1. EMAIL PROCESSING:")
    print("   ✓ Read email body and extract order information")
    print("   ✓ Identify customer, urgency, and intent")
    print("   ✓ Extract quantities and item descriptions")

    print("\n2. ATTACHMENT HANDLING:")
    print("   ✓ Download and process Excel files (.xlsx, .xls)")
    print("   ✓ Extract data from PDF documents")
    print("   ✓ OCR text from images (invoices, orders)")
    print("   ✓ Parse CSV and text files")

    print("\n3. DATA COMBINATION:")
    print("   ✓ Merge items from email body and attachments")
    print("   ✓ Avoid duplicates")
    print("   ✓ Create comprehensive order list")

    print("\n4. INTELLIGENT PROCESSING:")
    print("   ✓ Handle various Excel formats")
    print("   ✓ Extract relevant columns (item, quantity, code)")
    print("   ✓ OCR for scanned documents")
    print("   ✓ Combine with RAG inventory matching")

    print("\n5. USE CASES:")
    print("   • Customer sends order list as Excel attachment")
    print("   • PDF purchase orders attached to emails")
    print("   • Scanned invoices as images")
    print("   • Mixed orders (some in email, some in attachment)")


def main():
    # Create sample Excel
    create_sample_order_excel()

    # Simulate processing
    simulate_email_with_attachment()

    # Show capabilities
    show_enhanced_capabilities()

    print("\n\nTo use the enhanced Gmail agent:")
    print("1. It requires additional libraries: PyPDF2, Pillow, pytesseract")
    print("2. For OCR, you need to install Tesseract: brew install tesseract")
    print("3. The agent will automatically process all attachments")
    print("4. Results are combined with email body for complete order view")


if __name__ == "__main__":
    main()
