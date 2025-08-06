"""Debug version of run_factory_automation.py"""

import os
import sys

# Add debugging
print("Starting debug run...")
print(f"Python: {sys.executable}")
print(f"Working dir: {os.getcwd()}")

# Check if .env is loaded
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
print(
    f"OPENAI_API_KEY loaded: {'Yes' if api_key else 'No'} (length: {len(api_key) if api_key else 0})"
)

# Now run the main script
try:
    import run_factory_automation

    print("\nImported run_factory_automation successfully")

    # Check port selection
    print(f"Selected port: {run_factory_automation.SELECTED_PORT}")

    # Run main
    run_factory_automation.main()
except Exception as e:
    print(f"\nError: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
