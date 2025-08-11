#!/usr/bin/env python3
"""Test intelligent ingestion with all Excel files in inventory folder"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.intelligent_excel_ingestion import (
    IntelligentExcelIngestion,
)


def test_all_files():
    """Test intelligent ingestion on all Excel files"""

    print("🧠 Testing Intelligent Excel Ingestion on ALL Files")
    print("=" * 80)

    # Initialize ChromaDB
    print("\n📊 Initializing ChromaDB...")
    chroma_client = ChromaDBClient(collection_name="test_intelligent_ingestion")

    # Initialize intelligent ingestion with Stella for faster testing
    print("🤖 Initializing intelligent ingestion (using Stella for speed)...")
    ingestion = IntelligentExcelIngestion(
        chroma_client=chroma_client,
        embedding_model="stella-400m",  # Using Stella for faster testing
    )

    # Get all Excel files
    inventory_folder = Path("inventory")
    excel_files = sorted(
        list(inventory_folder.glob("*.xlsx")) + list(inventory_folder.glob("*.xls"))
    )

    print(f"\n📁 Found {len(excel_files)} Excel files to process")
    print("-" * 80)

    # Track results
    all_results = []
    total_items = 0
    successful_files = 0
    failed_files = 0
    processing_times = []

    # Process each file
    for idx, file_path in enumerate(excel_files, 1):
        file_name = file_path.name
        print(f"\n[{idx}/{len(excel_files)}] Processing: {file_name}")
        print("-" * 40)

        start_time = time.time()

        try:
            result = ingestion.ingest_excel_file(str(file_path))
            processing_time = time.time() - start_time
            processing_times.append(processing_time)

            if result["status"] == "success":
                successful_files += 1
                items = result.get("items_ingested", 0)
                total_items += items

                print("✅ SUCCESS")
                print(f"   • Items ingested: {items}")
                print(f"   • Brand detected: {result.get('brand', 'Unknown')}")
                print(f"   • Processing time: {processing_time:.2f}s")

                # Show column mapping
                mapping = result.get("column_mapping", {})
                if mapping:
                    print("   • Columns mapped:")
                    for original, mapped in mapping.items():
                        print(f"     - {original} → {mapped}")
            else:
                failed_files += 1
                print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                print(f"   • Processing time: {processing_time:.2f}s")

            all_results.append(result)

        except Exception as e:
            failed_files += 1
            print(f"❌ ERROR: {str(e)}")
            all_results.append(
                {"status": "error", "file": str(file_path), "error": str(e)}
            )

    # Print summary
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)

    print("\n📈 Overall Statistics:")
    print(f"   • Total files processed: {len(excel_files)}")
    print(
        f"   • Successful: {successful_files} ({successful_files/len(excel_files)*100:.1f}%)"
    )
    print(f"   • Failed: {failed_files} ({failed_files/len(excel_files)*100:.1f}%)")
    print(f"   • Total items ingested: {total_items}")
    if processing_times:
        print(
            f"   • Average processing time: {sum(processing_times)/len(processing_times):.2f}s"
        )
        print(f"   • Total processing time: {sum(processing_times):.2f}s")

    # Show success details
    print("\n✅ Successfully Processed Files:")
    for result in all_results:
        if result["status"] == "success":
            file_name = Path(result["file"]).name
            items = result.get("items_ingested", 0)
            brand = result.get("brand", "Unknown")
            print(f"   • {file_name}: {items} items ({brand})")

    # Show failed files
    if failed_files > 0:
        print("\n❌ Failed Files:")
        for result in all_results:
            if result["status"] == "error":
                file_name = Path(result["file"]).name
                error = result.get("error", "Unknown error")
                print(f"   • {file_name}: {error[:100]}")

    # Show learned patterns
    print("\n🧠 Learned Column Patterns:")
    patterns = ingestion.get_learned_mappings()
    for col_type, pattern_list in patterns.items():
        if pattern_list:
            unique_patterns = list(set(pattern_list))[
                :10
            ]  # Show max 10 unique patterns
            print(f"   • {col_type}: {', '.join(unique_patterns)}")

    # ChromaDB stats
    collection = chroma_client.collection
    print("\n🗄️  ChromaDB Collection Stats:")
    print(f"   • Collection name: {collection.name}")
    print(f"   • Total documents: {collection.count()}")

    # Success rate analysis
    print("\n📊 Success Rate Analysis:")
    if successful_files == len(excel_files):
        print("   🎉 PERFECT! All files processed successfully!")
    elif successful_files >= len(excel_files) * 0.8:
        print("   ✅ EXCELLENT! Over 80% success rate")
    elif successful_files >= len(excel_files) * 0.6:
        print("   🆗 GOOD! Over 60% success rate")
    else:
        print("   ⚠️  NEEDS IMPROVEMENT! Less than 60% success rate")

    # Compare with old system
    print("\n🔄 Comparison with Old System:")
    print("   Old system (hardcoded): ~25% success rate (3/12 files)")
    print(
        f"   New intelligent system: {successful_files/len(excel_files)*100:.1f}% success rate"
    )
    print(
        f"   Improvement: {(successful_files/len(excel_files)*100 - 25):.1f}% better!"
    )

    return all_results


if __name__ == "__main__":
    results = test_all_files()

    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)
