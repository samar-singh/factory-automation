"""Improved Human Review Interface with simplified interaction flow"""

import asyncio
import logging
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

    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface for human review"""

        with gr.Blocks(
            title="Human Review Dashboard", theme=gr.themes.Soft()
        ) as interface:
            gr.Markdown("# 🔍 Human Review Dashboard")
            gr.Markdown(
                "Review and approve orders that need manual intervention (<90% confidence)"
            )

            # State variable to track selected review
            selected_review_state = gr.State(value=None)

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
                    # Return 9 values: tabs + 7 review fields + decision_result
                    return (
                        gr.update(),
                        *[gr.update()] * 7,
                        gr.update(value="Please select a review first"),
                    )

                # Open the review
                result = self.open_review(review_id)

                # Return updates for all components plus tab selection
                return (
                    gr.update(selected=1),  # Switch to Current Review tab (index 1)
                    *result,  # All the review data (7 values)
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
            return [""] * 7  # Return empty values

        try:
            # Get review details
            review = asyncio.run(self.interaction_manager.get_review_details(review_id))

            if not review:
                return ["Review not found"] + [""] * 6

            # Store current review
            self.current_review = review

            # Debug logging
            logger.info(f"Opening review {review_id}")
            logger.debug(
                f"Review items type: {type(review.items)}, content: {review.items}"
            )
            logger.debug(f"Review search_results type: {type(review.search_results)}")

        except Exception as e:
            logger.error(f"Error opening review {review_id}: {e}")
            return [f"Error: {str(e)}"] + [""] * 6

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

        return (
            review.request_id,
            review.customer_email,
            review.subject,
            f"{review.confidence_score:.1%}",  # Format as percentage
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
