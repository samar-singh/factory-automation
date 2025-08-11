#!/usr/bin/env python3
"""
Main script for ingesting inventory data from Excel files into ChromaDB

Usage:
    python ingest_inventory_data.py                  # Ingest all files from inventory/ folder
    python ingest_inventory_data.py path/to/file.xlsx   # Ingest specific file
    python ingest_inventory_data.py path/to/folder/     # Ingest all Excel files from folder
"""

import sys
import logging
from pathlib import Path
from factory_automation.factory_rag.intelligent_excel_ingestion import (
    IntelligentExcelIngestion,
)
from factory_automation.factory_database.vector_db import ChromaDBClient

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main ingestion function"""

    # Default folder
    default_folder = "inventory"

    # Determine what to ingest
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = default_folder
        logger.info(f"No target specified, using default: {target}")

    # Initialize ChromaDB and ingestion system
    logger.info("Initializing ingestion system...")
    chromadb_client = ChromaDBClient()

    # Initialize intelligent ingestion with all features
    ingestion = IntelligentExcelIngestion(
        chroma_client=chromadb_client,
        embedding_model="stella-400m",  # Best accuracy
        use_vision_model=False,  # Set to True if you want vision analysis
        use_clip_embeddings=True,  # Enable CLIP for image embeddings
    )

    # Check if target is file or folder
    target_path = Path(target)

    if target_path.is_file():
        # Ingest single file
        logger.info(f"Ingesting single file: {target_path}")
        result = ingestion.ingest_excel_file(str(target_path))

        # Print results
        if result["status"] == "success":
            print(f"\n✅ Successfully ingested {target_path.name}")
            print(f"   - Items ingested: {result.get('items_ingested', 0)}")
            print(f"   - Items with images: {result.get('items_with_images', 0)}")
            print(
                f"   - Items with generated names: {result.get('items_with_generated_names', 0)}"
            )
            print(f"   - Brand: {result.get('brand', 'Unknown')}")
            if result.get("column_mapping"):
                print(f"   - Column mapping: {result['column_mapping']}")
        else:
            print(f"\n❌ Failed to ingest {target_path.name}")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    elif target_path.is_dir():
        # Ingest all Excel files in folder
        logger.info(f"Ingesting all Excel files from: {target_path}")
        results = ingestion.ingest_folder(str(target_path))

        # Print summary
        total_files = len(results)
        successful = sum(1 for r in results if r["status"] == "success")
        total_items = sum(
            r.get("items_ingested", 0) for r in results if r["status"] == "success"
        )
        total_images = sum(
            r.get("items_with_images", 0) for r in results if r["status"] == "success"
        )

        print("\n📊 Ingestion Summary:")
        print(f"   - Files processed: {total_files}")
        print(f"   - Successful: {successful}")
        print(f"   - Total items ingested: {total_items}")
        print(f"   - Items with images: {total_images}")

        # Show individual results
        print("\n📋 Individual Results:")
        for result in results:
            filename = Path(result["file"]).name
            if result["status"] == "success":
                print(f"   ✅ {filename}: {result.get('items_ingested', 0)} items")
            else:
                print(f"   ❌ {filename}: {result.get('error', 'Unknown error')}")

        # Show learned patterns
        print("\n🧠 Learned Column Patterns:")
        patterns = ingestion.get_learned_mappings()
        for field, columns in patterns.items():
            if columns:
                print(f"   - {field}: {', '.join(columns[:5])}")
    else:
        print(f"❌ Target not found: {target}")
        print("Please provide a valid file or folder path")
        sys.exit(1)

    print("\n✨ Ingestion complete!")
    print("   Run 'python run_factory_automation.py' to use the updated inventory")


if __name__ == "__main__":
    main()
