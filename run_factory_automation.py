#!/usr/bin/env python3
"""
Main Runner for Factory Automation System
Run this to start the complete system with all features
"""

import asyncio
import os
import sys
import threading
import webbrowser
from datetime import datetime

# Check for required environment variables
def check_environment():
    """Check if required environment variables are set"""
    
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key for AI orchestrator",
        # Add other required vars here if needed
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  - {var}: {description}")
    
    if missing:
        print("❌ Missing required environment variables:")
        print("\n".join(missing))
        print("\nSet them using:")
        print("  export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    print("✅ Environment variables configured")


def print_banner():
    """Print startup banner"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║     🏭 FACTORY AUTOMATION SYSTEM v2.0                     ║
║     Intelligent Order Processing with Human Review        ║
║                                                            ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Components:                                               ║
║  • AI Orchestrator (GPT-4)                                ║
║  • RAG Search (ChromaDB + Stella-400M)                    ║
║  • Human Review System (60-80% confidence)                ║
║  • Gmail Integration (Mock mode for testing)              ║
║  • Real-time Dashboard                                    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)


async def start_orchestrator():
    """Start the orchestrator with human interaction"""
    
    from factory_automation.factory_database.vector_db import ChromaDBClient
    from factory_automation.factory_agents.orchestrator_with_human import OrchestratorWithHuman
    
    print("🚀 Starting orchestrator...")
    
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    
    # Start monitoring
    try:
        await orchestrator.start_with_review_monitoring()
    except KeyboardInterrupt:
        print("\n⏹️  Stopping orchestrator...")
        await orchestrator.stop()


def start_web_interface():
    """Start the Gradio web interface"""
    
    from factory_automation.factory_database.vector_db import ChromaDBClient
    from factory_automation.factory_agents.orchestrator_with_human import OrchestratorWithHuman
    from factory_automation.factory_ui.human_review_interface import HumanReviewInterface
    import gradio as gr
    
    print("🌐 Starting web interface...")
    
    # Initialize components
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    human_manager = orchestrator.human_manager
    
    # Create review interface
    review_interface = HumanReviewInterface(
        interaction_manager=human_manager,
        chromadb_client=chromadb_client
    )
    
    # Create combined interface
    with gr.Blocks(title="Factory Automation", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("# 🏭 Factory Automation System")
        
        with gr.Tabs():
            # Main Processing Tab
            with gr.TabItem("🤖 Order Processing"):
                gr.Markdown("### AI-Powered Order Processing")
                
                with gr.Row():
                    with gr.Column():
                        email_input = gr.Textbox(
                            label="Paste Complete Email (with From:, Subject:, etc.)",
                            placeholder="""Example:
From: storerhppl@gmail.com
Subject: Allen Solly Order
Date: Monday, 28 July 2025

Dear Sir,
We need 1000 price tags for Allen Solly...
""",
                            lines=10
                        )
                        gr.Markdown("*Customer email will be extracted automatically from the 'From:' field*")
                        process_btn = gr.Button("📧 Process Order", variant="primary", size="lg")
                    
                    with gr.Column():
                        processing_result = gr.JSON(label="Processing Result")
                        extracted_info = gr.Textbox(label="Extracted Information", lines=3, interactive=False)
                
                async def process_order(email_body):
                    """Process a simulated order with automatic email extraction"""
                    import re
                    
                    # Extract sender email from the email body
                    # Look for patterns like "From: email@example.com" or just email addresses
                    from_pattern = r'[Ff]rom:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                    
                    from_match = re.search(from_pattern, email_body)
                    if from_match:
                        customer_email = from_match.group(1)
                    else:
                        # Try to find any email address in the content
                        email_match = re.search(email_pattern, email_body)
                        if email_match:
                            customer_email = email_match.group(1)
                        else:
                            customer_email = "unknown@example.com"
                    
                    # Extract subject if present
                    subject_pattern = r'[Ss]ubject:\s*(.+?)(?:\n|$)'
                    subject_match = re.search(subject_pattern, email_body)
                    subject = subject_match.group(1) if subject_match else "Order Request"
                    
                    # Clean the body (remove From:, Subject:, Date: lines if present)
                    clean_body = re.sub(r'^[Ff]rom:.*?\n', '', email_body, flags=re.MULTILINE)
                    clean_body = re.sub(r'^[Ss]ubject:.*?\n', '', clean_body, flags=re.MULTILINE)
                    clean_body = re.sub(r'^[Dd]ate:.*?\n', '', clean_body, flags=re.MULTILINE)
                    clean_body = clean_body.strip()
                    
                    # Create email data
                    email_data = {
                        "message_id": f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "from": customer_email,
                        "subject": subject,
                        "body": clean_body if clean_body else email_body,
                        "email_type": "order"
                    }
                    
                    # Process the email
                    result = await orchestrator.process_email(email_data)
                    
                    # Create extracted info summary
                    extracted = f"Customer: {customer_email}\nSubject: {subject}\nBody Length: {len(clean_body)} chars"
                    
                    return result, extracted
                
                process_btn.click(
                    fn=lambda body: asyncio.run(process_order(body)),
                    inputs=[email_input],
                    outputs=[processing_result, extracted_info]
                )
            
            # Human Review Tab
            with gr.TabItem("👤 Human Review"):
                review_interface.create_interface()
            
            # System Status Tab
            with gr.TabItem("📊 System Status"):
                gr.Markdown("### System Metrics")
                
                def get_status():
                    stats = human_manager.get_review_statistics()
                    return {
                        "orchestrator_running": orchestrator.is_running(),
                        "pending_reviews": stats['total_pending'],
                        "completed_reviews": stats['total_completed'],
                        "avg_review_time": f"{stats['average_review_time_seconds']:.1f}s",
                        "status_breakdown": stats['status_breakdown']
                    }
                
                status_display = gr.JSON(label="Current Status", value=get_status)
                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")
                
                refresh_btn.click(fn=get_status, outputs=[status_display])
    
    # Launch the app
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


def main():
    """Main entry point"""
    
    print_banner()
    
    # Check environment
    check_environment()
    
    print(f"\n📅 Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Start orchestrator in background thread
    orchestrator_thread = threading.Thread(
        target=lambda: asyncio.run(start_orchestrator()),
        daemon=True
    )
    orchestrator_thread.start()
    
    # Small delay to let orchestrator initialize
    import time
    time.sleep(2)
    
    print("\n🌐 Launching web interface...")
    print("   URL: http://localhost:7860")
    print("\n   Press Ctrl+C to stop\n")
    
    # Open browser automatically
    webbrowser.open("http://localhost:7860")
    
    # Start web interface (blocking)
    try:
        start_web_interface()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Factory Automation System")
        sys.exit(0)


if __name__ == "__main__":
    main()