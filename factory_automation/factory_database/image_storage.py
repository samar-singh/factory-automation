"""Image Storage Manager for full image data in ChromaDB"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ImageStorageManager:
    """Manages full image storage in a separate ChromaDB collection"""

    def __init__(
        self,
        persist_directory: str = "./chroma_data",
        collection_name: str = "tag_images_full",
    ):
        """Initialize image storage manager

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the image collection
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Create persistent client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Get or create image collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "description": "Full image storage with CLIP embeddings",
            },
        )

        logger.info(f"Image storage initialized: {self.collection_name}")

    def generate_image_id(self, base64_data: str, row_index: int, brand: str) -> str:
        """Generate unique ID for an image

        Args:
            base64_data: Base64 encoded image
            row_index: Row index in Excel
            brand: Brand name

        Returns:
            Unique image ID
        """
        # Create hash from image data
        image_hash = hashlib.md5(base64_data.encode()).hexdigest()[:8]
        return f"{brand}_row{row_index}_img_{image_hash}"

    def store_image(
        self,
        image_id: str,
        base64_data: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        text_description: Optional[str] = None,
    ) -> bool:
        """Store full image with metadata and optional embedding

        Args:
            image_id: Unique image identifier
            base64_data: Full base64 encoded image
            metadata: Image metadata (brand, row, filename, etc.)
            embedding: Optional CLIP embedding
            text_description: Optional text description for the image

        Returns:
            Success status
        """
        try:
            # Prepare document (text description or metadata summary)
            if text_description:
                document = text_description
            else:
                # Create text from metadata
                document = f"{metadata.get('brand', '')} {metadata.get('item_name', '')} {metadata.get('item_code', '')} image"

            # Store image data in metadata (ChromaDB can handle large metadata)
            full_metadata = {
                **metadata,
                "image_base64": base64_data,  # Store full image
                "image_size": len(base64_data),
                "has_full_image": True,
            }

            # Add to collection
            if embedding:
                self.collection.add(
                    ids=[image_id],
                    documents=[document],
                    metadatas=[full_metadata],
                    embeddings=[embedding],
                )
            else:
                self.collection.add(
                    ids=[image_id], documents=[document], metadatas=[full_metadata]
                )

            logger.debug(f"Stored image {image_id} ({len(base64_data)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Error storing image {image_id}: {e}")
            return False

    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full image by ID

        Args:
            image_id: Image identifier

        Returns:
            Dict with image data and metadata, or None if not found
        """
        try:
            result = self.collection.get(
                ids=[image_id], include=["metadatas", "documents", "embeddings"]
            )

            if result and result.get("ids") and len(result["ids"]) > 0:
                metadata = result["metadatas"][0] if result["metadatas"] else {}

                # Handle embeddings properly - check for numpy arrays
                embedding = None
                embeddings = result.get("embeddings")
                if embeddings is not None and len(embeddings) > 0:
                    emb = embeddings[0]
                    # Check if emb is not None - handle numpy arrays properly
                    try:
                        is_none = emb is None
                    except:
                        # For numpy arrays, check if it has content
                        is_none = False

                    if not is_none:
                        # Convert numpy array to list if needed
                        if hasattr(emb, "tolist"):
                            embedding = emb.tolist()
                        elif isinstance(emb, list):
                            embedding = emb

                return {
                    "id": image_id,
                    "base64": metadata.get("image_base64", ""),
                    "metadata": {
                        k: v for k, v in metadata.items() if k != "image_base64"
                    },
                    "document": result["documents"][0] if result["documents"] else "",
                    "embedding": embedding,
                }

            return None

        except Exception as e:
            import traceback

            logger.error(f"Error retrieving image {image_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_images_batch(self, image_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve multiple images by IDs

        Args:
            image_ids: List of image identifiers

        Returns:
            List of image data dictionaries
        """
        try:
            result = self.collection.get(
                ids=image_ids, include=["metadatas", "documents", "embeddings"]
            )

            images = []
            for i, img_id in enumerate(result.get("ids", [])):
                metadata = result["metadatas"][i] if result.get("metadatas") else {}
                images.append(
                    {
                        "id": img_id,
                        "base64": metadata.get("image_base64", ""),
                        "metadata": {
                            k: v for k, v in metadata.items() if k != "image_base64"
                        },
                        "document": (
                            result["documents"][i] if result.get("documents") else ""
                        ),
                        "embedding": self._safe_get_embedding(
                            result.get("embeddings"), i
                        ),
                    }
                )

            return images

        except Exception as e:
            logger.error(f"Error retrieving images batch: {e}")
            return []

    def search_by_embedding(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar images using embedding

        Args:
            query_embedding: Query embedding (e.g., from CLIP)
            n_results: Number of results to return
            where: Optional filter conditions

        Returns:
            List of matching images with similarity scores
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["metadatas", "distances", "documents"],
            )

            matches = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                matches.append(
                    {
                        "id": results["ids"][0][i],
                        "base64": metadata.get("image_base64", ""),
                        "metadata": {
                            k: v for k, v in metadata.items() if k != "image_base64"
                        },
                        "distance": results["distances"][0][i],
                        "similarity": 1
                        - results["distances"][0][i],  # Convert to similarity
                        "document": (
                            results["documents"][0][i] if results["documents"] else ""
                        ),
                    }
                )

            return matches

        except Exception as e:
            logger.error(f"Error searching by embedding: {e}")
            return []

    def update_image_metadata(
        self, image_id: str, metadata_updates: Dict[str, Any]
    ) -> bool:
        """Update metadata for an existing image

        Args:
            image_id: Image identifier
            metadata_updates: Metadata fields to update

        Returns:
            Success status
        """
        try:
            # Get existing image
            existing = self.get_image(image_id)
            if not existing:
                logger.warning(f"Image {image_id} not found for update")
                return False

            # Merge metadata
            updated_metadata = {**existing["metadata"], **metadata_updates}
            updated_metadata["image_base64"] = existing["base64"]  # Preserve image

            # Update in collection
            self.collection.update(ids=[image_id], metadatas=[updated_metadata])

            logger.debug(f"Updated metadata for image {image_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating image {image_id}: {e}")
            return False

    def delete_image(self, image_id: str) -> bool:
        """Delete an image from storage

        Args:
            image_id: Image identifier

        Returns:
            Success status
        """
        try:
            self.collection.delete(ids=[image_id])
            logger.debug(f"Deleted image {image_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting image {image_id}: {e}")
            return False

    def _safe_get_embedding(self, embeddings, index):
        """Safely extract embedding handling numpy arrays"""
        if not embeddings or len(embeddings) <= index:
            return None

        emb = embeddings[index]

        # Check if emb is None - handle numpy arrays properly
        try:
            is_none = emb is None
        except:
            # For numpy arrays, check if it has content
            is_none = False

        if is_none:
            return None

        # Convert numpy array to list if needed
        if hasattr(emb, "tolist"):
            return emb.tolist()
        elif isinstance(emb, list):
            return emb

        return None

    def count(self) -> int:
        """Get total number of images stored

        Returns:
            Number of images in collection
        """
        return self.collection.count()

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics

        Returns:
            Dictionary with storage stats
        """
        try:
            # Get sample to calculate average size
            sample = self.collection.get(limit=10, include=["metadatas"])

            total_size = 0
            for metadata in sample.get("metadatas", []):
                if metadata.get("image_size"):
                    total_size += metadata["image_size"]

            avg_size = (
                total_size / len(sample["metadatas"]) if sample.get("metadatas") else 0
            )

            return {
                "total_images": self.count(),
                "collection_name": self.collection_name,
                "average_image_size_bytes": avg_size,
                "estimated_total_size_mb": (avg_size * self.count()) / (1024 * 1024),
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_images": self.count(),
                "collection_name": self.collection_name,
                "error": str(e),
            }
