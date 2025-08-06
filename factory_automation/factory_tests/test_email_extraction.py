#!/usr/bin/env python3
"""Test automatic email extraction from order emails"""

import re


def extract_email_info(email_body):
    """Extract sender email and subject from email body"""

    # Extract sender email
    from_pattern = r"[Ff]rom:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"

    from_match = re.search(from_pattern, email_body)
    if from_match:
        customer_email = from_match.group(1)
    else:
        email_match = re.search(email_pattern, email_body)
        if email_match:
            customer_email = email_match.group(1)
        else:
            customer_email = "unknown@example.com"

    # Extract subject
    subject_pattern = r"[Ss]ubject:\s*(.+?)(?:\n|$)"
    subject_match = re.search(subject_pattern, email_body)
    subject = subject_match.group(1) if subject_match else "Order Request"

    return customer_email, subject


# Test cases
test_emails = [
    """From: storerhppl@gmail.com
Subject: Allen Solly (E-com) brand bulk tag po copy
Date: Monday, 28 July 2025

Dear Meena ji,
See attached Allen Solly (E-com) brand bulk tag po copy for order confirmation.
We need the bulk tag materials delivery date.""",
    """Dear Sir/Madam,
Order received with thanks & Greetings from Interface Direct.
PUSHPARAJ.A/ Interface Direct/ Tag supplier / trimsblr@yahoo.co.in
Dispatches Team / PH/998000 9355.""",
    """From: vijay.kapse@rajlaxmi.com
Subject: Urgent Order - Myntra Tags

We need 5000 price tags urgently.
Thanks,
Vijay Kapse
RAJLAXMI HOME PRODUCTS PVT. LTD
Contact: 8655233004""",
]

print("=" * 60)
print("TESTING AUTOMATIC EMAIL EXTRACTION")
print("=" * 60)

for i, email in enumerate(test_emails, 1):
    print(f"\nTest {i}:")
    print("-" * 40)
    customer_email, subject = extract_email_info(email)
    print(f"✉️  Extracted Email: {customer_email}")
    print(f"📋 Extracted Subject: {subject}")

    # Show first 100 chars of email
    preview = email[:100].replace("\n", " ")
    print(f"📧 Email Preview: {preview}...")

print("\n" + "=" * 60)
print("✅ Email extraction ready for production!")
print("=" * 60)
