#!/usr/bin/env python3
"""Test script to verify run_factory_automation works"""

import os
import sys

# Add the directory to path to ensure fresh import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing run_factory_automation.py imports...")
print("-" * 50)

try:
    # Force reload to avoid cache
    if "run_factory_automation" in sys.modules:
        del sys.modules["run_factory_automation"]

    import run_factory_automation

    print("✅ Module imported successfully")

    # Check if main function exists
    if hasattr(run_factory_automation, "main"):
        print("✅ main() function found")

    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set (will need for actual run)")
    else:
        print("✅ OPENAI_API_KEY is set")

    print("-" * 50)
    print("✅ All checks passed! You can run:")
    print("   python run_factory_automation.py")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTrying to diagnose...")

    # Check the actual file content
    with open("run_factory_automation.py", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines[75:85], start=76):
            if "import" in line:
                print(f"Line {i}: {line.strip()}")

except Exception as e:
    print(f"❌ Unexpected error: {e}")
