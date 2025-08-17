#!/usr/bin/env python3
"""Ingest Sheet2 data from Allen Solly Excel file into ChromaDB"""

import pandas as pd
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.embeddings_config import EmbeddingsManager
import hashlib

def ingest_sheet2_data():
    """Ingest Sheet2 data into ChromaDB"""
    
    # Initialize ChromaDB and embeddings
    print("Initializing ChromaDB and embeddings...")
    chromadb_client = ChromaDBClient()
    embeddings_manager = EmbeddingsManager(model_name="stella-400m")
    
    # Read Sheet2 data
    file_path = '/Users/samarsingh/Factory_flow_Automation/inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx'
    print(f"Reading Sheet2 from {file_path}...")
    df = pd.read_excel(file_path, sheet_name='Sheet2', header=0)
    
    print(f"Found {len(df)} rows in Sheet2")
    print(f"Columns: {df.columns.tolist()}")
    
    # Prepare data for ingestion
    documents = []
    metadatas = []
    ids = []
    
    for idx, row in df.iterrows():
        # Skip rows with no trim name
        trim_name = str(row.get('TRIM NAME', '')).strip()
        if not trim_name or trim_name == 'nan':
            continue
            
        trim_code = str(row.get('TRIM CODE', '')).strip()
        size = str(row.get('SIZE', '')).strip()
        qty = str(row.get('QTY', 0))
        
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
        
        if trim_name and 'RELAXED CROP' in trim_name.upper():
            print(f"  Found RELAXED CROP item: {trim_name} - {trim_code} - Size: {size}, Qty: {qty}")
    
    print(f"\nPrepared {len(documents)} items for ingestion")
    
    if documents:
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = embeddings_manager.encode_documents(documents)
        
        # Add to ChromaDB
        print("Adding to ChromaDB...")
        chromadb_client.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Successfully ingested {len(documents)} items from Sheet2")
        
        # Verify the data was added
        print("\nVerifying ingestion...")
        test_results = chromadb_client.collection.get(
            where={"sheet": "Sheet2"},
            limit=5
        )
        
        if test_results and test_results.get('metadatas'):
            print(f"Verified {len(test_results['metadatas'])} items from Sheet2 in ChromaDB")
            for metadata in test_results['metadatas'][:3]:
                print(f"  - {metadata.get('item_name')} ({metadata.get('tag_code')})")
    else:
        print("No valid items found to ingest")

if __name__ == "__main__":
    ingest_sheet2_data()