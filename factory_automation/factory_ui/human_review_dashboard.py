"""
Human Review Dashboard - Production Interface
Handles all pending order reviews with visual and text matching
Consolidated from multiple review interfaces into single clean dashboard
"""

import logging
from datetime import datetime
from typing import Optional

import gradio as gr
from sqlalchemy import text

from ..factory_agents.human_interaction_manager import HumanInteractionManager
from ..factory_database.connection import engine
from ..factory_database.vector_db import ChromaDBClient

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

        # Custom CSS for modern, clean styling
        custom_css = """
        /* Radio button styling for better visibility */
        input[type="radio"] {
            width: 18px !important;
            height: 18px !important;
            cursor: pointer !important;
            opacity: 1 !important;
            accent-color: #2563eb !important;
            -webkit-appearance: radio !important;
            appearance: radio !important;
            margin: 0 !important;
            vertical-align: middle !important;
        }
        
        input[type="radio"]:checked {
            accent-color: #2563eb !important;
        }
        
        /* Modern card-based design */
        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .label {
            color: #6b7280;
            font-weight: 500;
        }
        
        .value {
            color: #111827;
            font-weight: 600;
        }
        
        /* Priority badges */
        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 500;
            display: inline-block;
        }
        
        .priority-urgent {
            background: #fee2e2;
            color: #dc2626;
            border-left: 4px solid #dc2626;
        }
        
        .priority-high {
            background: #fed7aa;
            color: #ea580c;
            border-left: 4px solid #ea580c;
        }
        
        .priority-medium {
            background: #fef3c7;
            color: #d97706;
            border-left: 4px solid #d97706;
        }
        
        .priority-low {
            background: #e0e7ff;
            color: #4f46e5;
            border-left: 4px solid #4f46e5;
        }
        
        /* Confidence indicators */
        .confidence-bar {
            height: 8px;
            border-radius: 4px;
            margin-top: 0.5rem;
            background: #e5e7eb;
            position: relative;
            overflow: hidden;
        }
        
        .confidence-fill {
            height: 100%;
            transition: width 0.3s ease;
        }
        
        .confidence-high {
            background: linear-gradient(90deg, #10b981, #34d399);
        }
        
        .confidence-medium {
            background: linear-gradient(90deg, #f59e0b, #fbbf24);
        }
        
        .confidence-low {
            background: linear-gradient(90deg, #ef4444, #f87171);
        }
        
        /* Table styling */
        .dataframe tbody tr {
            transition: background-color 0.2s;
        }
        
        .dataframe tbody tr:hover {
            background-color: #f9fafb !important;
            cursor: pointer;
        }
        
        .dataframe tbody tr.selected {
            background-color: #eff6ff !important;
            border-left: 3px solid #3b82f6;
        }
        
        /* Match cards */
        .match-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            transition: box-shadow 0.2s;
        }
        
        .match-card:hover {
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Action buttons */
        .action-button {
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .action-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Status indicators */
        .status-pending { color: #f59e0b; }
        .status-approved { color: #10b981; }
        .status-rejected { color: #ef4444; }
        .status-in-review { color: #3b82f6; }
        
        /* Inventory match table */
        .match-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        
        .match-table th {
            background: #f3f4f6;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .match-table td {
            padding: 0.75rem;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: middle;
        }
        
        .match-table tr:hover {
            background: #f9fafb;
        }
        
        .match-table tr.selected-match {
            background: #eff6ff !important;
            border-left: 3px solid #3b82f6;
        }
        
        .match-image {
            width: 80px;
            height: 80px;
            object-fit: contain;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .match-image:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .confidence-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .confidence-high-badge {
            background: #d1fae5;
            color: #065f46;
        }
        
        .confidence-medium-badge {
            background: #fed7aa;
            color: #92400e;
        }
        
        .confidence-low-badge {
            background: #fee2e2;
            color: #991b1b;
        }
        
        /* Enhanced image modal styles */
        .image-modal-overlay {
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
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .image-modal-overlay.show {
            opacity: 1;
        }
        
        .modal-content {
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 80vh;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        
        .close-modal {
            position: absolute;
            top: 20px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
            z-index: 1000000;
            user-select: none;
            transition: color 0.3s ease;
        }
        
        .close-modal:hover {
            color: #fff;
            text-shadow: 0 0 10px rgba(255,255,255,0.5);
        }
        
        /* Enhanced clickable image styles */
        .clickable-image {
            transition: all 0.3s ease !important;
            border: 2px solid transparent !important;
        }
        
        .clickable-image:hover {
            transform: scale(1.05) !important;
            border: 2px solid #3b82f6 !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
            cursor: pointer !important;
        }
        
        .clickable-image:active {
            transform: scale(0.98) !important;
        }
        
        /* Document list styles */
        .document-list {
            max-height: 300px;
            overflow-y: auto;
            padding: 0.5rem;
            background: #f9fafb;
            border-radius: 4px;
        }
        
        .document-item {
            padding: 0.5rem;
            margin: 0.25rem 0;
            background: white;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .document-item:hover {
            background: #f3f4f6;
        }
        
        /* Radio button styling */
        .match-radio {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        .source-doc {
            font-size: 0.875rem;
            color: #6b7280;
            font-style: italic;
        }
        """

        with gr.Blocks(css=custom_css, theme=gr.themes.Base()) as interface:
            gr.Markdown("# 🎯 Human Review Dashboard")
            gr.Markdown("Review and process pending recommendations with confidence")

            # State management
            current_queue_id = gr.State(value=None)
            selected_items = gr.State(value=[])
            selected_match_id = gr.State(value=None)

            with gr.Row():
                # Left Panel: Queue List (35% width)
                with gr.Column(scale=35):
                    with gr.Row():
                        gr.Markdown("### 📋 Review Queue")
                        queue_count = gr.Markdown("0 pending items")

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

                    # Queue table
                    queue_table = gr.Dataframe(
                        headers=[
                            "Customer",
                            "Type",
                            "Priority",
                            "Confidence",
                            "Age",
                            "Select",
                        ],
                        label="Click any row to view details",
                        interactive=True,
                        wrap=True,
                        datatype=["str", "str", "str", "str", "str", "bool"],
                    )

                    # Batch controls
                    with gr.Row():
                        batch_btn = gr.Button(
                            "📦 Process (0)",
                            variant="primary",
                            interactive=False,  # Disabled until items selected
                        )
                        clear_btn = gr.Button(
                            "🗑️ Clear Selection", variant="secondary", interactive=False
                        )

                    # Batch processing result message
                    batch_result = gr.Markdown("", visible=False)

                # Right Panel: Details View (65% width)
                with gr.Column(scale=65):
                    # Details header
                    gr.Markdown("### 📄 Recommendation Details")

                    # Customer information card
                    customer_card = gr.HTML(
                        value='<div class="card"><p style="color:#9ca3af;">No item selected</p></div>'
                    )

                    # AI Recommendation card
                    recommendation_card = gr.HTML(
                        value='<div class="card"><h4>AI Recommendation</h4><p style="color:#9ca3af;">Select an item to view recommendation</p></div>'
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

                    # Decision notes
                    decision_notes = gr.Textbox(
                        label="Decision Notes (Optional)",
                        placeholder="Add any notes about your decision...",
                        lines=2,
                        interactive=False,
                    )

                    # Result message
                    result_message = gr.Markdown("")

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

                        # Format row
                        queue_data.append(
                            [
                                rec["customer_email"][:30],  # Truncate long emails
                                rec["recommendation_type"].replace("_", " ").title(),
                                rec["priority"],
                                f"{rec['confidence_score']:.0%}",
                                age_str,
                                False,  # Checkbox
                            ]
                        )

                    # Cache full data for details
                    self.recommendation_cache = {
                        rec["customer_email"][:30]: rec for rec in recommendations
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
                        f"{total} pending items",
                        total,
                        urgent,
                        avg_conf,
                        gr.update(interactive=False),  # batch_btn - disabled initially
                        gr.update(interactive=False),  # clear_btn - disabled initially
                    )

                except Exception as e:
                    logger.error(f"Error refreshing queue: {e}")
                    return [], "Error loading queue", 0, 0, 0, gr.update(), gr.update()

            def on_row_select(evt: gr.SelectData, table_data):
                """Handle row selection to show details"""
                import pandas as pd

                if evt.index is None or table_data is None:
                    return [gr.update()] * 9

                # Handle DataFrame properly
                if isinstance(table_data, pd.DataFrame):
                    if table_data.empty:
                        return [gr.update()] * 9
                    # Convert DataFrame to list
                    table_data = table_data.values.tolist()
                elif not table_data:
                    return [gr.update()] * 9

                try:
                    # Get selected row
                    row_idx = evt.index[0] if isinstance(evt.index, list) else evt.index
                    if row_idx >= len(table_data):
                        return [gr.update()] * 9

                    selected_row = table_data[row_idx]
                    customer_key = selected_row[0]  # Customer email (truncated)

                    # Find full recommendation data
                    rec = self.recommendation_cache.get(customer_key)
                    if not rec:
                        return [gr.update()] * 9

                    rec_data = rec.get("recommendation_data", {})

                    # Format customer card
                    customer_html = f"""
                    <div class="card">
                        <h4>👤 Customer Information</h4>
                        <div class="info-row">
                            <span class="label">Email:</span>
                            <span class="value">{rec["customer_email"]}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Queue ID:</span>
                            <span class="value" style="font-family:monospace;">{rec["queue_id"][:20]}...</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Priority:</span>
                            <span class="badge priority-{rec["priority"]}">{rec["priority"].upper()}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Created:</span>
                            <span class="value">{rec["created_at"][:19] if rec["created_at"] else "N/A"}</span>
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
                    <div class="card">
                        <h4>🤖 AI Recommendation</h4>
                        <div class="info-row">
                            <span class="label">Action:</span>
                            <span class="value">{action}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Confidence:</span>
                            <span class="value">{confidence:.1%}</span>
                        </div>
                        <div class="confidence-bar">
                            <div class="confidence-fill confidence-{conf_class}" style="width:{confidence*100}%"></div>
                        </div>
                        <div class="info-row" style="margin-top:1rem;">
                            <span class="label">Type:</span>
                            <span class="value">{rec["recommendation_type"]}</span>
                        </div>
                        {email_body and f'<div class="info-row"><span class="label">Email Preview:</span><span class="value" style="font-style:italic;">{email_body}...</span></div>' or ''}
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

                        # Add the table with proper styling
                        matches_html += """
                        <div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                        <table class="match-table" style="width: 100%; min-width: 700px;">
                            <thead>
                                <tr>
                                    <th style="width:60px; text-align:center;">Select</th>
                                    <th style="width:100px; text-align:center;">Image</th>
                                    <th style="min-width:120px;">Tag Code</th>
                                    <th style="min-width:150px;">Name</th>
                                    <th style="min-width:100px;">Brand</th>
                                    <th style="width:80px;">Type</th>
                                    <th style="width:120px;">Confidence</th>
                                    <th style="width:100px;">Status</th>
                                    <th style="min-width:180px;">Source Document</th>
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

                            # Escape the image URL for JavaScript by storing it in a data attribute
                            matches_html += f"""
                            <tr id="match-row-{match_id}" class="{selected_class}">
                                <td style="text-align: center;">
                                    <input type="radio" name="match-selection" class="match-radio" 
                                           value="{match_id}" onclick="selectMatch('{match_id}')" {checked}
                                           style="width: 18px; height: 18px; cursor: pointer; accent-color: #2563eb;">
                                </td>
                                <td>
                                    <img src="{image_url}" 
                                         class="match-image clickable-image" 
                                         alt="{tag_code}" 
                                         id="img-{match_id}"
                                         data-tag-code="{tag_code}"
                                         title="Click to enlarge - {tag_code}" 
                                         style="cursor: pointer; border: 2px solid transparent; transition: all 0.3s ease;" 
                                         onmouseover="this.style.border='2px solid #3b82f6'; this.style.transform='scale(1.05)';" 
                                         onmouseout="this.style.border='2px solid transparent'; this.style.transform='scale(1)';" 
                                         onclick="(function(e) {{ 
                                             e.stopPropagation(); 
                                             e.preventDefault(); 
                                             console.log('Image clicked directly: {tag_code}'); 
                                             var imgSrc = this.src; 
                                             var tagCode = this.getAttribute('data-tag-code') || '{tag_code}'; 
                                             if (typeof window.showImageModal === 'function') {{ 
                                                 console.log('Calling showImageModal with:', tagCode); 
                                                 window.showImageModal(imgSrc, tagCode); 
                                             }} else {{ 
                                                 console.error('showImageModal function not available:', typeof window.showImageModal); 
                                                 alert('Image zoom feature not available. Function type: ' + typeof window.showImageModal); 
                                             }} 
                                             return false; 
                                         }})(event)" />
                                </td>
                                <td><strong style="color: #2563eb; font-family: monospace;">{tag_code or "N/A"}</strong></td>
                                <td style="color: #000000;">{match.get("name", "N/A")[:30]}{'...' if len(match.get("name", "")) > 30 else ''}</td>
                                <td style="color: #000000;">{match.get("brand", match.get('metadata', {}).get('brand', "N/A"))}</td>
                                <td style="color: #000000;">{match.get("tag_type", match.get('metadata', {}).get('tag_type', "N/A"))}</td>
                                <td>
                                    <div class="confidence-bar" style="display: inline-block; width: 60px; background: #e5e7eb; border-radius: 10px; height: 20px; vertical-align: middle; margin-right: 8px;">
                                        <div class="confidence-fill confidence-{conf_class}" style="width:{confidence*100}%; height: 100%; border-radius: 10px; background: {'#10b981' if confidence > 0.8 else '#f59e0b' if confidence > 0.6 else '#ef4444'};"></div>
                                    </div>
                                    <span style="font-weight: 700; color: {'#059669' if confidence > 0.8 else '#d97706' if confidence > 0.6 else '#dc2626'};">
                                        {confidence:.0%}
                                    </span>
                                </td>
                                <td style="font-size: 13px; font-weight: 600; color: {'#dc2626' if confidence < 0.6 else '#f59e0b' if confidence < 0.8 else '#059669'};">
                                    {'Low Conf' if confidence < 0.6 else 'Medium' if confidence < 0.8 else 'Good'}
                                </td>
                                <td class="source-doc" style="font-size: 12px; color: #000000; max-width: 200px; word-wrap: break-word;" title="{source_doc}">
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

                    return (
                        customer_html,
                        recommendation_html,
                        matches_html,
                        gr.update(interactive=True),  # approve_btn
                        gr.update(interactive=True),  # defer_btn
                        gr.update(interactive=True),  # reject_btn
                        gr.update(interactive=True),  # decision_notes
                        "",  # Clear result message
                        rec["queue_id"],  # current_queue_id state
                    )

                except Exception as e:
                    logger.error(f"Error displaying details: {e}")
                    return [gr.update()] * 9

            def process_decision(queue_id, decision_type, notes):
                """Process the review decision"""
                if not queue_id:
                    return "⚠️ No item selected"

                try:
                    # Map decision to status
                    status_map = {
                        "approve": "approved",
                        "defer": "deferred",
                        "reject": "rejected",
                    }

                    # Update database
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

                    return f"✅ Item {status_map[decision_type]}! Notes: {notes if notes else 'None'}"

                except Exception as e:
                    logger.error(f"Error processing decision: {e}")
                    return f"❌ Error: {str(e)}"

            def clear_selection(table_data):
                """Clear all checkbox selections"""
                import pandas as pd

                if table_data is None:
                    return (
                        gr.update(),
                        gr.update(interactive=False, value="📦 Process (0)"),
                        gr.update(interactive=False),
                    )

                # Handle DataFrame properly
                if isinstance(table_data, pd.DataFrame):
                    if table_data.empty:
                        return (
                            gr.update(),
                            gr.update(interactive=False, value="📦 Process (0)"),
                            gr.update(interactive=False),
                        )
                    # Clear all checkboxes
                    table_data.iloc[:, -1] = False
                    return (
                        table_data,
                        gr.update(interactive=False, value="📦 Process (0)"),
                        gr.update(interactive=False),
                    )
                else:
                    if not table_data:
                        return (
                            gr.update(),
                            gr.update(interactive=False, value="📦 Process (0)"),
                            gr.update(interactive=False),
                        )
                    # Clear all checkboxes in list format
                    for row in table_data:
                        row[-1] = False
                    return (
                        table_data,
                        gr.update(interactive=False, value="📦 Process (0)"),
                        gr.update(interactive=False),
                    )

            def process_selected_batch(selected_items, selected_match_id):
                """Process the selected batch items"""
                if not selected_items:
                    return "⚠️ No items selected for processing"

                try:
                    processed_count = 0
                    errors = []

                    for item in selected_items:
                        try:
                            # Extract customer email from the selected item
                            customer_email = (
                                item[0]
                                if isinstance(item, list)
                                else item.get("customer_email", "")
                            )

                            # Find the corresponding recommendation in cache
                            rec = self.recommendation_cache.get(customer_email[:30])
                            if not rec:
                                errors.append(
                                    f"Could not find recommendation for {customer_email}"
                                )
                                continue

                            # Get the selected inventory match if available
                            selected_match = None
                            if selected_match_id and "inventory_matches" in rec.get(
                                "recommendation_data", {}
                            ):
                                matches = rec["recommendation_data"][
                                    "inventory_matches"
                                ]
                                for match in matches:
                                    if (
                                        match.get("id") == selected_match_id
                                        or f"match_{matches.index(match)}"
                                        == selected_match_id
                                    ):
                                        selected_match = match
                                        break

                            # Process the recommendation with the selected match
                            with engine.connect() as conn:
                                # Update recommendation queue status
                                update_query = text(
                                    """
                                    UPDATE recommendation_queue
                                    SET status = 'processing',
                                        processed_at = NOW(),
                                        reviewed_by = 'batch_processor',
                                        processing_notes = :notes
                                    WHERE queue_id = :queue_id
                                """
                                )

                                processing_notes = {
                                    "batch_processed": True,
                                    "selected_match": (
                                        selected_match.get("tag_code")
                                        if selected_match
                                        else None
                                    ),
                                    "confidence": (
                                        selected_match.get("confidence")
                                        if selected_match
                                        else None
                                    ),
                                    "processed_timestamp": datetime.now().isoformat(),
                                }

                                conn.execute(
                                    update_query,
                                    {
                                        "queue_id": rec["queue_id"],
                                        "notes": str(processing_notes),
                                    },
                                )
                                conn.commit()

                                # TODO: Here you would add:
                                # - Inventory update based on selected_match
                                # - Document generation (invoice, confirmation)
                                # - Email sending
                                # - Excel file updates

                                processed_count += 1

                        except Exception as e:
                            errors.append(
                                f"Error processing {customer_email}: {str(e)}"
                            )

                    # Prepare result message
                    result_msg = f"✅ Successfully processed {processed_count} out of {len(selected_items)} items."
                    if errors:
                        result_msg += "\n\n⚠️ Errors encountered:\n" + "\n".join(
                            errors[:3]
                        )
                        if len(errors) > 3:
                            result_msg += f"\n... and {len(errors) - 3} more errors"

                    return result_msg

                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    return f"❌ Batch processing failed: {str(e)}"

            def handle_batch_selection(table_data):
                """Handle checkbox selection for batch processing"""
                import pandas as pd

                if table_data is None:
                    return (
                        gr.update(interactive=False),
                        gr.update(interactive=False),
                        [],
                    )

                # Handle DataFrame properly
                if isinstance(table_data, pd.DataFrame):
                    if table_data.empty:
                        return (
                            gr.update(interactive=False),
                            gr.update(interactive=False),
                            [],
                        )
                    # Convert DataFrame to list
                    data_list = table_data.values.tolist()
                else:
                    if not table_data:
                        return (
                            gr.update(interactive=False),
                            gr.update(interactive=False),
                            [],
                        )
                    data_list = table_data

                # Count selected items
                selected = [
                    row for row in data_list if row[-1]
                ]  # Last column is checkbox

                if selected:
                    return (
                        gr.update(
                            interactive=True, value=f"📦 Process ({len(selected)})"
                        ),
                        gr.update(interactive=True),  # Enable clear button
                        selected,
                    )
                else:
                    return (
                        gr.update(interactive=False, value="📦 Process (0)"),
                        gr.update(interactive=False),  # Disable clear button
                        [],
                    )

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
                    batch_btn,
                    clear_btn,
                ],
            )

            queue_table.select(
                fn=on_row_select,
                inputs=[queue_table],
                outputs=[
                    customer_card,
                    recommendation_card,
                    matches_html,
                    approve_btn,
                    defer_btn,
                    reject_btn,
                    decision_notes,
                    result_message,
                    current_queue_id,
                ],
            )

            queue_table.change(
                fn=handle_batch_selection,
                inputs=[queue_table],
                outputs=[batch_btn, clear_btn, selected_items],
            )

            clear_btn.click(
                fn=clear_selection,
                inputs=[queue_table],
                outputs=[queue_table, batch_btn, clear_btn],
            )

            # Add batch processing button handler
            batch_btn.click(
                fn=process_selected_batch,
                inputs=[selected_items, selected_match_id],
                outputs=[batch_result],
            ).then(fn=lambda: gr.update(visible=True), outputs=[batch_result]).then(
                fn=refresh_queue,
                inputs=[priority_filter],
                outputs=[
                    queue_table,
                    queue_count,
                    pending_count,
                    urgent_count,
                    avg_confidence,
                    batch_btn,
                    clear_btn,
                ],
            )

            approve_btn.click(
                fn=lambda qid, notes: process_decision(qid, "approve", notes),
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
                    batch_btn,
                    clear_btn,
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
                    batch_btn,
                    clear_btn,
                ],
            )

            reject_btn.click(
                fn=lambda qid, notes: process_decision(qid, "reject", notes),
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
                    batch_btn,
                    clear_btn,
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
                    batch_btn,
                    clear_btn,
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
