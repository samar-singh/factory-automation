"""Run database migrations for recommendation queue system"""

import logging
from pathlib import Path

from connection import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration(migration_file: str):
    """Run a SQL migration file"""

    # Read migration file
    migration_path = Path(__file__).parent / "migrations" / migration_file

    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return False

    with open(migration_path, "r") as f:
        migration_sql = f.read()

    # Execute migration
    try:
        with engine.connect() as conn:
            # Split by semicolon but keep it for execution
            statements = migration_sql.split(";\n")

            for statement in statements:
                if statement.strip():
                    # Add semicolon back if it was removed
                    if not statement.strip().endswith(";"):
                        statement = statement + ";"

                    logger.info(f"Executing: {statement[:100]}...")
                    conn.execute(text(statement))
                    conn.commit()

        logger.info(f"Migration {migration_file} completed successfully")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    # Run the recommendation queue migration
    success = run_migration("add_recommendation_queue_tables.sql")

    if success:
        print("✅ Migration completed successfully")
        print("New tables created:")
        print("  - recommendation_queue")
        print("  - batch_operations")
        print("  - document_generation_log")
        print("  - inventory_change_log")
        print("New views created:")
        print("  - queue_metrics")
        print("  - batch_metrics")
    else:
        print("❌ Migration failed - check logs for details")
