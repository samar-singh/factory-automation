"""Enhanced Excel processor that extracts both data and embedded images"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import openpyxl
import pandas as pd
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


async def process_excel_with_images(filepath: str, filename: str) -> Dict[str, Any]:
    """Process Excel file and extract both data and embedded images

    Args:
        filepath: Path to the Excel file
        filename: Original filename

    Returns:
        Dictionary containing:
        - data: Extracted data from Excel
        - images: List of extracted image file paths
        - error: Error message if any
    """
    result = {"filename": filename, "data": [], "images": [], "error": None}

    try:
        # First extract data using pandas
        logger.info(f"Reading Excel data from {filepath}")
        df = pd.read_excel(filepath, engine="openpyxl")

        # Convert to list of dicts for easier processing
        if not df.empty:
            result["data"] = df.to_dict("records")
            logger.info(f"Extracted {len(df)} rows of data")

        # Now extract embedded images using openpyxl
        logger.info(f"Checking for embedded images in {filepath}")
        wb = openpyxl.load_workbook(filepath, data_only=True)

        # Create temp directory for images
        temp_dir = tempfile.mkdtemp(prefix="excel_images_")
        base_name = Path(filename).stem

        image_count = 0
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]

            # Check for images in the sheet
            if hasattr(sheet, "_images") and sheet._images:
                logger.info(
                    f"Found {len(sheet._images)} images in sheet '{sheet_name}'"
                )

                for idx, img in enumerate(sheet._images):
                    try:
                        # Extract image data
                        img_data = img._data()

                        # Determine image format
                        img_format = "png"  # Default
                        if hasattr(img, "format"):
                            img_format = img.format.lower()

                        # Save image to temp directory
                        img_filename = (
                            f"{base_name}_{sheet_name}_image{idx+1}.{img_format}"
                        )
                        img_path = os.path.join(temp_dir, img_filename)

                        # Write image data
                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        # Verify image is readable
                        pil_img = PILImage.open(img_path)
                        width, height = pil_img.size

                        result["images"].append(
                            {
                                "filepath": img_path,
                                "filename": img_filename,
                                "sheet": sheet_name,
                                "index": idx + 1,
                                "width": width,
                                "height": height,
                                "format": img_format,
                                "mime_type": f"image/{img_format}",
                            }
                        )

                        image_count += 1
                        logger.info(
                            f"Extracted image {idx+1} from sheet '{sheet_name}': {img_filename} ({width}x{height})"
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to extract image {idx+1} from sheet '{sheet_name}': {e}"
                        )

        wb.close()

        if image_count > 0:
            logger.info(f"Successfully extracted {image_count} images from Excel file")
        else:
            logger.info("No embedded images found in Excel file")

    except Exception as e:
        logger.error(f"Error processing Excel file with images: {e}")
        result["error"] = str(e)

    return result
