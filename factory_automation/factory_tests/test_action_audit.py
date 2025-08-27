#!/usr/bin/env python3
"""
Test script to verify ActionAudit table works correctly
Phase 1 verification for Two-Tier Action System
"""

import uuid
from datetime import datetime

from factory_automation.factory_database.connection import get_db
from factory_automation.factory_database.models import ActionAudit


def test_action_audit():
    """Test inserting and querying action audit records"""
    
    print("🧪 Testing ActionAudit table...")
    
    # Get database session
    with get_db() as db:
        # Create test action records
        test_actions = [
            {
                "action_id": f"TEST-{uuid.uuid4().hex[:8]}",
                "workflow_id": f"WF-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "action_type": "reversible",
                "action_category": "db_update",
                "action_name": "update_order_status",
                "description": "Test: Update order status to processing",
                "details": {"order_id": "TEST-001", "old_status": "pending", "new_status": "processing"},
                "can_rollback": 1,
                "rollback_data": {"order_id": "TEST-001", "restore_status": "pending"},
                "executed": 1,
                "executed_at": datetime.utcnow(),
                "confidence": 0.95,
                "reasoning": "Test action for database verification",
            },
            {
                "action_id": f"TEST-{uuid.uuid4().hex[:8]}",
                "workflow_id": f"WF-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "action_type": "irreversible",
                "action_category": "email_send",
                "action_name": "send_customer_email",
                "description": "Test: Send quotation email to customer",
                "details": {"to": "customer@test.com", "subject": "Quotation for Order TEST-001"},
                "can_rollback": 0,
                "requires_approval": 1,
                "executed": 0,
                "confidence": 0.85,
                "reasoning": "Test irreversible action requiring approval",
            }
        ]
        
        # Insert test records
        print("\n📝 Inserting test actions...")
        for action_data in test_actions:
            action = ActionAudit(**action_data)
            db.add(action)
            print(f"  ✅ Added {action_data['action_type']} action: {action_data['action_name']}")
        
        # Commit the changes
        db.commit()
        print("\n✅ Successfully committed to database")
        
        # Query back the records
        print("\n🔍 Querying action audit records...")
        
        # Query reversible actions
        reversible = db.query(ActionAudit).filter_by(action_type="reversible").all()
        print(f"  Found {len(reversible)} reversible actions")
        
        # Query irreversible actions
        irreversible = db.query(ActionAudit).filter_by(action_type="irreversible").all()
        print(f"  Found {len(irreversible)} irreversible actions")
        
        # Query actions requiring approval
        need_approval = db.query(ActionAudit).filter_by(requires_approval=1).all()
        print(f"  Found {len(need_approval)} actions requiring approval")
        
        # Display sample record
        if reversible:
            sample = reversible[0]
            print("\n📋 Sample reversible action:")
            print(f"  - Action ID: {sample.action_id}")
            print(f"  - Category: {sample.action_category}")
            print(f"  - Can Rollback: {'Yes' if sample.can_rollback else 'No'}")
            print(f"  - Executed: {'Yes' if sample.executed else 'No'}")
            print(f"  - Confidence: {sample.confidence:.1%}")
        
        if irreversible:
            sample = irreversible[0]
            print("\n📋 Sample irreversible action:")
            print(f"  - Action ID: {sample.action_id}")
            print(f"  - Category: {sample.action_category}")
            print(f"  - Requires Approval: {'Yes' if sample.requires_approval else 'No'}")
            print(f"  - Executed: {'Yes' if sample.executed else 'No'}")
            print(f"  - Confidence: {sample.confidence:.1%}")
        
        # Clean up test data
        print("\n🧹 Cleaning up test data...")
        for action in db.query(ActionAudit).filter(ActionAudit.action_id.like("TEST-%")).all():
            db.delete(action)
        db.commit()
        print("  ✅ Test data cleaned up")
        
    print("\n✅ ActionAudit table verification complete!")
    print("📊 Phase 1 database foundation is working correctly")
    return True


if __name__ == "__main__":
    try:
        test_action_audit()
    except Exception as e:
        print(f"\n❌ Error testing ActionAudit table: {e}")
        print("Make sure to run the migration script first:")
        print("  psql -U postgres -d factory_automation -f migrations/add_action_audit_table.sql")
        exit(1)