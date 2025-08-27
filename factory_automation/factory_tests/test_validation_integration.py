#!/usr/bin/env python3
"""Test ValidationAgent integration with Allen Solly email"""

import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_tests.standard_test_case import get_test_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_validation():
    """Test validation with standard Allen Solly email"""
    try:
        # Initialize ChromaDB
        logger.info("Initializing ChromaDB client...")
        chromadb_client = ChromaDBClient()
        
        # Initialize orchestrator with validation
        logger.info("Initializing orchestrator with validation enabled...")
        orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=True)
        
        # Get standard test email
        email_data = get_test_email()
        logger.info(f"Using test email from: {email_data['from']}")
        logger.info(f"Subject: {email_data['subject']}")
        logger.info(f"Attachments: {len(email_data.get('attachments', []))}")
        
        # Process with validation
        logger.info("\n" + "="*60)
        logger.info("Processing email with validation...")
        logger.info("="*60)
        
        result = await orchestrator.process_email(email_data)
        
        # Display validation results
        logger.info("\n" + "="*60)
        logger.info("VALIDATION RESULTS")
        logger.info("="*60)
        
        # Check validation stats
        validation_stats = result.get('validation_stats', {})
        logger.info(f"✅ Valid tool calls: {validation_stats.get('valid', 0)}")
        logger.info(f"❌ Wrong first tool: {validation_stats.get('wrong_first_tool', 0)}")
        logger.info(f"❌ Missing dependencies: {validation_stats.get('missing_dependencies', 0)}")
        logger.info(f"❌ Invalid parameters: {validation_stats.get('invalid_parameters', 0)}")
        
        # Display executed tools
        logger.info(f"\n📋 Tools executed: {result.get('executed_tools', [])}")
        logger.info(f"🎯 Workflow complete: {result.get('workflow_complete', False)}")
        logger.info(f"📧 Email type detected: {result.get('email_type', 'unknown')}")
        
        # Display two-tier results
        logger.info("\n" + "="*60)
        logger.info("TWO-TIER ACTION RESULTS")
        logger.info("="*60)
        
        auto_executed = result.get('auto_executed_actions', [])
        pending_approval = result.get('pending_approval_actions', [])
        
        if auto_executed:
            logger.info(f"\n✅ Auto-executed actions ({len(auto_executed)}):")
            for action in auto_executed:
                logger.info(f"  - {action.get('action_name')} ({action.get('status')})")
        
        if pending_approval:
            logger.info(f"\n🟠 Pending approval ({len(pending_approval)}):")
            for action in pending_approval:
                logger.info(f"  - {action.get('action_name')} (ID: {action.get('action_id')})")
        
        # Display final summary
        logger.info("\n" + "="*60)
        logger.info("FINAL SUMMARY")
        logger.info("="*60)
        logger.info(result.get('final_summary', 'No summary'))
        
        # Check if validation enforced correct order
        if validation_stats.get('wrong_first_tool', 0) > 0:
            logger.warning("\n⚠️ ValidationAgent prevented incorrect tool order!")
            logger.info("The AI tried to call the wrong tool first but was corrected.")
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        raise

def main():
    """Main entry point"""
    logger.info("\n" + "="*60)
    logger.info("VALIDATION INTEGRATION TEST")
    logger.info("Testing ValidationAgent with Allen Solly Email")
    logger.info("="*60)
    
    try:
        result = asyncio.run(test_validation())
        
        # Final verdict
        logger.info("\n" + "="*60)
        if result.get('success'):
            logger.info("✅ TEST PASSED - Validation integration working!")
        else:
            logger.error("❌ TEST FAILED - Check logs for details")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()