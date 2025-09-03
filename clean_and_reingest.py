#!/usr/bin/env python3
"""Clean ChromaDB collections and re-ingest inventory with intelligent ingestion"""

import logging
import chromadb
from chromadb.config import Settings
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_chromadb():
    """Clean all ChromaDB collections"""
    try:
        logger.info("Connecting to ChromaDB...")
        client = chromadb.PersistentClient(
            path='./chroma_data',
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        
        # Get all collections
        collections = client.list_collections()
        logger.info(f"Found {len(collections)} collections to clean:")
        
        for col in collections:
            count = col.count()
            logger.info(f"  - Deleting {col.name} with {count} items...")
            client.delete_collection(col.name)
            
        logger.info("✅ All collections cleaned successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning ChromaDB: {e}")
        return False

def reingest_inventory():
    """Re-ingest inventory with intelligent ingestion and image extraction"""
    try:
        logger.info("Starting intelligent inventory ingestion...")
        
        # Import the intelligent ingestion module
        from factory_automation.factory_rag.intelligent_excel_ingestion import IntelligentExcelIngestion
        from factory_automation.factory_database.vector_db import ChromaDBClient
        
        # Initialize ChromaDB client
        logger.info("Initializing ChromaDB client...")
        chroma_client = ChromaDBClient(
            persist_directory="./chroma_data",
            collection_name="tag_inventory"  # Single unified collection
        )
        
        # Initialize intelligent ingestion with image extraction
        logger.info("Initializing intelligent ingestion with image extraction...")
        ingester = IntelligentExcelIngestion(
            chroma_client=chroma_client,
            embedding_model="stella-400m",  # Use 1024 dimensions
            use_vision_model=False,  # Set to True if you want AI vision analysis
            use_clip_embeddings=True  # Enable CLIP for image embeddings
        )
        
        # Ingest all inventory files
        inventory_path = "inventory/"
        if not Path(inventory_path).exists():
            logger.error(f"Inventory path {inventory_path} does not exist!")
            return False
            
        logger.info(f"Ingesting files from {inventory_path}...")
        results = ingester.ingest_folder(inventory_path)
        
        # Summary
        total_ingested = 0
        total_images = 0
        total_errors = 0
        
        for result in results:
            if result['status'] == 'success':
                total_ingested += result.get('items_ingested', 0)
                total_images += result.get('items_with_images', 0)
                logger.info(f"  ✅ {result['file']}: {result['items_ingested']} items, {result.get('items_with_images', 0)} with images")
            else:
                total_errors += 1
                logger.error(f"  ❌ {result['file']}: {result.get('error', 'Unknown error')}")
        
        logger.info("\n" + "="*60)
        logger.info(f"✅ Ingestion Complete!")
        logger.info(f"  Total items ingested: {total_ingested}")
        logger.info(f"  Items with images: {total_images}")
        logger.info(f"  Files with errors: {total_errors}")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_ingestion():
    """Verify the ingestion worked correctly"""
    try:
        logger.info("\nVerifying ingestion...")
        
        client = chromadb.PersistentClient(
            path='./chroma_data',
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        
        collections = client.list_collections()
        logger.info(f"Collections after ingestion: {len(collections)}")
        
        for col in collections:
            count = col.count()
            logger.info(f"  - {col.name}: {count} items")
            
            # Test a sample query
            if count > 0:
                result = col.query(
                    query_texts=["Allen Solly black tag"],
                    n_results=3
                )
                if result and result['ids'] and len(result['ids'][0]) > 0:
                    logger.info(f"    Sample query returned {len(result['ids'][0])} results")
                    
        return True
        
    except Exception as e:
        logger.error(f"Error verifying ingestion: {e}")
        return False

def main():
    """Main execution"""
    logger.info("="*60)
    logger.info("ChromaDB Cleanup and Re-ingestion Script")
    logger.info("="*60)
    
    # Step 1: Clean ChromaDB
    logger.info("\n📧 Step 1: Cleaning ChromaDB collections...")
    if not clean_chromadb():
        logger.error("Failed to clean ChromaDB. Exiting.")
        sys.exit(1)
    
    # Step 2: Re-ingest inventory
    logger.info("\n📦 Step 2: Re-ingesting inventory with image extraction...")
    if not reingest_inventory():
        logger.error("Failed to re-ingest inventory. Exiting.")
        sys.exit(1)
    
    # Step 3: Verify
    logger.info("\n✔️ Step 3: Verifying ingestion...")
    if not verify_ingestion():
        logger.error("Verification failed.")
        sys.exit(1)
    
    logger.info("\n✅ All steps completed successfully!")
    logger.info("The system is now ready with a clean, unified ChromaDB collection.")

if __name__ == "__main__":
    main()