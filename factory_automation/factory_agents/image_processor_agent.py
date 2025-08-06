"""Image Processing Agent for tag images using Qwen2.5VL and ChromaDB storage"""

import base64
import hashlib
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI
from PIL import Image

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class ImageProcessorAgent:
    """Process tag images, extract information, and store in ChromaDB"""

    def __init__(self, chromadb_client: ChromaDBClient):
        """Initialize with ChromaDB client"""
        self.chromadb_client = chromadb_client
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.together_api_key = settings.together_api_key

        # Create a dedicated collection for image data
        self.image_collection_name = "tag_images"
        self._ensure_image_collection()

    def _ensure_image_collection(self):
        """Ensure the image collection exists in ChromaDB"""
        try:
            # Check if collection exists, create if not
            collections = [
                c.name for c in self.chromadb_client.client.list_collections()
            ]
            if self.image_collection_name not in collections:
                self.chromadb_client.client.create_collection(
                    name=self.image_collection_name,
                    metadata={"description": "Tag images with visual analysis"},
                )
                logger.info(f"Created image collection: {self.image_collection_name}")
        except Exception as e:
            logger.error(f"Error creating image collection: {e}")

    def image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 string"""
        try:
            with open(image_path, "rb") as image_file:
                base64_string = base64.b64encode(image_file.read()).decode("utf-8")
                return base64_string
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            raise

    def base64_to_image(self, base64_string: str) -> Image.Image:
        """Convert base64 string back to PIL Image"""
        try:
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))
            return image
        except Exception as e:
            logger.error(f"Error converting base64 to image: {e}")
            raise

    def generate_image_hash(self, base64_string: str) -> str:
        """Generate unique hash for image"""
        return hashlib.md5(base64_string.encode()).hexdigest()

    async def analyze_with_qwen(self, image_path: str) -> Dict[str, Any]:
        """Analyze image using Qwen2.5VL-72B via Together.ai"""
        try:
            # Convert image to base64
            base64_image = self.image_to_base64(image_path)

            # Prepare the prompt for Qwen2.5VL
            analysis_prompt = """Analyze this garment tag image and extract ALL visible information in detail:

1. **Tag Type**: Identify the type (price tag, care label, brand label, hang tag, etc.)
2. **Brand/Logo**: Identify any brand names or logos
3. **Text Content**: Extract ALL text visible on the tag (prices, sizes, product codes, care instructions, etc.)
4. **Colors**: Describe the color scheme (background, text, design elements)
5. **Material**: If visible, identify the material (paper, fabric, plastic, etc.)
6. **Size/Dimensions**: Estimate the tag dimensions if possible
7. **Special Features**: Note any special finishes (embossing, foiling, holographic, etc.)
8. **Product Codes/SKUs**: Extract any visible codes, barcodes, or SKUs
9. **Design Elements**: Describe any graphics, patterns, or design features
10. **Quality/Condition**: Note the print quality and overall condition

