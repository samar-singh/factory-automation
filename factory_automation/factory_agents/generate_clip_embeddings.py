#!/usr/bin/env python3
"""Generate CLIP embeddings for all inventory images"""

import base64
import io
import logging
import torch
import clip
from PIL import Image
from typing import List

logger = logging.getLogger(__name__)


class CLIPEmbeddingGenerator:
    """Generate CLIP embeddings for inventory images"""

    def __init__(self, chromadb_client):
        """Initialize with ChromaDB client and CLIP model"""
        self.chromadb_client = chromadb_client

        # Load CLIP model
        logger.info("Loading CLIP model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        logger.info(f"CLIP model loaded on {self.device}")

    def base64_to_embedding(self, base64_string: str) -> List[float]:
        """Convert base64 image to CLIP embedding"""
        try:
            # Decode base64 to image
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")

            # Preprocess and extract features
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                # Normalize the features
                image_features = image_features / image_features.norm(
                    dim=-1, keepdim=True
                )

            # Convert to list for ChromaDB
            embedding = image_features.cpu().numpy().flatten().tolist()

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def create_clip_collection(self):
        """Create a new collection specifically for CLIP embeddings"""
        collection_name = "tag_inventory_clip"

        # Check if collection exists
        existing = [c.name for c in self.chromadb_client.client.list_collections()]

        if collection_name in existing:
            logger.info(f"Collection {collection_name} already exists, getting it...")
            return self.chromadb_client.client.get_collection(collection_name)
        else:
            logger.info(f"Creating new collection: {collection_name}")
            # Create with cosine distance for similarity search
            return self.chromadb_client.client.create_collection(
                name=collection_name, metadata={"hnsw:space": "cosine"}
            )

    def generate_embeddings_for_inventory(self):
        """Generate CLIP embeddings for all inventory images"""

        # Get the source collection with base64 images
        source_collection = self.chromadb_client.client.get_collection(
            "tag_images_full"
        )

        # Create/get the CLIP collection
        clip_collection = self.create_clip_collection()

        # Get all items with images
        all_items = source_collection.get(include=["metadatas", "documents"])

        logger.info(f"Processing {len(all_items['ids'])} inventory images...")

        successful = 0
        failed = 0

        for i, item_id in enumerate(all_items["ids"]):
            metadata = all_items["metadatas"][i]

            # Check if has base64 image
            if "image_base64" not in metadata:
                logger.warning(f"Item {item_id} has no base64 image, skipping")
                failed += 1
                continue

            # Generate CLIP embedding
            base64_img = metadata["image_base64"]
            clip_embedding = self.base64_to_embedding(base64_img)

            if clip_embedding is None:
                logger.error(f"Failed to generate embedding for {item_id}")
                failed += 1
                continue

            # Prepare metadata for CLIP collection
            clip_metadata = {
                "item_id": item_id,
                "brand": metadata.get("brand", "Unknown"),
                "item_name": metadata.get("item_name", "Unknown"),
                "item_code": metadata.get("item_code", "Unknown"),
                "tag_code": metadata.get(
                    "item_code", "Unknown"
                ),  # Use item_code as tag_code
                "tag_type": "price_tag",  # Default tag type
                "has_clip_embedding": True,
                "embedding_model": "CLIP_ViT-B/32",
                "embedding_dim": len(clip_embedding),
                "source_collection": "tag_images_full",
                "image_path": f"inventory/{item_id}.png",  # Virtual path
            }

            # Create searchable document
            document = f"{metadata.get('brand', '')} {metadata.get('item_name', '')} {metadata.get('item_code', '')} tag"

            # Check if already exists in CLIP collection
            existing = clip_collection.get(ids=[item_id])

            if existing["ids"]:
                # Update existing
                clip_collection.update(
                    ids=[item_id],
                    embeddings=[clip_embedding],
                    metadatas=[clip_metadata],
                    documents=[document],
                )
                logger.debug(f"Updated CLIP embedding for {item_id}")
            else:
                # Add new
                clip_collection.add(
                    ids=[item_id],
                    embeddings=[clip_embedding],
                    metadatas=[clip_metadata],
                    documents=[document],
                )
                logger.debug(f"Added CLIP embedding for {item_id}")

            successful += 1

            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(all_items['ids'])} images...")

        logger.info(
            f"Completed! Successfully generated {successful} CLIP embeddings, {failed} failed"
        )

        # Verify the collection
        final_count = clip_collection.count()
        logger.info(f"CLIP collection now has {final_count} items")

        return successful, failed


if __name__ == "__main__":
    import sys

    sys.path.append("/Users/samarsingh/Factory_flow_Automation")

    from factory_automation.factory_database.vector_db import ChromaDBClient

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize ChromaDB
    chromadb_client = ChromaDBClient()

    # Generate embeddings
    generator = CLIPEmbeddingGenerator(chromadb_client)
    successful, failed = generator.generate_embeddings_for_inventory()

    print(f"\n✅ Generated {successful} CLIP embeddings")
    if failed > 0:
        print(f"❌ Failed to generate {failed} embeddings")
