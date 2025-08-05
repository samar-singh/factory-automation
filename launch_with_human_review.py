"""Launch Factory Automation with Human Review System"""

import asyncio
import threading
from datetime import datetime

import gradio as gr

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_with_human import OrchestratorWithHuman
from factory_automation.factory_ui.human_review_interface import HumanReviewInterface
from factory_automation.factory_ui.gradio_app_ai import create_gradio_interface


def create_combined_interface():
    """Create combined interface with main app and human review"""
    
    print("🚀 Initializing Factory Automation System with Human Review...")
    
    # Initialize shared components
    chromadb_client = ChromaDBClient()
    
    # Initialize orchestrator with human interaction
    orchestrator = OrchestratorWithHuman(chromadb_client)
    human_manager = orchestrator.human_manager
    
    # Create human review interface
    review_interface = HumanReviewInterface(
        interaction_manager=human_manager,
        chromadb_client=chromadb_client
    )
    
    print("✅ Components initialized")
    
    # Create combined Gradio interface
    with gr.Blocks(title="Factory Automation System", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("# 🏭 Factory Automation System")
        gr.Markdown("Intelligent order processing with human-in-the-loop review")
        
        with gr.Tabs():
            
            # Tab 1: Main Application
            with gr.TabItem("🤖 AI Order Processing"):
                gr.Markdown("### Automated Order Processing")
                
                # Include main app interface
                main_interface = create_gradio_interface()
                
            # Tab 2: Human Review
            with gr.TabItem("👤 Human Review Dashboard"):
                gr.Markdown("### Manual Review Queue (60-80% confidence)")
                
                # Include review interface tabs
                with gr.Tabs():
                    
                    # Review Queue
                    with gr.TabItem("📋 Review Queue"):
                        with gr.Row():
                            with gr.Column(scale=1):
                                priority_filter = gr.Dropdown(
                                    choices=["All", "Urgent", "High", "Medium", "Low"],
                                    value="All",
                                    label="Filter by Priority"
                                )
                                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")
                            
                            with gr.Column(scale=3):
                                queue_display = gr.Dataframe(
                                    headers=["ID", "Customer", "Subject", "Confidence", "Priority", "Status", "Created"],
                                    label="Pending Reviews"
                                )
                        
                        review_id_input = gr.Textbox(label="Review ID to Open")
                        open_review_btn = gr.Button("📂 Open Review", variant="primary")
                        queue_stats = gr.JSON(label="Queue Statistics")
                    
                    # Current Review
                    with gr.TabItem("✏️ Current Review"):
                        with gr.Row():
                            with gr.Column():
                                review_details = gr.JSON(label="Review Details")
                                decision_dropdown = gr.Dropdown(
                                    choices=["Approve", "Reject", "Clarify", "Alternative"],
                                    label="Decision",
                                    value="Approve"
                                )
                                review_notes = gr.Textbox(label="Notes", lines=3)
                                submit_btn = gr.Button("✅ Submit", variant="primary")
                                decision_result = gr.Textbox(label="Result")
            
            # Tab 3: System Status
            with gr.TabItem("📊 System Status"):
                gr.Markdown("### System Health & Metrics")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Orchestrator Status")
                        orchestrator_status = gr.JSON(
                            value={
                                "status": "Running" if orchestrator.is_running() else "Stopped",
                                "monitoring": orchestrator.is_monitoring,
                                "tool_calls": len(orchestrator.tool_call_history)
                            },
                            label="Orchestrator"
                        )
                    
                    with gr.Column():
                        gr.Markdown("#### Review Statistics")
                        review_stats = gr.JSON(
                            value=human_manager.get_review_statistics(),
                            label="Human Reviews"
                        )
                
                with gr.Row():
                    start_monitoring_btn = gr.Button("▶️ Start Monitoring", variant="primary")
                    stop_monitoring_btn = gr.Button("⏹️ Stop Monitoring", variant="secondary")
                    export_metrics_btn = gr.Button("📥 Export Metrics")
        
        # Event handlers for review interface
        refresh_btn.click(
            fn=review_interface.refresh_queue,
            inputs=[priority_filter],
            outputs=[queue_display, queue_stats]
        )
        
        open_review_btn.click(
            fn=lambda rid: review_interface.open_review(rid),
            inputs=[review_id_input],
            outputs=[review_details]
        )
        
        submit_btn.click(
            fn=lambda rid, dec, notes: asyncio.run(
                human_manager.submit_review_decision(rid, dec.lower(), notes)
            ),
            inputs=[review_id_input, decision_dropdown, review_notes],
            outputs=[decision_result]
        )
        
        # Orchestrator control handlers
        async def start_monitoring():
            await orchestrator.start_with_review_monitoring()
            return {"status": "Monitoring started"}
        
        async def stop_monitoring():
            await orchestrator.stop()
            return {"status": "Monitoring stopped"}
        
        start_monitoring_btn.click(
            fn=lambda: asyncio.run(start_monitoring()),
            outputs=[orchestrator_status]
        )
        
        stop_monitoring_btn.click(
            fn=lambda: asyncio.run(stop_monitoring()),
            outputs=[orchestrator_status]
        )
        
        # Auto-refresh stats
        app.load(
            fn=lambda: (
                review_interface.refresh_queue("All"),
                human_manager.get_review_statistics()
            ),
            outputs=[queue_display, queue_stats, review_stats]
        )
    
    return app, orchestrator, human_manager


def main():
    """Main entry point"""
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║     Factory Automation System with Human Review          ║
║                                                           ║
║  Features:                                                ║
║  • AI-powered order processing                           ║
║  • Confidence-based routing (>80% auto, 60-80% manual)   ║
║  • Human review dashboard for manual approvals           ║
║  • Real-time monitoring and metrics                      ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Create combined interface
    app, orchestrator, human_manager = create_combined_interface()
    
    # Start orchestrator in background thread
    def run_orchestrator():
        asyncio.run(orchestrator.start_with_review_monitoring())
    
    monitoring_thread = threading.Thread(target=run_orchestrator, daemon=True)
    monitoring_thread.start()
    
    print("\n✅ System initialized successfully!")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🌐 Launching web interface...")
    print("   Main App: http://localhost:7860")
    print("   Human Review: http://localhost:7860 (integrated)")
    
    # Launch the app
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()