"""Enhanced Human Review Interface with Image Display"""

import logging
from typing import Dict, List, Optional

import gradio as gr

from ..factory_agents.human_interaction_manager import (
    HumanInteractionManager,
    Priority,
    ReviewRequest,
)
from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class HumanReviewWithImages:
    """Gradio-based interface for human reviewers with image matching display"""

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
        self.current_image_matches: List[Dict] = []

    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface for human review with image display"""

        with gr.Blocks(
            title="Human Review Dashboard", theme=gr.themes.Soft()
        ) as interface:
            gr.Markdown("# 🔍 Human Review Dashboard with Visual Matching")
            gr.Markdown(
                "Review orders with visual comparison of customer images vs inventory"
            )

            # State variables
            selected_review_state = gr.State(value=None)
            gr.State(value=[])

            with gr.Tabs() as tabs:
                # Tab 1: Review Queue
                with gr.TabItem("📋 Review Queue", id=0):
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
                                interactive=True,
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

                # Tab 2: Current Review with Images
                with gr.TabItem("🖼️ Visual Review", id=1):
                    with gr.Row():
                        # Left column: Order details
                        with gr.Column(scale=1):
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
                                label="Overall Confidence (%)", interactive=False
                            )

                            # Confidence breakdown
                            gr.Markdown("### 📊 Confidence Breakdown")
                            text_confidence = gr.Number(
                                label="Text Match Confidence (%)", interactive=False
                            )
                            image_confidence = gr.Number(
                                label="Image Match Confidence (%)", interactive=False
                            )

                            gr.Markdown("### 📦 Requested Items")
                            requested_items = gr.JSON(
                                label="Items from Email", open=True
                            )

                        # Middle column: Customer's image
                        with gr.Column(scale=1):
                            gr.Markdown("### 📸 Customer's Tag Image")
                            customer_image = gr.Image(
                                label="Attached Image",
                                type="filepath",
                                height=400,
                            )
                            customer_image_analysis = gr.Textbox(
                                label="AI Analysis of Customer Image",
                                lines=5,
                                interactive=False,
                            )

                        # Right column: Matching inventory images
                        with gr.Column(scale=2):
                            gr.Markdown("### 🎯 Top Matching Inventory Tags")

                            # Create a row for each potential match (top 5)
                            match_displays = []
                            for i in range(5):
                                with gr.Row():
                                    with gr.Column(scale=1):
                                        match_image = gr.Image(
                                            label=f"Match {i+1}",
                                            type="filepath",
                                            height=200,
                                        )
                                        match_displays.append(
                                            {
                                                "image": match_image,
                                            }
                                        )

                                    with gr.Column(scale=2):
                                        match_details = gr.Textbox(
                                            label=f"Match {i+1} Details",
                                            lines=4,
                                            interactive=False,
                                        )
                                        match_confidence = gr.Number(
                                            label="Visual Similarity",
                                            interactive=False,
                                        )
                                        match_displays[i]["details"] = match_details
                                        match_displays[i][
                                            "confidence"
                                        ] = match_confidence

                    # Search results and alternatives
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 🔎 Text-Based Search Results")
                            search_results = gr.JSON(
                                label="Matched Items from Inventory", open=False
                            )

                        with gr.Column():
                            gr.Markdown("### 🎯 Suggested Alternatives")
                            with gr.Row():
                                alternative_search = gr.Textbox(
                                    label="Search for Alternatives",
                                    placeholder="Enter search query",
                                    scale=3,
                                )
                                search_alternatives_btn = gr.Button(
                                    "🔍 Search", variant="secondary", scale=1
                                )
                            alternative_results = gr.JSON(
                                label="Alternative Items", open=False
                            )

                    # Review decision section
                    gr.Markdown("### 📝 Review Decision")
                    with gr.Row():
                        with gr.Column():
                            decision_dropdown = gr.Dropdown(
                                choices=[
                                    "Approve with Best Image Match",
                                    "Approve with Text Match",
                                    "Request Better Image",
                                    "Suggest Alternative",
                                    "Reject",
                                    "Defer",
                                ],
                                label="Decision",
                                value="Approve with Best Image Match",
                            )

                            selected_match = gr.Dropdown(
                                label="Select Approved Item (if approving)",
                                choices=[],
                                value=None,
                            )

                            review_notes = gr.Textbox(
                                label="Review Notes",
                                placeholder="Add notes about visual match quality...",
                                lines=3,
                            )

                        with gr.Column():
                            gr.Markdown("### 📈 Recommendation")
                            ai_recommendation = gr.Textbox(
                                label="AI Recommendation",
                                lines=4,
                                interactive=False,
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

            # Event handlers

            def on_row_select(data, evt: gr.SelectData):
                """Handle row selection in the queue"""
                try:
                    if evt.index is not None:
                        row_idx = (
                            evt.index[0] if isinstance(evt.index, list) else evt.index
                        )
                        if data is not None and not data.empty and row_idx < len(data):
                            selected_row = data.iloc[row_idx]
                            review_id = selected_row.iloc[0]
                            return f"Selected: {review_id}", review_id
                except Exception as e:
                    logger.error(f"Error in row selection: {e}")
                return "No review selected", None

            queue_display.select(
                fn=on_row_select,
                inputs=[queue_display],
                outputs=[selected_review_text, selected_review_state],
            )

            # Enhanced open review function with image loading
            def open_review_with_images(review_id):
                """Open review and load matching images"""
                if not review_id:
                    return [gr.update()] * 20  # Return empty updates

                try:
                    # Get review details
                    review = self.interaction_manager.get_review(review_id)
                    if not review:
                        return [gr.update()] * 20

                    # Extract image matches from the review data
                    image_matches = review.additional_data.get("image_matches", [])

                    # Get customer's attached image if available
                    customer_img_path = None
                    if review.order and review.order.attachments:
                        for att in review.order.attachments:
                            if att.type == "image" and att.file_path:
                                customer_img_path = att.file_path
                                break

                    # Calculate confidence breakdown
                    text_conf = review.confidence_score
                    img_conf = 0.0
                    if image_matches:
                        img_conf = max(
                            m.get("confidence", 0) for m in image_matches[:3]
                        )

                    # Prepare match displays
                    match_updates = []
                    match_choices = []

                    for i in range(5):
                        if i < len(image_matches):
                            match = image_matches[i]
                            # Get image path from match
                            img_path = match.get("image_path", "")
                            if not img_path and match.get("metadata", {}).get(
                                "image_path"
                            ):
                                img_path = match["metadata"]["image_path"]

                            # Prepare details text
                            details = f"Tag Code: {match.get('tag_code', 'Unknown')}\n"
                            details += f"Brand: {match.get('brand', 'Unknown')}\n"
                            details += f"Similarity: {match.get('confidence', 0):.1%}\n"

                            match_updates.extend(
                                [
                                    gr.update(
                                        value=img_path if img_path else None
                                    ),  # image
                                    gr.update(value=details),  # details
                                    gr.update(
                                        value=match.get("confidence", 0) * 100
                                    ),  # confidence
                                ]
                            )

                            # Add to choices for selection
                            match_choices.append(
                                f"{match.get('tag_code', 'Unknown')} - {match.get('confidence', 0):.1%}"
                            )
                        else:
                            match_updates.extend(
                                [
                                    gr.update(value=None),  # empty image
                                    gr.update(value=""),  # empty details
                                    gr.update(value=0),  # zero confidence
                                ]
                            )

                    # Generate AI recommendation based on confidence
                    if img_conf > 0.85:
                        recommendation = "Strong visual match found! Recommend approval with top image match."
                    elif img_conf > 0.70:
                        recommendation = (
                            "Good visual match. Consider approval but verify details."
                        )
                    elif img_conf > 0.50:
                        recommendation = "Moderate match. Request clearer image or additional details."
                    else:
                        recommendation = "Low visual match. Rely on text description or request better image."

                    return [
                        gr.update(selected=1),  # Switch to Visual Review tab
                        review_id,  # review_id_display
                        (
                            review.order.customer.email if review.order else ""
                        ),  # customer_email
                        (
                            review.order.email_subject if review.order else ""
                        ),  # email_subject
                        review.confidence_score * 100,  # overall confidence
                        text_conf * 100,  # text confidence
                        img_conf * 100,  # image confidence
                        (
                            review.order.items[0].__dict__
                            if review.order and review.order.items
                            else {}
                        ),  # requested_items
                        customer_img_path,  # customer_image
                        "AI analysis pending...",  # customer_image_analysis
                        *match_updates,  # 15 updates for 5 matches (image, details, confidence each)
                        (
                            review.suggested_matches[:5]
                            if review.suggested_matches
                            else []
                        ),  # search_results
                        gr.update(
                            choices=match_choices,
                            value=match_choices[0] if match_choices else None,
                        ),  # selected_match
                        recommendation,  # ai_recommendation
                    ]

                except Exception as e:
                    logger.error(f"Error opening review with images: {e}")
                    return [gr.update()] * 20

            # Wire up the open review button
            all_outputs = [
                tabs,
                review_id_display,
                customer_email,
                email_subject,
                confidence_score,
                text_confidence,
                image_confidence,
                requested_items,
                customer_image,
                customer_image_analysis,
            ]

            # Add all match display components
            for match_display in match_displays:
                all_outputs.extend(
                    [
                        match_display["image"],
                        match_display["details"],
                        match_display["confidence"],
                    ]
                )

            all_outputs.extend(
                [
                    search_results,
                    selected_match,
                    ai_recommendation,
                ]
            )

            open_review_btn.click(
                fn=open_review_with_images,
                inputs=[selected_review_state],
                outputs=all_outputs,
            )

            # Refresh queue
            refresh_btn.click(
                fn=self.refresh_queue,
                inputs=[priority_filter],
                outputs=[queue_display, queue_stats],
            )

            # Submit decision
            submit_decision_btn.click(
                fn=self.submit_review_decision,
                inputs=[
                    review_id_display,
                    decision_dropdown,
                    selected_match,
                    review_notes,
                ],
                outputs=[decision_result],
            )

            # Back to queue
            back_to_queue_btn.click(
                fn=lambda: gr.update(selected=0),
                outputs=[tabs],
            )

            # Search alternatives
            search_alternatives_btn.click(
                fn=self.search_alternatives,
                inputs=[alternative_search],
                outputs=[alternative_results],
            )

            # Load initial queue
            interface.load(
                fn=self.refresh_queue,
                inputs=[priority_filter],
                outputs=[queue_display, queue_stats],
            )

        return interface

    def refresh_queue(self, priority_filter: str):
        """Refresh the review queue"""
        try:
            # Get pending reviews
            if priority_filter == "All":
                reviews = self.interaction_manager.get_pending_reviews()
            else:
                priority = Priority[priority_filter.upper()]
                reviews = self.interaction_manager.get_reviews_by_priority(priority)

            # Format for display
            queue_data = []
            for review in reviews:
                queue_data.append(
                    [
                        review.review_id,
                        review.order.customer.email if review.order else "Unknown",
                        review.order.email_subject if review.order else "No subject",
                        f"{review.confidence_score:.1%}",
                        review.priority.value,
                        review.status.value,
                        review.created_at.strftime("%Y-%m-%d %H:%M"),
                    ]
                )

            # Calculate stats
            stats = {
                "total_pending": len(reviews),
                "urgent": sum(1 for r in reviews if r.priority == Priority.URGENT),
                "high": sum(1 for r in reviews if r.priority == Priority.HIGH),
                "medium": sum(1 for r in reviews if r.priority == Priority.MEDIUM),
                "low": sum(1 for r in reviews if r.priority == Priority.LOW),
            }

            return queue_data, stats

        except Exception as e:
            logger.error(f"Error refreshing queue: {e}")
            return [], {"error": str(e)}

    def submit_review_decision(
        self,
        review_id: str,
        decision: str,
        selected_match: str,
        notes: str,
    ):
        """Submit review decision"""
        try:
            # Map decision to action
            if "Approve" in decision:
                action = "approved"
                # Extract tag code from selected match
                approved_items = []
                if selected_match:
                    tag_code = selected_match.split(" - ")[0]
                    approved_items = [tag_code]
            elif "Reject" in decision:
                action = "rejected"
                approved_items = []
            elif "Better Image" in decision:
                action = "request_clarification"
                approved_items = []
                notes = f"Please provide a clearer image of the tag. {notes}"
            else:
                action = "deferred"
                approved_items = []

            # Submit decision
            success = self.interaction_manager.submit_review(
                review_id=review_id,
                decision=action,
                reviewer_name="Human Reviewer",
                notes=notes,
                approved_items=approved_items,
            )

            if success:
                return f"✅ Decision submitted successfully: {action}"
            else:
                return "❌ Failed to submit decision"

        except Exception as e:
            logger.error(f"Error submitting decision: {e}")
            return f"❌ Error: {str(e)}"

    def search_alternatives(self, query: str):
        """Search for alternative items"""
        try:
            # Use ChromaDB to search
            results = self.chromadb_client.search_inventory(
                query=query,
                limit=5,
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "tag_code": result.get("metadata", {}).get(
                            "tag_code", "Unknown"
                        ),
                        "brand": result.get("metadata", {}).get("brand", "Unknown"),
                        "confidence": result.get("confidence", 0),
                        "description": result.get("text", ""),
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching alternatives: {e}")
            return {"error": str(e)}


def launch_human_review_with_images(
    interaction_manager: HumanInteractionManager,
    chromadb_client: ChromaDBClient,
    port: int = 7861,
):
    """Launch the human review interface with image display"""
    interface = HumanReviewWithImages(interaction_manager, chromadb_client)
    app = interface.create_interface()
    app.launch(server_name="0.0.0.0", server_port=port, share=False)
    return app
