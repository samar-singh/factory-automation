"""Gradio dashboard for the Factory Automation System."""

import logging

import gradio as gr
import pandas as pd

logger = logging.getLogger(__name__)


def create_dashboard():
    """Create the main Gradio dashboard."""

    # Sample data for demonstration
    sample_orders = pd.DataFrame(
        {
            "Order ID": ["ORD-001", "ORD-002", "ORD-003"],
            "Customer": ["Goutam Trading", "ABC Corp", "XYZ Ltd"],
            "Status": ["Pending Approval", "Payment Due", "Processing"],
            "Items": [3, 5, 2],
            "Days Open": [2, 7, 1],
        }
    )

    with gr.Blocks(title="Factory Automation Dashboard") as app:
        gr.Markdown("# 🏭 Factory Price Tag Automation System")

        with gr.Tabs():
            # Tab 1: Order Pipeline
            with gr.Tab("Order Pipeline"):
                gr.Markdown("## Active Orders")
                _ = gr.DataFrame(  # orders_df - will be used when order fetching is implemented
                    value=sample_orders, label="Current Orders", interactive=False
                )

                _ = gr.Button("🔄 Refresh Orders", variant="primary")  # refresh_btn

            # Tab 2: Tag Search
            with gr.Tab("Tag Search"):
                gr.Markdown("## Search Inventory")

                with gr.Row():
                    with gr.Column(scale=1):
                        search_image = gr.Image(
                            label="Upload Tag Image", type="filepath"
                        )
                        search_text = gr.Textbox(
                            label="Tag Description",
                            placeholder="Enter tag description...",
                        )
                        search_size = gr.Textbox(
                            label="Size", placeholder="e.g., 101 x 51 mm"
                        )
                        search_btn = gr.Button("🔍 Search", variant="primary")

                    with gr.Column(scale=2):
                        search_results = gr.Gallery(
                            label="Matching Tags",
                            show_label=True,
                            columns=3,
                            rows=2,
                            height="auto",
                        )

                        results_table = gr.DataFrame(
                            headers=[
                                "Tag Code",
                                "Description",
                                "Size",
                                "Stock",
                                "Similarity %",
                            ],
                            label="Match Details",
                        )

            # Tab 3: Email Processing
            with gr.Tab("Email Processing"):
                gr.Markdown("## Process Email")

                email_upload = gr.File(
                    label="Upload Email (.eml) or Paste Content",
                    file_types=[".eml", ".txt"],
                )

                email_content = gr.Textbox(
                    label="Or Paste Email Content",
                    lines=10,
                    placeholder="Paste email content here...",
                )

                process_email_btn = gr.Button("📧 Process Email", variant="primary")

                with gr.Row():
                    email_type = gr.Textbox(label="Detected Type")
                    extracted_info = gr.JSON(label="Extracted Information")

            # Tab 4: Pending Approvals
            with gr.Tab("Pending Approvals"):
                gr.Markdown("## Items Requiring Approval")

                _ = gr.DataFrame(  # approval_queue
                    headers=["Order ID", "Customer", "Tag", "Quantity", "Match %"],
                    label="Approval Queue",
                )

                with gr.Row():
                    with gr.Column():
                        _ = gr.Image(label="Requested Tag")  # requested_img
                    with gr.Column():
                        _ = gr.Image(label="Best Match")  # matched_img

                with gr.Row():
                    _ = gr.Button("✅ Approve", variant="primary")  # approve_btn
                    _ = gr.Button("❌ Reject", variant="stop")  # reject_btn
                    _ = gr.Button(
                        "🆕 Create New", variant="secondary"
                    )  # create_new_btn

            # Tab 5: Analytics
            with gr.Tab("Analytics"):
                gr.Markdown("## System Analytics")

                with gr.Row():
                    _ = gr.Number(label="Total Orders", value=47)  # total_orders
                    _ = gr.Number(
                        label="Pending Approvals", value=3
                    )  # pending_approvals
                    _ = gr.Number(
                        label="Pending Payments", value=12
                    )  # pending_payments

                _ = gr.Plot(label="Order Trends")  # order_chart
                _ = gr.Plot(label="Payment Status Distribution")  # payment_chart

        # Event handlers
        def search_inventory(image, text, size):
            # Placeholder for actual search
            results_data = pd.DataFrame(
                {
                    "Tag Code": ["SMT-01", "SMT-02", "SMT-03"],
                    "Description": ["Similar Tag 1", "Similar Tag 2", "Similar Tag 3"],
                    "Size": ["101 x 51 mm", "100 x 50 mm", "102 x 52 mm"],
                    "Stock": [100, 50, 200],
                    "Similarity %": [95, 87, 82],
                }
            )
            return None, results_data  # Return empty gallery for now

        def process_email(file, content):
            # Placeholder for email processing
            return "new_order", {"customer": "Sample Customer", "items": 5}

        # Connect event handlers
        search_btn.click(
            fn=search_inventory,
            inputs=[search_image, search_text, search_size],
            outputs=[search_results, results_table],
        )

        process_email_btn.click(
            fn=process_email,
            inputs=[email_upload, email_content],
            outputs=[email_type, extracted_info],
        )

        gr.Markdown(
            """
        ---
        **System Status**: 🟢 All systems operational |
        **Last Update**: Just now |
        **Version**: 0.1.0
        """
        )

    return app


# For standalone testing
if __name__ == "__main__":
    app = create_dashboard()
    app.launch()
