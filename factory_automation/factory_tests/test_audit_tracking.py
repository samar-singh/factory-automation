#!/usr/bin/env python3
"""
Simple test to verify action audit tracking works

Usage with uv:
    uv run python test_audit_tracking.py
"""

import asyncio

from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_database.connection import get_db
from factory_automation.factory_database.models import ActionAudit
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_simple_tracking():
    """Test basic action tracking functionality"""
    
    print("🧪 Testing Action Audit Tracking...")
    
    # Initialize orchestrator
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=False)
    
    # Generate workflow ID
    orchestrator.current_workflow_id = orchestrator._generate_workflow_id()
    print(f"  Workflow ID: {orchestrator.current_workflow_id}")
    
    # Track a test action (no order_id to avoid FK constraint)
    action_id = await orchestrator._track_action(
        action_name="test_search_inventory",
        action_category="inventory_search",
        details={"query": "Allen Solly tags", "limit": 10},
        confidence=0.95,
        order_id=None  # No order ID to avoid FK constraint
    )
    
    print(f"  Action ID: {action_id}")
    
    # Verify in database
    with get_db() as db:
        action = db.query(ActionAudit).filter_by(action_id=action_id).first()
        
        if action:
            print("\n✅ Action found in database:")
            print(f"  - Name: {action.action_name}")
            print(f"  - Type: {action.action_type}")
            print(f"  - Category: {action.action_category}")
            print(f"  - Workflow: {action.workflow_id}")
            print(f"  - Can Rollback: {'Yes' if action.can_rollback else 'No'}")
            print(f"  - Requires Approval: {'Yes' if action.requires_approval else 'No'}")
            
            # Clean up
            db.delete(action)
            db.commit()
            print("\n🧹 Test data cleaned")
        else:
            print("❌ Action not found in database")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_simple_tracking())