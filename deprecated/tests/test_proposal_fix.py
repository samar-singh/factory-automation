#!/usr/bin/env python3
"""Test script to verify proposal UI formatting fix"""

import asyncio
from factory_automation.factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_ui.proposal_review_dashboard import ProposalReviewDashboard

async def test_proposal_formatting():
    print("Testing proposal formatting fix...")
    
    # Initialize components
    chromadb_client = ChromaDBClient()
    orchestrator = ProposalOrchestratorV4(chromadb_client, use_mock_gmail=True)
    dashboard = ProposalReviewDashboard(orchestrator_v4=orchestrator)
    
    # Create a test email
    email_data = {
        'from': 'test@example.com',
        'subject': 'Test Order',
        'body': 'Need 100 tags',
        'attachments': []
    }
    
    # Generate proposal
    print("Generating proposal...")
    proposal = await orchestrator.process_email(email_data)
    
    if proposal:
        print(f"✅ Proposal generated: {proposal.workflow_id}")
        
        # Test formatting
        try:
            details = dashboard.get_proposal_details(proposal.workflow_id)
            formatted = dashboard.format_proposal_display(details)
            print("✅ Formatting successful!")
            print(f"   - Confidence: {proposal.confidence:.1%}")
            print(f"   - Actions: {len(proposal.proposed_actions)}")
            
            # Check for None values
            for action in proposal.proposed_actions:
                if action.confidence is None:
                    print(f"⚠️  Action {action.step} has None confidence")
            
            return True
        except Exception as e:
            print(f"❌ Formatting error: {e}")
            return False
    else:
        print("❌ No proposal generated")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_proposal_formatting())
    if success:
        print("\n✅ All tests passed - formatting fix is working!")
    else:
        print("\n❌ Tests failed - formatting issue persists")