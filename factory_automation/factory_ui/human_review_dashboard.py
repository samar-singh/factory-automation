"""
Human Review Dashboard - Production Interface
Handles all pending order reviews with visual and text matching
Consolidated from multiple review interfaces into single clean dashboard
"""

import json
import logging
from datetime import datetime
from typing import Optional

import gradio as gr
from sqlalchemy import text

from ..factory_agents.human_interaction_manager import HumanInteractionManager
from ..factory_database.connection import engine
from ..factory_database.vector_db import ChromaDBClient
from .assets import load_css, load_js

logger = logging.getLogger(__name__)


class HumanReviewDashboard:
    """Single unified dashboard for reviewing orders with modern UI"""

    def __init__(
        self,
        interaction_manager: Optional[HumanInteractionManager] = None,
        chromadb_client: Optional[ChromaDBClient] = None,
    ):
        """Initialize the dashboard with necessary components"""
        self.interaction_manager = interaction_manager or HumanInteractionManager()
        self.chromadb_client = chromadb_client or ChromaDBClient()
        self.recommendation_cache = {}  # Cache for quick detail access

    def format_two_tier_actions(self, executed_actions, pending_actions):
        """
        Format two-tier actions for display with colored bullets.
        Phase 5 - Display executed and pending actions clearly.
        
        Args:
            executed_actions: List of auto-executed action IDs
            pending_actions: List of pending action dictionaries
            
        Returns:
            Tuple of (executed_html, pending_html)
        """
        # Format executed actions with green bullets
        if executed_actions and len(executed_actions) > 0:
            executed_html = '<div class="card" style="border-left: 4px solid #10b981; padding: 1rem; margin-bottom: 0.5rem;">'
            executed_html += '<h5 style="color: #10b981;">✅ Auto-Executed Actions</h5>'
            executed_html += '<ul style="list-style: none; padding-left: 0;">'
            
            for action_id in executed_actions:
                # In production, we'd look up action details from the database
                # For now, show the action ID
                executed_html += f'<li style="margin: 0.5rem 0;"><span style="color: #10b981;">●</span> {action_id}</li>'
            
            executed_html += '</ul></div>'
        else:
            executed_html = '<div class="card" style="border-left: 4px solid #10b981; padding: 1rem; margin-bottom: 0.5rem;"><h5 style="color: #10b981;">✅ Auto-Executed Actions</h5><p style="color:#9ca3af;">No actions executed yet</p></div>'
        
        # Format pending actions with orange bullets and expandable details
        if pending_actions and len(pending_actions) > 0:
            pending_html = '<div class="card" style="border-left: 4px solid #f59e0b; padding: 1rem; margin-bottom: 1rem;">'
            pending_html += '<h5 style="color: #f59e0b;">⏳ Pending Approval</h5>'
            pending_html += '<ul style="list-style: none; padding-left: 0;">'
            
            for action in pending_actions:
                action_name = action.get('action_name', 'Unknown Action')
                action_id = action.get('action_id', '')
                preview = action.get('preview', '')
                reasoning = action.get('reasoning', '')
                
                # Create expandable details for each pending action
                pending_html += f'''
                <li style="margin: 0.5rem 0;">
                    <details style="cursor: pointer;">
                        <summary style="display: list-item; list-style: none;">
                            <span style="color: #f59e0b;">●</span> {action_name}
                            <span style="color: #6b7280; font-size: 0.875rem;"> - {preview}</span>
                        </summary>
                        <div style="padding: 0.5rem 0 0 1.5rem; color: #6b7280; font-size: 0.875rem;">
                            <p><strong>Action ID:</strong> {action_id}</p>
                            <p><strong>Reasoning:</strong> {reasoning if reasoning else "No reasoning provided"}</p>
                            <div style="margin-top: 0.5rem;">
                                <button onclick="approveAction('{action_id}')" style="background: #10b981; color: white; padding: 0.25rem 0.5rem; border: none; border-radius: 4px; cursor: pointer; margin-right: 0.5rem;">Approve</button>
                                <button onclick="rejectAction('{action_id}')" style="background: #ef4444; color: white; padding: 0.25rem 0.5rem; border: none; border-radius: 4px; cursor: pointer;">Reject</button>
                            </div>
                        </div>
                    </details>
                </li>
                '''
            
            pending_html += '</ul></div>'
        else:
            pending_html = '<div class="card" style="border-left: 4px solid #f59e0b; padding: 1rem; margin-bottom: 1rem;"><h5 style="color: #f59e0b;">⏳ Pending Approval</h5><p style="color:#9ca3af;">No actions pending approval</p></div>'
        
        return executed_html, pending_html
    
    def generate_contextual_email_response(self, rec_data, confidence_score):
        """Generate a contextual email response based on the recommendation data"""
        customer_email = rec_data.get("customer_email", "Customer")
        customer_name = rec_data.get("customer_name", customer_email.split("@")[0])
        action = rec_data.get("action", "review")
        
        # Get inventory matches to understand what was found
        matches = rec_data.get("inventory_matches", [])
        has_matches = len(matches) > 0
        
        # Generate response based on confidence and matches
        if confidence_score >= 0.8 and has_matches:
            # High confidence with matches - order can be processed
            email_body = f"""Dear {customer_name},

Thank you for your order. We are pleased to confirm that we have received your request and have identified the following matching items from our inventory:

"""
            for match in matches[:5]:  # Show top 5 matches
                tag_code = match.get("tag_code", "N/A")
                name = match.get("name", "Item")
                email_body += f"• {name} (Code: {tag_code})\n"
            
            email_body += """
We will process your order shortly and send you a proforma invoice with the complete details including pricing and delivery timeline.

If you have any questions or need to make changes to your order, please don't hesitate to contact us.

Best regards,
Factory Automation Team"""
            
        elif 0.6 <= confidence_score < 0.8 and has_matches:
            # Medium confidence - need clarification
            email_body = f"""Dear {customer_name},

Thank you for your order. We have identified some potential matches for your request, but we need to confirm a few details to ensure accuracy:

"""
            for match in matches[:3]:  # Show top 3 matches
                tag_code = match.get("tag_code", "N/A")
                name = match.get("name", "Item")
                email_body += f"• {name} (Code: {tag_code})\n"
            
            email_body += """
Could you please confirm if these are the correct items you're looking for? If not, please provide additional details such as:
- Specific tag codes or product names
- Quantities required for each item
- Any special specifications or requirements

Once we have this information, we'll process your order immediately.

Best regards,
Factory Automation Team"""
            
        else:
            # Low confidence or no matches - need more information
            email_body = f"""Dear {customer_name},

Thank you for your inquiry. We've reviewed your request but need additional information to identify the exact items you need from our inventory.

Could you please provide:
1. Specific tag codes or product references
2. Brand names (Allen Solly, Van Heusen, Peter England, etc.)
3. Quantities required for each item
4. Any specific size or color requirements

You can also share any product images or specification sheets that would help us identify the correct items.

We're here to help and will process your order as soon as we have the necessary details.

Best regards,
Factory Automation Team"""
        
        return email_body

    def format_additional_context(self, rec_data):
        """Format any additional context from the recommendation data"""
        context_html = ""

        # Show any additional important fields
        important_fields = {
            "reason": "Reason",
            "customer_requirements": "Customer Requirements",
            "issues": "Issues Found",
            "action_needed": "Action Needed",
            "suggested_message": "Suggested Message",
            "payment_terms": "Payment Terms",
            "delivery_date": "Delivery Date",
        }

        context_items = []
        for field, label in important_fields.items():
            if field in rec_data:
                value = rec_data[field]
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value[:3])
                elif isinstance(value, dict):
                    value = str(value)[:100] + "..."
                else:
                    value = str(value)[:200]

                if value:
                    context_items.append(
                        f"""
                    <div class="info-row">
                        <span class="label">{label}:</span>
                        <span class="value">{value}</span>
                    </div>
                    """
                    )

        if context_items:
            context_html = f"""
            <div class="card">
                <h4>📌 Additional Context</h4>
                {''.join(context_items)}
            </div>
            """

        return context_html

    def create_interface(self) -> gr.Blocks:
        """Create the main dashboard interface with modern design"""

        # Load external CSS and JavaScript assets
        custom_css = load_css("dashboard.css")
        accessibility_js = load_js("accessibility.js")
        
        with gr.Blocks(css=custom_css, theme=gr.themes.Base(), js=accessibility_js) as interface:
            gr.Markdown("# 🎯 Human Review Dashboard", elem_id="main-content")
            gr.Markdown("Review and process pending recommendations with confidence")

            # State management
            current_queue_id = gr.State(value=None)
            selected_match_id = gr.State(value=None)

            with gr.Row():
                # Left Panel: Queue List (25% width - more compact)
                with gr.Column(scale=25):
                    with gr.Row():
                        gr.Markdown("### 📋 Queue")
                        queue_count = gr.Markdown("0 items")

                    # Filters and controls
                    with gr.Row():
                        priority_filter = gr.Dropdown(
                            choices=["All", "urgent", "high", "medium", "low"],
                            value="All",
                            label="Priority Filter",
                            scale=2,
                        )
                        refresh_btn = gr.Button("🔄 Refresh", scale=1)

                    # Queue metrics
                    with gr.Row():
                        pending_count = gr.Number(
                            label="Pending", value=0, interactive=False
                        )
                        urgent_count = gr.Number(
                            label="Urgent", value=0, interactive=False
                        )
                        avg_confidence = gr.Number(
                            label="Avg Confidence", value=0, interactive=False
                        )

                    # Queue table - Make it read-only to prevent editing
                    queue_table = gr.Dataframe(
                        headers=[
                            "Customer",
                            "Priority",
                            "Conf%",
                            "Age",
                        ],
                        label="Click row for details",
                        interactive=False,  # Prevent editing/adding columns
                        wrap=True,
                        datatype=["str", "str", "str", "str"],
                        max_height=400,  # Fixed height for compact display
                    )


                # Right Panel: Details View (75% width - more space for content)
                with gr.Column(scale=75):
                    # Details header
                    gr.Markdown("### 📄 Recommendation Details")

                    # Customer information card
                    customer_card = gr.HTML(
                        value='<div class="card customer-info-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; border: 2px solid #667eea !important; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25) !important; color: white !important; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;"><h4 style="color: white !important;">👤 Customer Information</h4><p style="color:rgba(255,255,255,0.8);">No item selected</p></div>'
                    )

                    # AI Recommendation card
                    recommendation_card = gr.HTML(
                        value='<div class="card ai-recommendation-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important; border: 2px solid #f093fb !important; box-shadow: 0 4px 6px rgba(240, 147, 251, 0.25) !important; color: white !important; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;"><h4 style="color: white !important;">🤖 AI Recommendation</h4><p style="color:rgba(255,255,255,0.8);">Select an item to view recommendation</p></div>'
                    )
                    
                    # Phase 5: Two-Tier Actions Display
                    gr.Markdown("#### 🎯 Workflow Actions")
                    
                    # Executed Actions (Green bullets)
                    executed_actions_card = gr.HTML(
                        value='<div class="card" style="border-left: 4px solid #10b981; padding: 1rem; margin-bottom: 0.5rem;"><h5 style="color: #10b981;">✅ Auto-Executed Actions</h5><p style="color:#9ca3af;">No actions executed yet</p></div>'
                    )
                    
                    # Pending Actions (Orange bullets)
                    pending_actions_card = gr.HTML(
                        value='<div class="card" style="border-left: 4px solid #f59e0b; padding: 1rem; margin-bottom: 1rem;"><h5 style="color: #f59e0b;">⏳ Pending Approval</h5><p style="color:#9ca3af;">No actions pending approval</p></div>'
                    )

                    # Inventory matches section with integrated images
                    gr.Markdown("#### 📦 Inventory Matches with Images")
                    matches_html = gr.HTML(
                        value='<div class="card"><p style="color:#9ca3af;">No matches to display</p></div>'
                    )

                    # Decision section
                    gr.Markdown("### ⚡ Quick Decision")
                    with gr.Row():
                        approve_btn = gr.Button(
                            "✅ Approve",
                            variant="primary",
                            elem_classes=["action-button"],
                            interactive=False,
                        )
                        defer_btn = gr.Button(
                            "⏸️ Defer",
                            variant="secondary",
                            elem_classes=["action-button"],
                            interactive=False,
                        )
                        reject_btn = gr.Button(
                            "❌ Reject",
                            variant="stop",
                            elem_classes=["action-button"],
                            interactive=False,
                        )
                        delete_btn = gr.Button(
                            "🗑️ Delete",
                            variant="stop",
                            elem_classes=["action-button"],
                            interactive=False,
                        )

                    # Decision notes
                    decision_notes = gr.Textbox(
                        label="Decision Notes (Optional)",
                        placeholder="Add any notes about your decision...",
                        lines=2,
                        interactive=False,
                    )
                    
                    # Email Response Section (for email_response type)
                    gr.Markdown("### 📧 Email Response (Editable)")
                    email_response_text = gr.Textbox(
                        label="Email Body",
                        placeholder="Email response will appear here when an email type order is selected...",
                        lines=8,
                        interactive=False,
                        visible=False,
                    )
                    
                    email_attachments = gr.File(
                        label="Attachments (Optional)",
                        file_count="multiple",
                        interactive=False,
                        visible=False,
                    )
                    
                    send_email_btn = gr.Button(
                        "📤 Send Email",
                        variant="primary",
                        interactive=False,
                        visible=False,
                    )

                    # Result message
                    result_message = gr.Markdown("")
                    
                    # Loading status (Phase 6: Added loading states)
                    loading_status = gr.Markdown("", visible=False)

            # Event Handlers

            def refresh_queue(priority_filter):
                """Refresh the queue from database"""
                try:
                    # Get pending recommendations from database
                    priority = None if priority_filter == "All" else priority_filter
                    recommendations = (
                        self.interaction_manager.get_pending_recommendations(
                            limit=100, priority_filter=priority
                        )
                    )

                    # Format for display
                    queue_data = []
                    for rec in recommendations:
                        # Calculate age
                        created = (
                            datetime.fromisoformat(rec["created_at"])
                            if rec["created_at"]
                            else datetime.now()
                        )
                        age = datetime.now() - created
                        if age.days > 0:
                            age_str = f"{age.days}d ago"
                        elif age.seconds > 3600:
                            age_str = f"{age.seconds // 3600}h ago"
                        else:
                            age_str = f"{age.seconds // 60}m ago"

                        # Format row - simplified for compact display
                        queue_data.append(
                            [
                                rec["customer_email"][:20],  # Truncate long emails
                                rec["priority"].upper(),
                                f"{rec['confidence_score']:.0%}",
                                age_str,
                            ]
                        )

                    # Cache full data for details
                    self.recommendation_cache = {
                        rec["customer_email"][:20]: rec for rec in recommendations
                    }

                    # Calculate metrics
                    total = len(recommendations)
                    urgent = sum(
                        1 for r in recommendations if r["priority"] == "urgent"
                    )
                    avg_conf = (
                        sum(r["confidence_score"] for r in recommendations) / total
                        if total > 0
                        else 0
                    )

                    # Update UI
                    return (
                        queue_data,
                        f"{total} items",
                        total,
                        urgent,
                        avg_conf,
                    )

                except Exception as e:
                    logger.error(f"Error refreshing queue: {e}")
                    return [], "Error", 0, 0, 0

            def on_row_select(evt: gr.SelectData, table_data):
                """Handle row selection to show details"""
                import pandas as pd

                if evt.index is None or table_data is None:
                    return [gr.update()] * 15  # Updated for new fields including two-tier actions

                # Handle DataFrame properly
                if isinstance(table_data, pd.DataFrame):
                    if table_data.empty:
                        return [gr.update()] * 15  # Updated for new fields including two-tier actions
                    # Convert DataFrame to list
                    table_data = table_data.values.tolist()
                elif not table_data:
                    return [gr.update()] * 15  # Updated for new fields including two-tier actions

                try:
                    # Get selected row
                    row_idx = evt.index[0] if isinstance(evt.index, list) else evt.index
                    if row_idx >= len(table_data):
                        return [gr.update()] * 15  # Updated for new fields including two-tier actions

                    selected_row = table_data[row_idx]
                    customer_key = selected_row[0]  # Customer email (truncated)

                    # Find full recommendation data
                    rec = self.recommendation_cache.get(customer_key)
                    if not rec:
                        return [gr.update()] * 15  # Updated for new fields including two-tier actions

                    rec_data = rec.get("recommendation_data", {})

                    # Format customer card
                    customer_html = f"""
                    <div class="card customer-info-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; border: 2px solid #667eea !important; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25) !important; color: white !important; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;">
                        <h4 style="color: white !important; margin-top: 0;">👤 Customer Information</h4>
                        <div class="info-row" style="border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 0.75rem 0;">
                            <span class="label" style="color: rgba(255, 255, 255, 0.9) !important;">Email:</span>
                            <span class="value" style="color: white !important; font-weight: 600;">{rec["customer_email"]}</span>
                        </div>
                        <div class="info-row" style="border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 0.75rem 0;">
                            <span class="label" style="color: rgba(255, 255, 255, 0.9) !important;">Queue ID:</span>
                            <span class="value" style="font-family:monospace; word-break: break-all; color: white !important; font-weight: 600;">{rec["queue_id"]}</span>
                        </div>
                        <div class="info-row" style="border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 0.75rem 0;">
                            <span class="label" style="color: rgba(255, 255, 255, 0.9) !important;">Priority:</span>
                            <span class="badge" style="background: rgba(255, 255, 255, 0.2); color: white !important; padding: 0.25rem 0.75rem; border-radius: 12px;">{rec["priority"].upper()}</span>
                        </div>
                        <div class="info-row" style="padding: 0.75rem 0;">
                            <span class="label" style="color: rgba(255, 255, 255, 0.9) !important;">Created:</span>
                            <span class="value" style="color: white !important; font-weight: 600;">{rec["created_at"][:19] if rec["created_at"] else "N/A"}</span>
                        </div>
                    </div>
                    """

                    # Format recommendation card with enhanced details
                    confidence = rec["confidence_score"]
                    conf_class = (
                        "high"
                        if confidence > 0.8
                        else "medium" if confidence > 0.6 else "low"
                    )

                    # Extract key recommendation info
                    if rec["recommendation_type"] == "email_response":
                        action = rec_data.get("email_draft", {}).get(
                            "subject", "Send email response"
                        )
                        email_body = rec_data.get("email_draft", {}).get("body", "")[
                            :200
                        ]
                    elif rec["recommendation_type"] == "document_generation":
                        action = f"Generate {rec_data.get('document_type', 'document')}"
                        email_body = ""
                    else:
                        action = rec["recommendation_type"].replace("_", " ").title()
                        email_body = ""

                    # Extract document information
                    documents_html = ""

                    # Check for attachments - show ALL with details
                    if "attachments" in rec_data:
                        attachments = rec_data["attachments"]
                        if attachments:
                            documents_html += '<div class="info-row"><span class="label">📎 All Attachments:</span></div>'
                            documents_html += '<div class="document-list">'
                            for i, att in enumerate(attachments):
                                # Extract file info if available
                                if isinstance(att, dict):
                                    filename = att.get("filename", f"Attachment {i+1}")
                                    filesize = att.get("size", "")
                                    filetype = att.get("type", "")
                                    filedate = att.get("date", "")
                                else:
                                    filename = str(att)
                                    filesize = filetype = filedate = ""

                                documents_html += f"""
                                <div class="document-item">
                                    <div>
                                        <strong>{filename}</strong>
                                        {f'<br><small>{filetype} • {filesize}</small>' if filetype else ''}
                                        {f'<br><small>Received: {filedate}</small>' if filedate else ''}
                                    </div>
                                </div>
                                """
                            documents_html += "</div>"

                    # Check for processed files
                    if "files_processed" in rec_data:
                        files = rec_data["files_processed"]
                        if files:
                            documents_html += '<div class="info-row"><span class="label">📄 Files Processed:</span><span class="value">'
                            for file in files[:3]:
                                documents_html += f"<br>• {file}"
                            documents_html += "</span></div>"

                    # Check for documents
                    if "documents" in rec_data:
                        docs = rec_data["documents"]
                        if docs:
                            documents_html += '<div class="info-row"><span class="label">📚 Documents:</span><span class="value">'
                            if isinstance(docs, list):
                                for doc in docs[:3]:
                                    documents_html += f"<br>• {doc}"
                            else:
                                documents_html += f"{docs}"
                            documents_html += "</span></div>"

                    # Check for email thread/conversation
                    email_thread_html = ""
                    if "email_thread" in rec_data:
                        thread = rec_data["email_thread"]
                        email_thread_html = f"""
                        <div class="info-row">
                            <span class="label">📧 Email Thread:</span>
                            <span class="value">{thread[:100]}...</span>
                        </div>
                        """

                    # Check for order reference
                    if "order_reference" in rec_data:
                        order_ref = rec_data["order_reference"]
                        email_thread_html += f"""
                        <div class="info-row">
                            <span class="label">📋 Order Reference:</span>
                            <span class="value">{order_ref}</span>
                        </div>
                        """

                    # Check for previous interactions
                    if "previous_emails" in rec_data:
                        prev_emails = rec_data["previous_emails"]
                        email_thread_html += f"""
                        <div class="info-row">
                            <span class="label">📨 Previous Emails:</span>
                            <span class="value">{len(prev_emails)} emails in thread</span>
                        </div>
                        """

                    # Build complete recommendation card
                    recommendation_html = f"""
                    <div class="card ai-recommendation-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important; border: 2px solid #f093fb !important; box-shadow: 0 4px 6px rgba(240, 147, 251, 0.25) !important; color: white !important; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;">
                        <h4 style="color: white !important; margin-top: 0;">🤖 AI Recommendation</h4>
                        <div class="info-row" style="border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 0.75rem 0;">
                            <span class="label" style="color: rgba(255, 255, 255, 0.9) !important;">Action:</span>
                            <span class="value" style="color: white !important; font-weight: 600;">{action}</span>
                        </div>
                        <div class="info-row" style="border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 0.75rem 0;">
                            <span class="label" style="color: rgba(255, 255, 255, 0.9) !important;">Confidence:</span>
                            <span class="value" style="color: white !important; font-weight: 600;">{confidence:.1%}</span>
                        </div>
                        <div class="confidence-bar" style="height: 8px; border-radius: 4px; margin-top: 0.5rem; background: rgba(255, 255, 255, 0.2); overflow: hidden;">
                            <div class="confidence-fill" style="width:{confidence*100}%; height: 100%; background: rgba(255, 255, 255, 0.8);"></div>
                        </div>
                        <div class="info-row" style="margin-top:1rem; padding: 0.75rem 0;">
                            <span class="label" style="color: rgba(255, 255, 255, 0.9) !important;">Type:</span>
                            <span class="value" style="color: white !important; font-weight: 600;">{rec["recommendation_type"]}</span>
                        </div>
                        {email_body and f'<div class="info-row"><span class="label">Email Preview:</span><span class="value" style="font-style:italic; white-space: pre-wrap;">{email_body}</span></div>' or ''}
                    </div>
                    
                    {documents_html and f'<div class="card"><h4>📁 Documents & Attachments</h4>{documents_html}</div>' or ''}
                    
                    {email_thread_html and f'<div class="card"><h4>💬 Communication History</h4>{email_thread_html}</div>' or ''}
                    
                    {self.format_additional_context(rec_data)}
                    """

                    # Format matches as HTML table with images
                    matches_html = '<div class="card">'
                    if (
                        "inventory_matches" in rec_data
                        and rec_data["inventory_matches"]
                    ):
                        # Add JavaScript for image modal and radio selection - using a single global script
                        # This ensures proper execution timing and avoids Gradio's script sanitization
                        matches_html += """
                        <div id="image-modal-container"></div>
                        <script type="text/javascript">
                        (function() {
                            // Ensure functions are properly attached to window
                            if (typeof window.selectMatch === 'undefined') {
                                window.selectMatch = function(matchId) {
                                    console.log('selectMatch called:', matchId);
                                    try {
                                        // Update visual selection
                                        document.querySelectorAll('.match-table tr').forEach(row => {
                                            row.classList.remove('selected-match');
                                        });
                                        var targetRow = document.getElementById('match-row-' + matchId);
                                        if (targetRow) {
                                            targetRow.classList.add('selected-match');
                                        }
                                        
                                        // Store selected match ID
                                        var hiddenInput = document.getElementById('selected-match-id');
                                        if (hiddenInput) {
                                            hiddenInput.value = matchId;
                                        }
                                    } catch (e) {
                                        console.error('Error in selectMatch:', e);
                                    }
                                };
                            }
                            
                            if (typeof window.showImageModal === 'undefined') {
                                window.showImageModal = function(imageSrc, tagCode) {
                                    console.log('showImageModal called with:', tagCode, imageSrc.substring(0, 50) + '...');
                                    
                                    try {
                                        // Remove any existing modal first
                                        var existingModal = document.querySelector('.image-modal-overlay');
                                        if (existingModal) {
                                            existingModal.remove();
                                        }
                                        
                                        // Create modal overlay
                                        var modalOverlay = document.createElement('div');
                                        modalOverlay.className = 'image-modal-overlay';
                                        modalOverlay.style.cssText = `
                                            display: flex !important;
                                            position: fixed;
                                            z-index: 999999;
                                            left: 0;
                                            top: 0;
                                            width: 100%;
                                            height: 100%;
                                            background-color: rgba(0,0,0,0.95);
                                            align-items: center;
                                            justify-content: center;
                                            flex-direction: column;
                                            cursor: pointer;
                                        `;
                                        
                                        // Create close button
                                        var closeBtn = document.createElement('span');
                                        closeBtn.innerHTML = '&times;';
                                        closeBtn.style.cssText = `
                                            position: absolute;
                                            top: 20px;
                                            right: 35px;
                                            color: #f1f1f1;
                                            font-size: 40px;
                                            font-weight: bold;
                                            cursor: pointer;
                                            z-index: 1000000;
                                            user-select: none;
                                        `;
                                        closeBtn.title = 'Close (ESC)';
                                        
                                        // Create image container
                                        var imgContainer = document.createElement('div');
                                        imgContainer.style.cssText = `
                                            max-width: 90%;
                                            max-height: 80vh;
                                            display: flex;
                                            flex-direction: column;
                                            align-items: center;
                                            cursor: default;
                                        `;
                                        
                                        // Create image
                                        var img = document.createElement('img');
                                        img.src = imageSrc;
                                        img.alt = tagCode;
                                        img.style.cssText = `
                                            max-width: 100%;
                                            max-height: 70vh;
                                            object-fit: contain;
                                            border-radius: 8px;
                                            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                                        `;
                                        
                                        // Create caption
                                        var caption = document.createElement('div');
                                        caption.style.cssText = `
                                            text-align: center;
                                            color: white;
                                            margin-top: 20px;
                                            background: rgba(0,0,0,0.7);
                                            padding: 15px 25px;
                                            border-radius: 8px;
                                            max-width: 400px;
                                        `;
                                        caption.innerHTML = `
                                            <h3 style="color:white; margin:0 0 10px 0; font-size: 18px;">${tagCode}</h3>
                                            <p style="color:#ccc; margin:0; font-size: 14px;">Click outside image or press ESC to close</p>
                                        `;
                                        
                                        // Assemble modal
                                        imgContainer.appendChild(img);
                                        imgContainer.appendChild(caption);
                                        modalOverlay.appendChild(closeBtn);
                                        modalOverlay.appendChild(imgContainer);
                                        
                                        // Add to body
                                        document.body.appendChild(modalOverlay);
                                        
                                        // Event handlers
                                        var closeModal = function() {
                                            try {
                                                modalOverlay.remove();
                                            } catch (e) {
                                                console.error('Error closing modal:', e);
                                            }
                                        };
                                        
                                        // Close button click
                                        closeBtn.onclick = closeModal;
                                        
                                        // Click outside to close
                                        modalOverlay.onclick = function(event) {
                                            if (event.target === modalOverlay) {
                                                closeModal();
                                            }
                                        };
                                        
                                        // Prevent image container from closing modal
                                        imgContainer.onclick = function(e) {
                                            e.stopPropagation();
                                        };
                                        
                                        // ESC key to close
                                        var escHandler = function(e) {
                                            if (e.key === 'Escape') {
                                                closeModal();
                                                document.removeEventListener('keydown', escHandler);
                                            }
                                        };
                                        document.addEventListener('keydown', escHandler);
                                        
                                        // Add some animation
                                        modalOverlay.style.opacity = '0';
                                        setTimeout(function() {
                                            modalOverlay.style.transition = 'opacity 0.3s ease';
                                            modalOverlay.style.opacity = '1';
                                        }, 10);
                                        
                                        console.log('Modal created successfully for:', tagCode);
                                        
                                    } catch (e) {
                                        console.error('Error in showImageModal:', e);
                                        alert('Error opening image: ' + e.message);
                                    }
                                    
                                    return false; // Prevent default action
                                };
                            }
                            
                            // Enhanced debugging function
                            window.debugImageModal = function() {
                                var debug = [];
                                debug.push('showImageModal function: ' + typeof window.showImageModal);
                                debug.push('selectMatch function: ' + typeof window.selectMatch);
                                var images = document.querySelectorAll('.clickable-image');
                                debug.push('Found clickable images: ' + images.length);
                                images.forEach(function(img, i) {
                                    debug.push('Image ' + i + ' - id: ' + img.id + ', onclick: ' + (img.onclick ? 'defined' : 'undefined') + ', tag: ' + img.getAttribute('data-tag-code'));
                                });
                                
                                // Also check for modal elements
                                var existingModal = document.querySelector('.image-modal-overlay');
                                debug.push('Existing modal: ' + (existingModal ? 'found' : 'none'));
                                
                                var debugMessage = debug.join('<br>');
                                console.log(debugMessage.replace(/<br>/g, '\n'));
                                
                                // Update debug panel if available
                                if (typeof updateDebugInfo === 'function') {
                                    updateDebugInfo('Debug scan completed: ' + images.length + ' images found');
                                    setTimeout(function() {
                                        updateDebugInfo(debugMessage);
                                    }, 100);
                                }
                            };
                            
                            console.log('Image modal functions initialized');
                        })();
                        </script>
                        <input type="hidden" id="selected-match-id" value="">
                        
                        <!-- Removed debug panel and buttons for production -->
                        """

                        # Add the table with proper responsive container
                        matches_html += """
                        <div class="table-container">
                        <table class="match-table">
                            <thead>
                                <tr>
                                    <th>Select</th>
                                    <th>Image</th>
                                    <th>Tag Code</th>
                                    <th>Name</th>
                                    <th>Brand</th>
                                    <th>Size</th>
                                    <th>Quantity</th>
                                    <th>Confidence</th>
                                    <th>Status</th>
                                    <th>Source</th>
                                </tr>
                            </thead>
                            <tbody>
                        """

                        for i, match in enumerate(
                            rec_data["inventory_matches"][:10]
                        ):  # Show up to 10 matches
                            confidence = match.get("confidence", 0)
                            conf_class = (
                                "high"
                                if confidence > 0.8
                                else "medium" if confidence > 0.6 else "low"
                            )
                            match_id = match.get("id", f"match_{i}")

                            # Get image - prioritize actual image data from ChromaDB
                            image_url = match.get("image_path", "")
                            tag_code = match.get("tag_code", "")
                            size = match.get("size", "")

                            # First, try to get the actual image from ChromaDB if we have an image_id
                            if "metadata" in match and "image_id" in match["metadata"]:
                                image_id = match["metadata"]["image_id"]
                                try:
                                    # Get image from tag_images_full collection which stores base64 images
                                    collection = (
                                        self.chromadb_client.client.get_collection(
                                            "tag_images_full"
                                        )
                                    )
                                    results = collection.get(
                                        ids=[image_id], include=["metadatas"]
                                    )

                                    if results["metadatas"] and results["metadatas"][0]:
                                        metadata = results["metadatas"][0]
                                        # Use the actual base64 image from ChromaDB
                                        if (
                                            "image_base64" in metadata
                                            and metadata["image_base64"]
                                        ):
                                            image_url = f"data:image/png;base64,{metadata['image_base64']}"
                                            logger.debug(
                                                f"Retrieved actual image for {tag_code} from ChromaDB"
                                            )
                                except Exception as e:
                                    logger.debug(
                                        f"Could not retrieve image {image_id}: {e}"
                                    )

                            # If we still don't have an image, check for embedded base64 in the match
                            if not image_url and "image_base64" in match:
                                image_url = (
                                    f"data:image/png;base64,{match['image_base64']}"
                                )

                            # Clear virtual paths - we'll handle them differently
                            if image_url and image_url.startswith("inventory/"):
                                image_url = ""  # Clear virtual path

                            # Construct actual file path
                            if not image_url and tag_code:
                                import base64
                                import os

                                # Try with size suffix first (for size-specific images)
                                actual_path = None
                                if size:
                                    size_specific_path = f"/Users/samarsingh/Factory_flow_Automation/sample_images/{tag_code}_{size}.png"
                                    if os.path.exists(size_specific_path):
                                        actual_path = size_specific_path

                                # Try base tag code without size
                                if not actual_path:
                                    base_path = f"/Users/samarsingh/Factory_flow_Automation/sample_images/{tag_code}.png"
                                    if os.path.exists(base_path):
                                        actual_path = base_path

                                # Try fallback patterns for common tag codes in sample_images
                                if not actual_path:
                                    sample_dir = "/Users/samarsingh/Factory_flow_Automation/sample_images"
                                    if os.path.exists(sample_dir):
                                        sample_files = os.listdir(sample_dir)
                                        # Look for partial matches
                                        for file in sample_files:
                                            if file.endswith(".png"):
                                                file_base = file.replace(".png", "")
                                                if (
                                                    tag_code.lower()
                                                    in file_base.lower()
                                                    or file_base.lower()
                                                    in tag_code.lower()
                                                ):
                                                    actual_path = os.path.join(
                                                        sample_dir, file
                                                    )
                                                    break

                                # Convert to base64 data URI for Gradio compatibility
                                if actual_path and os.path.exists(actual_path):
                                    try:
                                        with open(actual_path, "rb") as img_file:
                                            img_data = base64.b64encode(
                                                img_file.read()
                                            ).decode()
                                            image_url = (
                                                f"data:image/png;base64,{img_data}"
                                            )
                                    except Exception as e:
                                        logger.warning(
                                            f"Failed to encode image {actual_path}: {e}"
                                        )
                                        image_url = ""

                            # If still no image, use a placeholder with tag info
                            if not image_url:
                                tag_text = tag_code[:10] if tag_code else "No Image"
                                image_url = f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Crect width='80' height='80' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%239ca3af' font-size='10'%3E{tag_text}%3C/text%3E%3C/svg%3E"

                            # Get source document information from metadata
                            source_doc = ""
                            if "metadata" in match:
                                metadata = match["metadata"]
                                source_doc = metadata.get(
                                    "source_file", metadata.get("source_document", "")
                                )
                                if not source_doc:
                                    source_doc = metadata.get(
                                        "excel_file", metadata.get("file_name", "")
                                    )

                            # Clean up the source document name - extract just the filename
                            if source_doc and "/" in source_doc:
                                source_doc = source_doc.split("/")[-1]
                            elif not source_doc:
                                source_doc = "Direct Search"

                            # Keep full name for display (no truncation)

                            # Set first match as selected by default
                            selected_class = "selected-match" if i == 0 else ""
                            checked = "checked" if i == 0 else ""

                            # Simplify table row for better responsiveness
                            matches_html += f"""
                            <tr id="match-row-{match_id}" class="{selected_class}">
                                <td style="text-align: center;">
                                    <input type="radio" name="match-selection" class="match-radio" 
                                           value="{match_id}" onclick="selectMatch('{match_id}')" {checked}>
                                </td>
                                <td style="text-align: center;">
                                    <img src="{image_url}" 
                                         class="match-image clickable-image" 
                                         alt="{tag_code}" 
                                         id="img-{match_id}"
                                         data-tag-code="{tag_code}"
                                         title="Click to enlarge" 
                                         style="width: 60px; height: 60px; object-fit: cover; cursor: pointer; border-radius: 4px;" 
                                         onclick="(function(e) {{ 
                                             e.stopPropagation(); 
                                             e.preventDefault(); 
                                             var imgSrc = this.src; 
                                             var tagCode = '{tag_code}'; 
                                             if (typeof window.showImageModal === 'function') {{ 
                                                 window.showImageModal(imgSrc, tagCode); 
                                             }} 
                                             return false; 
                                         }})(event)" />
                                </td>
                                <td><strong style="font-family: monospace; font-size: 0.9em;">{tag_code or "N/A"}</strong></td>
                                <td style="word-wrap: break-word; max-width: 200px;">{match.get("name", "N/A")}</td>
                                <td>{match.get("brand", match.get('metadata', {}).get('brand', "N/A"))}</td>
                                <td>{match.get("size", match.get('metadata', {}).get('size', "N/A"))}</td>
                                <td>{match.get("quantity", match.get('metadata', {}).get('quantity', match.get('metadata', {}).get('QTY', "N/A")))}</td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 4px;">
                                        <div style="width: 40px; background: #e5e7eb; border-radius: 8px; height: 16px;">
                                            <div style="width:{confidence*100}%; height: 100%; border-radius: 8px; background: {'#10b981' if confidence > 0.8 else '#f59e0b' if confidence > 0.6 else '#ef4444'};"></div>
                                        </div>
                                        <span style="font-weight: 600; color: {'#059669' if confidence > 0.8 else '#d97706' if confidence > 0.6 else '#dc2626'}; font-size: 0.85em;">
                                            {confidence:.0%}
                                        </span>
                                    </div>
                                </td>
                                <td style="font-weight: 600; color: {'#dc2626' if confidence < 0.6 else '#f59e0b' if confidence < 0.8 else '#059669'}; font-size: 0.85em;">
                                    {'Low' if confidence < 0.6 else 'Med' if confidence < 0.8 else 'Good'}
                                </td>
                                <td style="font-size: 0.85em; word-wrap: break-word; max-width: 250px;">
                                    {source_doc}
                                </td>
                            </tr>
                            """

                        matches_html += """
                            </tbody>
                        </table>
                        </div>  <!-- End table wrapper -->
                        """

                        # Add decision support information
                        matches_html += """
                        <div style="margin-top: 1rem; padding: 1rem; background: #f9fafb; border-radius: 4px;">
                            <h4 style="margin-bottom: 0.5rem;">📊 Decision Support Information</h4>
                        """

                        # Add confidence breakdown if available
                        if rec_data.get("confidence_factors"):
                            matches_html += '<div class="info-row"><span class="label">Confidence Factors:</span><ul style="margin: 0.5rem 0;">'
                            for factor in rec_data["confidence_factors"][:3]:
                                matches_html += f"<li>{factor}</li>"
                            matches_html += "</ul></div>"

                        # Add alternative suggestions
                        num_matches = len(rec_data["inventory_matches"])
                        if num_matches > 5:
                            matches_html += f"""
                            <div class="info-row">
                                <span class="label">Alternative Options:</span>
                                <span class="value">{num_matches - 5} more matches available with lower confidence</span>
                            </div>
                            """

                        # Add risk indicators
                        risk_factors = []
                        if rec_data.get("is_first_time_customer"):
                            risk_factors.append("First-time customer")
                        if rec_data.get("high_value_order"):
                            risk_factors.append("High-value order")
                        if rec_data.get("unusual_quantity"):
                            risk_factors.append("Unusual quantity requested")

                        if risk_factors:
                            matches_html += f"""
                            <div class="info-row">
                                <span class="label">⚠️ Risk Indicators:</span>
                                <span class="value" style="color: #dc2626;">{", ".join(risk_factors)}</span>
                            </div>
                            """

                        matches_html += "</div>"  # Close decision support div
                    else:
                        matches_html += (
                            '<p style="color:#9ca3af;">No inventory matches found</p>'
                        )

                    matches_html += "</div>"
                    
                    # Phase 5: Extract and format two-tier actions
                    executed_actions = rec_data.get("auto_executed_actions", [])
                    pending_actions = rec_data.get("pending_approval_actions", [])
                    executed_html, pending_html = self.format_two_tier_actions(executed_actions, pending_actions)
                    
                    # Extract email response if available
                    email_response = ""
                    show_email_fields = False
                    if rec["recommendation_type"] == "email_response":
                        # Try to get existing email draft, otherwise generate contextual response
                        email_response = rec_data.get("email_draft", {}).get("body", "")
                        if not email_response or "placeholder" in email_response.lower():
                            # Generate contextual email response based on confidence and matches
                            confidence = rec.get("confidence_score", 0.5)
                            email_response = self.generate_contextual_email_response(rec_data, confidence)
                        show_email_fields = True

                    return (
                        customer_html,
                        recommendation_html,
                        executed_html,  # executed_actions_card
                        pending_html,   # pending_actions_card  
                        matches_html,
                        gr.update(interactive=True),  # approve_btn
                        gr.update(interactive=True),  # defer_btn
                        gr.update(interactive=True),  # reject_btn
                        gr.update(interactive=True),  # delete_btn
                        gr.update(interactive=True),  # decision_notes
                        gr.update(value=email_response, interactive=show_email_fields, visible=show_email_fields),  # email_response_text
                        gr.update(interactive=show_email_fields, visible=show_email_fields),  # email_attachments
                        gr.update(interactive=show_email_fields, visible=show_email_fields),  # send_email_btn
                        "",  # Clear result message
                        rec["queue_id"],  # current_queue_id state
                    )

                except Exception as e:
                    logger.error(f"Error displaying details: {e}")
                    return [gr.update()] * 15  # Updated count for new fields including two-tier actions

            def process_decision(queue_id, decision_type, notes):
                """Process the review decision"""
                if not queue_id:
                    return "⚠️ No item selected"

                try:
                    # Check if we're in approval mode and need to process pending actions
                    import yaml
                    try:
                        with open('config.yaml', 'r') as f:
                            config = yaml.safe_load(f)
                            approval_mode = config.get('orchestrator', {}).get('approval_mode', False)
                    except:
                        approval_mode = False
                    
                    if approval_mode and decision_type == "approve":
                        # In approval mode, we need to execute pending actions
                        # Get the workflow_id associated with this queue item
                        with engine.connect() as conn:
                            # Get workflow_id from recommendation_data
                            query = text(
                                """SELECT recommendation_data 
                                FROM recommendation_queue 
                                WHERE queue_id = :queue_id"""
                            )
                            result = conn.execute(query, {"queue_id": queue_id})
                            row = result.fetchone()
                            
                            if row and row[0]:
                                rec_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                                workflow_id = rec_data.get('workflow_id')
                                
                                if workflow_id:
                                    # Get pending actions from ActionAudit table
                                    action_query = text(
                                        """SELECT action_id, action_name, parameters
                                        FROM action_audit
                                        WHERE workflow_id = :workflow_id
                                        AND executed = false
                                        AND action_type = 'irreversible'"""
                                    )
                                    actions = conn.execute(action_query, {"workflow_id": workflow_id})
                                    
                                    approved_count = 0
                                    errors = []
                                    
                                    # Process each pending action
                                    for action in actions:
                                        action_id = action[0]
                                        action_name = action[1]
                                        
                                        # Call the orchestrator's approve_action method to actually execute the action
                                        try:
                                            # Import here to avoid circular dependency
                                            from run_factory_automation import SHARED_ORCHESTRATOR
                                            
                                            if SHARED_ORCHESTRATOR and hasattr(SHARED_ORCHESTRATOR, 'approve_action'):
                                                # Call the orchestrator's approve method (async)
                                                import asyncio
                                                loop = asyncio.new_event_loop()
                                                asyncio.set_event_loop(loop)
                                                result = loop.run_until_complete(
                                                    SHARED_ORCHESTRATOR.approve_action(action_id)
                                                )
                                                loop.close()
                                                
                                                if result and result.get('success'):
                                                    approved_count += 1
                                                    logger.info(f"✅ Successfully executed approved action {action_id}: {action_name}")
                                                else:
                                                    errors.append(f"Failed to execute {action_name}: {result.get('error', 'Unknown error')}")
                                                    logger.error(f"Failed to execute action {action_id}: {result}")
                                            else:
                                                # Fallback: just mark as executed in database
                                                update_query = text(
                                                    """UPDATE action_audit
                                                    SET executed = true,
                                                        result = :result
                                                    WHERE action_id = :action_id"""
                                                )
                                                conn.execute(
                                                    update_query,
                                                    {
                                                        "action_id": action_id,
                                                        "result": json.dumps({"status": "approved_by_human"})
                                                    }
                                                )
                                                approved_count += 1
                                                logger.info(f"Approved action {action_id}: {action_name} (database only)")
                                                
                                        except Exception as e:
                                            errors.append(f"Error executing {action_name}: {str(e)}")
                                            logger.error(f"Error executing action {action_id}: {e}")
                                    
                                    conn.commit()
                                    
                                    if approved_count > 0:
                                        # Also update the queue status
                                        update_queue = text(
                                            """UPDATE recommendation_queue
                                            SET status = 'approved',
                                                reviewed_at = NOW(),
                                                reviewed_by = 'human_reviewer'
                                            WHERE queue_id = :queue_id"""
                                        )
                                        conn.execute(update_queue, {"queue_id": queue_id})
                                        conn.commit()
                                        
                                        if errors:
                                            return f"✅ Approved {approved_count} actions. ⚠️ Errors: {'; '.join(errors)}"
                                        else:
                                            return f"✅ Approved {approved_count} pending actions! Workflow {workflow_id} approved."
                                    elif errors:
                                        return f"❌ Failed to approve actions: {'; '.join(errors)}"
                    
                    elif approval_mode and decision_type == "reject":
                        # In approval mode, mark actions as rejected
                        with engine.connect() as conn:
                            # Get workflow_id from recommendation_data
                            query = text(
                                """SELECT recommendation_data 
                                FROM recommendation_queue 
                                WHERE queue_id = :queue_id"""
                            )
                            result = conn.execute(query, {"queue_id": queue_id})
                            row = result.fetchone()
                            
                            if row and row[0]:
                                rec_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                                workflow_id = rec_data.get('workflow_id')
                                
                                if workflow_id:
                                    # Mark pending actions as rejected
                                    update_query = text(
                                        """UPDATE action_audit
                                        SET result = :result
                                        WHERE workflow_id = :workflow_id
                                        AND executed = false
                                        AND action_type = 'irreversible'"""
                                    )
                                    conn.execute(
                                        update_query,
                                        {
                                            "workflow_id": workflow_id,
                                            "result": json.dumps({"status": "rejected_by_human", "notes": notes})
                                        }
                                    )
                                    conn.commit()
                                    
                                    # Update queue status
                                    update_queue = text(
                                        """UPDATE recommendation_queue
                                        SET status = 'rejected',
                                            reviewed_at = NOW(),
                                            reviewed_by = 'human_reviewer'
                                        WHERE queue_id = :queue_id"""
                                    )
                                    conn.execute(update_queue, {"queue_id": queue_id})
                                    conn.commit()
                                    
                                    return f"❌ Rejected pending actions for workflow {workflow_id}. Notes: {notes if notes else 'None'}"
                    
                    # Map decision to status for normal flow
                    status_map = {
                        "approve": "approved",
                        "defer": "deferred",
                        "reject": "rejected",
                        "delete": "deleted",
                    }

                    if decision_type == "delete":
                        # Delete from database
                        with engine.connect() as conn:
                            # First get the order_id
                            get_order = text(
                                "SELECT order_id FROM recommendation_queue WHERE queue_id = :queue_id"
                            )
                            result = conn.execute(get_order, {"queue_id": queue_id})
                            order_id = result.scalar()
                            
                            # Delete from recommendation_queue
                            delete_queue = text(
                                "DELETE FROM recommendation_queue WHERE queue_id = :queue_id"
                            )
                            conn.execute(delete_queue, {"queue_id": queue_id})
                            
                            # Delete associated order if exists
                            if order_id:
                                delete_order = text(
                                    "DELETE FROM orders WHERE order_id = :order_id"
                                )
                                conn.execute(delete_order, {"order_id": order_id})
                            
                            conn.commit()
                        
                        return "🗑️ Item and associated order deleted from database!"
                    else:
                        # Update database with status
                        with engine.connect() as conn:
                            query = text(
                                """
                                UPDATE recommendation_queue
                                SET status = :status,
                                    reviewed_at = NOW(),
                                    reviewed_by = 'human_reviewer'
                                WHERE queue_id = :queue_id
                                """
                            )

                            conn.execute(
                                query,
                                {"status": status_map[decision_type], "queue_id": queue_id},
                            )
                            conn.commit()
                            
                            # TODO: Update inventory_change_log table when inventory is affected
                            # Note: inventory_change_log table exists in DB but update logic not yet implemented

                        return f"✅ Item {status_map[decision_type]}! Notes: {notes if notes else 'None'}"

                except Exception as e:
                    logger.error(f"Error processing decision: {e}")
                    return f"❌ Error: {str(e)}"


            def send_email_response(queue_id, email_body, attachments):
                """Send the email response"""
                if not queue_id:
                    return "⚠️ No order selected"
                
                if not email_body or not email_body.strip():
                    return "⚠️ Email body cannot be empty"
                
                try:
                    # Get the recommendation details
                    with engine.connect() as conn:
                        query = text(
                            """
                            SELECT customer_email, recommendation_data
                            FROM recommendation_queue
                            WHERE queue_id = :queue_id
                            """
                        )
                        result = conn.execute(query, {"queue_id": queue_id})
                        row = result.fetchone()
                        
                        if not row:
                            return "❌ Order not found"
                        
                        customer_email = row[0]
                        
                        # TODO: Integrate with actual email sending service
                        # For now, just save the email and mark as sent
                        update_query = text(
                            """
                            UPDATE recommendation_queue
                            SET status = 'email_sent',
                                reviewed_at = NOW(),
                                reviewed_by = 'human_reviewer',
                                recommendation_data = jsonb_set(
                                    COALESCE(recommendation_data, '{}'::jsonb),
                                    '{email_sent}',
                                    :email_data::jsonb
                                )
                            WHERE queue_id = :queue_id
                            """
                        )
                        
                        email_data = {
                            "body": email_body,
                            "attachments": len(attachments) if attachments else 0,
                            "sent_at": datetime.now().isoformat(),
                            "to": customer_email
                        }
                        
                        conn.execute(
                            update_query,
                            {
                                "queue_id": queue_id,
                                "email_data": json.dumps(email_data)
                            }
                        )
                        conn.commit()
                    
                    # Check if we're in approval mode and should execute the email action
                    import yaml
                    try:
                        with open('config.yaml', 'r') as f:
                            config = yaml.safe_load(f)
                            approval_mode = config.get('orchestrator', {}).get('approval_mode', False)
                    except:
                        approval_mode = False
                    
                    if approval_mode:
                        # In approval mode, look for pending send_email action and execute it
                        rec_data = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        workflow_id = rec_data.get('workflow_id')
                        
                        if workflow_id:
                            # Find and execute the send_email action with the modified body
                            with engine.connect() as conn:
                                # Get the send_email action
                                action_query = text(
                                    """SELECT action_id, parameters
                                    FROM action_audit
                                    WHERE workflow_id = :workflow_id
                                    AND action_name = 'send_email_response'
                                    AND executed = false"""
                                )
                                action_result = conn.execute(action_query, {"workflow_id": workflow_id})
                                action = action_result.fetchone()
                                
                                if action:
                                    action_id = action[0]
                                    # Update the action with the modified email body
                                    updated_params = json.loads(action[1]) if isinstance(action[1], str) else action[1]
                                    updated_params['body'] = email_body
                                    
                                    # Mark as executed with modified params
                                    update_action = text(
                                        """UPDATE action_audit
                                        SET executed = true,
                                            parameters = :params,
                                            result = :result
                                        WHERE action_id = :action_id"""
                                    )
                                    conn.execute(
                                        update_action,
                                        {
                                            "action_id": action_id,
                                            "params": json.dumps(updated_params),
                                            "result": json.dumps({"status": "executed_with_modifications", "modified_by": "human"})
                                        }
                                    )
                                    conn.commit()
                                    
                                    # TODO: Actually send the email using the tool
                                    # This would require calling the actual email tool with the modified params
                    
                    # In production, integrate with Gmail API here
                    # gmail_service.send_email(to=customer_email, body=email_body, attachments=attachments)
                    
                    return f"✅ Email sent to {customer_email}! (Note: Email integration pending - saved to database)"
                    
                except Exception as e:
                    logger.error(f"Error sending email: {e}")
                    return f"❌ Error: {str(e)}"


            # Wire up event handlers
            refresh_btn.click(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                ],
            )

            queue_table.select(
                fn=on_row_select,
                inputs=[queue_table],
                outputs=[
                    customer_card,
                    recommendation_card,
                    executed_actions_card,  # Phase 5: Added
                    pending_actions_card,   # Phase 5: Added
                    matches_html,
                    approve_btn,
                    defer_btn,
                    reject_btn,
                    delete_btn,
                    decision_notes,
                    email_response_text,
                    email_attachments,
                    send_email_btn,
                    result_message,
                    current_queue_id,
                ],
            )

            approve_btn.click(
                fn=lambda: gr.update(value="⏳ Processing approval...", visible=True),
                outputs=[loading_status],
            ).then(
                fn=lambda qid, notes: process_decision(qid, "approve", notes),
                inputs=[current_queue_id, decision_notes],
                outputs=[result_message],
            ).then(
                fn=lambda: gr.update(visible=False),
                outputs=[loading_status],
            ).then(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                ],
            )

            defer_btn.click(
                fn=lambda qid, notes: process_decision(qid, "defer", notes),
                inputs=[current_queue_id, decision_notes],
                outputs=[result_message],
            ).then(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                ],
            )

            reject_btn.click(
                fn=lambda: gr.update(value="⏳ Processing rejection...", visible=True),
                outputs=[loading_status],
            ).then(
                fn=lambda qid, notes: process_decision(qid, "reject", notes),
                inputs=[current_queue_id, decision_notes],
                outputs=[result_message],
            ).then(
                fn=lambda: gr.update(visible=False),
                outputs=[loading_status],
            ).then(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                ],
            )
            
            delete_btn.click(
                fn=lambda qid, notes: process_decision(qid, "delete", notes),
                inputs=[current_queue_id, decision_notes],
                outputs=[result_message],
            ).then(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                ],
            )
            
            send_email_btn.click(
                fn=lambda: gr.update(value="⏳ Sending email...", visible=True),
                outputs=[loading_status],
            ).then(
                fn=send_email_response,
                inputs=[current_queue_id, email_response_text, email_attachments],
                outputs=[result_message],
            ).then(
                fn=lambda: gr.update(visible=False),
                outputs=[loading_status],
            ).then(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                ],
            )

            # Load initial data
            interface.load(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                ],
            )

        return interface


def launch_human_review_dashboard(port: int = 7862):
    """Launch the human review dashboard"""

    # Initialize components
    interaction_manager = HumanInteractionManager()
    chromadb_client = ChromaDBClient()

    # Create dashboard
    dashboard = HumanReviewDashboard(interaction_manager, chromadb_client)

    # Create and launch interface
    app = dashboard.create_interface()
    app.launch(server_name="0.0.0.0", server_port=port, share=False, show_error=True)

    return app


if __name__ == "__main__":
    launch_human_review_dashboard()