Return the analysis as a detailed JSON object with all extracted information."""

            # Call Qwen2.5VL via Together.ai
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.together.xyz/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.together_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "Qwen/Qwen2.5-VL-72B",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": analysis_prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        },
                                    },
                                ],
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    analysis = json.loads(result["choices"][0]["message"]["content"])

                    # Add metadata
                    analysis["analysis_timestamp"] = datetime.now().isoformat()
                    analysis["model_used"] = "Qwen2.5-VL-72B"
                    analysis["image_hash"] = self.generate_image_hash(base64_image)

                    return analysis
                else:
                    logger.error(
                        f"Qwen2.5VL API error: {response.status_code} - {response.text}"
                    )
                    return self._fallback_analysis(image_path)

        except Exception as e:
            logger.error(f"Error analyzing image with Qwen2.5VL: {e}")
            return self._fallback_analysis(image_path)

    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """Fallback analysis using basic image properties"""
        try:
            img = Image.open(image_path)
            return {
                "tag_type": "unknown",
                "analysis_method": "fallback",
                "image_properties": {
                    "format": img.format,
                    "size": img.size,
                    "mode": img.mode,
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "error": "Visual analysis unavailable",
            }
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            return {"error": str(e)}

    async def process_and_store_image(
        self,
        image_path: str,
        order_id: str,
        customer_name: str,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process image and store in ChromaDB with metadata"""

        try:
            # Convert image to base64
            base64_image = self.image_to_base64(image_path)
            image_hash = self.generate_image_hash(base64_image)

            # Check if image already exists
            collection = self.chromadb_client.client.get_collection(
                self.image_collection_name
            )
            existing = collection.get(ids=[image_hash])

            if existing["ids"]:
                logger.info(f"Image already exists in database: {image_hash}")
                return {
                    "status": "exists",
                    "image_hash": image_hash,
                    "metadata": existing["metadatas"][0],
                }

            # Analyze image with Qwen2.5VL
            analysis = await self.analyze_with_qwen(image_path)

            # Prepare metadata for ChromaDB
            metadata = {
                "order_id": order_id,
                "customer_name": customer_name,
                "image_path": str(image_path),
                "base64_image": base64_image[:100]
                + "...",  # Store truncated for reference
                "full_base64_size": len(base64_image),
                "upload_timestamp": datetime.now().isoformat(),
                "analysis": json.dumps(analysis),
                "tag_type": analysis.get("tag_type", "unknown"),
                "brand": analysis.get("brand", "unknown"),
                "colors": json.dumps(analysis.get("colors", [])),
                "text_content": analysis.get("text_content", ""),
                "product_codes": json.dumps(analysis.get("product_codes", [])),
            }

            # Add additional metadata if provided
            if additional_metadata:
                metadata.update(additional_metadata)

            # Create searchable document text from analysis
            document_text = self._create_searchable_text(analysis, customer_name)

            # Store in ChromaDB
            collection.add(
                ids=[image_hash],
                documents=[document_text],
                metadatas=[metadata],
                # Store full base64 in a separate field if needed
                # Note: ChromaDB has size limits, so we might need to store in chunks
            )

            # Also store the full base64 image in a separate storage system if needed
            # For now, we'll store a reference and can retrieve from file system

            logger.info(f"Successfully stored image {image_hash} in ChromaDB")

            return {
                "status": "success",
                "image_hash": image_hash,
                "analysis": analysis,
                "metadata": metadata,
                "searchable_text": document_text,
            }

        except Exception as e:
            logger.error(f"Error processing and storing image: {e}")
            return {"status": "error", "error": str(e)}

    def _create_searchable_text(
        self, analysis: Dict[str, Any], customer_name: str
    ) -> str:
        """Create searchable text from image analysis"""
        parts = [
            f"Customer: {customer_name}",
            f"Tag Type: {analysis.get('tag_type', 'unknown')}",
            f"Brand: {analysis.get('brand', 'unknown')}",
            f"Text: {analysis.get('text_content', '')}",
            f"Colors: {', '.join(analysis.get('colors', []))}",
            f"Product Codes: {', '.join(analysis.get('product_codes', []))}",
            f"Special Features: {', '.join(analysis.get('special_features', []))}",
            f"Material: {analysis.get('material', 'unknown')}",
        ]

        return " | ".join(parts)

    async def search_similar_images(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar images in ChromaDB"""
        try:
            collection = self.chromadb_client.client.get_collection(
                self.image_collection_name
            )

            # Search in the image collection
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                include=["metadatas", "documents", "distances"],
            )

            # Process results
            similar_images = []
            if results["ids"][0]:
                for i, image_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]

                    # Parse the stored analysis
                    analysis = json.loads(metadata.get("analysis", "{}"))

                    similar_images.append(
                        {
                            "image_hash": image_id,
                            "similarity_score": 1 - results["distances"][0][i],
                            "order_id": metadata.get("order_id"),
                            "customer_name": metadata.get("customer_name"),
                            "tag_type": metadata.get("tag_type"),
                            "brand": metadata.get("brand"),
                            "analysis": analysis,
                            "upload_timestamp": metadata.get("upload_timestamp"),
                        }
                    )

            return similar_images

        except Exception as e:
            logger.error(f"Error searching similar images: {e}")
            return []

    async def retrieve_image_by_hash(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve image data by hash from ChromaDB"""
        try:
            collection = self.chromadb_client.client.get_collection(
                self.image_collection_name
            )

            result = collection.get(
                ids=[image_hash], include=["metadatas", "documents"]
            )

            if result["ids"]:
                metadata = result["metadatas"][0]
                return {
                    "image_hash": image_hash,
                    "metadata": metadata,
                    "analysis": json.loads(metadata.get("analysis", "{}")),
                    "document": result["documents"][0],
                }

            return None

        except Exception as e:
            logger.error(f"Error retrieving image: {e}")
            return None

    async def update_image_metadata(
        self, image_hash: str, updates: Dict[str, Any]
    ) -> bool:
        """Update metadata for an existing image"""
        try:
            collection = self.chromadb_client.client.get_collection(
                self.image_collection_name
            )

            # Get existing metadata
            existing = collection.get(ids=[image_hash])
            if not existing["ids"]:
                logger.warning(f"Image {image_hash} not found for update")
                return False

            # Update metadata
            current_metadata = existing["metadatas"][0]
            current_metadata.update(updates)
            current_metadata["last_updated"] = datetime.now().isoformat()

            # Update in ChromaDB
            collection.update(ids=[image_hash], metadatas=[current_metadata])

            logger.info(f"Updated metadata for image {image_hash}")
            return True

        except Exception as e:
            logger.error(f"Error updating image metadata: {e}")
            return False
