#!/usr/bin/env python3
"""
Create ActionAudit table using SQLAlchemy
Phase 1 - Database Foundation
"""

from sqlalchemy import text
from factory_automation.factory_database.connection import engine
from factory_automation.factory_database.models import Base, ActionAudit


def create_action_audit_table():
    """Create the action_audit table in the database"""
    
    print("🔨 Creating ActionAudit table...")
    
    try:
        # Use the imported engine
        
        # Create all tables defined in models (including ActionAudit)
        # This will only create tables that don't exist
        Base.metadata.create_all(engine, tables=[ActionAudit.__table__])
        
        print("✅ ActionAudit table created successfully!")
        
        # Verify the table exists
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'action_audit'"
            ))
            count = result.scalar()
            
            if count > 0:
                print("✅ Verified: action_audit table exists in database")
                
                # Get column count
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_name = 'action_audit'"
                ))
                col_count = result.scalar()
                print(f"📊 Table has {col_count} columns")
                
                return True
            else:
                print("❌ Table creation may have failed - table not found")
                return False
                
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False


if __name__ == "__main__":
    success = create_action_audit_table()
    if success:
        print("\n✅ Phase 1 - Database foundation ready!")
        print("📝 You can now run: python test_action_audit.py")
    else:
        print("\n❌ Failed to create table. Check database connection.")
        exit(1)