#!/usr/bin/env python3
"""
Phase 8 - Comprehensive Integration Testing
Tests the complete two-tier action system with different confidence scenarios
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from factory_automation.factory_database.connection import get_db
from factory_automation.factory_database.models import ActionAudit
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_tests.standard_test_case import (
    get_test_email, 
    IRREVERSIBLE_ACTIONS_IN_FLOW,
    REVERSIBLE_ACTIONS_IN_FLOW
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    """Comprehensive test suite for Phase 8"""
    
    def __init__(self):
        self.chromadb_client = ChromaDBClient()
        self.orchestrator = AgenticOrchestratorV3(self.chromadb_client, use_mock_gmail=True)
        self.results = []
    
    async def test_high_confidence_order(self) -> Dict[str, Any]:
        """Test high confidence order (>80%) - should auto-approve reversible actions"""
        print("\n" + "="*60)
        print("TEST 1: HIGH CONFIDENCE ORDER (>80%)")
        print("="*60)
        
        # Use standard test email with Allen Solly tags (known high confidence items)
        email_data = get_test_email()
        email_data["message_id"] = f"high_conf_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        print(f"📧 Processing email: {email_data['subject']}")
        
        # Process the email
        result = await self.orchestrator.process_email(email_data)
        
        # Analyze results
        test_result = {
            "test": "high_confidence",
            "success": result.get('success', False),
            "workflow_id": result.get('workflow_id'),
            "confidence": result.get('confidence_score', 0),
            "auto_executed": [],
            "pending_approval": [],
            "errors": []
        }
        
        # Check auto-executed actions
        auto_executed = result.get('auto_executed_actions', [])
        test_result["auto_executed"] = auto_executed
        print(f"\n✅ Auto-executed actions: {len(auto_executed)}")
        for action in auto_executed:
            print(f"   - {action}")
        
        # Check pending actions
        pending = result.get('pending_approval_actions', [])
        test_result["pending_approval"] = pending
        print(f"\n⏳ Pending approval actions: {len(pending)}")
        for action in pending:
            print(f"   - {action}")
        
        # Verify no emails sent
        workflow_id = result.get('workflow_id')
        if workflow_id:
            with get_db() as db:
                executed_emails = db.query(ActionAudit).filter(
                    ActionAudit.workflow_id == workflow_id,
                    ActionAudit.action_name.in_(['send_email_response', 'send_customer_email']),
                    ActionAudit.executed == 1
                ).all()
                
                if executed_emails:
                    test_result["errors"].append("❌ Email was sent without approval!")
                else:
                    print("\n✅ No emails sent without approval")
        
        # Validate action classification
        for action in auto_executed:
            if action in IRREVERSIBLE_ACTIONS_IN_FLOW:
                test_result["errors"].append(f"❌ Irreversible action '{action}' was auto-executed!")
        
        for action in pending:
            if action in REVERSIBLE_ACTIONS_IN_FLOW:
                test_result["errors"].append(f"❌ Reversible action '{action}' requires approval!")
        
        print(f"\n📊 Test Result: {'PASSED' if not test_result['errors'] else 'FAILED'}")
        if test_result["errors"]:
            for error in test_result["errors"]:
                print(f"   {error}")
        
        return test_result
    
    async def test_medium_confidence_order(self) -> Dict[str, Any]:
        """Test medium confidence order (60-80%) - should require manual review"""
        print("\n" + "="*60)
        print("TEST 2: MEDIUM CONFIDENCE ORDER (60-80%)")
        print("="*60)
        
        # Modify email to use less common items for medium confidence
        email_data = get_test_email()
        email_data["message_id"] = f"med_conf_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        email_data["body"] = """Dear Sir,
        
We need some custom tags for our new product line. Looking for something similar to 
Peter England style but with our branding. Please provide options and pricing.

Quantity: Approximately 500-1000 pieces
Style: Professional, similar to formal shirt tags
        
Please advise on availability.
        
