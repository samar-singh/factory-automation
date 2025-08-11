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
                            file_types=[
                                ".xlsx",
                                ".xls",
                                ".pdf",
                                ".png",
                                ".jpg",
                                ".jpeg",
                            ],
                            file_count="multiple",
                            type="filepath",
                        )

                        gr.Markdown(
                            "*Customer email will be extracted automatically from the 'From:' field. Documents will be processed for additional order details.*"
                        )
                        process_btn = gr.Button(
                            "📧 Process Order with Documents",
                            variant="primary",
                            size="lg",
                        )

                    with gr.Column():
                        processing_result = gr.JSON(label="Processing Result")
                        extracted_info = gr.Textbox(
                            label="Extracted Information", lines=3, interactive=False
                        )
                        document_analysis = gr.Textbox(
                            label="Document Analysis", lines=5, interactive=False
                        )

                # Image matching results display
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🖼️ Visual Matching Results")
                        image_match_summary = gr.Textbox(
                            label="Image Match Summary", lines=3, interactive=False
                        )
                        image_matches_display = gr.Gallery(
                            label="All Matching Inventory Images",
                            show_label=True,
                            elem_id="gallery",
                            columns=4,
                            rows=5,
                            object_fit="contain",
                            height="auto",
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

                                if file_ext in [".xlsx", ".xls"]:
                                    # Process Excel file
                                    df = pd.read_excel(file_path)
                                    document_content.append(f"Excel file: {file_name}")
                                    document_content.append(
                                        f"Rows: {len(df)}, Columns: {len(df.columns)}"
                                    )
                                    document_content.append(
                                        f"Columns: {', '.join(df.columns.tolist())}"
                                    )
                                    # Extract first few rows as sample
                                    if len(df) > 0:
                                        sample = df.head(5).to_string()
                                        document_content.append(
                                            f"Sample data:\n{sample}"
                                        )
                                    document_summary.append(
                                        f"📊 {file_name}: {len(df)} rows of data"
                                    )

                                elif file_ext == ".pdf":
                                    # Process PDF file
                                    with open(file_path, "rb") as pdf_file:
                                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                                        num_pages = len(pdf_reader.pages)
                                        document_content.append(
                                            f"PDF file: {file_name}"
                                        )
                                        document_content.append(f"Pages: {num_pages}")
                                        # Extract text from first page
                                        if num_pages > 0:
                                            first_page_text = pdf_reader.pages[
                                                0
                                            ].extract_text()[:500]
                                            document_content.append(
                                                f"First page text:\n{first_page_text}"
                                            )
                                    document_summary.append(
                                        f"📄 {file_name}: {num_pages} pages"
                                    )

                                elif file_ext in [".png", ".jpg", ".jpeg"]:
                                    # Process image file
                                    img = Image.open(file_path)
                                    document_content.append(f"Image file: {file_name}")
                                    document_content.append(
                                        f"Size: {img.width}x{img.height}"
                                    )
                                    document_content.append(f"Format: {img.format}")
                                    document_summary.append(
                                        f"🖼️ {file_name}: {img.width}x{img.height} image"
                                    )

                            except Exception as e:
                                document_content.append(
                                    f"Error processing {file_name}: {str(e)}"
                                )
                                document_summary.append(
                                    f"❌ {file_name}: Processing error"
                                )

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
                                logger.info(
                                    f"Processing attachment: {file_name} at {abs_file_path}"
                                )

                                # Determine MIME type
                                mime_type = "application/octet-stream"
                                if file_ext in [".xlsx", ".xls"]:
                                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                elif file_ext == ".pdf":
                                    mime_type = "application/pdf"
                                elif file_ext in [".png"]:
                                    mime_type = "image/png"
                                elif file_ext in [".jpg", ".jpeg"]:
                                    mime_type = "image/jpeg"

                                # Pass the absolute file path
                                attachment_list.append(
                                    {
                                        "filename": file_name,
                                        "filepath": abs_file_path,  # Pass the absolute file path
                                        "mime_type": mime_type,
                                    }
                                )
                                logger.info(
                                    f"Added attachment: {file_name} with path: {abs_file_path}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error processing attachment: {e}", exc_info=True
                                )

                    # Create email data with proper attachment structure
                    email_data = {
                        "message_id": f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "from": customer_email,
                        "subject": subject,
                        "body": clean_body if clean_body else email_body,
                        "email_type": "order",
                        "attachments": attachment_list,  # Pass actual attachment data
                    }

                    # Process the email
                    result = await orchestrator.process_email(email_data)

                    # Create extracted info summary
                    extracted = f"Customer: {customer_email}\nSubject: {subject}\nBody Length: {len(clean_body)} chars"
                    if document_summary:
                        extracted += f"\nAttachments: {len(document_summary)} files"

                    # Create document analysis summary
                    doc_analysis = (
                        "\n".join(document_summary)
                        if document_summary
                        else "No documents attached"
                    )

                    # Process image matches if available
                    image_summary = "No image matching performed"
                    image_gallery = []

                    # Check both direct image_matches and nested order_result
                    image_match_count = 0
                    image_matches_list = []

                    if isinstance(result, dict):
                        logger.info(f"Result keys: {list(result.keys())}")

                        # First, always check for image_matches list at top level
                        if "image_matches" in result:
                            if isinstance(result["image_matches"], list):
                                image_matches_list = result["image_matches"]
                                image_match_count = len(image_matches_list)
                                logger.info(
                                    f"Found {image_match_count} image matches LIST in result['image_matches']"
                                )
                            else:
                                logger.info(
                                    f"result['image_matches'] is not a list: {type(result['image_matches'])}"
                                )

                        # Also check order_result for count (usually just a number)
                        if "order_result" in result and result["order_result"]:
                            logger.info(
                                f"Order result keys: {list(result['order_result'].keys())}"
                            )
                            if "image_matches" in result["order_result"]:
                                if isinstance(
                                    result["order_result"]["image_matches"], list
                                ):
                                    # If it's a list here and we don't have one at top level, use it
                                    if not image_matches_list:
                                        image_matches_list = result["order_result"][
                                            "image_matches"
                                        ]
                                        image_match_count = len(image_matches_list)
                                        logger.info(
                                            f"Found {image_match_count} image matches in result['order_result']['image_matches']"
                                        )
                                else:
                                    # It's a number, use it for count if we don't have a list
                                    if not image_matches_list:
                                        image_match_count = result["order_result"].get(
                                            "image_matches", 0
                                        )
                                        logger.info(
                                            f"Order result image_matches is a number: {image_match_count}"
                                        )

                    if image_match_count > 0:
                        # Extract items with image matches
                        items_with_images = []
                        if "order_result" in result and result["order_result"]:
                            items_with_images = result["order_result"].get("items", [])
                        elif "items" in result:
                            items_with_images = result.get("items", [])

                        # Create summary based on image match count
                        image_summary = f"Found {image_match_count} visual matches\n"

                        # Look for best image match in items
                        best_image_conf = 0
                        best_image_code = "Unknown"
                        for item in items_with_images:
                            if "best_image_match" in item and item["best_image_match"]:
                                conf = item["best_image_match"].get("confidence", 0)
                                if conf > best_image_conf:
                                    best_image_conf = conf
                                    best_image_code = item["best_image_match"].get(
                                        "tag_code", "Unknown"
                                    )

                        if best_image_conf > 0:
                            image_summary += f"Best match: {best_image_code} "
                            image_summary += f"(Confidence: {best_image_conf:.1%})\n"

                        # Determine recommendation based on confidence
                        if best_image_conf > 0.85:
                            image_summary += (
                                "✅ Strong visual match - recommend approval"
                            )
                        elif best_image_conf > 0.70:
                            image_summary += "⚠️ Good match - review details"
                        else:
                            image_summary += "❌ Weak match - request better image"

                        # Create image gallery from matches
                        if image_matches_list:
                            logger.info(
                                f"Creating image gallery from {len(image_matches_list)} matches"
                            )

                            # Deduplicate matches by tag_code AND image_path before displaying
                            seen_identifiers = set()
                            unique_matches = []

                            for match in image_matches_list:
                                tag_code = match.get("tag_code", "")
                                image_path = match.get("image_path", "")

                                # Create a unique identifier from tag_code and image_path
                                # This ensures we only show each unique tag once
                                if tag_code:
                                    identifier = (
                                        tag_code  # Use tag_code as primary identifier
                                    )
                                elif image_path:
                                    identifier = image_path  # Fallback to image_path
                                else:
                                    # No reliable identifier, skip this match
                                    logger.debug(
                                        f"Skipping match with no tag_code or image_path: {match}"
                                    )
                                    continue

                                if identifier not in seen_identifiers:
                                    unique_matches.append(match)
                                    seen_identifiers.add(identifier)
                                else:
                                    logger.debug(
                                        f"Filtering duplicate match with identifier: {identifier}"
                                    )

                            # Sort unique matches by similarity
                            all_matches = sorted(
                                unique_matches,
                                key=lambda x: x.get(
                                    "similarity_score", x.get("confidence", 0)
                                ),
                                reverse=True,
                            )

                            logger.info(
                                f"Displaying {len(all_matches)} unique matches (deduplicated from {len(image_matches_list)} total)"
                            )

                            # Log deduplication results for transparency
                            if len(image_matches_list) > len(all_matches):
                                logger.info(
                                    f"✅ Removed {len(image_matches_list) - len(all_matches)} duplicate matches"
                                )

                            # Generate image gallery
                            for match in all_matches:
                                # Try to get image from ChromaDB
                                try:
                                    # Get the image from tag_images_full collection
                                    images_collection = orchestrator.chromadb_client.client.get_collection(
                                        "tag_images_full"
                                    )

                                    # The match should have an image_path or we need to search by tag_code
                                    tag_code = match.get("tag_code", "")

                                    # First try to get by the image_path if available
                                    if "image_path" in match and match["image_path"]:
                                        # Extract ID from image_path (e.g., "inventory/ALLEN SOLLY (AS)_row8_img_1c2b149a.png")
                                        image_id = (
                                            match["image_path"]
                                            .replace("inventory/", "")
                                            .replace(".png", "")
                                        )
                                        results = images_collection.get(
                                            ids=[image_id], include=["metadatas"]
                                        )
                                    elif tag_code:
                                        # Search for images with this tag code
                                        results = images_collection.get(
                                            where={"item_code": tag_code},
                                            limit=1,
                                            include=["metadatas"],
                                        )
                                    else:
                                        results = {"ids": []}

                                    if results["ids"]:
                                        metadata = results["metadatas"][0]
                                        if "image_base64" in metadata:
                                            # Convert base64 to PIL Image for display
                                            import base64
                                            from io import BytesIO
                                            from PIL import Image

                                            image_data = base64.b64decode(
                                                metadata["image_base64"]
                                            )
                                            img = Image.open(BytesIO(image_data))

                                            # Create detailed caption with all available info
                                            tag_code = match.get("tag_code", "Unknown")
                                            brand = match.get("brand", "Unknown")
                                            similarity = match.get(
                                                "similarity_score", 0
                                            )

                                            # Get additional metadata from the match
                                            item_name = metadata.get("item_name", "")
                                            tag_name = metadata.get("tag_name", "")
                                            tag_type = match.get(
                                                "tag_type", metadata.get("tag_type", "")
                                            )

                                            # Build comprehensive caption
                                            caption_parts = []
                                            if tag_code and tag_code != "Unknown":
                                                caption_parts.append(
                                                    f"Code: {tag_code}"
                                                )
                                            # Prefer tag_name over item_name for better descriptions
                                            if tag_name:
                                                caption_parts.append(
                                                    f"Name: {tag_name}"
                                                )
                                            elif item_name:
                                                caption_parts.append(
                                                    f"Name: {item_name}"
                                                )
                                            if brand and brand != "Unknown":
                                                caption_parts.append(f"Brand: {brand}")
                                            if tag_type:
                                                caption_parts.append(
                                                    f"Type: {tag_type}"
                                                )
                                            caption_parts.append(
                                                f"Match: {similarity:.1%}"
                                            )

                                            caption = " | ".join(caption_parts)
                                            image_gallery.append((img, caption))
                                            logger.info(
                                                f"Added image to gallery: {caption}"
                                            )
                                    else:
                                        logger.debug(
                                            f"No image found for tag_code={tag_code}"
                                        )
                                except Exception as e:
                                    logger.error(
                                        f"Could not load image for {match.get('tag_code')}: {e}",
                                        exc_info=True,
                                    )

                            # Update summary with actual gallery count
                            if image_gallery:
                                image_summary += f"\n📸 Displaying {len(image_gallery)} matching images below"
                            else:
                                image_summary += f"\n📊 {image_match_count} images were compared with inventory"
                    else:
                        image_summary = (
                            "No image matching performed (no images in attachments)"
                        )

                    return result, extracted, doc_analysis, image_summary, image_gallery

                process_btn.click(
                    fn=lambda body, files: asyncio.run(
                        process_order_with_documents(body, files)
                    ),
                    inputs=[email_input, attached_files],
                    outputs=[
                        processing_result,
                        extracted_info,
                        document_analysis,
                        image_match_summary,
                        image_matches_display,
                    ],
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
                            lines=1,
                        )
                        search_btn = gr.Button("🔍 Search", variant="primary")

                        # Advanced options
                        with gr.Accordion("Advanced Options", open=False):
                            n_results = gr.Slider(
                                label="Number of Results",
                                minimum=1,
                                maximum=20,
                                value=5,
                                step=1,
                            )
                            show_images = gr.Checkbox(
                                label="Show Product Images", value=True
                            )

                    with gr.Column():
                        search_results_text = gr.JSON(label="Search Results")
                        search_images_html = gr.HTML(label="Product Images")

                def search_inventory(query, num_results, display_images):
                    """Search inventory with image enrichment"""
                    from factory_automation.factory_rag.enhanced_search import (
                        EnhancedRAGSearch,
                    )

                    try:
                        # Use the orchestrator's ChromaDB client
                        search_engine = EnhancedRAGSearch(
                            chromadb_client=orchestrator.chromadb_client,
                            enable_reranking=True,
                            enable_image_search=display_images,
                        )

                        # Perform search
                        results, stats = search_engine.search(
                            query=query, n_results=num_results
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
                                "has_image": result.get("image_data") is not None,
                            }
                            formatted_results.append(formatted)

                        # Create image gallery if enabled
                        images_html = ""
                        if display_images:
                            images_html = create_image_gallery_html(
                                results, max_items=num_results
                            )

                        return formatted_results, images_html

                    except Exception as e:
                        return [{"error": str(e)}], "<p>Error performing search</p>"

                search_btn.click(
                    fn=search_inventory,
                    inputs=[search_query, n_results, show_images],
                    outputs=[search_results_text, search_images_html],
                )

            # Data Ingestion Tab
            with gr.TabItem("📁 Data Ingestion"):
                gr.Markdown("### Upload Files for Ingestion")
                gr.Markdown(
                    """
                Upload files to add to the inventory database:
                - **Excel (.xlsx, .xls)**: Product inventory with images
                - **PDF**: Product catalogs and documentation
                - **Word (.doc, .docx)**: Product descriptions
                - **Images (.png, .jpg, .jpeg)**: Standalone product tags
                """
                )

                with gr.Row():
                    with gr.Column():
                        upload_files = gr.File(
                            label="Select Files to Ingest",
                            file_types=[
                                ".xlsx",
                                ".xls",
                                ".pdf",
                                ".doc",
                                ".docx",
                                ".png",
                                ".jpg",
                                ".jpeg",
                            ],
                            file_count="multiple",
                            type="filepath",
                        )

                        # Optional metadata
                        with gr.Accordion(
                            "Additional Information (Optional)", open=False
                        ):
                            brand_input = gr.Textbox(
                                label="Brand Name",
                                placeholder="e.g., Allen Solly, Peter England",
                                lines=1,
                            )
                            category_input = gr.Textbox(
                                label="Category",
                                placeholder="e.g., Shirts, Trousers, Accessories",
                                lines=1,
                            )
                            notes_input = gr.Textbox(
                                label="Notes",
                                placeholder="Any additional information about these files",
                                lines=2,
                            )

                        ingest_btn = gr.Button(
                            "📥 Ingest Files", variant="primary", size="lg"
                        )

                    with gr.Column():
                        ingestion_status = gr.Textbox(
                            label="Ingestion Status", lines=10, interactive=False
                        )
                        ingestion_results = gr.JSON(label="Detailed Results")

                async def ingest_uploaded_files(files, brand, category, notes):
                    """Process uploaded files for ingestion"""
                    from factory_automation.factory_rag.multi_format_ingestion import (
                        MultiFormatIngestion,
                    )

                    if not files:
                        return "❌ No files selected", {}

                    status_messages = []
                    all_results = []

                    try:
                        # Initialize ingestion system
                        status_messages.append("🚀 Initializing ingestion system...")
                        ingestion_system = MultiFormatIngestion(
                            chromadb_client=orchestrator.chromadb_client,
                            embedding_model="stella-400m",
                            use_vision_model=True,  # Enable vision for image analysis
                            use_clip_embeddings=True,
                        )

                        # Prepare metadata
                        metadata = {}
                        if brand:
                            metadata["brand"] = brand
                        if category:
                            metadata["category"] = category
                        if notes:
                            metadata["notes"] = notes

                        # Process each file
                        for file_path in files:
                            file_name = os.path.basename(file_path)
                            status_messages.append(f"\n📄 Processing: {file_name}")

                            # Ingest file
                            result = ingestion_system.ingest_file(file_path, metadata)
                            all_results.append(result)

                            # Update status based on result
                            if result["status"] == "success":
                                if "chunks_created" in result:
                                    status_messages.append(
                                        f"   ✅ Created {result['chunks_created']} chunks"
                                    )
                                elif "items_ingested" in result:
                                    status_messages.append(
                                        f"   ✅ Ingested {result['items_ingested']} items"
                                    )
                                elif "image_id" in result:
                                    status_messages.append(
                                        f"   ✅ Image stored: {result.get('brand_detected', 'Unknown brand')}"
                                    )
                                else:
                                    status_messages.append(
                                        "   ✅ Successfully processed"
                                    )
                            else:
                                status_messages.append(
                                    f"   ❌ Error: {result.get('error', 'Unknown error')}"
                                )

                        # Summary
                        successful = sum(
                            1 for r in all_results if r["status"] == "success"
                        )
                        status_messages.append("\n📊 Summary:")
                        status_messages.append(f"   - Files processed: {len(files)}")
                        status_messages.append(f"   - Successful: {successful}")
                        status_messages.append(
                            f"   - Failed: {len(files) - successful}"
                        )

                        status_messages.append("\n✨ Ingestion complete!")
                        status_messages.append(
                            "   Data is now available for search and processing."
                        )

                    except Exception as e:
                        status_messages.append(f"\n❌ Error during ingestion: {str(e)}")
                        logger.error(f"Ingestion error: {e}", exc_info=True)

                    return "\n".join(status_messages), {"results": all_results}

                ingest_btn.click(
                    fn=lambda files, brand, cat, notes: asyncio.run(
                        ingest_uploaded_files(files, brand, cat, notes)
                    ),
                    inputs=[upload_files, brand_input, category_input, notes_input],
                    outputs=[ingestion_status, ingestion_results],
                )

            # Database Management Tab
            with gr.TabItem("🗄️ Database Management"):
                gr.Markdown("### Duplicate Detection and Removal")
                gr.Markdown(
                    """
                Manage duplicates in the inventory database:
                - **Exact Duplicates**: Same content and metadata
                - **Near Duplicates**: >95% similarity in embeddings
                - **Semantic Duplicates**: Same item with different descriptions
                """
                )

                with gr.Row():
                    with gr.Column():
                        # Deduplication controls
                        gr.Markdown("#### Deduplication Settings")

                        dedup_strategy = gr.Radio(
                            label="Detection Strategy",
                            choices=["exact", "near", "semantic"],
                            value="exact",
                            info="How to identify duplicates",
                        )

                        keep_strategy = gr.Radio(
                            label="Keep Strategy",
                            choices=["first", "last", "best"],
                            value="best",
                            info="Which duplicate to keep (best = most complete metadata)",
                        )

                        dry_run = gr.Checkbox(
                            label="Dry Run (Preview only, don't delete)",
                            value=True,
                            info="Check this to see what would be deleted without actually removing",
                        )

                        with gr.Row():
                            check_duplicates_btn = gr.Button(
                                "🔍 Check Duplicates", variant="secondary"
                            )
                            remove_duplicates_btn = gr.Button(
                                "🗑️ Remove Duplicates", variant="primary"
                            )

                    with gr.Column():
                        # Results display
                        dedup_status = gr.Textbox(
                            label="Status", lines=10, interactive=False
                        )
                        dedup_results = gr.JSON(label="Detailed Results")

                # Statistics section
                gr.Markdown("#### Database Statistics")
                with gr.Row():
                    refresh_stats_btn = gr.Button(
                        "📊 Refresh Statistics", variant="secondary"
                    )

                db_stats = gr.JSON(label="Database Statistics")

                async def check_duplicates(strategy):
                    """Check for duplicates in the database"""
                    from factory_automation.factory_rag.deduplication_manager import (
                        DeduplicationManager,
                    )

                    try:
                        dedup_manager = DeduplicationManager(
                            orchestrator.chromadb_client
                        )
                        stats = dedup_manager.get_deduplication_stats()

                        status_lines = ["📊 Duplicate Analysis Results:\n"]

                        for collection, col_stats in stats.get(
                            "collections", {}
                        ).items():
                            status_lines.append(f"\n{collection}:")
                            status_lines.append(
                                f"  Total items: {col_stats['total_items']}"
                            )
                            status_lines.append(
                                f"  Exact duplicates: {col_stats['exact_duplicates']}"
                            )
                            status_lines.append(
                                f"  Near duplicates: {col_stats['near_duplicates']}"
                            )
                            status_lines.append(
                                f"  Duplicate %: {col_stats['duplicate_percentage']:.1f}%"
                            )

                        status_lines.append("\n📈 Overall Statistics:")
                        status_lines.append(f"  Total items: {stats['total_items']}")
                        status_lines.append(
                            f"  Total exact duplicates: {stats['total_exact_duplicates']}"
                        )
                        status_lines.append(
                            f"  Overall duplicate %: {stats['overall_duplicate_percentage']:.1f}%"
                        )

                        return "\n".join(status_lines), stats

                    except Exception as e:
                        return f"❌ Error checking duplicates: {str(e)}", {}

                async def remove_duplicates(strategy, keep, is_dry_run):
                    """Remove duplicates from the database"""
                    from factory_automation.factory_rag.deduplication_manager import (
                        DeduplicationManager,
                    )

                    try:
                        dedup_manager = DeduplicationManager(
                            orchestrator.chromadb_client
                        )

                        status_lines = []
                        if is_dry_run:
                            status_lines.append(
                                "🔍 DRY RUN MODE - No data will be deleted\n"
                            )
                        else:
                            status_lines.append(
                                "⚠️ REMOVING DUPLICATES - This action cannot be undone!\n"
                            )

                        # Process all collections
                        results = dedup_manager.deduplicate_all_collections(
                            strategy=strategy, keep=keep, dry_run=is_dry_run
                        )

                        # Format results
                        for collection, result in results.get("details", {}).items():
                            status_lines.append(f"\n{collection}:")
                            if result["status"] == "success":
                                if is_dry_run:
                                    status_lines.append(
                                        f"  Would remove: {result.get('would_remove', 0)} items"
                                    )
                                else:
                                    status_lines.append(
                                        f"  Removed: {result.get('removed', 0)} items"
                                    )
                            else:
                                status_lines.append(
                                    f"  Status: {result.get('message', 'No action needed')}"
                                )

                        # Summary
                        total = results.get("total_removed", 0)
                        if is_dry_run:
                            status_lines.append(
                                f"\n✅ Dry run complete. Would remove {total} duplicates total."
                            )
                        else:
                            status_lines.append(
                                f"\n✅ Deduplication complete. Removed {total} duplicates."
                            )

                        return "\n".join(status_lines), results

                    except Exception as e:
                        return f"❌ Error removing duplicates: {str(e)}", {}

                async def get_db_stats():
                    """Get database statistics"""
                    from factory_automation.factory_rag.deduplication_manager import (
                        DeduplicationManager,
                    )

                    try:
                        dedup_manager = DeduplicationManager(
                            orchestrator.chromadb_client
                        )
                        return dedup_manager.get_deduplication_stats()
                    except Exception as e:
                        return {"error": str(e)}

                # Wire up buttons
                check_duplicates_btn.click(
                    fn=lambda s: asyncio.run(check_duplicates(s)),
                    inputs=[dedup_strategy],
                    outputs=[dedup_status, dedup_results],
                )

                remove_duplicates_btn.click(
                    fn=lambda s, k, d: asyncio.run(remove_duplicates(s, k, d)),
                    inputs=[dedup_strategy, keep_strategy, dry_run],
                    outputs=[dedup_status, dedup_results],
                )

                refresh_stats_btn.click(
                    fn=lambda: asyncio.run(get_db_stats()), outputs=[db_stats]
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
