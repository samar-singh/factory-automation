"""Human Review Interface for Manual Approvals"""

import gradio as gr
import asyncio
import json
from datetime import datetime
from typing import List, Optional

from ..factory_agents.human_interaction_manager import (
    HumanInteractionManager,
    ReviewRequest,
    Priority
)
from ..factory_database.vector_db import ChromaDBClient


class HumanReviewInterface:
    """Gradio-based interface for human reviewers"""
    
    def __init__(
        self,
        interaction_manager: HumanInteractionManager,
        chromadb_client: ChromaDBClient
    ):
        """Initialize the review interface"""
        self.interaction_manager = interaction_manager
        self.chromadb_client = chromadb_client
        self.current_review: Optional[ReviewRequest] = None
        
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface for human review"""
        
        with gr.Blocks(title="Human Review Dashboard", theme=gr.themes.Soft()) as interface:
            
            gr.Markdown("# 🔍 Human Review Dashboard")
            gr.Markdown("Review and approve orders that need manual intervention (60-80% confidence)")
            
            with gr.Tabs():
                
                # Tab 1: Review Queue
                with gr.TabItem("📋 Review Queue"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            priority_filter = gr.Dropdown(
                                choices=["All", "Urgent", "High", "Medium", "Low"],
                                value="All",
                                label="Filter by Priority"
                            )
                            refresh_btn = gr.Button("🔄 Refresh Queue", variant="secondary")
                        
                        with gr.Column(scale=3):
                            queue_display = gr.Dataframe(
                                headers=["ID", "Customer", "Subject", "Confidence", "Priority", "Status", "Created"],
                                label="Pending Reviews",
                                interactive=False
                            )
                    
                    with gr.Row():
                        review_id_input = gr.Textbox(
                            label="Review ID to Open",
                            placeholder="Enter review ID (e.g., REV-20250103-0001)"
                        )
                        open_review_btn = gr.Button("📂 Open Review", variant="primary")
                    
                    queue_stats = gr.JSON(label="Queue Statistics")
                
                # Tab 2: Current Review
                with gr.TabItem("✏️ Current Review"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("### 📧 Order Details")
                            review_id_display = gr.Textbox(label="Review ID", interactive=False)
                            customer_email = gr.Textbox(label="Customer Email", interactive=False)
                            email_subject = gr.Textbox(label="Email Subject", interactive=False)
                            confidence_score = gr.Number(label="Confidence Score (%)", interactive=False)
                            
                            gr.Markdown("### 📦 Requested Items")
                            requested_items = gr.JSON(label="Items from Email")
                        
                        with gr.Column(scale=2):
                            gr.Markdown("### 🔎 Search Results")
                            search_results = gr.JSON(label="Matched Items from Inventory")
                            
                            gr.Markdown("### 🎯 Suggested Alternatives")
                            alternative_search = gr.Textbox(
                                label="Search for Alternatives",
                                placeholder="Enter search query for alternative items"
                            )
                            search_alternatives_btn = gr.Button("🔍 Search", variant="secondary")
                            alternative_results = gr.JSON(label="Alternative Items")
                    
                    gr.Markdown("### 📝 Review Decision")
                    with gr.Row():
                        with gr.Column():
                            decision_dropdown = gr.Dropdown(
                                choices=["Approve", "Reject", "Clarify", "Alternative"],
                                label="Decision",
                                value="Approve"
                            )
                            review_notes = gr.Textbox(
                                label="Review Notes",
                                placeholder="Add any notes about your decision...",
                                lines=3
                            )
                        
                        with gr.Column():
                            selected_alternatives = gr.CheckboxGroup(
                                label="Select Alternative Items (if choosing 'Alternative')",
                                choices=[],
                                value=[]
                            )
                    
                    with gr.Row():
                        submit_decision_btn = gr.Button("✅ Submit Decision", variant="primary", size="lg")
                        skip_review_btn = gr.Button("⏭️ Skip to Next", variant="secondary")
                    
                    decision_result = gr.Textbox(label="Decision Result", interactive=False)
                
                # Tab 3: Review History
                with gr.TabItem("📊 Review History"):
                    with gr.Row():
                        start_date = gr.Textbox(label="Start Date", placeholder="YYYY-MM-DD")
                        end_date = gr.Textbox(label="End Date", placeholder="YYYY-MM-DD")
                        status_filter = gr.Dropdown(
                            choices=["All", "Approved", "Rejected", "Needs Clarification", "Alternative Suggested"],
                            value="All",
                            label="Filter by Status"
                        )
                        export_btn = gr.Button("📥 Export Data", variant="secondary")
                    
                    history_display = gr.Dataframe(
                        headers=["ID", "Customer", "Confidence", "Decision", "Reviewer", "Review Time", "Notes"],
                        label="Completed Reviews",
                        interactive=False
                    )
                    
                    performance_metrics = gr.JSON(label="Performance Metrics")
            
            # Event handlers
            refresh_btn.click(
                fn=self.refresh_queue,
                inputs=[priority_filter],
                outputs=[queue_display, queue_stats]
            )
            
            open_review_btn.click(
                fn=self.open_review,
                inputs=[review_id_input],
                outputs=[
                    review_id_display,
                    customer_email,
                    email_subject,
                    confidence_score,
                    requested_items,
                    search_results,
                    selected_alternatives
                ]
            )
            
            search_alternatives_btn.click(
                fn=self.search_alternatives,
                inputs=[alternative_search],
                outputs=[alternative_results, selected_alternatives]
            )
            
            submit_decision_btn.click(
                fn=self.submit_decision,
                inputs=[
                    review_id_display,
                    decision_dropdown,
                    review_notes,
                    selected_alternatives
                ],
                outputs=[decision_result]
            )
            
            skip_review_btn.click(
                fn=self.skip_to_next,
                inputs=[],
                outputs=[
                    review_id_display,
                    customer_email,
                    email_subject,
                    confidence_score,
                    requested_items,
                    search_results
                ]
            )
            
            export_btn.click(
                fn=self.export_data,
                inputs=[],
                outputs=[gr.File(label="Exported Data")]
            )
            
            # Auto-refresh queue on load
            interface.load(
                fn=self.refresh_queue,
                inputs=[priority_filter],
                outputs=[queue_display, queue_stats]
            )
        
        return interface
    
    def refresh_queue(self, priority_filter: str):
        """Refresh the review queue"""
        
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
            queue_data.append([
                review.request_id,
                review.customer_email,
                review.subject[:50] + "..." if len(review.subject) > 50 else review.subject,
                f"{review.confidence_score:.1f}%",
                review.priority.value,
                review.status.value,
                review.created_at.strftime("%Y-%m-%d %H:%M")
            ])
        
        # Get statistics
        stats = self.interaction_manager.get_review_statistics()
        
        return queue_data, stats
    
    def open_review(self, review_id: str):
        """Open a specific review for processing"""
        
        if not review_id:
            return [""] * 7  # Return empty values
        
        # Get review details
        review = asyncio.run(
            self.interaction_manager.get_review_details(review_id)
        )
        
        if not review:
            return ["Review not found"] + [""] * 6
        
        # Store current review
        self.current_review = review
        
        # Format search results for display
        search_results_formatted = []
        for result in review.search_results[:5]:  # Top 5 results
            search_results_formatted.append({
                "name": result.get("name", "Unknown"),
                "code": result.get("code", "N/A"),
                "brand": result.get("brand", "Unknown"),
                "similarity": f"{result.get('similarity_score', 0) * 100:.1f}%",
                "price": result.get("price", 0),
                "stock": result.get("stock", 0)
            })
        
        # Create alternative checkboxes (initially empty)
        alternatives_choices = []
        
        return (
            review.request_id,
            review.customer_email,
            review.subject,
            review.confidence_score,
            review.items,
            search_results_formatted,
            alternatives_choices
        )
    
    def search_alternatives(self, query: str):
        """Search for alternative items"""
        
        if not query:
            return [], []
        
        # Search using ChromaDB directly
        results = self.chromadb_client.collection.query(
            query_texts=[query],
            n_results=10,
            include=["metadatas", "distances", "documents"]
        )
        
        # Format results
        alternatives = []
        choices = []
        
        if results and results.get("ids") and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                similarity = 1 - results["distances"][0][i]  # Convert distance to similarity
                
                item_info = {
                    "id": results["ids"][0][i],
                    "name": metadata.get("trim_name", "Unknown"),
                    "code": metadata.get("trim_code", "N/A"),
                    "brand": metadata.get("brand", "Unknown"),
                    "similarity": f"{similarity * 100:.1f}%",
                    "price": metadata.get("price", 0),
                    "stock": metadata.get("stock", 0)
                }
                alternatives.append(item_info)
                
                # Create choice label
                choice_label = f"{item_info['name']} ({item_info['code']}) - {item_info['brand']} - {item_info['similarity']}"
                choices.append(choice_label)
        
        # Create checkbox group with choices
        return alternatives, gr.CheckboxGroup(choices=choices, value=[])
    
    def submit_decision(
        self,
        review_id: str,
        decision: str,
        notes: str,
        selected_alternatives: List[str]
    ):
        """Submit the review decision"""
        
        if not review_id:
            return "Error: No review selected"
        
        # Parse selected alternatives
        alternative_items = []
        if decision == "Alternative" and selected_alternatives:
            for alt in selected_alternatives:
                # Parse the alternative from the label
                parts = alt.split(" - ")
                if len(parts) >= 3:
                    name_code = parts[0]
                    brand = parts[1]
                    alternative_items.append({
                        "name": name_code.split("(")[0].strip(),
                        "code": name_code.split("(")[1].replace(")", "").strip() if "(" in name_code else "N/A",
                        "brand": brand
                    })
        
        # Submit decision
        result = asyncio.run(
            self.interaction_manager.submit_review_decision(
                request_id=review_id,
                decision=decision.lower(),
                notes=notes,
                alternative_items=alternative_items if alternative_items else None
            )
        )
        
        if result["success"]:
            return f"✅ Decision submitted successfully! Review {review_id} marked as {result['status']}. Review time: {result['review_time_seconds']:.1f} seconds"
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"
    
    def skip_to_next(self):
        """Skip to the next review in queue"""
        
        # Get next pending review
        reviews = asyncio.run(
            self.interaction_manager.get_pending_reviews()
        )
        
        if not reviews:
            return ["No pending reviews"] + [""] * 5
        
        # Open the first review
        return self.open_review(reviews[0].request_id)
    
    def export_data(self):
        """Export review data to JSON file"""
        
        data = self.interaction_manager.export_review_data()
        
        # Save to file
        filename = f"review_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = f"/tmp/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return filepath


def launch_human_review_interface():
    """Launch the human review interface"""
    
    # Initialize components
    chromadb_client = ChromaDBClient()
    interaction_manager = HumanInteractionManager()
    
    # Create interface
    review_interface = HumanReviewInterface(
        interaction_manager=interaction_manager,
        chromadb_client=chromadb_client
    )
    
    # Create and launch Gradio app
    app = review_interface.create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Different port from main app
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    launch_human_review_interface()