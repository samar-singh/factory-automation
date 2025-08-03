"""AI-Enhanced Gradio dashboard with intelligent order processing."""

import asyncio
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

from factory_automation.factory_agents.ai_bridge import get_ai_bridge  # noqa: E402
from factory_automation.factory_database.vector_db import ChromaDBClient  # noqa: E402

logger = logging.getLogger(__name__)


def create_ai_dashboard():
    """Create the AI-powered Gradio dashboard."""

    # Initialize ChromaDB connection
    try:
        # Use the new Stella collection
        chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
        collection = chroma_client.collection
        total_items = collection.count()
        print(f"Connected to ChromaDB (Stella): {total_items} items in inventory")

        # Initialize AI bridge
        ai_bridge = get_ai_bridge(chroma_client=chroma_client)
        ai_enabled = True
    except Exception as e:
        print(f"Error initializing AI components: {e}")
        chroma_client = None
        ai_bridge = None
        total_items = 0
        ai_enabled = False

    with gr.Blocks(
        title="AI Factory Automation Dashboard", theme=gr.themes.Soft()
    ) as app:
        gr.Markdown("# 🏭 AI-Powered Factory Price Tag Automation System")
        gr.Markdown(
            f"**Inventory Database**: {total_items} items loaded | **AI Status**: {'✅ Enabled' if ai_enabled else '❌ Disabled'}"
        )

        with gr.Tabs():
            # Tab 1: AI-Enhanced Inventory Search
            with gr.Tab("🔍 AI Inventory Search"):
                gr.Markdown("## AI-Enhanced Tag Inventory Search")
                gr.Markdown(
                    "The AI understands natural language queries and provides intelligent search results."
                )

                with gr.Row():
                    search_query = gr.Textbox(
                        label="Search Query",
                        placeholder="e.g., I need 500 blue cotton tags for VH brand, urgent delivery",
                        scale=3,
                    )
                    search_btn = gr.Button("AI Search", variant="primary", scale=1)

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

                # AI Search function
                def ai_search_inventory(query, confidence_threshold, max_results):
                    if not query or not ai_bridge:
                        return pd.DataFrame({"Message": ["AI not available"]})

                    try:
                        # Run async function in sync context
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(
                            ai_bridge.search_with_ai_enhancement(
                                query, confidence_threshold, max_results
                            )
                        )
                        return result

                    except Exception as e:
                        logger.error(f"AI search error: {e}")
                        return pd.DataFrame({"Error": [str(e)]})

                search_btn.click(
                    fn=ai_search_inventory,
                    inputs=[search_query, confidence_threshold, max_results],
                    outputs=search_results,
                )

            # Tab 2: AI Order Processing
            with gr.Tab("📧 AI Order Processing"):
                gr.Markdown("## AI-Powered Email Order Processing")
                gr.Markdown(
                    "The AI orchestrator analyzes orders, extracts items, and matches with inventory intelligently."
                )

                with gr.Row():
                    order_text = gr.Textbox(
                        label="Order Text",
                        placeholder="Paste email content or order details here...",
                        lines=10,
                    )

                with gr.Row():
                    process_btn = gr.Button(
                        "Process with AI", variant="primary", icon="🤖"
                    )
                    clear_btn = gr.Button("Clear", variant="secondary")

                order_results = gr.DataFrame(
                    headers=[
                        "Order Line",
                        "Best Match",
                        "Stock Status",
                        "Confidence",
                        "Action",
                        "AI Understanding",
                    ],
                    label="AI Order Matching Results",
                )

                recommendation = gr.Textbox(
                    label="AI Recommendation", interactive=False, lines=5
                )

                ai_details = gr.JSON(label="AI Processing Details", visible=False)

                def ai_process_order(order_text):
                    if not order_text or not ai_bridge:
                        return (
                            pd.DataFrame({"Message": ["AI not available"]}),
                            "AI processing not available",
                            {},
                        )

                    try:
                        # Run async function in sync context
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        df, rec, context = loop.run_until_complete(
                            ai_bridge.process_order_with_ai(order_text)
                        )
                        return df, rec, context

                    except Exception as e:
                        logger.error(f"AI order processing error: {e}")
                        return (
                            pd.DataFrame({"Error": [str(e)]}),
                            f"Error: {str(e)}",
                            {},
                        )

                process_btn.click(
                    fn=ai_process_order,
                    inputs=order_text,
                    outputs=[order_results, recommendation, ai_details],
                )

                clear_btn.click(
                    fn=lambda: ("", pd.DataFrame(), "", {}),
                    outputs=[order_text, order_results, recommendation, ai_details],
                )

                # Toggle AI details visibility
                show_details = gr.Checkbox(label="Show AI Processing Details")
                show_details.change(
                    fn=lambda x: gr.update(visible=x),
                    inputs=show_details,
                    outputs=ai_details,
                )

            # Tab 3: AI System Status
            with gr.Tab("📊 AI System Status"):
                gr.Markdown("## AI System Information")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown(
                            f"""
                        ### AI Components Status
                        - **Orchestrator**: {'✅ Active' if ai_enabled else '❌ Inactive'}
                        - **GPT-4**: {'✅ Connected' if ai_enabled else '❌ Not Connected'}
                        - **Qwen2.5VL**: {'✅ Ready' if ai_enabled else '❌ Not Ready'}
                        - **Embeddings**: Stella-400M (1024 dims)
                        
                        ### Database Status
                        - **ChromaDB**: {'✅ Connected' if chroma_client else '❌ Not Connected'}
                        - **Total Items**: {total_items}
                        """
                        )

                    with gr.Column():
                        gr.Markdown(
                            """
                        ### AI Capabilities
                        - ✅ Natural language understanding
                        - ✅ Multi-step reasoning
                        - ✅ Context-aware processing
                        - ✅ Email & attachment analysis
                        - ✅ Visual tag understanding
                        - ✅ Intelligent matching
                        - ⏳ Payment OCR (coming soon)
                        - ⏳ Document generation (coming soon)
                        """
                        )

                refresh_btn = gr.Button("Test AI System")
                status_output = gr.Textbox(
                    label="AI System Test Results", lines=10, interactive=False
                )

                def test_ai_system():
                    try:
                        if not ai_bridge:
                            return "AI system not initialized"

                        # Test the AI with a simple query
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        test_result = loop.run_until_complete(
                            ai_bridge.orchestrator.handle_complex_request(
                                "Test: What capabilities do you have?",
                                context={"test": True},
                            )
                        )

                        if test_result.get("success"):
                            return f"✅ AI System Test Passed\n\nAI Response:\n{test_result.get('result', 'No response')}"
                        else:
                            return f"❌ AI System Test Failed\n\nError: {test_result.get('error', 'Unknown error')}"

                    except Exception as e:
                        return f"❌ AI System Error: {str(e)}"

                refresh_btn.click(fn=test_ai_system, outputs=status_output)

        gr.Markdown(
            """
            ---
            **AI Factory Automation System** | Version 0.2.0 (AI-Powered) |
            [Documentation](https://github.com/samar-singh/factory-automation)
            """
        )

    return app


# For standalone testing
if __name__ == "__main__":
    app = create_ai_dashboard()
    app.launch()