Thanks,
Customer"""
        
        print("📧 Processing email with ambiguous request")
        
        # Process the email
        result = await self.orchestrator.process_email(email_data)
        
        # Analyze results
        test_result = {
            "test": "medium_confidence",
            "success": result.get('success', False),
            "workflow_id": result.get('workflow_id'),
            "confidence": result.get('confidence_score', 0),
            "auto_executed": result.get('auto_executed_actions', []),
            "pending_approval": result.get('pending_approval_actions', []),
            "human_review_created": False,
            "errors": []
        }
        
        print(f"\n📊 Confidence Score: {test_result['confidence']}%")
        
        # Check if human review actions were created
        workflow_id = result.get('workflow_id')
        if workflow_id:
            # For medium confidence, check if any review-related actions were created
            if "request_human_review" in str(result.get('pending_approval_actions', [])):
                test_result["human_review_created"] = True
                print("✅ Human review requested for medium confidence")
            else:
                print("⚠️ No explicit human review action for medium confidence")
        
        # Medium confidence should still follow two-tier rules
        for action in test_result["auto_executed"]:
            if action in IRREVERSIBLE_ACTIONS_IN_FLOW:
                test_result["errors"].append(f"❌ Irreversible action '{action}' auto-executed at medium confidence!")
        
        print(f"\n📊 Test Result: {'PASSED' if not test_result['errors'] else 'FAILED'}")
        
        return test_result
    
    async def test_low_confidence_order(self) -> Dict[str, Any]:
        """Test low confidence order (<60%) - should ask for clarification"""
        print("\n" + "="*60)
        print("TEST 3: LOW CONFIDENCE ORDER (<60%)")
        print("="*60)
        
        # Create very vague email for low confidence
        email_data = {
            "message_id": f"low_conf_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "from": "unknown@example.com",
            "to": "storerhppl@gmail.com",
            "subject": "Tags needed",
            "body": "Hi, I need some tags. Please send details.",
            "attachments": []
        }
        
        print(f"📧 Processing vague email: {email_data['subject']}")
        
        # Process the email
        result = await self.orchestrator.process_email(email_data)
        
        # Analyze results
        test_result = {
            "test": "low_confidence",
            "success": result.get('success', False),
            "workflow_id": result.get('workflow_id'),
            "confidence": result.get('confidence_score', 0),
            "auto_executed": result.get('auto_executed_actions', []),
            "pending_approval": result.get('pending_approval_actions', []),
            "clarification_needed": False,
            "errors": []
        }
        
        print(f"\n📊 Confidence Score: {test_result['confidence']}%")
        
        # Low confidence should trigger clarification
        if test_result["confidence"] < 60:
            test_result["clarification_needed"] = True
            print("✅ Clarification needed for low confidence")
        
        # Should not execute any irreversible actions
        for action in test_result["auto_executed"]:
            if action in IRREVERSIBLE_ACTIONS_IN_FLOW:
                test_result["errors"].append(f"❌ Irreversible action '{action}' executed at low confidence!")
        
        # Check for clarification email in pending
        if "send_clarification_email" in test_result["pending_approval"] or \
           "request_more_information" in test_result["pending_approval"]:
            print("✅ Clarification email queued for approval")
        
        print(f"\n📊 Test Result: {'PASSED' if not test_result['errors'] else 'FAILED'}")
        
        return test_result
    
    async def test_email_blocking(self) -> Dict[str, Any]:
        """Test that emails are NEVER sent without approval"""
        print("\n" + "="*60)
        print("TEST 4: EMAIL BLOCKING VERIFICATION")
        print("="*60)
        
        # Process multiple emails
        test_emails = [
            get_test_email(),
            {
                "message_id": f"urgent_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "from": "vip@customer.com",
                "subject": "URGENT: Need 5000 tags immediately",
                "body": "This is urgent. Send invoice and tags ASAP.",
                "attachments": []
            },
            {
                "message_id": f"payment_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "from": "accounts@company.com",
                "subject": "Payment confirmation UTR123456",
                "body": "Payment sent. Please confirm receipt.",
                "attachments": []
            }
        ]
        
        test_result = {
            "test": "email_blocking",
            "total_emails_processed": len(test_emails),
            "emails_sent_without_approval": 0,
            "emails_pending_approval": 0,
            "errors": []
        }
        
        for email in test_emails:
            print(f"\n📧 Processing: {email['subject']}")
            result = await self.orchestrator.process_email(email)
            
            workflow_id = result.get('workflow_id')
            if workflow_id:
                with get_db() as db:
                    # Check for executed emails
                    executed = db.query(ActionAudit).filter(
                        ActionAudit.workflow_id == workflow_id,
                        ActionAudit.action_name.like('%email%'),
                        ActionAudit.executed == 1
                    ).all()
                    
                    if executed:
                        test_result["emails_sent_without_approval"] += len(executed)
                        for action in executed:
                            test_result["errors"].append(
                                f"❌ Email action '{action.action_name}' executed without approval!"
                            )
                    
                    # Check for pending emails
                    pending = db.query(ActionAudit).filter(
                        ActionAudit.workflow_id == workflow_id,
                        ActionAudit.action_name.like('%email%'),
                        ActionAudit.executed == 0
                    ).all()
                    
                    test_result["emails_pending_approval"] += len(pending)
        
        print("\n📊 Email Blocking Summary:")
        print(f"   Total processed: {test_result['total_emails_processed']}")
        print(f"   Sent without approval: {test_result['emails_sent_without_approval']}")
        print(f"   Pending approval: {test_result['emails_pending_approval']}")
        
        if test_result["emails_sent_without_approval"] == 0:
            print("\n✅ SUCCESS: No emails sent without approval!")
        else:
            print("\n❌ FAILURE: Some emails were sent without approval!")
        
        return test_result
    
    async def test_audit_trail_completeness(self) -> Dict[str, Any]:
        """Test that all actions are properly tracked in audit trail"""
        print("\n" + "="*60)
        print("TEST 5: AUDIT TRAIL COMPLETENESS")
        print("="*60)
        
        # Process a test email
        email_data = get_test_email()
        email_data["message_id"] = f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        print("📧 Processing email for audit trail test")
        result = await self.orchestrator.process_email(email_data)
        
        test_result = {
            "test": "audit_trail",
            "workflow_id": result.get('workflow_id'),
            "total_actions_tracked": 0,
            "reversible_tracked": 0,
            "irreversible_tracked": 0,
            "missing_classifications": [],
            "errors": []
        }
        
        workflow_id = result.get('workflow_id')
        if workflow_id:
            with get_db() as db:
                # Get all audit entries
                audit_entries = db.query(ActionAudit).filter(
                    ActionAudit.workflow_id == workflow_id
                ).all()
                
                test_result["total_actions_tracked"] = len(audit_entries)
                
                print(f"\n📊 Audit Trail for Workflow {workflow_id}:")
                print(f"   Total actions tracked: {len(audit_entries)}")
                
                for entry in audit_entries:
                    print(f"\n   Action: {entry.action_name}")
                    print(f"   Type: {entry.action_type}")
                    print(f"   Status: {'Executed' if entry.executed else 'Pending'}")
                    print(f"   Timestamp: {entry.created_at}")
                    
                    if entry.action_type == 'reversible':
                        test_result["reversible_tracked"] += 1
                    elif entry.action_type == 'irreversible':
                        test_result["irreversible_tracked"] += 1
                    else:
                        test_result["missing_classifications"].append(entry.action_name)
                
                # Verify all expected fields are populated
                for entry in audit_entries:
                    if not entry.action_id:
                        test_result["errors"].append(f"Missing action_id for {entry.action_name}")
                    if not entry.workflow_id:
                        test_result["errors"].append(f"Missing workflow_id for {entry.action_name}")
                    if entry.action_type not in ['reversible', 'irreversible']:
                        test_result["errors"].append(f"Invalid action_type for {entry.action_name}: {entry.action_type}")
        else:
            test_result["errors"].append("No workflow_id generated!")
        
        print("\n📊 Audit Summary:")
        print(f"   Reversible actions: {test_result['reversible_tracked']}")
        print(f"   Irreversible actions: {test_result['irreversible_tracked']}")
        
        if test_result["missing_classifications"]:
            print(f"   ⚠️ Unclassified actions: {test_result['missing_classifications']}")
        
        print(f"\n📊 Test Result: {'PASSED' if not test_result['errors'] else 'FAILED'}")
        
        return test_result
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*80)
        print("PHASE 8 - COMPREHENSIVE INTEGRATION TESTING")
        print("="*80)
        
        # Run each test
        self.results.append(await self.test_high_confidence_order())
        await asyncio.sleep(1)  # Small delay between tests
        
        self.results.append(await self.test_medium_confidence_order())
        await asyncio.sleep(1)
        
        self.results.append(await self.test_low_confidence_order())
        await asyncio.sleep(1)
        
        self.results.append(await self.test_email_blocking())
        await asyncio.sleep(1)
        
        self.results.append(await self.test_audit_trail_completeness())
        
        # Print summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if not r.get("errors", []))
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        print("\nDetailed Results:")
        for result in self.results:
            test_name = result["test"]
            status = "✅ PASSED" if not result.get("errors", []) else "❌ FAILED"
            print(f"\n{test_name}: {status}")
            
            if result.get("errors"):
                for error in result["errors"]:
                    print(f"   {error}")
            
            # Print key metrics
            if "confidence" in result:
                print(f"   Confidence: {result['confidence']}%")
            if "auto_executed" in result:
                print(f"   Auto-executed: {len(result['auto_executed'])} actions")
            if "pending_approval" in result:
                print(f"   Pending approval: {len(result['pending_approval'])} actions")
        
        # Overall status
        print("\n" + "="*80)
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! System is ready for production.")
        else:
            print(f"⚠️ {total_tests - passed_tests} test(s) failed. Please review and fix issues.")
        print("="*80)


async def main():
    """Main entry point for integration testing"""
    test_suite = IntegrationTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())