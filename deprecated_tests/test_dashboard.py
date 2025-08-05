#!/usr/bin/env python3
"""Test if the Gradio dashboard is working properly."""

import subprocess
import sys
import time

# Add project to path
sys.path.append("./factory_automation")


def test_dashboard():
    """Test the Gradio dashboard."""
    print("Testing Gradio Dashboard...")
    print("=" * 60)

    # Start the dashboard in background
    print("Starting dashboard server...")
    process = subprocess.Popen(
        [sys.executable, "-m", "factory_automation.factory_ui.gradio_app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it time to start
    time.sleep(5)

    # Check if process is running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print("Dashboard failed to start!")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False

    print("Dashboard is running!")
    print("\nYou can access it at: http://localhost:7860")
    print("\nPress Ctrl+C to stop the dashboard")

    try:
        # Keep running until interrupted
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        process.terminate()
        process.wait()

    return True


if __name__ == "__main__":
    test_dashboard()
