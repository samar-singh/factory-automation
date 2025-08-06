#!/usr/bin/env python3
"""Create the review_decisions table in the database"""

import logging

from factory_automation.factory_database.connection import engine
from factory_automation.factory_database.models import ReviewDecision

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_review_decisions_table():
    """Create the review_decisions table if it doesn't exist"""
    try:
        # Create the table
        ReviewDecision.__table__.create(engine, checkfirst=True)
        logger.info("✅ review_decisions table created successfully!")

        # Verify table exists
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "review_decisions" in tables:
            logger.info("✅ Verified: review_decisions table exists in database")

            # Show columns
            columns = inspector.get_columns("review_decisions")
            logger.info("\nTable columns:")
            for col in columns:
                logger.info(f"  - {col['name']} ({col['type']})")
        else:
            logger.error("❌ Table creation failed - table not found")

    except Exception as e:
        logger.error(f"Error creating table: {e}")


if __name__ == "__main__":
    print("Creating review_decisions table...")
    create_review_decisions_table()
