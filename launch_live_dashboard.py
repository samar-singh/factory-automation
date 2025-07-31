#!/usr/bin/env python3
"""Launch the enhanced Gradio dashboard with live inventory search."""

import socket
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.append("./factory_automation")

# Import the live dashboard
from factory_automation.factory_ui.gradio_app_live import (  # noqa: E402
    create_live_dashboard,
)


def find_free_port(start_port=7860):
    """Find a free port starting from the given port."""
    port = start_port
    while port < start_port + 100:  # Try 100 ports
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                port += 1
    return start_port


def main():
    print("Launching Factory Automation Dashboard (Live Version)...")
    print("=" * 60)
    print("Features:")
    print("- Live inventory search with 478 items")
    print("- Order processing with confidence scoring")
    print("- System status monitoring")

    # Find available port
    port = find_free_port(7860)
    if port != 7860:
        print(f"\nNote: Port 7860 was busy, using port {port} instead")

    print(f"\nOpening in your browser at: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Create and launch the dashboard
    app = create_live_dashboard()
    try:
        app.launch(
            server_name="0.0.0.0",  # Allow external connections
            server_port=port,
            share=False,  # Set to True to create a public link
            quiet=False,
            inbrowser=True,  # Automatically open in browser
        )
    except KeyboardInterrupt:
        print("\nShutting down dashboard...")
    except Exception as e:
        print(f"\nError launching dashboard: {e}")
        print("Try running with a different port or checking your firewall settings.")


if __name__ == "__main__":
    main()
