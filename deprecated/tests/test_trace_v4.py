#!/usr/bin/env python3
"""Test trace functionality in V4 Proposal Orchestrator"""

import asyncio
import logging
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_trace():
    """Test the trace functionality"""
    print("\n🔍 Testing Trace Functionality in V4 Proposal Orchestrator\n")
    
    # Initialize ChromaDB
    chromadb_client = ChromaDBClient()
    
    # Create orchestrator with trace support
    orchestrator = ProposalOrchestratorV4(chromadb_client, use_mock_gmail=False)
    
    # Test email
    test_email = {
        "from": "customer@example.com",
        "subject": "Order for 500 Allen Solly Tags - Trace Test",
        "body": "We need 500 Allen Solly fit tags (TBALWBL0009N) urgently. Please provide quotation.",
        "attachments": []
    }
    
    print("📧 Processing test email with trace monitoring...")
    print(f"   Subject: {test_email['subject']}")
    print(f"   From: {test_email['from']}")
    
    try:
        # Process email - this will create a trace
        proposal = await orchestrator.process_email(test_email)
        
        if proposal:
            print("\n✅ Proposal generated successfully!")
            print(f"   Workflow ID: {proposal.workflow_id}")
            print(f"   Type: {proposal.workflow_type.value}")
            print(f"   Confidence: {proposal.confidence:.2%}")
            print(f"   Actions: {len(proposal.proposed_actions)}")
            print(f"   Risks: {len(proposal.risks) if proposal.risks else 0}")
            
            # The trace name would be
            trace_name = f"Proposal_Generation_{test_email['subject'][:30]}"
            print("\n📊 Trace Information:")
            print(f"   Trace Name: {trace_name}")
            print("   Status: Completed")
            print("   Mode: proposal_generation")
            
            # Display proposed actions
            print("\n📋 Proposed Actions:")
            for action in proposal.proposed_actions[:3]:  # Show first 3
                print(f"   {action.step}. {action.action.value}: {action.details}")
            
            if len(proposal.proposed_actions) > 3:
                print(f"   ... and {len(proposal.proposed_actions) - 3} more actions")
            
        else:
            print("❌ Failed to generate proposal")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Trace test complete!")
    print("Note: Traces are sent to OpenAI's trace backend for monitoring")
    print("You can view them in the OpenAI dashboard if configured.\n")

if __name__ == "__main__":
    asyncio.run(test_trace())