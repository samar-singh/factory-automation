#!/usr/bin/env python3
"""Simple re-ingestion script for inventory data"""

import os
import sys
import pandas as pd
from pathlib import Path
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.embeddings_config import EmbeddingsManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main ingestion function"""
    logger.info("Starting simple inventory re-ingestion...")
    
    # Initialize ChromaDB client
    chroma_client = ChromaDBClient(
        persist_directory="./chroma_data",
        collection_name="tag_inventory"  # Single unified collection
    )
    
    # Initialize embeddings with Stella-400M (1024 dimensions)
    logger.info("Initializing Stella-400M embeddings...")
    embeddings = EmbeddingsManager("stella-400m", device="cpu")
    
    # Process each Excel file
    inventory_path = Path("inventory/")
    excel_files = list(inventory_path.glob("*.xlsx")) + list(inventory_path.glob("*.xls"))
    
    logger.info(f"Found {len(excel_files)} Excel files")
    
    total_items = 0
    
    for file_path in excel_files:
        try:
            logger.info(f"Processing {file_path.name}...")
            
            # Extract brand from filename
            brand = file_path.stem.upper()
            brand = brand.replace(" STOCK 2026", "").replace("20", "").strip()
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Process each row
            for idx, row in df.iterrows():
                # Create searchable text
                text_parts = [f"Brand: {brand}"]
                
                # Add any column that might contain useful info
                for col in df.columns:
                    if pd.notna(row[col]) and "Unnamed" not in str(col):
                        text_parts.append(f"{col}: {row[col]}")
                
                text = " | ".join(text_parts)
                
                # Create metadata
                metadata = {
                    "brand": brand,
                    "source_file": file_path.name,
                    "row_index": idx
                }
                
                # Add column values to metadata
                for col in df.columns:
                    if pd.notna(row[col]) and "Unnamed" not in str(col):
                        col_clean = str(col).lower().replace(" ", "_")
                        metadata[col_clean] = str(row[col])[:500]  # Limit length
                
                # Generate embedding
                embedding = embeddings.encode_documents([text])[0].tolist()
                
                # Create unique ID
                doc_id = f"{brand}_{idx}_{hash(text) % 100000}"
                
                # Add to ChromaDB
                chroma_client.collection.add(
                    documents=[text],
                    metadatas=[metadata],
                    ids=[doc_id],
                    embeddings=[embedding]
                )
                
                total_items += 1
                
                if (idx + 1) % 100 == 0:
                    logger.info(f"  Processed {idx + 1} items from {file_path.name}")
            
            logger.info(f"✅ Completed {file_path.name}: {len(df)} items")
            
        except Exception as e:
            logger.error(f"❌ Error processing {file_path.name}: {e}")
    
    logger.info(f"\n✅ Ingestion complete! Total items: {total_items}")
    
    # Verify
    count = chroma_client.collection.count()
    logger.info(f"ChromaDB collection now has {count} items")
    
    # Test search
    logger.info("\nTesting search...")
    results = chroma_client.collection.query(
        query_texts=["Allen Solly TBALWBL0009N"],
        n_results=3
    )
    
    if results and results['ids']:
        logger.info(f"✅ Search test successful! Found {len(results['ids'][0])} results")
    else:
        logger.warning("⚠️ Search test returned no results")

if __name__ == "__main__":
    main()