#!/usr/bin/env python3
"""Test PostgreSQL database connection and operations."""

import os
import sys
from datetime import datetime

sys.path.append("./factory_automation")

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()


def test_database():
    """Test database connectivity and basic operations."""
    print("Testing PostgreSQL Database")
    print("=" * 50)

    # Get connection string
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://samarsingh@localhost:5432/factory_automation"
    )
    print(f"Connecting to: {db_url.split('@')[1]}")  # Hide username

    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print("✓ Connected to PostgreSQL")

        # Test tables exist
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """
        )
        tables = cursor.fetchall()
        print(f"\n✓ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table['table_name']}")

        # Insert test customer
        print("\nTesting data operations...")
        cursor.execute(
            """
            INSERT INTO customers (email, name, company, phone)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE
            SET name = EXCLUDED.name
            RETURNING id;
        """,
            ("test@example.com", "Test Customer", "Test Company", "123-456-7890"),
        )
        customer_id = cursor.fetchone()["id"]
        print(f"✓ Created/updated customer with ID: {customer_id}")

        # Insert test order
        order_num = f"ORD-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute(
            """
            INSERT INTO orders (order_number, customer_id, status, total_amount)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """,
            (order_num, customer_id, "pending", 100.00),
        )
        order_id = cursor.fetchone()["id"]
        print(f"✓ Created order: {order_num}")

        # Insert test order item
        cursor.execute(
            """
            INSERT INTO order_items (order_id, tag_code, description, quantity, unit_price, total_price)
            VALUES (%s, %s, %s, %s, %s, %s);
        """,
            (order_id, "BLU-CTN-23", "Blue Cotton Tag 2x3", 100, 1.00, 100.00),
        )
        print("✓ Added order item")

        # Query the data
        cursor.execute(
            """
            SELECT o.order_number, c.name, oi.tag_code, oi.quantity
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.id = %s;
        """,
            (order_id,),
        )
        result = cursor.fetchone()
        print("\n✓ Query test:")
        print(f"  Order: {result['order_number']}")
        print(f"  Customer: {result['name']}")
        print(f"  Item: {result['tag_code']} x {result['quantity']}")

        # Commit changes
        conn.commit()
        print("\n✓ All database operations successful!")

        # Cleanup
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n✗ Database error: {str(e)}")
        return False

    return True


if __name__ == "__main__":
    test_database()
