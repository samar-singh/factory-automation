"""Test script to verify stock comparison fix in excel_ingestion.py"""

import os
import sys

import pandas as pd

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion


def test_stock_fix():
    """Test the _create_searchable_text method with various stock values"""

    print("Testing stock comparison fix in ExcelInventoryIngestion\n")
    print("=" * 60)

    # Create instance of ExcelInventoryIngestion
    ingestion = ExcelInventoryIngestion()

    # Create test data with various stock values
    test_cases = [
        # Stock value, Expected stock after cleaning, Description
        ("NILL", 0, "String 'NILL' should be converted to 0"),
        ("NIL", 0, "String 'NIL' should be converted to 0"),
        ("100", 100, "String '100' should be converted to 100"),
        (100, 100, "Numeric 100 should remain 100"),
        (0, 0, "Numeric 0 should remain 0"),
        ("1,500", 1500, "String '1,500' with comma should be converted to 1500"),
        ("NA", 0, "String 'NA' should be converted to 0"),
        ("-", 0, "String '-' should be converted to 0"),
        (None, 0, "None/NaN should be converted to 0"),
        ("", 0, "Empty string should be converted to 0"),
        ("invalid", 0, "Invalid string should be converted to 0"),
    ]

    print("\nTesting _clean_stock_value method:")
    print("-" * 60)

    all_passed = True
    for stock_value, expected, description in test_cases:
        # Test the clean_stock_value method
        result = ingestion._clean_stock_value(stock_value)
        passed = result == expected
        status = "✓ PASS" if passed else "✗ FAIL"

        print(
            f"{status} | Input: {repr(stock_value):15} | Expected: {expected:5} | Got: {result:5} | {description}"
        )

        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    print("\nTesting _create_searchable_text method with different stock values:")
    print("-" * 60)

    # Test the searchable text creation with different stock values
    brand = "TestBrand"

    for stock_value, expected_stock, _ in test_cases[:5]:  # Test first 5 cases
        # Create a mock row
        row = pd.Series(
            {"code": "TEST123", "name": "Test Cotton Tag", "stock": stock_value}
        )

        # Generate searchable text
        searchable_text = ingestion._create_searchable_text(row, brand)

        # Check if the correct stock status is in the text
        has_in_stock = "In stock" in searchable_text
        has_out_of_stock = "Out of stock" in searchable_text
        stock_units = f"Stock available: {expected_stock} units" in searchable_text

        print(f"\nStock value: {repr(stock_value)}")
        print(f"Expected cleaned stock: {expected_stock}")
        print("Generated text snippet:")

        # Extract and print the stock-related parts
        text_parts = searchable_text.split(" | ")
        stock_parts = [part for part in text_parts if "stock" in part.lower()]
        for part in stock_parts:
            print(f"  - {part}")

        # Verify correctness
        if expected_stock > 0:
            if has_in_stock and stock_units and not has_out_of_stock:
                print("  ✓ Correctly shows as in stock")
            else:
                print("  ✗ ERROR: Should show as in stock")
                all_passed = False
        else:
            if has_out_of_stock and not has_in_stock:
                print("  ✓ Correctly shows as out of stock")
            else:
                print("  ✗ ERROR: Should show as out of stock")
                all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("\n✅ All tests PASSED! The stock comparison fix is working correctly.")
    else:
        print("\n❌ Some tests FAILED! Please check the implementation.")
    print("=" * 60)


if __name__ == "__main__":
    test_stock_fix()
