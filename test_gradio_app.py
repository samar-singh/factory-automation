#!/usr/bin/env python3
"""Test the Gradio app functions directly"""

import sys

sys.path.append(".")

# Import the gradio app module
from factory_automation.factory_ui import gradio_app_live

print("=" * 80)
print("TESTING GRADIO APP FUNCTIONS")
print("=" * 80)

# Test the process_order function
print("\n1. Testing process_order function")
print("-" * 50)

# Create test order text
test_order = """Dear Interface Team,
Please find our order for the following items:
1. SYMBOL hand tag - 500 pieces
2. Allen Solly main tag - 300 pieces
3. Peter England label - 200 pieces

Please confirm availability and delivery timeline.

Best regards,
Test Customer"""

try:
    # Call the function directly (without UI)
    result = gradio_app_live.process_order(test_order)
    print("Process order succeeded!")
    print(f"Result type: {type(result)}")
    if hasattr(result, "shape"):
        print(f"Result shape: {result.shape}")
    print("\nFirst few rows:")
    print(result.head() if hasattr(result, "head") else result)
except Exception as e:
    print(f"ERROR in process_order: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

# Test the search_inventory function
print("\n\n2. Testing search_inventory function")
print("-" * 50)

test_queries = ["SYMBOL tag", "Allen Solly", "blue cotton"]

for query in test_queries:
    print(f"\nSearching for: '{query}'")
    try:
        result = gradio_app_live.search_inventory(query)
        print("Search succeeded!")
        if hasattr(result, "shape"):
            print(f"Found {len(result)} results")
        print(result.head() if hasattr(result, "head") else result)
    except Exception as e:
        print(f"ERROR in search: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("GRADIO APP TEST COMPLETE")
print("=" * 80)
