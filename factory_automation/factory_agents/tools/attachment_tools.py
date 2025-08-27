"""Attachment processing tools for orchestrators"""

import base64
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from agents import function_tool

logger = logging.getLogger(__name__)


class AttachmentTools:
    """Attachment extraction and processing tools"""
    
    def __init__(self, image_processor=None, mode="execute"):
        """
        Initialize attachment tools
        
        Args:
            image_processor: ImageProcessorAgent instance (optional)
            mode: "execute" for v3, "propose" for v4
        """
        self.image_processor = image_processor
        self.mode = mode
    
    def create_tools(self):
        """Create and return attachment-related tools"""
        tools = []
        
        # Extract Excel data tool
        @function_tool(
            name_override="extract_excel_data",
            description_override="Extract order data from Excel file attachment" if self.mode == "execute" else "Analyze Excel attachment for proposal",
        )
        async def extract_excel_data(filename: str, content: Optional[str] = None) -> str:
            """Extract and parse data from Excel attachment"""
            try:
                if self.mode == "execute":
                    # V3: Actually extract data
                    import pandas as pd
                    
                    # Check if filename is a path that exists
                    if content is None and Path(filename).exists():
                        # Read directly from file path
                        logger.info(f"Reading Excel directly from path: {filename}")
                        df = pd.read_excel(filename)
                        tmp_path = None  # No temp file to clean up
                    elif content:
                        # Decode base64 content if provided
                        if isinstance(content, str):
                            content_bytes = base64.b64decode(content)
                        else:
                            content_bytes = content
                        
                        # Save temporarily and read with pandas
                        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                            tmp_file.write(content_bytes)
                        tmp_path = tmp_file.name
                        
                        # Read Excel file from temp path
                        df = pd.read_excel(tmp_path)
                    else:
                        return json.dumps({
                            "error": "No valid file path or content provided for Excel extraction"
                        })
                    
                    # Extract relevant data
                    extracted_data = {
                        "filename": filename,
                        "rows": len(df),
                        "columns": list(df.columns),
                        "sample_data": df.head(10).to_dict(orient="records"),
                        "summary": f"Excel file with {len(df)} rows and {len(df.columns)} columns",
                    }
                    
                    # Clean up temp file if we created one
                    if tmp_path:
                        Path(tmp_path).unlink()
                    
                    logger.info(f"Extracted data from Excel: {filename}")
                    return json.dumps(extracted_data, indent=2)
                else:
                    # V4: Propose extraction
                    return json.dumps({
                        "proposal": "excel_extraction",
                        "filename": filename,
                        "analysis": {
                            "type": "spreadsheet",
                            "likely_content": "order data",
                            "confidence": 0.9
                        },
                        "proposed_actions": [
                            "Extract tabular data",
                            "Parse order items",
                            "Validate quantities and prices",
                            "Map to inventory items"
                        ]
                    })
                    
            except Exception as e:
                logger.error(f"Error extracting Excel data: {e}")
                return json.dumps({"error": str(e), "filename": filename})
        
        tools.append(extract_excel_data)
        
        # Extract PDF data tool
        @function_tool(
            name_override="extract_pdf_data",
            description_override="Extract text content from PDF attachment" if self.mode == "execute" else "Analyze PDF attachment for proposal",
        )
        async def extract_pdf_data(filename: str, content: Optional[str] = None) -> str:
            """Extract text from PDF attachment
            
            Args:
                filename: Path to the PDF file or filename
                content: Optional base64 encoded content (if not provided, will read from filename path)
            """
            try:
                if self.mode == "execute":
                    # V3: Actually extract text
                    import PyPDF2
                    
                    # Check if filename is a path that exists
                    if content is None and Path(filename).exists():
                        # Read directly from file path
                        tmp_path = filename
                        cleanup_needed = False
                        logger.info(f"Reading PDF directly from path: {filename}")
                    else:
                        # Use base64 content
                        if content is None:
                            return json.dumps({
                                "error": f"File not found and no content provided: {filename}",
                                "status": "failed"
                            })
                        
                        # Decode base64 content if needed
                        if isinstance(content, str):
                            content_bytes = base64.b64decode(content)
                        else:
                            content_bytes = content
                        
                        # Save temporarily
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                            tmp_file.write(content_bytes)
                            tmp_path = tmp_file.name
                        cleanup_needed = True
                    
                    # Read PDF
                    with open(tmp_path, "rb") as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        num_pages = len(pdf_reader.pages)
                        
                        # Extract text from all pages
                        extracted_text = []
                        for page_num in range(min(num_pages, 10)):  # Limit to first 10 pages
                            page = pdf_reader.pages[page_num]
                            text = page.extract_text()
                            if text:
                                extracted_text.append(f"Page {page_num + 1}:\n{text}")
                    
                    # Clean up if needed
                    if cleanup_needed:
                        Path(tmp_path).unlink()
                    
                    result = {
                        "filename": filename,
                        "pages": num_pages,
                        "extracted_text": "\n\n".join(extracted_text),
                        "summary": f"PDF with {num_pages} pages",
                    }
                    
                    logger.info(f"Extracted text from PDF: {filename}")
                    return json.dumps(result, indent=2)
                else:
                    # V4: Propose extraction
                    return json.dumps({
                        "proposal": "pdf_extraction",
                        "filename": filename,
                        "analysis": {
                            "type": "document",
                            "likely_content": "order documentation",
                            "confidence": 0.8
                        },
                        "proposed_actions": [
                            "Extract text content",
                            "Parse order details",
                            "Extract customer information",
                            "Identify special requirements"
                        ]
                    })
                    
            except Exception as e:
                logger.error(f"Error extracting PDF data: {e}")
                return json.dumps({"error": str(e), "filename": filename})
        
        tools.append(extract_pdf_data)
        
        # Process image tool
        @function_tool(
            name_override="process_tag_image",
            description_override="Process tag image with Qwen2.5VL and store in ChromaDB" if self.mode == "execute" else "Analyze image for visual matching proposal",
        )
        async def process_tag_image(
            image_path: str, order_id: str, customer_name: str
        ) -> str:
            """Process and analyze tag image"""
            try:
                if self.mode == "execute" and self.image_processor:
                    # V3: Actually process image
                    result = await self.image_processor.process_and_store_image(
                        image_path=image_path,
                        order_id=order_id,
                        customer_name=customer_name,
                    )
                    
                    response = {
                        "status": result.get("status"),
                        "image_hash": result.get("image_hash"),
                        "tag_type": result.get("analysis", {}).get("tag_type"),
                        "brand": result.get("analysis", {}).get("brand"),
                        "text_content": result.get("analysis", {}).get("text_content"),
                        "colors": result.get("analysis", {}).get("colors"),
                        "stored_in_chromadb": result.get("status") == "success",
                    }
                    
                    return json.dumps(response, indent=2)
                else:
                    # V4: Propose image processing
                    return json.dumps({
                        "proposal": "image_processing",
                        "image_path": image_path,
                        "analysis": {
                            "type": "product_image",
                            "order_id": order_id,
                            "customer": customer_name,
                            "confidence": 0.7
                        },
                        "proposed_actions": [
                            "Analyze visual features",
                            "Extract text from image",
                            "Match against inventory images",
                            "Store in image database"
                        ],
                        "requires_visual_ai": True
                    })
                    
            except Exception as e:
                logger.error(f"Error processing tag image: {e}")
                return json.dumps({"error": str(e), "status": "failed"})
        
        tools.append(process_tag_image)
        
        # Analyze attachments for proposal (V4 specific)
        if self.mode == "propose":
            @function_tool(
                name_override="analyze_attachments_for_proposal",
                description_override="Analyze email attachments to extract data for proposal. Does not modify attachments.",
            )
            async def analyze_attachments_for_proposal(
                attachment_names: List[str],
                attachment_types: List[str]
            ) -> str:
                """Analyze attachments for proposal generation"""
                extracted_data = []
                
                for name, att_type in zip(attachment_names, attachment_types):
                    if "excel" in att_type.lower() or "csv" in att_type.lower():
                        extracted_data.append({
                            "filename": name,
                            "type": "spreadsheet",
                            "analysis": "Contains structured order data",
                            "confidence": 0.9
                        })
                    elif "pdf" in att_type.lower():
                        extracted_data.append({
                            "filename": name,
                            "type": "document",
                            "analysis": "Contains order documentation",
                            "confidence": 0.8
                        })
                    elif "image" in att_type.lower() or name.lower().endswith(('.jpg', '.png', '.jpeg')):
                        extracted_data.append({
                            "filename": name,
                            "type": "image",
                            "analysis": "Contains product images for matching",
                            "confidence": 0.7
                        })
                    else:
                        extracted_data.append({
                            "filename": name,
                            "type": "unknown",
                            "analysis": "Unknown file type",
                            "confidence": 0.3
                        })
                
                return json.dumps({
                    "success": True,
                    "attachments_analyzed": len(extracted_data),
                    "extracted_data": extracted_data,
                    "message": f"Analyzed {len(extracted_data)} attachments for proposal"
                })
            
            tools.append(analyze_attachments_for_proposal)
        
        return tools