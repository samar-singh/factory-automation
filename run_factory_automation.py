#!/usr/bin/env python3
"""
Main Runner for Factory Automation System
Run this to start the complete system with all features
"""

import asyncio
import os
import socket
import sys
import threading
import webbrowser
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def find_available_port(start_port=7860, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No available ports found in range {start_port}-{start_port + max_attempts}"
    )


# Global variable to store the selected port
SELECTED_PORT = find_available_port()

# Global orchestrator instance to be shared
SHARED_ORCHESTRATOR = None


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
    print(
        """
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
    """
    )


async def start_orchestrator():
    """Start the orchestrator with human interaction"""

    global SHARED_ORCHESTRATOR

    from factory_automation.factory_agents.orchestrator_with_human import (
        OrchestratorWithHuman,
    )
    from factory_automation.factory_database.vector_db import ChromaDBClient

    print("🚀 Starting orchestrator...")

    try:
        chromadb_client = ChromaDBClient()
        SHARED_ORCHESTRATOR = OrchestratorWithHuman(
            chromadb_client, use_mock_gmail=False
        )

        # Start monitoring
        await SHARED_ORCHESTRATOR.start_with_review_monitoring()
    except KeyboardInterrupt:
        print("\n⏹️  Stopping orchestrator...")
        if SHARED_ORCHESTRATOR:
            await SHARED_ORCHESTRATOR.stop()
    except Exception as e:
        print(f"❌ Orchestrator initialization error: {e}")
        import traceback

        traceback.print_exc()
        raise


def start_web_interface():
    """Start the Gradio web interface"""

    global SHARED_ORCHESTRATOR

    import gradio as gr

    from factory_automation.factory_ui.human_review_interface_improved import (
        HumanReviewInterface,
    )

    print("🌐 Starting web interface...")

    # Wait for orchestrator to be initialized
    import time

    while SHARED_ORCHESTRATOR is None:
        print("⏳ Waiting for orchestrator to initialize...")
        time.sleep(1)

    # Use the shared orchestrator
    orchestrator = SHARED_ORCHESTRATOR
    human_manager = orchestrator.human_manager

    # Create review interface
    review_interface = HumanReviewInterface(
        interaction_manager=human_manager, chromadb_client=orchestrator.chromadb_client
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
                            lines=10,
                        )
                        gr.Markdown(
                            "*Customer email will be extracted automatically from the 'From:' field*"
                        )
                        process_btn = gr.Button(
                            "📧 Process Order", variant="primary", size="lg"
                        )

                    with gr.Column():
                        processing_result = gr.JSON(label="Processing Result")
                        extracted_info = gr.Textbox(
                            label="Extracted Information", lines=3, interactive=False
                        )

                async def process_order(email_body):
                    """Process a simulated order with automatic email extraction"""
                    import re

                    # Extract sender email from the email body
                    # Look for patterns like "From: email@example.com" or just email addresses
                    from_pattern = (
                        r"[Ff]rom:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
                    )
                    email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"

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
                    subject_pattern = r"[Ss]ubject:\s*(.+?)(?:\n|$)"
                    subject_match = re.search(subject_pattern, email_body)
                    subject = (
                        subject_match.group(1) if subject_match else "Order Request"
                    )

                    # Clean the body (remove From:, Subject:, Date: lines if present)
                    clean_body = re.sub(
                        r"^[Ff]rom:.*?\n", "", email_body, flags=re.MULTILINE
                    )
                    clean_body = re.sub(
                        r"^[Ss]ubject:.*?\n", "", clean_body, flags=re.MULTILINE
                    )
                    clean_body = re.sub(
                        r"^[Dd]ate:.*?\n", "", clean_body, flags=re.MULTILINE
                    )
                    clean_body = clean_body.strip()

                    # Create email data
                    email_data = {
                        "message_id": f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "from": customer_email,
                        "subject": subject,
                        "body": clean_body if clean_body else email_body,
                        "email_type": "order",
                    }

                    # Process the email
                    result = await orchestrator.process_email(email_data)

                    # Create extracted info summary
                    extracted = f"Customer: {customer_email}\nSubject: {subject}\nBody Length: {len(clean_body)} chars"

                    return result, extracted

                process_btn.click(
                    fn=lambda body: asyncio.run(process_order(body)),
                    inputs=[email_input],
                    outputs=[processing_result, extracted_info],
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
                        "orchestrator_running": (
                            orchestrator.is_running()
                            if hasattr(orchestrator, "is_running")
                            else True
                        ),
                        "pending_reviews": stats["total_pending"],
                        "completed_reviews": stats["total_completed"],
                        "avg_review_time": f"{stats['average_review_time_seconds']:.1f}s",
                        "status_breakdown": stats["status_breakdown"],
                    }

                status_display = gr.JSON(label="Current Status", value=get_status)
                refresh_btn = gr.Button("🔄 Refresh", variant="secondary")

                refresh_btn.click(fn=get_status, outputs=[status_display])

    # Launch the app
    app.launch(
        server_name="127.0.0.1",  # Changed from 0.0.0.0 for Safari compatibility
        server_port=SELECTED_PORT,
        share=False,
        show_error=True,
        inbrowser=False,  # Don't auto-open browser from Gradio
    )


def main():
    """Main entry point"""

    print_banner()

    # Check environment
    check_environment()

    print(f"\n📅 Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Start orchestrator in background thread
    orchestrator_thread = threading.Thread(
        target=lambda: asyncio.run(start_orchestrator()), daemon=True
    )
    orchestrator_thread.start()

    # Wait for orchestrator to be initialized
    import time

    max_wait = 10  # seconds
    waited = 0
    while SHARED_ORCHESTRATOR is None and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5

    if SHARED_ORCHESTRATOR is None:
        print("❌ Orchestrator failed to initialize")
        sys.exit(1)

    print("\n🌐 Launching web interface...")
    print(f"   URL: http://127.0.0.1:{SELECTED_PORT}")
    if SELECTED_PORT != 7860:
        print(f"   (Port 7860 was busy, using {SELECTED_PORT} instead)")
    print("\n   Safari users: If page doesn't load, try:")
    print(f"   - http://127.0.0.1:{SELECTED_PORT}")
    print("   - Use Chrome or Firefox")
    print("\n   Press Ctrl+C to stop\n")

    # Open browser automatically with 127.0.0.1 for better compatibility
    webbrowser.open(f"http://127.0.0.1:{SELECTED_PORT}")

    # Start web interface (blocking)
    try:
        start_web_interface()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Factory Automation System")
        sys.exit(0)


if __name__ == "__main__":
    main()
