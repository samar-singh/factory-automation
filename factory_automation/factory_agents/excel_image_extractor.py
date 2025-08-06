"""Excel Image Extraction Enhancement for Order Processor"""

import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ExcelImageExtractor:
    """Extract embedded images from Excel files"""

    @staticmethod
    def extract_images_from_excel(excel_content: bytes) -> List[Dict[str, Any]]:
        """
        Extract all embedded images from an Excel file

        Args:
            excel_content: Excel file content as bytes

        Returns:
            List of dictionaries containing image data and metadata
        """
        extracted_images = []

        with tempfile.TemporaryDirectory() as temp_dir:
            # Save Excel content to temp file
            excel_path = os.path.join(temp_dir, "temp.xlsx")
            with open(excel_path, "wb") as f:
                f.write(excel_content)

            try:
                # Excel files are zip archives
                with zipfile.ZipFile(excel_path, "r") as zip_ref:
                    # Look for images in xl/media folder
                    image_files = [
                        f for f in zip_ref.namelist() if f.startswith("xl/media/")
                    ]

                    for idx, img_file in enumerate(image_files):
                        # Extract image
                        img_data = zip_ref.read(img_file)

                        # Determine file extension
                        ext = Path(img_file).suffix

                        # Save to temp file for processing
                        img_path = os.path.join(temp_dir, f"excel_image_{idx}{ext}")
                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        extracted_images.append(
                            {
                                "filename": f"excel_embedded_{idx}{ext}",
                                "path": img_path,
                                "data": img_data,
                                "source": "excel_embedded",
                                "index": idx,
                            }
                        )

                        logger.info(
                            f"Extracted image {idx} from Excel: {len(img_data)} bytes"
                        )

            except Exception as e:
                logger.error(f"Error extracting images from Excel: {e}")

        return extracted_images


def enhance_excel_processing(order_processor_agent):
    """
    Monkey-patch the order processor to handle Excel images

    This is a temporary enhancement until properly integrated
    """
    original_process_excel = order_processor_agent._process_excel_attachment

    async def _enhanced_process_excel_attachment(
        self, content: bytes, filename: str
    ) -> Dict[str, Any]:
        # First, get the original Excel data processing
        excel_data = await original_process_excel(content, filename)

        # Then extract and process any embedded images
        try:
            extracted_images = ExcelImageExtractor.extract_images_from_excel(content)

            if extracted_images:
                excel_data["embedded_images"] = []

                for img_info in extracted_images:
                    # Process each image with the image processor
                    if hasattr(self, "image_processor"):
                        result = await self.image_processor.analyze_with_qwen(
                            img_info["path"]
                        )

                        excel_data["embedded_images"].append(
                            {
                                "filename": img_info["filename"],
                                "analysis": result,
                                "index": img_info["index"],
                            }
                        )

                        logger.info(
                            f"Processed embedded image {img_info['index']} from Excel"
                        )

                excel_data["has_embedded_images"] = True
                excel_data["embedded_image_count"] = len(extracted_images)

        except Exception as e:
            logger.error(f"Error processing Excel embedded images: {e}")
            excel_data["embedded_images_error"] = str(e)

        return excel_data

    # Replace the method
    order_processor_agent._process_excel_attachment = (
        _enhanced_process_excel_attachment.__get__(
            order_processor_agent, order_processor_agent.__class__
        )
    )

    logger.info("Enhanced Excel processor with image extraction capability")
