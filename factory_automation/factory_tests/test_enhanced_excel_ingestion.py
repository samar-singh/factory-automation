#!/usr/bin/env python3
"""Test enhanced Excel ingestion with image extraction and data recovery"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory_automation.factory_rag.intelligent_excel_ingestion import IntelligentExcelIngestion
from factory_automation.factory_database.vector_db import ChromaDBClient


def test_enhanced_ingestion():
    """Test the enhanced ingestion with image extraction and recovery"""
    
    print("="*60)
    print("TESTING ENHANCED EXCEL INGESTION")
    print("="*60)
    
    # Initialize ingestion system
    print("\n1. Initializing system...")
    chroma_client = ChromaDBClient(collection_name="test_enhanced_ingestion")
    
    # Test with vision model disabled first (faster)
    # Use minilm for testing since it doesn't require API keys
    ingestion = IntelligentExcelIngestion(
        chroma_client=chroma_client,
        embedding_model="minilm",  # Use minilm for testing (no API needed)
        use_vision_model=False  # Set to True if you have vision model configured
    )
    
    # Test files
    test_files = [
        "inventory/PETER ENGLAND STOCK 2026.xlsx",
        "inventory/MYNTRA STOCK 2026.xlsx",
        "inventory/ALLEN SOLLY (AS) STOCK 2026.xlsx"
    ]
    
    results = []
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"\n❌ File not found: {file_path}")
            continue
            
        print(f"\n2. Processing: {file_path}")
        print("-"*40)
        
        result = ingestion.ingest_excel_file(file_path)
        results.append(result)
        
        if result["status"] == "success":
            print(f"✅ Successfully processed {file_path}")
            print(f"   - Total items ingested: {result['items_ingested']}")
            print(f"   - Items with images: {result.get('items_with_images', 0)}")
            print(f"   - Items with generated names: {result.get('items_with_generated_names', 0)}")
            print(f"   - Rows recovered: {result.get('rows_recovered', 0)}")
            print(f"   - Column mapping: {result.get('column_mapping', {})}")
        else:
            print(f"❌ Failed to process {file_path}")
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    # Test search on ingested data
    print("\n3. Testing search on ingested data...")
    print("-"*40)
    
    test_queries = [
        "peter england blue shirt",
        "myntra tag",
        "allen solly trim",
        "items with no name",
        "recovered items"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        try:
            results = chroma_client.search(query, n_results=3)
            print(f"   Found {len(results['documents'][0])} results")
            
            if results['documents'][0]:
                for i, (doc, meta, dist) in enumerate(zip(
                    results['documents'][0][:2],
                    results['metadatas'][0][:2],
                    results['distances'][0][:2]
                )):
                    print(f"\n   Result {i+1} (distance: {dist:.3f}):")
                    print(f"   - Item: {meta.get('item_name', 'N/A')}")
                    print(f"   - Brand: {meta.get('brand', 'N/A')}")
                    print(f"   - Code: {meta.get('item_code', 'N/A')}")
                    print(f"   - Has Image: {meta.get('has_image', False)}")
                    print(f"   - Name Source: {meta.get('name_source', 'original')}")
                    
        except Exception as e:
            print(f"   Error searching: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_ingested = sum(r['items_ingested'] for r in results if r['status'] == 'success')
    total_images = sum(r.get('items_with_images', 0) for r in results if r['status'] == 'success')
    total_recovered = sum(r.get('rows_recovered', 0) for r in results if r['status'] == 'success')
    
    print(f"Total items ingested: {total_ingested}")
    print(f"Total items with images: {total_images}")
    print(f"Total rows recovered: {total_recovered}")
    
    if total_recovered > 0:
        print(f"\n🎉 Successfully recovered {total_recovered} rows that would have been lost!")
    
    # Cleanup test collection
    print("\n4. Cleaning up test collection...")
    try:
        chroma_client.client.delete_collection("test_enhanced_ingestion")
        print("✅ Test collection deleted")
    except:
        pass
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


def test_image_extraction_only():
    """Test just the image extraction functionality"""
    
    print("\n" + "="*60)
    print("TESTING IMAGE EXTRACTION")
    print("="*60)
    
    from factory_automation.factory_rag.intelligent_excel_ingestion import IntelligentExcelIngestion
    
    ingestion = IntelligentExcelIngestion(embedding_model="minilm", use_vision_model=False)
    
    test_file = "inventory/PETER ENGLAND STOCK 2026.xlsx"
    
    if os.path.exists(test_file):
        print(f"\nExtracting images from: {test_file}")
        images = ingestion.extract_embedded_images(test_file)
        
        print(f"Found {len(images)} embedded images")
        
        if images:
            print("\nImage positions:")
            for row, img_data in list(images.items())[:5]:  # Show first 5
                print(f"  - Row {row}: {img_data['filename']} ({len(img_data['base64'])} bytes base64)")
        else:
            print("No embedded images found - the Excel may use image indicators instead")
    else:
        print(f"Test file not found: {test_file}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test enhanced Excel ingestion")
    parser.add_argument("--images-only", action="store_true", help="Test only image extraction")
    parser.add_argument("--with-vision", action="store_true", help="Enable vision model for tag name generation")
    
    args = parser.parse_args()
    
    if args.images_only:
        test_image_extraction_only()
    else:
        if args.with_vision:
            print("Note: Vision model enabled - this will use Together.ai API")
        test_enhanced_ingestion()