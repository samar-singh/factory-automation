#!/usr/bin/env python3
"""Reingest all inventory files with Sheet2 support and merged cell handling"""

from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion
from factory_automation.factory_database.vector_db import ChromaDBClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def clean_and_reingest():
    """Clean ChromaDB and reingest all inventory files"""
    
    print("\n" + "="*70)
    print("Cleaning and Reingesting All Inventory with Sheet2 Support")
    print("="*70 + "\n")
    
    # Initialize
    client = ChromaDBClient()
    ingestion = ExcelInventoryIngestion(embedding_model="stella-400m")
    
    # First, clean existing data
    print("🧹 Cleaning existing data...")
    try:
        # Get all existing items
        existing = client.collection.get(limit=10000)
        if existing and existing.get('ids'):
            print(f"Removing {len(existing['ids'])} existing items...")
            # Delete in batches
            batch_size = 500
            for i in range(0, len(existing['ids']), batch_size):
                batch_ids = existing['ids'][i:i+batch_size]
                client.collection.delete(ids=batch_ids)
            print("✅ Existing data cleaned")
    except Exception as e:
        print(f"Note: Could not clean existing data: {e}")
    
    # Reingest all inventory
    print("\n📦 Reingesting all inventory files...")
    results = ingestion.ingest_inventory_folder('/Users/samarsingh/Factory_flow_Automation/inventory')
    
    # Summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70 + "\n")
    
    total_items = 0
    total_sheets = 0
    
    for result in results:
        if result['status'] == 'success':
            file_name = result['file'].split('/')[-1]
            items = result.get('total_items_ingested', 0)
            sheets = result.get('sheets_processed', [])
            
            print(f"✅ {file_name}")
            for sheet_info in sheets:
                print(f"   - {sheet_info['sheet']}: {sheet_info['items_ingested']} items")
            
            total_items += items
            total_sheets += len(sheets)
    
    print(f"\n📊 Total: {total_items} items from {total_sheets} sheets")
    
    # Verify AS RELAXED CROP WB
    print("\n" + "="*70)
    print("Verifying AS RELAXED CROP WB Data")
    print("="*70 + "\n")
    
    results = client.collection.get(
        where={"tag_code": "TBALTAG0392N"},
        limit=5
    )
    
    if results and results.get('ids'):
        print(f"✅ AS RELAXED CROP WB Size 26 found: {results['metadatas'][0]}")
    else:
        print("❌ AS RELAXED CROP WB not found")
    
    print("\n✅ Reingestion complete!")

if __name__ == "__main__":
    clean_and_reingest()