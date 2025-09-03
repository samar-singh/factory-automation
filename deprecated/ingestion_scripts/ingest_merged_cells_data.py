#!/usr/bin/env python3
"""Properly ingest Sheet2 data with merged cells handling"""

import pandas as pd
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.embeddings_config import EmbeddingsManager
import hashlib

def ingest_sheet2_with_merged_cells():
    """Ingest Sheet2 data handling merged cells properly"""
    
    # Initialize ChromaDB and embeddings
    print("Initializing ChromaDB and embeddings...")
    chromadb_client = ChromaDBClient()
    embeddings_manager = EmbeddingsManager(model_name="stella-400m")
    
    # Read Sheet2 data
    file_path = '/Users/samarsingh/Factory_flow_Automation/inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx'
    print(f"Reading Sheet2 from {file_path} with merged cell handling...")
    df = pd.read_excel(file_path, sheet_name='Sheet2', header=0)
    
    # Forward fill the TRIM NAME column to handle merged cells
    df['TRIM NAME'] = df['TRIM NAME'].fillna(method='ffill')
    
    print(f"Found {len(df)} rows in Sheet2")
    print(f"Columns: {df.columns.tolist()}")
    
    # Prepare data for ingestion
    documents = []
    metadatas = []
    ids = []
    
    ingested_count = 0
    relaxed_crop_count = 0
    
    for idx, row in df.iterrows():
        # Skip rows with no trim code or where trim code is NaN
        trim_code = str(row.get('TRIM CODE', '')).strip()
        if not trim_code or trim_code == 'nan':
            continue
            
        trim_name = str(row.get('TRIM NAME', '')).strip()
        if not trim_name or trim_name == 'nan':
            continue
            
        size = str(row.get('SIZE', '')).strip()
        qty = str(row.get('QTY', 0))
        
        # Skip if size is nan
        if size == 'nan':
            continue
        
        # Create document text for embedding
        doc_text = f"{trim_name} {trim_code} size {size}"
        
        # Create metadata
        metadata = {
            'item_name': trim_name,
            'tag_name': trim_name,
            'tag_code': trim_code,
            'item_code': trim_code,
            'size': size,
            'quantity': qty,
            'QTY': qty,
            'brand': 'ALLEN SOLLY (AS)',
            'source_document': 'ALLEN SOLLY (AS) STOCK 2026.xlsx - Sheet2',
            'sheet': 'Sheet2'
        }
        
        # Create unique ID
        doc_id = f"as_sheet2_{trim_code}_{size}_{hashlib.md5(doc_text.encode()).hexdigest()[:8]}"
        
        documents.append(doc_text)
        metadatas.append(metadata)
        ids.append(doc_id)
        
        if 'RELAXED CROP' in trim_name.upper():
            relaxed_crop_count += 1
            print(f"  AS RELAXED CROP: {trim_code} - Size: {size}, Qty: {qty}")
        
        ingested_count += 1
    
    print(f"\nPrepared {len(documents)} items for ingestion")
    print(f"Including {relaxed_crop_count} AS RELAXED CROP WB variations")
    
    if documents:
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = embeddings_manager.encode_documents(documents)
        
        # First, remove any existing Sheet2 data to avoid duplicates
        print("Removing old Sheet2 data...")
        try:
            # Get all existing Sheet2 items
            existing = chromadb_client.collection.get(
                where={"sheet": "Sheet2"},
                limit=1000
            )
            if existing and existing.get('ids'):
                print(f"Removing {len(existing['ids'])} old Sheet2 items...")
                chromadb_client.collection.delete(ids=existing['ids'])
        except Exception as e:
            print(f"Note: Could not remove old data: {e}")
        
        # Add to ChromaDB
        print("Adding new data to ChromaDB...")
        chromadb_client.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Successfully ingested {len(documents)} items from Sheet2")
        
        # Verify AS RELAXED CROP WB data
        print("\nVerifying AS RELAXED CROP WB data...")
        test_results = chromadb_client.collection.get(
            where={"tag_code": "TBALTAG0392N"},
            limit=1
        )
        
        if test_results and test_results.get('metadatas'):
            print("✓ Found TBALTAG0392N (AS RELAXED CROP WB Size 26)")
            
        # Check a few more sizes
        for code in ["TBALTAG0394N", "TBALTAG0397N", "TBALTAG0401N"]:
            test_results = chromadb_client.collection.get(
                where={"tag_code": code},
                limit=1
            )
            if test_results and test_results.get('metadatas'):
                metadata = test_results['metadatas'][0]
                print(f"✓ Found {code} - Size {metadata.get('size')}, Qty: {metadata.get('quantity')}")
    else:
        print("No valid items found to ingest")

if __name__ == "__main__":
    ingest_sheet2_with_merged_cells()