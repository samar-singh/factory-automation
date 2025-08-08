"""Helper functions for displaying images in UI results"""

import base64
import io
import logging
from typing import Any, Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)


def base64_to_pil_image(base64_string: str) -> Optional[Image.Image]:
    """Convert base64 string to PIL Image
    
    Args:
        base64_string: Base64 encoded image
        
    Returns:
        PIL Image object or None if conversion fails
    """
    try:
        # Remove data URL prefix if present
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Create PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        return image
        
    except Exception as e:
        logger.error(f"Error converting base64 to image: {e}")
        return None


def create_image_html(base64_string: str, max_width: int = 200) -> str:
    """Create HTML for displaying base64 image
    
    Args:
        base64_string: Base64 encoded image
        max_width: Maximum width for display
        
    Returns:
        HTML string for image display
    """
    if not base64_string:
        return "<p>No image available</p>"
    
    # Ensure proper data URL format
    if not base64_string.startswith('data:image'):
        base64_string = f"data:image/jpeg;base64,{base64_string}"
    
    return f'''
    <img src="{base64_string}" 
         style="max-width: {max_width}px; height: auto; border: 1px solid #ddd; border-radius: 4px;"
         alt="Product Image" />
    '''


def format_search_result_with_image(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format search result including image data for display
    
    Args:
        result: Search result dictionary
        
    Returns:
        Formatted result with image display ready
    """
    formatted = {
        "name": result.get("metadata", {}).get("item_name", "Unknown"),
        "code": result.get("metadata", {}).get("item_code", "N/A"),
        "brand": result.get("metadata", {}).get("brand", "Unknown"),
        "confidence": f"{result.get('confidence_percentage', 0)}%",
        "has_image": False,
        "image_html": ""
    }
    
    # Check for image data
    if result.get("image_data") and result["image_data"].get("base64"):
        formatted["has_image"] = True
        formatted["image_html"] = create_image_html(
            result["image_data"]["base64"],
            max_width=150
        )
        formatted["has_clip"] = result["image_data"].get("has_clip_embedding", False)
    
    return formatted


def create_image_gallery_html(results: List[Dict[str, Any]], max_items: int = 10) -> str:
    """Create HTML gallery of images from search results
    
    Args:
        results: List of search results with image data
        max_items: Maximum number of images to display
        
    Returns:
        HTML string for image gallery
    """
    html_parts = ['<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px;">']
    
    count = 0
    for result in results[:max_items]:
        if result.get("image_data") and result["image_data"].get("base64"):
            metadata = result.get("metadata", {})
            
            # Create image card
            card_html = f'''
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 8px; text-align: center;">
                {create_image_html(result["image_data"]["base64"], max_width=140)}
                <div style="margin-top: 5px; font-size: 12px;">
                    <strong>{metadata.get("item_name", "Unknown")[:20]}</strong><br>
                    {metadata.get("item_code", "N/A")}<br>
                    <span style="color: #666;">{metadata.get("brand", "")}</span><br>
                    <span style="color: #0066cc;">Conf: {result.get("confidence_percentage", 0)}%</span>
                </div>
            </div>
            '''
            html_parts.append(card_html)
            count += 1
    
    html_parts.append('</div>')
    
    if count == 0:
        return "<p>No images available in search results</p>"
    
    return ''.join(html_parts)


def create_comparison_view(query_image_base64: Optional[str], results: List[Dict[str, Any]]) -> str:
    """Create side-by-side comparison of query image and results
    
    Args:
        query_image_base64: Base64 of query image (if image search)
        results: Search results with images
        
    Returns:
        HTML for comparison view
    """
    html_parts = ['<div style="display: flex; gap: 20px;">']
    
    # Query image section
    if query_image_base64:
        html_parts.append('''
        <div style="flex: 0 0 200px;">
            <h4>Query Image:</h4>
        ''')
        html_parts.append(create_image_html(query_image_base64, max_width=180))
        html_parts.append('</div>')
    
    # Results section
    html_parts.append('''
    <div style="flex: 1;">
        <h4>Matching Items:</h4>
    ''')
    html_parts.append(create_image_gallery_html(results, max_items=6))
    html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    return ''.join(html_parts)


def extract_images_for_display(results: List[Dict[str, Any]]) -> List[Image.Image]:
    """Extract PIL Images from search results for Gradio Image component
    
    Args:
        results: Search results with image data
        
    Returns:
        List of PIL Images
    """
    images = []
    
    for result in results:
        if result.get("image_data") and result["image_data"].get("base64"):
            pil_image = base64_to_pil_image(result["image_data"]["base64"])
            if pil_image:
                images.append(pil_image)
    
    return images