#!/usr/bin/env python3
"""Test the updated Excel ingestion with Sheet2 and merged cell handling"""

from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion
from factory_automation.factory_database.vector_db import ChromaDBClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_sheet2_ingestion():
    """Test ingesting Sheet2 with merged cells"""
    
    print("\n" + "="*70)
    print("Testing Updated Excel Ingestion with Sheet2 Support")
    print("="*70 + "\n")
    
    # Initialize ingestion
    ingestion = ExcelInventoryIngestion(embedding_model="stella-400m")
    
    # Test files with Sheet2
    test_files = [
        '/Users/samarsingh/Factory_flow_Automation/inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx',
        '/Users/samarsingh/Factory_flow_Automation/inventory/FM STOCK 2026.xlsx'
    ]
    
    for file_path in test_files:
        print(f"\n📁 Testing: {file_path.split('/')[-1]}")
        print("-"*50)
        
        # Ingest the file
        result = ingestion.ingest_excel_file(file_path)
        
        if result['status'] == 'success':
            print(f"✅ Status: {result['status']}")
            print(f"📊 Total items ingested: {result.get('total_items_ingested', 0)}")
            print("📑 Sheets processed:")
            
            for sheet_info in result.get('sheets_processed', []):
                print(f"   - {sheet_info['sheet']}: {sheet_info['items_ingested']} items")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    # Now test search for AS RELAXED CROP WB
    print("\n" + "="*70)
    print("Testing Search for AS RELAXED CROP WB")
    print("="*70 + "\n")
    
    # Search using ChromaDB directly
    client = ChromaDBClient()
    
    # Search for AS RELAXED CROP WB items
    # Note: ChromaDB doesn't support $contains, we need to get all Sheet2 items and filter
    results = client.collection.get(
        where={"sheet": "Sheet2"},
        limit=500  # Get enough to find all AS RELAXED CROP items
    )
    
    if results and results.get('ids'):
        # Filter for AS RELAXED CROP items
        relaxed_crop_items = []
        for i, metadata in enumerate(results['metadatas']):
            trim_name = metadata.get('trim_name', metadata.get('tag_name', ''))
            if 'RELAXED CROP' in trim_name.upper():
                relaxed_crop_items.append(metadata)
        
        print(f"Found {len(relaxed_crop_items)} AS RELAXED CROP WB items from Sheet2:")
        
        # Group by size
        size_dict = {}
        for metadata in relaxed_crop_items:
            size = metadata.get('size', 'N/A')
            tag_code = metadata.get('tag_code', metadata.get('trim_code', 'N/A'))
            qty = metadata.get('quantity', metadata.get('QTY', 'N/A'))
            
            if size not in size_dict:
                size_dict[size] = []
            size_dict[size].append((tag_code, qty))
        
        # Display sorted by size
        for size in sorted(size_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            for tag_code, qty in size_dict[size]:
                print(f"  Size {size}: {tag_code} (Qty: {qty})")
    else:
        print("❌ No AS RELAXED CROP WB items found in Sheet2")
    
    print("\n✅ Ingestion test complete!")

if __name__ == "__main__":
    test_sheet2_ingestion()