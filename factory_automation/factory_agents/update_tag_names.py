#!/usr/bin/env python3
"""Update tag names in ChromaDB to have meaningful identifiers"""

import logging
from typing import Dict, Any
from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class TagNameUpdater:
    """Update tag names to be more meaningful"""

    def __init__(self, chromadb_client: ChromaDBClient):
        self.chromadb_client = chromadb_client

    def generate_tag_name(self, metadata: Dict[str, Any]) -> str:
        """Generate a meaningful tag name from metadata"""

        # Components for the tag name
        brand = metadata.get("brand", "Unknown")
        item_name = metadata.get("item_name", "")
        item_code = metadata.get("item_code", metadata.get("tag_code", ""))
        source_file = metadata.get("source_file", "")
        row_index = metadata.get("row_index", "")

        # Build tag name
        name_parts = []

        # Add brand
        if brand and brand != "Unknown":
            name_parts.append(brand)

        # Add item name or code
        if item_name and item_name not in ["NILL", "Unknown", ""]:
            name_parts.append(item_name)
        elif item_code and item_code not in ["NILL", "Unknown", ""]:
            name_parts.append(f"Tag-{item_code}")

        # If still no meaningful name, use source info
        if len(name_parts) == 0 or (len(name_parts) == 1 and name_parts[0] == brand):
            if source_file:
                # Extract customer/document name from source file
                file_base = source_file.replace(".xlsx", "").replace(".xls", "")
                name_parts.append(f"Doc-{file_base}")
            if row_index:
                name_parts.append(f"Row-{row_index}")

        # Join parts to create tag name
        tag_name = " - ".join(name_parts) if name_parts else "Unnamed Tag"

        return tag_name

    def update_collection_names(self, collection_name: str):
        """Update all items in a collection with better names"""

        try:
            collection = self.chromadb_client.client.get_collection(collection_name)

            # Get all items
            all_items = collection.get(include=["metadatas"])

            updated_count = 0

            for i, item_id in enumerate(all_items["ids"]):
                metadata = all_items["metadatas"][i]

                # Generate new tag name
                tag_name = self.generate_tag_name(metadata)

                # Update metadata with tag name
                metadata["tag_name"] = tag_name

                # Also ensure item_name is set if it's missing
                if not metadata.get("item_name") or metadata.get("item_name") == "NILL":
                    # Use tag name as item name
                    metadata["item_name"] = tag_name

                # Update in collection
                collection.update(ids=[item_id], metadatas=[metadata])

                updated_count += 1

                if updated_count % 10 == 0:
                    logger.info(f"Updated {updated_count} items with tag names...")

            logger.info(
                f"Successfully updated {updated_count} items in {collection_name}"
            )
            return updated_count

        except Exception as e:
            logger.error(f"Error updating collection {collection_name}: {e}")
            return 0

    def update_all_collections(self):
        """Update tag names in all relevant collections"""

        collections_to_update = [
            "tag_images_full",
            "tag_inventory_clip",
            "tag_inventory_stella_smart",
            "tag_inventory_vision_enhanced",
        ]

        total_updated = 0

        for collection_name in collections_to_update:
            try:
                # Check if collection exists
                existing = [
                    c.name for c in self.chromadb_client.client.list_collections()
                ]
                if collection_name in existing:
                    logger.info(f"Updating tag names in {collection_name}...")
                    count = self.update_collection_names(collection_name)
                    total_updated += count
                else:
                    logger.info(f"Collection {collection_name} not found, skipping...")
            except Exception as e:
                logger.error(f"Error processing {collection_name}: {e}")

        logger.info(f"Total items updated across all collections: {total_updated}")
        return total_updated


# Function to use during new ingestion
def generate_tag_name_for_ingestion(
    brand: str,
    item_name: str,
    item_code: str,
    customer_name: str = None,
    document_name: str = None,
    row_number: int = None,
) -> str:
    """Generate a meaningful tag name during ingestion"""

    name_parts = []

    # Add brand if meaningful
    if brand and brand not in ["Unknown", "NILL", ""]:
        name_parts.append(brand)

    # Add item name or code
    if item_name and item_name not in ["NILL", "Unknown", ""]:
        name_parts.append(item_name)
    elif item_code and item_code not in ["NILL", "Unknown", ""]:
        name_parts.append(f"Tag-{item_code}")

    # If still not enough info, add context
    if len(name_parts) <= 1:
        if customer_name:
            name_parts.append(f"Customer-{customer_name}")
        elif document_name:
            name_parts.append(f"Doc-{document_name}")

        if row_number is not None:
            name_parts.append(f"Row-{row_number}")

    return " - ".join(name_parts) if name_parts else "Unnamed Tag"


if __name__ == "__main__":
    # Update existing tags with better names
    import sys

    sys.path.append("/Users/samarsingh/Factory_flow_Automation")

    from factory_automation.factory_database.vector_db import ChromaDBClient

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize
    chromadb_client = ChromaDBClient()
    updater = TagNameUpdater(chromadb_client)

    # Update all collections
    total = updater.update_all_collections()

    print(f"\n✅ Updated {total} items with meaningful tag names")
