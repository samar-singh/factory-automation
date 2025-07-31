#!/usr/bin/env python3
"""Launch the Gradio dashboard with live inventory search."""

import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.append("./factory_automation")

# Import Gradio app
from factory_automation.factory_ui.gradio_app import create_dashboard  # noqa: E402


def main():
    print("Launching Factory Automation Dashboard...")
    print("=" * 60)
    print("Opening in your browser at: http://localhost:7860")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Create and launch the dashboard
    app = create_dashboard()
    app.launch(
        server_name="0.0.0.0",  # Allow external connections
        server_port=7860,
        share=False,  # Set to True to create a public link
        quiet=False,
    )


if __name__ == "__main__":
    main()
