#!/usr/bin/env python3
"""Reset ChromaDB and ingest with consistent embeddings."""

import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.append("./factory_automation")

# Import and run ingestion
from factory_automation.factory_database.vector_db import ChromaDBClient  # noqa: E402
from factory_automation.factory_rag.excel_ingestion import (  # noqa: E402
    ExcelInventoryIngestion,
)


def main():
    print("Resetting ChromaDB and ingesting inventory...")
    print("=" * 60)

    # Delete existing ChromaDB data
    chroma_path = Path("./chroma_data")
    if chroma_path.exists():
        print(f"Removing existing ChromaDB data at {chroma_path}")
        shutil.rmtree(chroma_path)

    # Initialize ChromaDB fresh
    chroma_client = ChromaDBClient()

    # Use all-MiniLM-L6-v2 for consistency (384 dimensions)
    print("Using all-MiniLM-L6-v2 embeddings (384 dimensions)")
    ingestion = ExcelInventoryIngestion(
        chroma_client=chroma_client, embedding_model="all-MiniLM-L6-v2"
    )

    # Ingest all Excel files
    inventory_folder = Path("inventory")
    if not inventory_folder.exists():
        print(f"Error: {inventory_folder} folder not found!")
        return

    print(f"Ingesting from {inventory_folder}...")
    results = ingestion.ingest_inventory_folder(str(inventory_folder))

    # Summary
    total_ingested = sum(
        r.get("items_ingested", 0) for r in results if r["status"] == "success"
    )
    failed_files = [r["file"] for r in results if r["status"] == "error"]

    print("\n" + "=" * 60)
    print("Ingestion Complete!")
    print(f"Total items ingested: {total_ingested}")
    print(f"Successful files: {len([r for r in results if r['status'] == 'success'])}")
    print(f"Failed files: {len(failed_files)}")

    if failed_files:
        print("\nFailed files:")
        for f in failed_files:
            print(f"  - {f}")

    # Show collection info
    collection = chroma_client.collection
    print(
        f"\nChromaDB collection '{collection.name}' now has {collection.count()} items"
    )
    print("\nYou can now run the demo scripts!")


if __name__ == "__main__":
    main()
