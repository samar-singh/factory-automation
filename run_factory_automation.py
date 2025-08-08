#!/usr/bin/env python3
"""
Main Runner for Factory Automation System
Run this to start the complete system with all features
"""

import asyncio
import logging
import os
import socket
import sys
import threading
import webbrowser
from datetime import datetime

from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

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
    from factory_automation.factory_ui.image_display_helper import (
        create_image_gallery_html,
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
                gr.Markdown("### AI-Powered Order Processing with Document Support")

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
                            lines=8,
                        )
                        
                        gr.Markdown("### 📎 Attach Documents (Optional)")
                        attached_files = gr.File(
                            label="Upload Documents (Excel, PDF, Images)",
                            file_types=[".xlsx", ".xls", ".pdf", ".png", ".jpg", ".jpeg"],
                            file_count="multiple",
                            type="filepath"
                        )
                        
                        gr.Markdown(
                            "*Customer email will be extracted automatically from the 'From:' field. Documents will be processed for additional order details.*"
                        )
                        process_btn = gr.Button(
                            "📧 Process Order with Documents", variant="primary", size="lg"
                        )

                    with gr.Column():
                        processing_result = gr.JSON(label="Processing Result")
                        extracted_info = gr.Textbox(
                            label="Extracted Information", lines=3, interactive=False
                        )
                        document_analysis = gr.Textbox(
                            label="Document Analysis", lines=5, interactive=False
                        )

                async def process_order_with_documents(email_body, files):
                    """Process a simulated order with automatic email extraction and document processing"""
                    import re
                    import pandas as pd
                    import PyPDF2
                    from PIL import Image
                    
                    # Debug logging for files parameter
                    logger.info(f"Files parameter type: {type(files)}")
                    logger.info(f"Files parameter value: {files}")
                    if files:
                        logger.info(f"Number of files: {len(files)}")
                        for i, f in enumerate(files):
                            logger.info(f"File {i}: type={type(f)}, value={f}")

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

                    # Process attached documents
                    document_content = []
                    document_summary = []
                    
                    if files:
                        for file_path in files:
                            try:
                                file_name = os.path.basename(file_path)
                                file_ext = os.path.splitext(file_name)[1].lower()
                                
                                if file_ext in ['.xlsx', '.xls']:
                                    # Process Excel file
                                    df = pd.read_excel(file_path)
                                    document_content.append(f"Excel file: {file_name}")
                                    document_content.append(f"Rows: {len(df)}, Columns: {len(df.columns)}")
                                    document_content.append(f"Columns: {', '.join(df.columns.tolist())}")
                                    # Extract first few rows as sample
                                    if len(df) > 0:
                                        sample = df.head(5).to_string()
                                        document_content.append(f"Sample data:\n{sample}")
                                    document_summary.append(f"📊 {file_name}: {len(df)} rows of data")
                                    
                                elif file_ext == '.pdf':
                                    # Process PDF file
                                    with open(file_path, 'rb') as pdf_file:
                                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                                        num_pages = len(pdf_reader.pages)
                                        document_content.append(f"PDF file: {file_name}")
                                        document_content.append(f"Pages: {num_pages}")
                                        # Extract text from first page
                                        if num_pages > 0:
                                            first_page_text = pdf_reader.pages[0].extract_text()[:500]
                                            document_content.append(f"First page text:\n{first_page_text}")
                                    document_summary.append(f"📄 {file_name}: {num_pages} pages")
                                    
                                elif file_ext in ['.png', '.jpg', '.jpeg']:
                                    # Process image file
                                    img = Image.open(file_path)
                                    document_content.append(f"Image file: {file_name}")
                                    document_content.append(f"Size: {img.width}x{img.height}")
                                    document_content.append(f"Format: {img.format}")
                                    document_summary.append(f"🖼️ {file_name}: {img.width}x{img.height} image")
                                    
                            except Exception as e:
                                document_content.append(f"Error processing {file_name}: {str(e)}")
                                document_summary.append(f"❌ {file_name}: Processing error")

                    # Prepare attachments - just pass file paths
                    attachment_list = []
                    if files:
                        for file_path in files:
                            try:
                                # Check if file_path is valid
                                if not file_path:
                                    logger.warning("Empty file path in files list")
                                    continue
                                    
                                file_name = os.path.basename(file_path)
                                file_ext = os.path.splitext(file_name)[1].lower()
                                
                                # Verify file exists
                                if not os.path.exists(file_path):
                                    logger.error(f"File does not exist: {file_path}")
                                    continue
                                
                                # Get absolute path
                                abs_file_path = os.path.abspath(file_path)
                                logger.info(f"Processing attachment: {file_name} at {abs_file_path}")
                                
                                # Determine MIME type
                                mime_type = 'application/octet-stream'
                                if file_ext in ['.xlsx', '.xls']:
                                    mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                                elif file_ext == '.pdf':
                                    mime_type = 'application/pdf'
                                elif file_ext in ['.png']:
                                    mime_type = 'image/png'
                                elif file_ext in ['.jpg', '.jpeg']:
                                    mime_type = 'image/jpeg'
                                
                                # Pass the absolute file path
                                attachment_list.append({
                                    'filename': file_name,
                                    'filepath': abs_file_path,  # Pass the absolute file path
                                    'mime_type': mime_type
                                })
                                logger.info(f"Added attachment: {file_name} with path: {abs_file_path}")
                            except Exception as e:
                                logger.error(f"Error processing attachment: {e}", exc_info=True)
                    
                    # Create email data with proper attachment structure
                    email_data = {
                        "message_id": f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "from": customer_email,
                        "subject": subject,
                        "body": clean_body if clean_body else email_body,
                        "email_type": "order",
                        "attachments": attachment_list  # Pass actual attachment data
                    }

                    # Process the email
                    result = await orchestrator.process_email(email_data)

                    # Create extracted info summary
                    extracted = f"Customer: {customer_email}\nSubject: {subject}\nBody Length: {len(clean_body)} chars"
                    if document_summary:
                        extracted += f"\nAttachments: {len(document_summary)} files"
                    
                    # Create document analysis summary
                    doc_analysis = "\n".join(document_summary) if document_summary else "No documents attached"

                    return result, extracted, doc_analysis

                process_btn.click(
                    fn=lambda body, files: asyncio.run(process_order_with_documents(body, files)),
                    inputs=[email_input, attached_files],
                    outputs=[processing_result, extracted_info, document_analysis],
                )

            # Human Review Tab
            with gr.TabItem("👤 Human Review"):
                review_interface.create_interface()

            # Inventory Search Tab
            with gr.TabItem("🔍 Inventory Search"):
                gr.Markdown("### Search Inventory with Images")
                
                with gr.Row():
                    with gr.Column():
                        search_query = gr.Textbox(
                            label="Search Query",
                            placeholder="e.g., Peter England blue shirt, Allen Solly tag",
                            lines=1
                        )
                        search_btn = gr.Button("🔍 Search", variant="primary")
                        
                        # Advanced options
                        with gr.Accordion("Advanced Options", open=False):
                            n_results = gr.Slider(
                                label="Number of Results",
                                minimum=1,
                                maximum=20,
                                value=5,
                                step=1
                            )
                            show_images = gr.Checkbox(
                                label="Show Product Images",
                                value=True
                            )
                    
                    with gr.Column():
                        search_results_text = gr.JSON(label="Search Results")
                        search_images_html = gr.HTML(label="Product Images")
                
                def search_inventory(query, num_results, display_images):
                    """Search inventory with image enrichment"""
                    from factory_automation.factory_rag.enhanced_search import EnhancedRAGSearch
                    
                    try:
                        # Use the orchestrator's ChromaDB client
                        search_engine = EnhancedRAGSearch(
                            chromadb_client=orchestrator.chromadb_client,
                            enable_reranking=True,
                            enable_image_search=display_images
                        )
                        
                        # Perform search
                        results, stats = search_engine.search(
                            query=query,
                            n_results=num_results
                        )
                        
                        # Format results for display
                        formatted_results = []
                        for result in results:
                            metadata = result.get("metadata", {})
                            formatted = {
                                "name": metadata.get("item_name", "Unknown"),
                                "code": metadata.get("item_code", "N/A"),
                                "brand": metadata.get("brand", "Unknown"),
                                "confidence": f"{result.get('confidence_percentage', 0)}%",
                                "has_image": result.get("image_data") is not None
                            }
                            formatted_results.append(formatted)
                        
                        # Create image gallery if enabled
                        images_html = ""
                        if display_images:
                            images_html = create_image_gallery_html(results, max_items=num_results)
                        
                        return formatted_results, images_html
                        
                    except Exception as e:
                        return [{"error": str(e)}], "<p>Error performing search</p>"
                
                search_btn.click(
                    fn=search_inventory,
                    inputs=[search_query, n_results, show_images],
                    outputs=[search_results_text, search_images_html]
                )
            
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
