"""
Proposal Review Dashboard for V4 Orchestrator
Displays workflow proposals for human review and approval
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
import gradio as gr

from ..factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4
from ..factory_models import ProposedWorkflow, ApprovalStatus

logger = logging.getLogger(__name__)


class ProposalReviewDashboard:
    """Dashboard for reviewing and approving workflow proposals"""
    
    def __init__(self, orchestrator_v4: Optional[ProposalOrchestratorV4] = None):
        """Initialize the proposal dashboard"""
        self.orchestrator = orchestrator_v4
        self.selected_proposal_id = None
        
    def get_proposals_dataframe(self) -> pd.DataFrame:
        """Get all proposals as a dataframe for display"""
        if not self.orchestrator:
            return pd.DataFrame()
            
        proposals = self.orchestrator.get_all_proposals()
        
        if not proposals:
            return pd.DataFrame(columns=[
                "Workflow ID", "Type", "Confidence", "Status", 
                "Customer", "Actions", "Created"
            ])
        
        data = []
        for proposal in proposals:
            data.append({
                "Workflow ID": proposal.workflow_id,
                "Type": proposal.workflow_type.value.replace("_", " ").title(),
                "Confidence": f"{proposal.confidence:.1%}",
                "Status": proposal.approval_status.value,
                "Customer": proposal.customer_tier.value,
                "Actions": len(proposal.proposed_actions),
                "Created": proposal.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        return pd.DataFrame(data)
    
    def get_proposal_details(self, workflow_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific proposal"""
        if not self.orchestrator or not workflow_id:
            return {}
            
        proposal = self.orchestrator.get_proposal_by_id(workflow_id)
        if not proposal:
            return {}
            
        details = {
            "workflow_id": proposal.workflow_id,
            "type": proposal.workflow_type.value,
            "confidence": proposal.confidence,
            "status": proposal.approval_status.value,
            "customer_tier": proposal.customer_tier.value,
            "reasoning": proposal.reasoning,
            "estimated_value": proposal.estimated_value,
            "created_at": proposal.created_at.isoformat(),
            "actions": [],
            "risks": [],
            "alternatives": [],
            "email_draft": None,
            "inventory_matches": []
        }
        
        # Add proposed actions
        for action in proposal.proposed_actions:
            details["actions"].append({
                "step": action.step,
                "type": action.action.value,
                "details": action.details,
                "confidence": action.confidence,
                "risk": action.risk.value
            })
        
        # Add risks
        if proposal.risks:
            for risk in proposal.risks:
                details["risks"].append({
                    "risk": risk.risk,
                    "description": risk.description,
                    "likelihood": risk.likelihood,
                    "impact": risk.impact,
                    "mitigation": risk.mitigation
                })
        
        # Add alternatives
        if proposal.alternatives:
            for alt in proposal.alternatives:
                details["alternatives"].append({
                    "action": alt.action,
                    "reason": alt.reason,
                    "confidence": alt.confidence
                })
        
        # Add email draft
        if proposal.email_content:
            details["email_draft"] = {
                "subject": proposal.email_content.subject,
                "body": proposal.email_content.body
            }
        
        # Add inventory matches
        if proposal.analysis and proposal.analysis.inventory_matches:
            for match in proposal.analysis.inventory_matches[:10]:
                details["inventory_matches"].append({
                    "tag_code": match.get("tag_code", "N/A"),
                    "name": match.get("tag_name", "Unknown"),
                    "confidence": match.get("confidence", 0)
                })
        
        return details
    
    def format_proposal_display(self, details: Dict[str, Any]) -> str:
        """Format proposal details for display"""
        if not details:
            return "No proposal selected"
            
        output = f"""# Workflow Proposal: {details['workflow_id']}

## Overview
- **Type:** {details['type'].replace('_', ' ').title()}
- **Confidence:** {details['confidence']:.1%}
- **Status:** {details['status']}
- **Customer Tier:** {details['customer_tier']}
- **Estimated Value:** ${details['estimated_value']:.2f if details['estimated_value'] else 0} {'(estimated)' if details['estimated_value'] else 'N/A'}

## Reasoning
{details['reasoning']}

## Proposed Actions ({len(details['actions'])} steps)
"""
        
        for action in details['actions']:
            risk_emoji = "🟢" if action['risk'] == "low" else "🟡" if action['risk'] == "medium" else "🔴"
            output += f"\n**Step {action['step']}:** {action['type'].replace('_', ' ').title()} {risk_emoji}\n"
            output += f"- {action['details']}\n"
            output += f"- Confidence: {action['confidence']:.1%} | Risk: {action['risk']}\n"
        
        if details['inventory_matches']:
            output += f"\n## Inventory Matches ({len(details['inventory_matches'])} items)\n"
            for match in details['inventory_matches'][:5]:
                output += f"- **{match['tag_code']}**: {match['name']} (Confidence: {match['confidence']:.1%})\n"
        
        if details['risks']:
            output += f"\n## Risk Assessment\n"
            for risk in details['risks']:
                output += f"\n**{risk['risk']}**\n"
                output += f"- {risk['description']}\n"
                output += f"- Likelihood: {risk['likelihood']} | Impact: {risk['impact']}\n"
                output += f"- Mitigation: {risk['mitigation']}\n"
        
        if details['alternatives']:
            output += f"\n## Alternative Actions\n"
            for alt in details['alternatives']:
                output += f"- **{alt['action']}**: {alt['reason']} (Confidence: {alt['confidence']:.1%})\n"
        
        if details['email_draft']:
            output += f"\n## Draft Email Response\n"
            output += f"**Subject:** {details['email_draft']['subject']}\n\n"
            output += f"```\n{details['email_draft']['body']}\n```\n"
        
        return output
    
    def approve_proposal(self, workflow_id: str, approver_email: str) -> str:
        """Approve a proposal"""
        if not self.orchestrator or not workflow_id:
            return "❌ No proposal selected"
            
        if not approver_email:
            return "❌ Please enter your email for approval tracking"
            
        success = self.orchestrator.approve_proposal(workflow_id, approver_email)
        
        if success:
            logger.info(f"Proposal {workflow_id} approved by {approver_email}")
            return f"✅ Proposal {workflow_id} approved! Ready for execution."
        else:
            return f"❌ Failed to approve proposal {workflow_id}"
    
    def reject_proposal(self, workflow_id: str, reason: str) -> str:
        """Reject a proposal"""
        if not self.orchestrator or not workflow_id:
            return "❌ No proposal selected"
            
        if not reason:
            return "❌ Please provide a reason for rejection"
            
        success = self.orchestrator.reject_proposal(workflow_id, reason)
        
        if success:
            logger.info(f"Proposal {workflow_id} rejected: {reason}")
            return f"✅ Proposal {workflow_id} rejected"
        else:
            return f"❌ Failed to reject proposal {workflow_id}"
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface for proposal review"""
        with gr.Blocks() as interface:
            gr.Markdown("### 📋 Workflow Proposal Review")
            
            with gr.Row():
                with gr.Column(scale=1):
                    # Proposal list
                    gr.Markdown("#### Pending Proposals")
                    proposals_table = gr.DataFrame(
                        value=self.get_proposals_dataframe(),
                        interactive=False,
                        label="Click on a proposal to view details"
                    )
                    
                    refresh_btn = gr.Button("🔄 Refresh Proposals", variant="secondary")
                    
                    # Selection
                    selected_id = gr.Textbox(
                        label="Selected Workflow ID",
                        interactive=False,
                        visible=False
                    )
                    
                with gr.Column(scale=2):
                    # Proposal details
                    gr.Markdown("#### Proposal Details")
                    proposal_display = gr.Markdown(
                        value="Select a proposal from the list to view details",
                        elem_classes=["proposal-details"]
                    )
                    
                    # Approval section
                    with gr.Row():
                        approver_email = gr.Textbox(
                            label="Your Email (for approval tracking)",
                            placeholder="approver@company.com"
                        )
                        
                    with gr.Row():
                        approve_btn = gr.Button("✅ Approve", variant="primary")
                        reject_reason = gr.Textbox(
                            label="Rejection Reason",
                            placeholder="Enter reason for rejection..."
                        )
                        reject_btn = gr.Button("❌ Reject", variant="stop")
                    
                    approval_result = gr.Textbox(
                        label="Result",
                        interactive=False
                    )
            
            # Event handlers
            def on_select(evt: gr.SelectData, df):
                """Handle proposal selection from table"""
                if evt.index[0] < len(df):
                    workflow_id = df.iloc[evt.index[0]]["Workflow ID"]
                    details = self.get_proposal_details(workflow_id)
                    display = self.format_proposal_display(details)
                    return workflow_id, display
                return "", "No proposal selected"
            
            def refresh_proposals():
                """Refresh the proposals table"""
                return self.get_proposals_dataframe()
            
            # Wire up events
            proposals_table.select(
                on_select,
                inputs=[proposals_table],
                outputs=[selected_id, proposal_display]
            )
            
            refresh_btn.click(
                refresh_proposals,
                outputs=[proposals_table]
            )
            
            approve_btn.click(
                lambda wid, email: self.approve_proposal(wid, email),
                inputs=[selected_id, approver_email],
                outputs=[approval_result]
            ).then(
                refresh_proposals,
                outputs=[proposals_table]
            )
            
            reject_btn.click(
                lambda wid, reason: self.reject_proposal(wid, reason),
                inputs=[selected_id, reject_reason],
                outputs=[approval_result]
            ).then(
                refresh_proposals,
                outputs=[proposals_table]
            )
        
        return interface