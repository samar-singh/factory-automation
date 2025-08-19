#!/usr/bin/env python3
"""Debug script to check inventory data mismatch"""

from factory_automation.factory_database.vector_db import ChromaDBClient
import pandas as pd

def check_chromadb_data():
    """Check what's stored in ChromaDB for AS RELAXED CROP WB"""
    
    # Initialize ChromaDB client
    client = ChromaDBClient()
    
    # Get all items directly instead of querying with embeddings
    print("Getting all items from ChromaDB...")
    all_items = client.collection.get(limit=1000, include=['metadatas', 'documents'])
    
    # Filter for AS RELAXED CROP WB
    print("Searching for 'AS RELAXED CROP WB' in retrieved items...")
    matching_items = []
    for i, (doc, metadata) in enumerate(zip(all_items['documents'], all_items['metadatas'])):
        if 'RELAXED CROP' in str(doc).upper() or 'RELAXED CROP' in str(metadata).upper():
            matching_items.append((doc, metadata))
    
    if matching_items:
        print(f"\nFound {len(matching_items)} items matching RELAXED CROP:")
        for i, (doc, metadata) in enumerate(matching_items[:5]):  # Show first 5
            print(f"\n--- Result {i+1} ---")
            print(f"Document: {doc[:100]}...")
            print("Metadata:")
            for key, value in metadata.items():
                if key != 'image_base64':  # Skip large base64 data
                    print(f"  {key}: {value}")
    else:
        print("No RELAXED CROP items found in ChromaDB")
    
    # Also check specific TBALTAG codes
    print("\n" + "="*50)
    print("Looking for specific tag codes (TBALTAG0392N to TBALTAG0401N)...")
    
    tag_codes_to_check = [f"TBALTAG0{i}N" for i in range(392, 402)]
    
    for doc, metadata in zip(all_items['documents'], all_items['metadatas']):
        tag_code = metadata.get('tag_code', metadata.get('item_code', ''))
        if tag_code in tag_codes_to_check:
            name = metadata.get('item_name', metadata.get('tag_name', 'N/A'))
            size = metadata.get('size', 'N/A')
            qty = metadata.get('quantity', metadata.get('QTY', 'N/A'))
            print(f"  {tag_code}: {name} - Size: {size}, Qty: {qty}")

def check_excel_data():
    """Check what's in the Excel file"""
    
    excel_files = [
        '/Users/samarsingh/Factory_flow_Automation/inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx'
    ]
    
    for file_path in excel_files:
        try:
            print(f"\n{'='*50}")
            print(f"Checking Excel file: {file_path}")
            
            # Try reading with different header rows
            for header_row in [0, 1]:
                try:
                    df = pd.read_excel(file_path, header=header_row)
                    print(f"\nWith header row {header_row}:")
                    print(f"Columns: {df.columns.tolist()}")
                    
                    # Search for AS RELAXED CROP
                    for col in df.columns:
                        if df[col].dtype == 'object':  # Only search text columns
                            mask = df[col].astype(str).str.contains('RELAXED CROP', case=False, na=False)
                            if mask.any():
                                print(f"\nFound 'RELAXED CROP' in column '{col}':")
                                matching_rows = df[mask]
                                print(matching_rows.head())
                                break
                except Exception as e:
                    print(f"  Error with header {header_row}: {e}")
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

if __name__ == "__main__":
    print("Debugging Inventory Match Issue")
    print("=" * 50)
    
    check_chromadb_data()
    check_excel_data()