"""Enhanced Gradio dashboard with live inventory search."""

import logging
import sys
from pathlib import Path

import gradio as gr
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from factory_automation.factory_database.vector_db import ChromaDBClient  # noqa: E402
from factory_automation.factory_rag.excel_ingestion import (  # noqa: E402
    ExcelInventoryIngestion,
)

logger = logging.getLogger(__name__)


def create_live_dashboard():
    """Create the Gradio dashboard with live inventory search."""

    # Initialize ChromaDB connection
    try:
        chroma_client = ChromaDBClient()
        collection = chroma_client.collection
        total_items = collection.count()
        print(f"Connected to ChromaDB: {total_items} items in inventory")

        # Initialize ingestion for search
        ingestion = ExcelInventoryIngestion(
            chroma_client=chroma_client, embedding_model="all-MiniLM-L6-v2"
        )
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        chroma_client = None
        ingestion = None
        total_items = 0

    with gr.Blocks(title="Factory Automation Dashboard", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🏭 Factory Price Tag Automation System")
        gr.Markdown(f"**Inventory Database**: {total_items} items loaded")

        with gr.Tabs():
            # Tab 1: Inventory Search
            with gr.Tab("🔍 Inventory Search"):
                gr.Markdown("## Search Tag Inventory")

                with gr.Row():
                    search_query = gr.Textbox(
                        label="Search Query",
                        placeholder="e.g., VH cotton tags, blue FM tags, Allen Solly size 32",
                        scale=3,
                    )
                    search_btn = gr.Button("Search", variant="primary", scale=1)

                with gr.Row():
                    confidence_threshold = gr.Slider(
                        minimum=0,
                        maximum=100,
                        value=50,
                        step=5,
                        label="Minimum Confidence %",
                    )
                    max_results = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1, label="Max Results"
                    )

                search_results = gr.DataFrame(
                    headers=["Item", "Brand", "Stock", "Confidence %", "Match Reason"],
                    label="Search Results",
                    interactive=False,
                )

                # Search function
                def search_inventory(query, confidence_threshold, max_results):
                    if not query or not ingestion:
                        return pd.DataFrame()

                    try:
                        # Perform search
                        results = ingestion.search_inventory(
                            query=query, limit=int(max_results)
                        )

                        # Format results for display
                        if results["matches"]:
                            data = []
                            for match in results["matches"]:
                                data.append(
                                    {
                                        "Item": match["item_name"],
                                        "Brand": match["brand"],
                                        "Stock": f"{match['available_stock']} units",
                                        "Confidence %": f"{match['confidence_score']*100:.1f}%",
                                        "Match Reason": match.get(
                                            "match_reason", "Text similarity"
                                        ),
                                    }
                                )
                            return pd.DataFrame(data)
                        else:
                            return pd.DataFrame({"Message": ["No matches found"]})

                    except Exception as e:
                        logger.error(f"Search error: {e}")
                        return pd.DataFrame({"Error": [str(e)]})

                search_btn.click(
                    fn=search_inventory,
                    inputs=[search_query, confidence_threshold, max_results],
                    outputs=search_results,
                )

            # Tab 2: Order Processing
            with gr.Tab("📧 Order Processing"):
                gr.Markdown("## Process Email Orders")

                with gr.Row():
                    order_text = gr.Textbox(
                        label="Order Text",
                        placeholder="Paste email content or order details here...",
                        lines=10,
                    )

                with gr.Row():
                    process_btn = gr.Button("Process Order", variant="primary")
                    clear_btn = gr.Button("Clear", variant="secondary")

                order_results = gr.DataFrame(
                    headers=[
                        "Order Line",
                        "Best Match",
                        "Stock Status",
                        "Confidence",
                        "Action",
                    ],
                    label="Order Matching Results",
                )

                recommendation = gr.Textbox(label="Recommendation", interactive=False)

                def process_order(order_text):
                    if not order_text or not ingestion:
                        return pd.DataFrame(), ""

                    try:
                        # Extract order lines (simple extraction)
                        lines = []
                        for line in order_text.split("\n"):
                            line = line.strip()
                            if line and any(
                                word in line.lower()
                                for word in ["tag", "tags", "pcs", "pieces", "units"]
                            ):
                                if line.startswith("-"):
                                    line = line[1:].strip()
                                lines.append(line)

                        if not lines:
                            return (
                                pd.DataFrame({"Message": ["No order lines found"]}),
                                "Please provide order details",
                            )

                        # Process each line
                        results = []
                        auto_approve = True

                        for line in lines:
                            # Search for the item
                            search_result = ingestion.search_inventory(
                                query=line, limit=1
                            )

                            if search_result["matches"]:
                                match = search_result["matches"][0]

                                # Check stock
                                if match["available_stock"] > 0:
                                    # status = "✅ In Stock"
                                    action = (
                                        "Auto-approve"
                                        if match["confidence_score"] > 0.8
                                        else "Review"
                                    )
                                else:
                                    # status = "❌ Out of Stock"
                                    action = "Find alternative"
                                    auto_approve = False

                                if match["confidence_score"] < 0.7:
                                    auto_approve = False

                                results.append(
                                    {
                                        "Order Line": (
                                            line[:50] + "..."
                                            if len(line) > 50
                                            else line
                                        ),
                                        "Best Match": match["item_name"],
                                        "Stock Status": f"{match['available_stock']} units",
                                        "Confidence": f"{match['confidence_score']*100:.1f}%",
                                        "Action": action,
                                    }
                                )
                            else:
                                results.append(
                                    {
                                        "Order Line": (
                                            line[:50] + "..."
                                            if len(line) > 50
                                            else line
                                        ),
                                        "Best Match": "No match found",
                                        "Stock Status": "N/A",
                                        "Confidence": "0%",
                                        "Action": "Manual search",
                                    }
                                )
                                auto_approve = False

                        # Recommendation
                        if auto_approve:
                            rec = "✅ Recommendation: AUTO-APPROVE - All items available with high confidence"
                        else:
                            rec = "⚠️ Recommendation: MANUAL REVIEW - Some items need attention"

                        return pd.DataFrame(results), rec

                    except Exception as e:
                        logger.error(f"Order processing error: {e}")
                        return (
                            pd.DataFrame({"Error": [str(e)]}),
                            "Error processing order",
                        )

                process_btn.click(
                    fn=process_order,
                    inputs=order_text,
                    outputs=[order_results, recommendation],
                )

                clear_btn.click(
                    fn=lambda: ("", pd.DataFrame(), ""),
                    outputs=[order_text, order_results, recommendation],
                )

            # Tab 3: System Status
            with gr.Tab("📊 System Status"):
                gr.Markdown("## System Information")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown(
                            f"""
                        ### Database Status
                        - **ChromaDB**: {'✅ Connected' if chroma_client else '❌ Not Connected'}
                        - **Total Items**: {total_items}
                        - **Embedding Model**: all-MiniLM-L6-v2
                        - **Dimensions**: 384
                        """
                        )

                    with gr.Column():
                        gr.Markdown(
                            """
                        ### System Features
                        - ✅ Natural language search
                        - ✅ Order processing
                        - ✅ Stock checking
                        - ✅ Confidence scoring
                        - ⏳ Gmail integration (pending)
                        - ⏳ Payment tracking (pending)
                        """
                        )

                refresh_btn = gr.Button("Refresh Status")
                status_output = gr.Textbox(
                    label="System Log", lines=10, interactive=False
                )

                def refresh_status():
                    try:
                        count = collection.count() if collection else 0
                        return f"Database refreshed. Total items: {count}"
                    except Exception as e:
                        return f"Error: {str(e)}"

                refresh_btn.click(fn=refresh_status, outputs=status_output)

        gr.Markdown(
            """
            ---
            **Factory Automation System** | Version 0.1.0 | 
            [Documentation](https://github.com/samar-singh/factory-automation)
            """
        )

    return app


# For standalone testing
if __name__ == "__main__":
    app = create_live_dashboard()
    app.launch()
