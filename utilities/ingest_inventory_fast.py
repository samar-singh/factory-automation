#!/usr/bin/env python3
"""Fast inventory ingestion using all-MiniLM-L6-v2 for quick testing"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent / "factory_automation"))

import logging

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run inventory ingestion with fast embeddings"""

    # Initialize ChromaDB client
    logger.info("Initializing ChromaDB client...")
    chroma_client = ChromaDBClient()

    # Initialize ingestion with fast embeddings
    logger.info(
        "Initializing Excel ingestion with all-MiniLM-L6-v2 (fast) embeddings..."
    )
    ingestion = ExcelInventoryIngestion(
        chroma_client=chroma_client,
        embedding_model="all-MiniLM-L6-v2",  # Use the fast model
        device="cpu",
    )

    # Ingest all Excel files from inventory folder
    inventory_folder = "inventory"
    if not os.path.exists(inventory_folder):
        logger.error(f"Inventory folder '{inventory_folder}' not found!")
        return

    logger.info(f"Starting ingestion from {inventory_folder}...")
    results = ingestion.ingest_inventory_folder(inventory_folder)

    # Print summary
    print("\n" + "=" * 50)
    print("INGESTION SUMMARY")
    print("=" * 50)

    successful = 0
    total_items = 0

    for result in results:
        if result["status"] == "success":
            successful += 1
            total_items += result["items_ingested"]
            print(f"✓ {result['brand']}: {result['items_ingested']} items")
        elif result["status"] == "warning":
            print(f"⚠ {result['file']}: {result.get('message', 'Warning')}")
        else:
            print(f"✗ {result['file']}: {result.get('error', 'Error')}")

    print(f"\nTotal: {successful}/{len(results)} files processed successfully")
    print(f"Total items in database: {total_items}")

    # Test some searches
    print("\n" + "=" * 50)
    print("TESTING SEARCH FUNCTIONALITY")
    print("=" * 50)

    test_queries = [
        ("Allen Solly casual tag", None),
        ("black tag with thread", None),
        ("Myntra invictus", "MYNTRA"),
        ("Peter England formal", None),
        ("available stock cotton", None),
    ]

    for query, brand_filter in test_queries:
        print(
            f"\nQuery: '{query}'"
            + (f" (Brand: {brand_filter})" if brand_filter else "")
        )
        results = ingestion.search_inventory(
            query=query, brand_filter=brand_filter, min_stock=0, limit=3
        )

        if results:
            for i, result in enumerate(results, 1):
                meta = result["metadata"]
                print(f"{i}. {meta.get('trim_name', 'N/A')[:50]}...")
                print(
                    f"   Code: {meta.get('trim_code', 'N/A')}, "
                    f"Stock: {meta.get('stock', 0)}, "
                    f"Brand: {meta.get('brand', 'N/A')}, "
                    f"Score: {result['score']:.3f}"
                )
        else:
            print("   No results found")


if __name__ == "__main__":
    main()
