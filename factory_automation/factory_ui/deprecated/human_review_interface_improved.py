"""Improved Human Review Interface with simplified interaction flow"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import gradio as gr

from ..factory_agents.human_interaction_manager import (
    HumanInteractionManager,
    Priority,
    ReviewRequest,
)
from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class HumanReviewInterface:
    """Gradio-based interface for human reviewers with improved UX"""

    def __init__(
        self,
        interaction_manager: HumanInteractionManager,
        chromadb_client: ChromaDBClient,
    ):
        """Initialize the review interface"""
        self.interaction_manager = interaction_manager
        self.chromadb_client = chromadb_client
        self.current_review: Optional[ReviewRequest] = None
        self.selected_review_id: Optional[str] = None
        self.recommendation_cache = {}  # Cache for details viewer

    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface for human review"""

        with gr.Blocks(
            title="Human Review Dashboard", theme=gr.themes.Soft()
        ) as interface:
            gr.Markdown("# 🔍 Human Review Dashboard")
            gr.Markdown(
                "Review and approve orders that need manual intervention. Process items individually or in batches."
            )

            # State variables
            selected_review_state = gr.State(value=None)
            selected_batch_items = gr.State(value=[])  # For batch processing
            current_batch_id = gr.State(value=None)

            with gr.Tabs() as tabs:
                # Tab 1: Database Queue (NEW)
                with gr.TabItem("🗄️ Database Queue", id=0):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Queue Controls")
                            db_priority_filter = gr.Dropdown(
                                choices=["All", "urgent", "high", "medium", "low"],
                                value="All",
                                label="Filter by Priority",
                            )
                            db_refresh_btn = gr.Button(
                                "🔄 Refresh Queue", variant="secondary"
                            )

                            # Queue metrics
                            queue_metrics = gr.JSON(label="Queue Metrics", open=True)

                            # Batch controls
                            gr.Markdown("### Batch Processing")
                            create_batch_btn = gr.Button(
                                "📦 Create Batch from Selected", variant="primary"
                            )
                            batch_name_input = gr.Textbox(
                                label="Batch Name (optional)",
                                placeholder="Enter batch name...",
                            )

                        with gr.Column(scale=3):
                            gr.Markdown("### Pending Recommendations from Database")
                            gr.Markdown(
                                "Check the boxes in the last column to select items for batch processing"
                            )

                            # Add view details section
                            with gr.Row():
                                with gr.Column(scale=2):
                                    detail_selector = gr.Dropdown(
                                        label="View Details for:",
                                        choices=[],
                                        value=None,
                                        interactive=True,
                                    )
                                with gr.Column(scale=1):
                                    view_details_btn = gr.Button(
                                        "📋 View Full Details", variant="secondary"
                                    )

                            # Single table with checkboxes as last column
                            db_queue_display = gr.Dataframe(
                                headers=[
                                    "Queue ID",
                                    "Type",
                                    "Customer",
                                    "Confidence",
                                    "Priority",
                                    "Recommendation",
                                    "Created",
                                    "Select",
                                ],
                                label="",
                                interactive=True,  # Allow checkbox interaction
                                wrap=True,
                                datatype=[
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                    "bool",
                                ],  # Last column is boolean
                            )

                            # Details display area (initially hidden)
                            with gr.Row(visible=False) as details_row:
                                with gr.Column():
                                    gr.Markdown("### 📋 Full Recommendation Details")
                                    with gr.Row():
                                        with gr.Column():
                                            gr.Markdown("#### 📧 Email & Customer Info")
                                            detail_customer = gr.JSON(
                                                label="Customer Details", open=True
                                            )
                                        with gr.Column():
                                            gr.Markdown("#### 🎯 AI Recommendation")
                                            detail_recommendation = gr.JSON(
                                                label="Recommendation Data", open=True
                                            )

                                    with gr.Row():
                                        with gr.Column():
                                            gr.Markdown("#### 📦 Inventory Matches")
                                            detail_matches = gr.Dataframe(
                                                headers=[
                                                    "Tag Code",
                                                    "Name",
                                                    "Brand",
                                                    "Confidence",
                                                    "Price",
                                                    "Stock",
                                                ],
                                                label="Top Matches",
                                            )
                                        with gr.Column():
                                            gr.Markdown("#### 🖼️ Image Matches")
                                            detail_images = gr.Gallery(
                                                label="Visual Matches",
                                                columns=3,
                                                height=200,
                                            )

                                    close_details_btn = gr.Button(
                                        "❌ Close Details", variant="secondary"
                                    )

                            # Hidden state to track selected items
                            selected_queue_ids = gr.State(value=[])

                            with gr.Row():
                                selected_count = gr.Textbox(
                                    label="Selected Items",
                                    value="0 items selected",
                                    interactive=False,
                                )
                                process_batch_btn = gr.Button(
                                    "⚡ Process Selected Batch",
                                    variant="primary",
                                    visible=False,
                                )

                # Tab 2: Legacy Review Queue (keeping for backward compatibility)
                with gr.TabItem("📋 Legacy Queue", id=1):
                    with gr.Row():
                        with gr.Column(scale=1):
                            priority_filter = gr.Dropdown(
                                choices=["All", "Urgent", "High", "Medium", "Low"],
                                value="All",
                                label="Filter by Priority",
                            )
                            refresh_btn = gr.Button(
                                "🔄 Refresh Queue", variant="secondary"
                            )

                            # Queue stats
                            queue_stats = gr.JSON(label="Queue Statistics", open=False)

                        with gr.Column(scale=3):
                            gr.Markdown("### Pending Reviews")
                            gr.Markdown(
                                "Click on a row to select it, then click 'Open Review'"
                            )

                            queue_display = gr.Dataframe(
                                headers=[
                                    "ID",
                                    "Customer",
                                    "Subject",
                                    "Confidence",
                                    "Priority",
                                    "Status",
                                    "Created",
                                ],
                                label="",
                                interactive=True,  # Make it interactive for selection
                                wrap=True,
                            )

                            with gr.Row():
                                selected_review_text = gr.Textbox(
                                    label="Selected Review",
                                    value="No review selected",
                                    interactive=False,
                                )
                                open_review_btn = gr.Button(
                                    "📂 Open Selected Review",
                                    variant="primary",
                                    size="lg",
                                )

                # Tab 2: Current Review
                with gr.TabItem("✏️ Current Review", id=1):
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("### 📧 Order Details")
                            review_id_display = gr.Textbox(
                                label="Review ID", interactive=False
                            )
                            customer_email = gr.Textbox(
                                label="Customer Email", interactive=False
                            )
                            email_subject = gr.Textbox(
                                label="Email Subject", interactive=False
                            )
                            confidence_score = gr.Number(
                                label="Confidence Score (%)", interactive=False
                            )

                            gr.Markdown("### 🤖 AI Orchestrator Recommendation")
                            orchestrator_recommendation = gr.Textbox(
                                label="Orchestrator's Analysis",
                                interactive=False,
                                lines=2,
                            )
                            recommended_action = gr.Textbox(
                                label="Recommended Action", interactive=False
                            )

                            gr.Markdown("### 📦 Requested Items")
                            requested_items = gr.JSON(
                                label="Items from Email", open=True
                            )

                        with gr.Column(scale=2):
                            gr.Markdown("### 🔎 Search Results")
                            search_results = gr.JSON(
                                label="Matched Items from Inventory", open=True
                            )

                            gr.Markdown("### 🎯 Suggested Alternatives")
                            with gr.Row():
                                alternative_search = gr.Textbox(
                                    label="Search for Alternatives",
                                    placeholder="Enter search query for alternative items",
                                    scale=3,
                                )
                                search_alternatives_btn = gr.Button(
                                    "🔍 Search", variant="secondary", scale=1
                                )

                            alternative_results = gr.JSON(
                                label="Alternative Items", open=False
                            )

                    gr.Markdown("### 📝 Review Decision")
                    with gr.Row():
                        with gr.Column():
                            decision_dropdown = gr.Dropdown(
                                choices=[
                                    "Approve",
                                    "Reject",
                                    "Clarify",
                                    "Alternative",
                                    "Defer",
                                ],
                                label="Decision",
                                value="Approve",
                            )
                            review_notes = gr.Textbox(
                                label="Review Notes",
                                placeholder="Add any notes about your decision...",
                                lines=3,
                            )

                        with gr.Column():
                            selected_alternatives = gr.CheckboxGroup(
                                label="Select Alternative Items (if choosing 'Alternative')",
                                choices=[],
                                value=[],
                            )

                    with gr.Row():
                        submit_decision_btn = gr.Button(
                            "✅ Submit Decision", variant="primary", size="lg"
                        )
                        back_to_queue_btn = gr.Button(
                            "⬅️ Back to Queue", variant="secondary"
                        )

                    decision_result = gr.Textbox(
                        label="Decision Result", interactive=False
                    )

                # Tab 3: Batch Review (NEW)
                with gr.TabItem("📦 Batch Review", id=2):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Current Batch")
                            batch_info = gr.JSON(label="Batch Information", open=True)

                            gr.Markdown("### Batch Items")
                            batch_items_display = gr.Dataframe(
                                headers=[
                                    "Queue ID",
                                    "Type",
                                    "Customer",
                                    "Confidence",
                                    "Priority",
                                    "Action",
                                ],
                                label="",
                                interactive=False,
                                wrap=True,
                            )

                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Batch Actions")

                            # Email template for batch
                            batch_email_template = gr.Textbox(
                                label="Email Template for Batch",
                                lines=5,
                                placeholder="Enter email template with variables like {{customer_name}}, {{order_id}}...",
                            )

                            # Document generation options
                            gr.Markdown("### Document Generation")
                            generate_docs_checkbox = gr.CheckboxGroup(
                                choices=[
                                    "Proforma Invoice",
                                    "Quotation",
                                    "Order Confirmation",
                                    "Delivery Note",
                                ],
                                label="Generate Documents",
                                value=["Proforma Invoice"],
                            )

                            # Database update options
                            gr.Markdown("### Database Updates")
                            db_update_checkbox = gr.CheckboxGroup(
                                choices=[
                                    "PostgreSQL (Order History)",
                                    "ChromaDB (Search Index)",
                                    "Excel Change Log",
                                ],
                                label="Update Databases",
                                value=[
                                    "PostgreSQL (Order History)",
                                    "Excel Change Log",
                                ],
                            )

                    with gr.Row():
                        approve_batch_btn = gr.Button(
                            "✅ Approve Batch", variant="primary", size="lg"
                        )
                        reject_batch_btn = gr.Button(
                            "❌ Reject Batch", variant="stop", size="lg"
                        )
                        modify_batch_btn = gr.Button(
                            "✏️ Modify Items", variant="secondary"
                        )

                    batch_result = gr.Textbox(
                        label="Batch Processing Result", interactive=False, lines=3
                    )

                # Tab 4: Document Preview (NEW)
                with gr.TabItem("📄 Document Preview", id=3):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Document Settings")
                            doc_type_select = gr.Dropdown(
                                choices=[
                                    "Proforma Invoice",
                                    "Quotation",
                                    "Order Confirmation",
                                    "Delivery Note",
                                ],
                                value="Proforma Invoice",
                                label="Document Type",
                            )

                            doc_queue_id = gr.Textbox(
                                label="Queue ID",
                                placeholder="Enter queue ID for document generation",
                            )

                            generate_preview_btn = gr.Button(
                                "👁️ Generate Preview", variant="primary"
                            )

                            download_btn = gr.Button(
                                "📥 Download PDF", variant="secondary", visible=False
                            )

                        with gr.Column(scale=2):
                            gr.Markdown("### Document Preview")
                            doc_preview = gr.HTML(
                                label="Preview",
                                value="<p>Select a document type and queue ID, then click Generate Preview</p>",
                            )

                            # Hidden file component for download
                            doc_file = gr.File(
                                label="Generated Document", visible=False
                            )

            # Event handlers

            # Handle row selection in dataframe
            def on_row_select(data, evt: gr.SelectData):
                """Handle row selection in the queue"""
                try:
                    logger.info(
                        f"Row selection event - evt.index: {evt.index}, type: {type(evt.index)}"
                    )
                    logger.info(f"Data type: {type(data)}")

                    if evt.index is not None:
                        # Handle both single index and list of indices
                        if isinstance(evt.index, list):
                            row_idx = evt.index[0] if len(evt.index) > 0 else None
                        else:
                            row_idx = evt.index

                        logger.info(f"Using row index: {row_idx}")

                        # Check if we have valid data and index
                        # For DataFrame, we need to check differently
                        if (
                            data is not None
                            and not data.empty
                            and row_idx is not None
                            and row_idx < len(data)
                        ):
                            # Access row from DataFrame
                            selected_row = data.iloc[row_idx]
                            review_id = selected_row.iloc[
                                0
                            ]  # ID is first column using iloc for position
                            logger.info(
                                f"Selected review: {review_id} at index {row_idx}"
                            )
                            return f"Selected: {review_id}", review_id
                        else:
                            logger.warning(
                                f"Invalid selection - data empty: {data.empty if hasattr(data, 'empty') else 'N/A'}, row_idx: {row_idx}"
                            )
                except Exception as e:
                    logger.error(f"Error in row selection: {e}")
                    logger.error(
                        f"evt.index type: {type(evt.index)}, value: {evt.index}"
                    )
                    logger.error(f"data type: {type(data)}")
                    if hasattr(data, "shape"):
                        logger.error(f"data shape: {data.shape}")

                return "No review selected", None

            queue_display.select(
                fn=on_row_select,
                inputs=[queue_display],
                outputs=[selected_review_text, selected_review_state],
            )

            # Refresh queue
            refresh_btn.click(
                fn=self.refresh_queue,
                inputs=[priority_filter],
                outputs=[queue_display, queue_stats],
            )

            # Open review with automatic tab switch
            def open_and_switch_tab(review_id):
                """Open review and switch to Current Review tab"""
                if not review_id:
                    # Return 11 values: tabs + 9 review fields + decision_result
                    return (
                        gr.update(),
                        *[gr.update()] * 9,
                        gr.update(value="Please select a review first"),
                    )

                # Open the review
                result = self.open_review(review_id)

                # Return updates for all components plus tab selection
                return (
                    gr.update(selected=1),  # Switch to Current Review tab (index 1)
                    *result,  # All the review data (9 values)
                    gr.update(value=""),  # Clear decision_result
                )

            open_review_btn.click(
                fn=open_and_switch_tab,
                inputs=[selected_review_state],
                outputs=[
                    tabs,  # Tab component to switch
                    review_id_display,
                    customer_email,
                    email_subject,
                    confidence_score,
                    orchestrator_recommendation,  # New field
                    recommended_action,  # New field
                    requested_items,
                    search_results,
                    selected_alternatives,
                    decision_result,  # Clear any previous result
                ],
            )

            # Search alternatives
            search_alternatives_btn.click(
                fn=self.search_alternatives,
                inputs=[alternative_search],
                outputs=[alternative_results, selected_alternatives],
            )

            # Submit decision
            submit_decision_btn.click(
                fn=self.submit_decision,
                inputs=[
                    review_id_display,
                    decision_dropdown,
                    review_notes,
                    selected_alternatives,
                ],
                outputs=[decision_result],
            )

            # Back to queue button
            def go_back_to_queue():
                """Switch back to queue tab"""
                return gr.update(selected=0)

            back_to_queue_btn.click(fn=go_back_to_queue, inputs=[], outputs=[tabs])

            # Auto-refresh queue on load
            interface.load(
                fn=self.refresh_queue,
                inputs=[priority_filter],
                outputs=[queue_display, queue_stats],
            )

            # ========== New Database Queue Event Handlers ==========

            # Refresh database queue
            db_refresh_btn.click(
                fn=self.refresh_db_queue,
                inputs=[db_priority_filter],
                outputs=[db_queue_display, queue_metrics, detail_selector],
            )

            # View details function
            def view_details(selected_item):
                """Show full details for selected recommendation"""
                if not selected_item or not hasattr(self, "recommendation_cache"):
                    return gr.update(visible=False), {}, {}, [], []

                # Extract queue_id from the label
                queue_id = selected_item.split(" - ")[0].replace("...", "")

                # Find the full queue_id
                full_queue_id = None
                for qid in self.recommendation_cache.keys():
                    if qid.startswith(queue_id):
                        full_queue_id = qid
                        break

                if not full_queue_id or full_queue_id not in self.recommendation_cache:
                    return gr.update(visible=False), {}, {}, [], []

                rec = self.recommendation_cache[full_queue_id]
                rec_data = rec.get("recommendation_data", {})

                # Prepare customer details
                customer_info = {
                    "Email": rec["customer_email"],
                    "Queue ID": rec["queue_id"],
                    "Priority": rec["priority"],
                    "Created": rec["created_at"],
                    "Confidence": f"{rec['confidence_score']:.1%}",
                }

                # Prepare matches table
                matches_data = []
                if "inventory_matches" in rec_data:
                    for match in rec_data["inventory_matches"][:5]:
                        matches_data.append(
                            [
                                match.get("tag_code", "N/A"),
                                match.get("name", "N/A"),
                                match.get("brand", "N/A"),
                                (
                                    f"{match.get('confidence', 0):.1%}"
                                    if "confidence" in match
                                    else "N/A"
                                ),
                                match.get("price", "N/A"),
                                match.get("quantity", "N/A"),
                            ]
                        )

                # Prepare images (placeholder for now)
                image_paths = []

                return (
                    gr.update(visible=True),  # Show details row
                    customer_info,
                    rec_data,
                    matches_data if matches_data else [],
                    image_paths,
                )

            view_details_btn.click(
                fn=view_details,
                inputs=[detail_selector],
                outputs=[
                    details_row,
                    detail_customer,
                    detail_recommendation,
                    detail_matches,
                    detail_images,
                ],
            )

            # Close details
            close_details_btn.click(
                fn=lambda: gr.update(visible=False), outputs=[details_row]
            )

            # Update selected count when table changes (checkboxes)
            def update_selected_count(table_data):
                import pandas as pd

                if table_data is None:
                    return "0 items selected", gr.update(visible=False)

                # Handle DataFrame properly
                if isinstance(table_data, pd.DataFrame):
                    if table_data.empty:
                        return "0 items selected", gr.update(visible=False)
                    # Convert to list for processing
                    data_list = table_data.values.tolist()
                else:
                    if not table_data:
                        return "0 items selected", gr.update(visible=False)
                    data_list = table_data

                count = sum(1 for row in data_list if row[-1])  # Count checked rows
                visibility = count > 0
                return f"{count} items selected", gr.update(visible=visibility)

            db_queue_display.change(
                fn=update_selected_count,
                inputs=[db_queue_display],
                outputs=[selected_count, process_batch_btn],
            )

            # Create batch from selected items
            create_batch_btn.click(
                fn=self.create_batch_from_selected,
                inputs=[db_queue_display, batch_name_input],
                outputs=[batch_result],
            )

            # Process selected batch - create and go to batch review
            def process_selected_batch(table_data):
                """Create a batch and switch to batch review tab"""
                from datetime import datetime

                import pandas as pd

                if table_data is None:
                    return gr.update(), gr.update(), gr.update(), "No data in queue"

                # Handle DataFrame properly
                if isinstance(table_data, pd.DataFrame):
                    if table_data.empty:
                        return gr.update(), gr.update(), gr.update(), "No data in queue"
                    data_list = table_data.values.tolist()
                else:
                    if not table_data:
                        return gr.update(), gr.update(), gr.update(), "No data in queue"
                    data_list = table_data

                # Extract selected queue IDs
                queue_ids = []
                selected_items = []
                for row in data_list:
                    if row[-1]:  # Last column is checkbox
                        queue_ids.append(row[0])
                        selected_items.append(row)

                if not queue_ids:
                    return gr.update(), gr.update(), gr.update(), "No items selected"

                # Create batch with auto-generated name
                batch_name = f"Quick Batch - {datetime.now().strftime('%H:%M:%S')}"
                batch_id = self.interaction_manager.create_batch_from_queue(
                    queue_ids=queue_ids, batch_name=batch_name, batch_type="manual"
                )

                # Format batch items for display
                items_data = []
                for item in selected_items:
                    items_data.append(
                        [
                            item[0],  # Queue ID
                            item[1],  # Type
                            item[2],  # Customer
                            item[3],  # Confidence
                            item[4],  # Priority
                            "Pending Review",
                        ]
                    )

                batch_info = {
                    "Batch ID": batch_id,
                    "Batch Name": batch_name,
                    "Total Items": len(queue_ids),
                    "Status": "pending",
                    "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                # Switch to Batch Review tab (index 2) and populate it
                return (
                    gr.update(selected=2),  # Switch to Batch Review tab
                    batch_info,  # Batch info
                    items_data,  # Batch items
                    f"✅ Created batch {batch_id} with {len(queue_ids)} items - Ready for review!",
                    batch_id,  # Store batch_id in state
                )

            process_batch_btn.click(
                fn=process_selected_batch,
                inputs=[db_queue_display],
                outputs=[
                    tabs,
                    batch_info,
                    batch_items_display,
                    batch_result,
                    current_batch_id,
                ],
            )

            # Generate document preview
            generate_preview_btn.click(
                fn=self.generate_document_preview,
                inputs=[doc_type_select, doc_queue_id],
                outputs=[doc_preview, download_btn],
            )

            # Approve batch
            approve_batch_btn.click(
                fn=self.approve_batch,
                inputs=[
                    current_batch_id,
                    batch_email_template,
                    generate_docs_checkbox,
                    db_update_checkbox,
                ],
                outputs=[batch_result],
            )

            # Auto-load database queue on startup
            interface.load(
                fn=self.refresh_db_queue,
                inputs=[db_priority_filter],
                outputs=[db_queue_display, queue_metrics, detail_selector],
            )

        return interface

    def refresh_queue(self, priority_filter: str):
        """Refresh the review queue"""
        try:
            # Convert filter to enum
            priority = None
            if priority_filter != "All":
                priority = Priority[priority_filter.upper()]

            # Get pending reviews
            reviews = asyncio.run(
                self.interaction_manager.get_pending_reviews(priority_filter=priority)
            )

            # Format for display
            queue_data = []
            for review in reviews:
                queue_data.append(
                    [
                        review.request_id,
                        review.customer_email,
                        (
                            review.subject[:50] + "..."
                            if len(review.subject) > 50
                            else review.subject
                        ),
                        f"{review.confidence_score:.1f}%",
                        review.priority.value,
                        review.status.value,
                        review.created_at.strftime("%Y-%m-%d %H:%M"),
                    ]
                )

            logger.info(f"Refreshed queue with {len(queue_data)} reviews")

            # Get statistics
            stats = self.interaction_manager.get_review_statistics()

            return queue_data, stats

        except Exception as e:
            logger.error(f"Error refreshing queue: {e}")
            return [], {"error": str(e)}

    def open_review(self, review_id: str):
        """Open a specific review for processing"""

        if not review_id:
            return [""] * 9  # Return empty values (now 9 fields)

        try:
            # Get review details
            review = asyncio.run(self.interaction_manager.get_review_details(review_id))

            if not review:
                return ["Review not found"] + [""] * 8

            # Store current review
            self.current_review = review

            # Debug logging
            logger.info(f"Opening review {review_id}")
            logger.info(
                f"Orchestrator recommendation: {review.orchestrator_recommendation}"
            )
            logger.info(f"Recommended action: {review.recommended_action}")
            logger.debug(
                f"Review items type: {type(review.items)}, content: {review.items}"
            )
            logger.debug(f"Review search_results type: {type(review.search_results)}")

        except Exception as e:
            logger.error(f"Error opening review {review_id}: {e}")
            return [f"Error: {str(e)}"] + [""] * 8

        # Format items for display
        items_formatted = []
        try:
            if review.items and isinstance(review.items, list):
                for item in review.items[:10]:  # Limit to 10 items
                    if isinstance(item, dict):
                        items_formatted.append(
                            {
                                "item_id": item.get("item_id", "N/A"),
                                "tag_code": item.get("tag_code", "N/A"),
                                "quantity": item.get("quantity", 0),
                                "tag_type": item.get("tag_type", "unknown"),
                                "specifications": item.get("specifications", {}),
                            }
                        )
        except Exception as e:
            logger.error(f"Error formatting items: {e}")

        # Format search results for display
        search_results_formatted = []
        try:
            if review.search_results and isinstance(review.search_results, list):
                for result in review.search_results[:5]:  # Top 5 results
                    if isinstance(result, dict):
                        # Check if result has image data
                        has_image = False
                        if isinstance(result.get("metadata"), dict):
                            has_image = result["metadata"].get("has_image", False)

                        search_results_formatted.append(
                            {
                                "name": result.get(
                                    "name", result.get("tag_code", "Unknown")
                                ),
                                "code": result.get(
                                    "code", result.get("tag_code", "N/A")
                                ),
                                "brand": result.get("brand", "Unknown"),
                                "similarity": f"{result.get('similarity_score', result.get('confidence', 0)) * 100:.1f}%",
                                "price": result.get("price", 0),
                                "stock": result.get("stock", 0),
                                "has_image": "✓" if has_image else "✗",
                            }
                        )
        except Exception as e:
            logger.error(f"Error formatting search results: {e}")

        # Ensure we have valid data for JSON components
        items_display = (
            items_formatted if items_formatted else [{"message": "No items to display"}]
        )
        results_display = (
            search_results_formatted
            if search_results_formatted
            else [{"message": "No search results available"}]
        )

        # Create alternative checkboxes (initially empty)
        alternatives_choices = []

        # Get orchestrator recommendation
        orchestrator_rec = (
            review.orchestrator_recommendation or "No recommendation provided"
        )
        rec_action = review.recommended_action or "human_review"

        return (
            review.request_id,
            review.customer_email,
            review.subject,
            f"{review.confidence_score:.1%}",  # Format as percentage
            orchestrator_rec,  # Orchestrator's recommendation
            rec_action,  # Recommended action
            items_display,  # Return as list/dict for gr.JSON
            results_display,  # Return as list/dict for gr.JSON
            alternatives_choices,
        )

    def search_alternatives(self, query: str):
        """Search for alternative items"""

        if not query:
            return [], []

        try:
            # Search using ChromaDB directly
            results = self.chromadb_client.collection.query(
                query_texts=[query],
                n_results=10,
                include=["metadatas", "distances", "documents"],
            )

            # Format results
            alternatives = []
            choices = []

            if results and results.get("ids") and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i]
                    similarity = (
                        1 - results["distances"][0][i]
                    )  # Convert distance to similarity

                    item_info = {
                        "id": results["ids"][0][i],
                        "name": metadata.get("trim_name", "Unknown"),
                        "code": metadata.get("trim_code", "N/A"),
                        "brand": metadata.get("brand", "Unknown"),
                        "similarity": f"{similarity * 100:.1f}%",
                        "price": metadata.get("price", 0),
                        "stock": metadata.get("stock", 0),
                    }
                    alternatives.append(item_info)

                    # Create choice label
                    choice_label = f"{item_info['name']} ({item_info['code']}) - {item_info['brand']} - {item_info['similarity']}"
                    choices.append(choice_label)

            # Create checkbox group with choices
            return alternatives, gr.CheckboxGroup(choices=choices, value=[])

        except Exception as e:
            logger.error(f"Error searching alternatives: {e}")
            return [{"error": str(e)}], []

    def submit_decision(
        self,
        review_id: str,
        decision: str,
        notes: str,
        selected_alternatives: List[str],
    ):
        """Submit the review decision"""

        if not review_id:
            return "Error: No review selected"

        try:
            # Parse selected alternatives
            alternative_items = []
            if decision == "Alternative" and selected_alternatives:
                for alt in selected_alternatives:
                    # Parse the alternative from the label
                    parts = alt.split(" - ")
                    if len(parts) >= 3:
                        name_code = parts[0]
                        brand = parts[1]
                        alternative_items.append(
                            {
                                "name": name_code.split("(")[0].strip(),
                                "code": (
                                    name_code.split("(")[1].replace(")", "").strip()
                                    if "(" in name_code
                                    else "N/A"
                                ),
                                "brand": brand,
                            }
                        )

            # Submit decision
            result = asyncio.run(
                self.interaction_manager.submit_review_decision(
                    request_id=review_id,
                    decision=decision.lower(),
                    notes=notes,
                    alternative_items=alternative_items if alternative_items else None,
                )
            )

            if result["success"]:
                return f"✅ Decision submitted successfully! Review {review_id} marked as {result['status']}. Review time: {result['review_time_seconds']:.1f} seconds"
            else:
                return f"❌ Error: {result.get('error', 'Unknown error')}"

        except Exception as e:
            logger.error(f"Error submitting decision: {e}")
            return f"❌ Error: {str(e)}"

    # ========== New Database Queue Methods ==========

    def refresh_db_queue(self, priority_filter: str):
        """Refresh the database queue"""
        try:
            # Get pending recommendations from database
            priority = None if priority_filter == "All" else priority_filter
            recommendations = self.interaction_manager.get_pending_recommendations(
                limit=100, priority_filter=priority
            )

            # Format for display with checkboxes
            queue_data = []
            for rec in recommendations:
                # Extract summary from recommendation_data
                rec_data = rec.get("recommendation_data", {})
                summary = ""

                if rec["recommendation_type"] == "email_response":
                    email_draft = rec_data.get("email_draft", {})
                    summary = email_draft.get("subject", "Send email response")[:50]
                elif rec["recommendation_type"] == "document_generation":
                    doc_type = rec_data.get("document_type", "document")
                    invoice_num = rec_data.get("invoice_number", "")
                    summary = f"Generate {doc_type} {invoice_num}"[:50]
                elif rec["recommendation_type"] == "inventory_update":
                    reason = rec_data.get("reason", "Update inventory")
                    summary = reason[:50]
                elif rec["recommendation_type"] == "customer_follow_up":
                    reason = rec_data.get("reason", "Follow up with customer")
                    summary = reason[:50]
                elif rec["recommendation_type"] == "new_item_addition":
                    item_details = rec_data.get("item_details", {})
                    desc = item_details.get("description", "Add new item")
                    summary = desc[:50]
                else:
                    summary = "Review required"

                queue_data.append(
                    [
                        rec["queue_id"],
                        rec["recommendation_type"],
                        rec["customer_email"],
                        f"{rec['confidence_score']:.1%}",
                        rec["priority"],
                        summary,  # Orchestrator recommendation summary
                        rec["created_at"][:19] if rec["created_at"] else "N/A",
                        False,  # Checkbox column - initially unchecked
                    ]
                )

            # Create dropdown choices for details viewer
            detail_choices = []
            for rec in recommendations:
                label = f"{rec['queue_id'][:20]}... - {rec['customer_email']} ({rec['recommendation_type']})"
                detail_choices.append(label)

            # Store full recommendation data for details viewer
            self.recommendation_cache = {
                rec["queue_id"]: rec for rec in recommendations
            }

            # Get queue metrics
            from sqlalchemy import text

            from ..factory_database.connection import engine

            metrics = {}
            with engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM queue_metrics")).first()
                if result:
                    metrics = {
                        "Pending": result[0],
                        "In Review": result[1],
                        "Approved": result[2],
                        "Executed": result[3],
                        "Urgent Count": result[4],
                        "Avg Confidence": f"{result[7]:.2%}" if result[7] else "N/A",
                    }

            # Return table data, metrics, and dropdown choices
            return queue_data, metrics, gr.update(choices=detail_choices, value=None)

        except Exception as e:
            logger.error(f"Error refreshing database queue: {e}")
            return [], {"error": str(e)}, gr.update(choices=[], value=None)

    def create_batch_from_selected(self, table_data, batch_name: str):
        """Create a batch from selected queue items"""
        try:
            # Handle DataFrame properly
            import pandas as pd

            if table_data is None:
                return "No data in queue"

            # Check if it's a DataFrame or list
            if isinstance(table_data, pd.DataFrame):
                if table_data.empty:
                    return "No data in queue"
                # Convert DataFrame to list of lists
                data_list = table_data.values.tolist()
            else:
                # It's already a list
                if not table_data or len(table_data) == 0:
                    return "No data in queue"
                data_list = table_data

            # Extract queue IDs where checkbox (last column) is True
            queue_ids = []
            for row in data_list:
                if row[-1]:  # Last column is the checkbox
                    queue_ids.append(row[0])  # First column is queue_id

            if not queue_ids:
                return "No items selected - please check the boxes in the last column"

            batch_id = self.interaction_manager.create_batch_from_queue(
                queue_ids=queue_ids, batch_name=batch_name or None, batch_type="manual"
            )

            return f"✅ Created batch {batch_id} with {len(queue_ids)} items"

        except Exception as e:
            logger.error(f"Error creating batch: {e}")
            return f"❌ Error: {str(e)}"

    def load_batch_for_review(self, batch_id: str):
        """Load a batch for review"""
        try:
            batch = self.interaction_manager.get_batch_for_review(batch_id)

            if not batch:
                return None, [], "Batch not found"

            # Format batch items for display
            items_data = []
            for item in batch["items"]:
                items_data.append(
                    [
                        item["queue_id"],
                        item["recommendation_type"],
                        item["customer_email"],
                        f"{item['confidence_score']:.1%}",
                        item["priority"],
                        "Pending Review",
                    ]
                )

            batch_info = {
                "Batch ID": batch["batch_id"],
                "Batch Name": batch["batch_name"] or "Unnamed",
                "Total Items": batch["total_items"],
                "Status": batch["status"],
                "Created": batch["created_at"],
            }

            return batch_info, items_data, f"Loaded batch {batch_id}"

        except Exception as e:
            logger.error(f"Error loading batch: {e}")
            return None, [], f"❌ Error: {str(e)}"

    def generate_document_preview(self, doc_type: str, queue_id: str):
        """Generate a preview of a document"""
        try:
            # This is a placeholder for document generation
            # In production, this would use ReportLab or similar

            html_preview = f"""
            <div style="border: 1px solid #ccc; padding: 20px; background: white;">
                <h2>{doc_type}</h2>
                <p><strong>Queue ID:</strong> {queue_id}</p>
                <hr>
                <p><strong>Customer:</strong> Example Customer</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
                <hr>
                <h3>Items</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #ddd;">
                        <th style="text-align: left;">Item</th>
                        <th style="text-align: right;">Quantity</th>
                        <th style="text-align: right;">Price</th>
                    </tr>
                    <tr>
                        <td>Sample Item 1</td>
                        <td style="text-align: right;">100</td>
                        <td style="text-align: right;">$25.00</td>
                    </tr>
                </table>
                <hr>
                <p><strong>Total:</strong> $2,500.00</p>
                <p style="color: #666; font-size: 0.9em;">
                    This is a preview. Click Download PDF for the actual document.
                </p>
            </div>
            """

            return html_preview, gr.update(visible=True)

        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            return f"<p>Error: {str(e)}</p>", gr.update(visible=False)

    def approve_batch(
        self, batch_id: str, email_template: str, generate_docs: list, db_updates: list
    ):
        """Approve and process a batch"""
        try:
            if not batch_id:
                return "No batch loaded"

            # Get batch details
            batch = self.interaction_manager.get_batch_for_review(batch_id)
            if not batch:
                return "Batch not found"

            # Approve all items in batch
            queue_ids = [item["queue_id"] for item in batch["items"]]

            success = self.interaction_manager.approve_batch_items(
                batch_id=batch_id,
                approved_queue_ids=queue_ids,
                rejected_queue_ids=[],
                modifications={
                    "email_template": email_template,
                    "documents": generate_docs,
                    "databases": db_updates,
                },
            )

            if success:
                result = f"✅ Batch {batch_id} approved!\n"
                result += f"- {len(queue_ids)} items approved\n"
                if generate_docs:
                    result += f"- Documents to generate: {', '.join(generate_docs)}\n"
                if db_updates:
                    result += f"- Databases to update: {', '.join(db_updates)}"
                return result
            else:
                return "❌ Failed to approve batch"

        except Exception as e:
            logger.error(f"Error approving batch: {e}")
            return f"❌ Error: {str(e)}"


def launch_human_review_interface():
    """Launch the human review interface"""

    # Initialize components
    chromadb_client = ChromaDBClient()
    interaction_manager = HumanInteractionManager()

    # Create interface
    review_interface = HumanReviewInterface(
        interaction_manager=interaction_manager, chromadb_client=chromadb_client
    )

    # Create and launch Gradio app
    app = review_interface.create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,  # Different port for testing
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    launch_human_review_interface()
