"""
Comprehensive test suite for Proposal-Based Orchestrator V4
Tests the conversion from execution tools to proposal tools
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from factory_automation.factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4
from factory_automation.factory_models import (
    ProposedWorkflow,
    WorkflowType,
    ApprovalStatus,
    CustomerTier,
    RiskLevel,
    WorkflowAnalysis,
)
from factory_automation.factory_database.vector_db import ChromaDBClient


class TestProposalOrchestrator:
    """Test suite for the proposal-based orchestrator"""
    
    @pytest.fixture
    def mock_chromadb(self):
        """Create a mock ChromaDB client"""
        mock = Mock(spec=ChromaDBClient)
        
        # Mock search results
        mock.search.return_value = {
            "ids": [["TAG001", "TAG002", "TAG003"]],
            "documents": [["Allen Solly Fit Tag", "Van Heusen Label", "Peter England Tag"]],
            "distances": [[0.1, 0.2, 0.3]],
            "metadatas": [[
                {"quantity": 1000, "size": "32", "color": "blue"},
                {"quantity": 500, "size": "34", "color": "white"},
                {"quantity": 750, "size": "36", "color": "black"}
            ]]
        }
        
        return mock
    
    @pytest.fixture
    def mock_gmail_agent(self):
        """Create a mock Gmail agent"""
        mock = AsyncMock()
        mock.poll_emails.return_value = [
            {
                "from": "customer@example.com",
                "subject": "Order for Allen Solly Tags",
                "body": "We need 500 Allen Solly fit tags urgently.",
                "attachments": ["order.xlsx"],
                "date": datetime.now().isoformat()
            }
        ]
        return mock
    
    @pytest.fixture
    def orchestrator(self, mock_chromadb):
        """Create orchestrator instance with mocked dependencies"""
        with patch('factory_automation.factory_agents.orchestrator_v4_proposal.MockGmailAgent'):
            orchestrator = ProposalOrchestratorV4(mock_chromadb, use_mock_gmail=False)
            return orchestrator
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, mock_chromadb):
        """Test that orchestrator initializes correctly"""
        orchestrator = ProposalOrchestratorV4(mock_chromadb, use_mock_gmail=False)
        
        assert orchestrator.chromadb_client == mock_chromadb
        assert orchestrator.proposal_engine is not None
        assert orchestrator.proposals == []
        assert len(orchestrator.tools) > 0
        assert orchestrator.agent is not None
    
    @pytest.mark.asyncio
    async def test_proposal_generation_tool(self, orchestrator):
        """Test the analyze_email_and_propose tool"""
        # Get the tool
        tool = None
        for t in orchestrator.tools:
            if hasattr(t, '__name__') and 'analyze_email_and_propose' in t.__name__:
                tool = t
                break
        
        assert tool is not None, "analyze_email_and_propose tool not found"
        
        # Test the tool
        result = await tool(
            email_subject="Order for Tags",
            email_body="We need 500 tags",
            sender_email="customer@test.com",
            attachments=[]
        )
        
        assert result["success"] == True
        assert "workflow_id" in result
        assert "workflow_type" in result
        assert "confidence" in result
        assert "actions_count" in result
        assert len(orchestrator.proposals) > 0
    
    @pytest.mark.asyncio
    async def test_inventory_search_tool(self, orchestrator, mock_chromadb):
        """Test the search_inventory_for_proposal tool"""
        # Get the tool
        tool = None
        for t in orchestrator.tools:
            if hasattr(t, '__name__') and 'search_inventory_for_proposal' in t.__name__:
                tool = t
                break
        
        assert tool is not None, "search_inventory_for_proposal tool not found"
        
        # Test the tool
        result = tool(
            query="Allen Solly tags",
            min_quantity=100,
            limit=5
        )
        
        assert result["success"] == True
        assert "matches" in result
        assert result["matches_found"] > 0
        mock_chromadb.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attachment_analysis_tool(self, orchestrator):
        """Test the analyze_attachments_for_proposal tool"""
        # Get the tool
        tool = None
        for t in orchestrator.tools:
            if hasattr(t, '__name__') and 'analyze_attachments_for_proposal' in t.__name__:
                tool = t
                break
        
        assert tool is not None, "analyze_attachments_for_proposal tool not found"
        
        # Test the tool
        result = await tool(
            attachment_names=["order.xlsx", "invoice.pdf", "product.jpg"],
            attachment_types=["application/excel", "application/pdf", "image/jpeg"]
        )
        
        assert result["success"] == True
        assert result["attachments_analyzed"] == 3
        assert len(result["extracted_data"]) == 3
        
        # Check categorization
        assert result["extracted_data"][0]["type"] == "spreadsheet"
        assert result["extracted_data"][1]["type"] == "document"
        assert result["extracted_data"][2]["type"] == "image"
    
    @pytest.mark.asyncio
    async def test_context_enrichment_tool(self, orchestrator):
        """Test the enrich_proposal_with_context tool"""
        # First create a proposal with proper WorkflowAnalysis
        analysis = WorkflowAnalysis(
            email_classification="new_order",
            customer_context={},
            inventory_matches=[],
            confidence_metrics={"overall": 0.75},
            risk_assessment=[],
            extracted_requirements={}
        )
        
        orchestrator.proposals.append(
            ProposedWorkflow(
                workflow_id="WF-TEST-001",
                workflow_type=WorkflowType.NEW_ORDER,
                confidence=0.75,
                customer_tier=CustomerTier.NEW,
                analysis=analysis,
                proposed_actions=[],
                reasoning="Initial reasoning"
            )
        )
        
        # Get the tool
        tool = None
        for t in orchestrator.tools:
            if hasattr(t, '__name__') and 'enrich_proposal_with_context' in t.__name__:
                tool = t
                break
        
        assert tool is not None, "enrich_proposal_with_context tool not found"
        
        # Test the tool
        result = tool(
            workflow_id="WF-TEST-001",
            customer_email="customer@gmail.com"
        )
        
        assert result["success"] == True
        assert "context_added" in result
        assert result["context_added"]["customer_tier"] == "regular"
        assert "previous orders" in orchestrator.proposals[0].reasoning
    
    @pytest.mark.asyncio
    async def test_get_proposal_details_tool(self, orchestrator):
        """Test the get_proposal_details tool"""
        # Create a test proposal
        from factory_automation.factory_models import (
            ProposedAction, ActionType, EmailContent, AlternativeAction, RiskAssessment
        )
        
        analysis = WorkflowAnalysis(
            email_classification="new_order",
            customer_context={},
            inventory_matches=[],
            confidence_metrics={"overall": 0.85},
            risk_assessment=[],
            extracted_requirements={}
        )
        
        test_proposal = ProposedWorkflow(
            workflow_id="WF-TEST-002",
            workflow_type=WorkflowType.NEW_ORDER,
            confidence=0.85,
            customer_tier=CustomerTier.REGULAR,
            analysis=analysis,
            proposed_actions=[
                ProposedAction(
                    step=1,
                    action=ActionType.VALIDATE_INVENTORY,
                    details="Check inventory availability",
                    confidence=0.9,
                    risk=RiskLevel.LOW
                )
            ],
            reasoning="Test reasoning",
            alternatives=[
                AlternativeAction(
                    action="Request more info",
                    reason="Low confidence",
                    confidence=0.6,
                    impact="Delay processing"
                )
            ],
            risks=[
                RiskAssessment(
                    risk="stock_shortage",
                    description="Not enough inventory",
                    likelihood="low",
                    impact="high",
                    mitigation="Reserve immediately",
                    risk_level=RiskLevel.MEDIUM
                )
            ],
            email_content=EmailContent(
                subject="Re: Order",
                body="Thank you for your order"
            )
        )
        
        orchestrator.proposals.append(test_proposal)
        
        # Get the tool
        tool = None
        for t in orchestrator.tools:
            if hasattr(t, '__name__') and 'get_proposal_details' in t.__name__:
                tool = t
                break
        
        assert tool is not None, "get_proposal_details tool not found"
        
        # Test the tool
        result = tool(workflow_id="WF-TEST-002")
        
        assert result["success"] == True
        assert result["workflow_id"] == "WF-TEST-002"
        assert result["confidence"] == 0.85
        assert len(result["actions"]) == 1
        assert len(result["alternatives"]) == 1
        assert len(result["risks"]) == 1
        assert result["email_content"] is not None
    
    @pytest.mark.asyncio
    async def test_list_proposals_tool(self, orchestrator):
        """Test the list_proposals tool"""
        # Add some test proposals
        for i in range(3):
            orchestrator.proposals.append(
                ProposedWorkflow(
                    workflow_id=f"WF-TEST-{i:03d}",
                    workflow_type=WorkflowType.NEW_ORDER,
                    confidence=0.7 + i * 0.1,
                    customer_tier=CustomerTier.NEW,
                    analysis=MagicMock(),
                    proposed_actions=[],
                    reasoning=f"Test proposal {i}"
                )
            )
        
        # Get the tool
        tool = None
        for t in orchestrator.tools:
            if hasattr(t, '__name__') and 'list_proposals' in t.__name__:
                tool = t
                break
        
        assert tool is not None, "list_proposals tool not found"
        
        # Test the tool
        result = tool()
        
        assert result["success"] == True
        assert result["total_proposals"] == 3
        assert len(result["proposals"]) == 3
        assert all(p["workflow_type"] == "new_order_processing" for p in result["proposals"])
    
    @pytest.mark.asyncio
    async def test_process_email_generates_proposal(self, orchestrator, mock_chromadb):
        """Test that processing an email generates a proposal"""
        email_data = {
            "from": "customer@test.com",
            "subject": "Urgent Order Request",
            "body": "We need 1000 Allen Solly tags by next week",
            "attachments": ["order.pdf"]
        }
        
        # Mock the runner
        with patch.object(orchestrator.runner, 'run') as mock_run:
            mock_result = MagicMock()
            mock_result.messages = [
                MagicMock(content="Processed email and generated proposal WF-20250819-test1234")
            ]
            mock_run.return_value = mock_result
            
            # Add a proposal to be found
            test_proposal = ProposedWorkflow(
                workflow_id="WF-20250819-test1234",
                workflow_type=WorkflowType.NEW_ORDER,
                confidence=0.85,
                customer_tier=CustomerTier.NEW,
                analysis=MagicMock(),
                proposed_actions=[],
                reasoning="Test"
            )
            orchestrator.proposals.append(test_proposal)
            
            # Process the email
            proposal = await orchestrator.process_email(email_data)
            
            assert proposal is not None
            assert proposal.workflow_id == "WF-20250819-test1234"
            assert proposal.workflow_type == WorkflowType.NEW_ORDER
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_proposal(self, orchestrator):
        """Test approving a proposal"""
        # Add a test proposal
        test_proposal = ProposedWorkflow(
            workflow_id="WF-APPROVE-001",
            workflow_type=WorkflowType.NEW_ORDER,
            confidence=0.9,
            customer_tier=CustomerTier.PREMIUM,
            analysis=MagicMock(),
            proposed_actions=[],
            reasoning="Test"
        )
        orchestrator.proposals.append(test_proposal)
        
        # Approve it
        result = orchestrator.approve_proposal("WF-APPROVE-001", "test_user")
        
        assert result == True
        assert test_proposal.approval_status == ApprovalStatus.APPROVED
        assert test_proposal.approved_by == "test_user"
        assert test_proposal.approved_at is not None
    
    @pytest.mark.asyncio
    async def test_reject_proposal(self, orchestrator):
        """Test rejecting a proposal"""
        # Add a test proposal
        test_proposal = ProposedWorkflow(
            workflow_id="WF-REJECT-001",
            workflow_type=WorkflowType.NEW_ORDER,
            confidence=0.4,
            customer_tier=CustomerTier.NEW,
            analysis=MagicMock(),
            proposed_actions=[],
            reasoning="Test"
        )
        orchestrator.proposals.append(test_proposal)
        
        # Reject it
        result = orchestrator.reject_proposal("WF-REJECT-001", "Low confidence")
        
        assert result == True
        assert test_proposal.approval_status == ApprovalStatus.REJECTED
        assert test_proposal.approval_notes == "Low confidence"
    
    @pytest.mark.asyncio
    async def test_get_all_proposals(self, orchestrator):
        """Test retrieving all proposals"""
        # Add multiple proposals
        for i in range(5):
            orchestrator.proposals.append(
                ProposedWorkflow(
                    workflow_id=f"WF-ALL-{i:03d}",
                    workflow_type=WorkflowType.NEW_ORDER,
                    confidence=0.5 + i * 0.1,
                    customer_tier=CustomerTier.REGULAR,
                    analysis=MagicMock(),
                    proposed_actions=[],
                    reasoning=f"Proposal {i}"
                )
            )
        
        # Get all proposals
        all_proposals = orchestrator.get_all_proposals()
        
        assert len(all_proposals) == 5
        assert all(isinstance(p, ProposedWorkflow) for p in all_proposals)
        assert all_proposals[0].workflow_id == "WF-ALL-000"
        assert all_proposals[4].workflow_id == "WF-ALL-004"
    
    @pytest.mark.asyncio
    async def test_get_proposal_by_id(self, orchestrator):
        """Test retrieving a specific proposal by ID"""
        # Add test proposals
        target_proposal = ProposedWorkflow(
            workflow_id="WF-TARGET-001",
            workflow_type=WorkflowType.PAYMENT_PROCESSING,
            confidence=0.95,
            customer_tier=CustomerTier.VIP,
            analysis=MagicMock(),
            proposed_actions=[],
            reasoning="Target proposal"
        )
        
        orchestrator.proposals.extend([
            ProposedWorkflow(
                workflow_id="WF-OTHER-001",
                workflow_type=WorkflowType.NEW_ORDER,
                confidence=0.7,
                customer_tier=CustomerTier.NEW,
                analysis=MagicMock(),
                proposed_actions=[],
                reasoning="Other"
            ),
            target_proposal,
            ProposedWorkflow(
                workflow_id="WF-OTHER-002",
                workflow_type=WorkflowType.ORDER_CLARIFICATION,
                confidence=0.6,
                customer_tier=CustomerTier.REGULAR,
                analysis=MagicMock(),
                proposed_actions=[],
                reasoning="Another"
            )
        ])
        
        # Get specific proposal
        found = orchestrator.get_proposal_by_id("WF-TARGET-001")
        
        assert found is not None
        assert found.workflow_id == "WF-TARGET-001"
        assert found.workflow_type == WorkflowType.PAYMENT_PROCESSING
        assert found.confidence == 0.95
        
        # Test not found
        not_found = orchestrator.get_proposal_by_id("WF-NONEXISTENT")
        assert not_found is None


@pytest.mark.asyncio
async def test_proposal_workflow_end_to_end():
    """Test complete workflow from email to approved proposal"""
    
    # Setup mocks
    mock_chromadb = Mock(spec=ChromaDBClient)
    mock_chromadb.search.return_value = {
        "ids": [["TBALWBL0009N"]],
        "documents": [["Allen Solly Relaxed Fit Tag"]],
        "distances": [[0.05]],
        "metadatas": [[{"quantity": 2000, "size": "32", "price": 12.0}]]
    }
    
    # Create orchestrator
    orchestrator = ProposalOrchestratorV4(mock_chromadb, use_mock_gmail=False)
    
    # Process an email
    email_data = {
        "from": "premium@customer.com",
        "subject": "Urgent Order - Allen Solly Tags",
        "body": "Dear Team,\n\nWe urgently need 500 Allen Solly fit tags (TBALWBL0009N).\nPlease provide best price and delivery timeline.\n\nThanks",
        "attachments": []
    }
    
    # Manually call the proposal generation tool
    for tool in orchestrator.tools:
        if hasattr(tool, '__name__') and 'analyze_email_and_propose' in tool.__name__:
            result = await tool(
                email_subject=email_data["subject"],
                email_body=email_data["body"],
                sender_email=email_data["from"],
                attachments=email_data["attachments"]
            )
            break
    
    # Verify proposal was created
    assert len(orchestrator.proposals) > 0
    proposal = orchestrator.proposals[0]
    
    # Check proposal details
    assert proposal.workflow_type in [WorkflowType.NEW_ORDER, WorkflowType.QUOTATION_REQUEST]
    assert proposal.confidence > 0
    assert proposal.customer_tier in [CustomerTier.NEW, CustomerTier.REGULAR]
    assert proposal.reasoning != ""
    
    # Check email content was generated
    if proposal.email_content:
        assert "Allen Solly" in proposal.email_content.body or "order" in proposal.email_content.body.lower()
        assert proposal.email_content.subject != ""
    
    # Approve the proposal
    success = orchestrator.approve_proposal(proposal.workflow_id, "test_approver")
    assert success == True
    assert proposal.approval_status == ApprovalStatus.APPROVED
    
    print(f"\n✅ End-to-end test passed!")
    print(f"   Workflow ID: {proposal.workflow_id}")
    print(f"   Type: {proposal.workflow_type.value}")
    print(f"   Confidence: {proposal.confidence:.2%}")
    print(f"   Status: {proposal.approval_status.value}")


if __name__ == "__main__":
    # Run the end-to-end test
    asyncio.run(test_proposal_workflow_end_to_end())