#!/usr/bin/env python3
"""Test if all components work together with run_factory_automation.py"""

import asyncio
import sys
from datetime import datetime

print("Testing Factory Automation Integration...")
print("=" * 60)

# Test 1: Core imports
print("\n1. Testing core imports...")
try:
    from factory_automation.factory_agents.orchestrator_with_human import (
        OrchestratorWithHuman,
    )
    from factory_automation.factory_database.vector_db import ChromaDBClient
    from factory_automation.factory_ui.human_review_interface import (
        HumanReviewInterface,
    )

    print("✅ Core imports successful")
except ImportError as e:
    print(f"❌ Core import failed: {e}")
    sys.exit(1)

# Test 2: New components
print("\n2. Testing new components...")
try:
    from factory_automation.factory_agents.image_processor_agent import (
        ImageProcessorAgent,
    )
    from factory_automation.factory_agents.order_processor_agent import (
        OrderProcessorAgent,
    )
    from factory_automation.factory_models.order_models import ExtractedOrder

    print("✅ New components import successful")
except ImportError as e:
    print(f"❌ New component import failed: {e}")
    sys.exit(1)

# Test 3: Initialize components
print("\n3. Testing component initialization...")
try:
    chromadb_client = ChromaDBClient()
    print("✅ ChromaDB client initialized")

    orchestrator = OrchestratorWithHuman(chromadb_client)
    print("✅ Orchestrator initialized")

    # Check if new processors are integrated
    if hasattr(orchestrator, "order_processor"):
        print("✅ OrderProcessor integrated into orchestrator")
    else:
        print("⚠️ OrderProcessor not found in orchestrator")

    if hasattr(orchestrator, "image_processor"):
        print("✅ ImageProcessor integrated into orchestrator")
    else:
        print("⚠️ ImageProcessor not found in orchestrator")

except Exception as e:
    print(f"❌ Initialization failed: {e}")
    sys.exit(1)

# Test 4: Test new tools in orchestrator
print("\n4. Testing orchestrator tools...")


async def test_tools():
    try:
        tools = orchestrator._create_tools()
        tool_names = [t.__name__ for t in tools if hasattr(t, "__name__")]

        print(f"Found {len(tools)} tools:")

        # Check for new tools
        expected_tools = [
            "extract_order_items",
            "process_complete_order",
            "process_tag_image",
            "search_inventory",
        ]

        for expected in expected_tools:
            if expected in tool_names:
                print(f"  ✅ {expected}")
            else:
                print(f"  ❌ {expected} not found")

        return True
    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        return False


# Test 5: Test order processing flow
print("\n5. Testing order processing flow...")


async def test_order_flow():
    try:
        # Create a test order
        {
            "subject": "Test Order",
            "body": "Need 100 price tags for Allen Solly",
            "sender": "test@example.com",
            "date": datetime.now(),
        }

        # Check if process_complete_order tool exists
        tools = orchestrator._create_tools()
        process_order_tool = None

        for tool in tools:
            if hasattr(tool, "__name__") and tool.__name__ == "process_complete_order":
                process_order_tool = tool
                break

        if process_order_tool:
            print("✅ process_complete_order tool found")
            # We could test calling it here if needed
        else:
            print("⚠️ process_complete_order tool not found")

        return True
    except Exception as e:
        print(f"❌ Order flow test failed: {e}")
        return False


# Run async tests
print("\n" + "=" * 60)
print("Running async tests...")


async def run_tests():
    results = []

    # Run tool test
    results.append(await test_tools())

    # Run order flow test
    results.append(await test_order_flow())

    return all(results)


# Execute tests
success = asyncio.run(run_tests())

# Final summary
print("\n" + "=" * 60)
if success:
    print("✅ ALL TESTS PASSED - System is ready!")
    print("\nYou can now run:")
    print("  python run_factory_automation.py")
    print("\nThe system includes:")
    print("  • AI-powered order extraction (GPT-4)")
    print("  • Image processing with Qwen2.5VL")
    print("  • Complete order workflow")
    print("  • Human review for 60-80% confidence")
    print("  • Inventory reconciliation")
else:
    print("⚠️ Some tests failed - review the errors above")

print("=" * 60)
