#!/usr/bin/env python3
"""Launch the AI-enhanced Gradio application"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_ui.gradio_app_ai import launch_app

if __name__ == "__main__":
    print("\n🚀 Launching AI-Enhanced Factory Automation Dashboard...")
    print("   URL: http://localhost:7860")
    print("   Press Ctrl+C to stop\n")

    launch_app()
