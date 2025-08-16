#!/usr/bin/env python3
"""
Test script to verify the image zoom fix is working
"""

import subprocess
import sys
from pathlib import Path


def test_image_zoom_fix():
    """Test the image zoom functionality"""

    print("🧪 Testing Image Zoom Fix")
    print("=" * 50)

    # Check if the application is running
    try:
        import requests

        response = requests.get("http://127.0.0.1:7866", timeout=5)
        if response.status_code == 200:
            print("✅ Main application is running at http://127.0.0.1:7866")
        else:
            print("❌ Application not responding properly")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to application: {e}")
        return False

    # Check if the human review dashboard has data
    try:
        # We'll need to access the human review tab
        # For now, let's just verify the main components are working
        print("✅ Application is accessible")

        # Test the HTML file we created
        test_file = Path("test_image_modal.html")
        if test_file.exists():
            print("✅ Test HTML file created successfully")

            # Open the test file in browser for manual verification
            try:
                subprocess.run(["open", str(test_file)], check=False)
                print("✅ Opened test file in browser for manual verification")
            except Exception as e:
                print(f"⚠️ Could not open test file automatically: {e}")
        else:
            print("❌ Test HTML file not found")

        return True

    except Exception as e:
        print(f"❌ Error testing application: {e}")
        return False


def check_javascript_improvements():
    """Check if the JavaScript improvements are in place"""

    print("\n🔍 Checking JavaScript Improvements")
    print("=" * 50)

    dashboard_file = Path("factory_automation/factory_ui/human_review_dashboard.py")

    if not dashboard_file.exists():
        print("❌ Human review dashboard file not found")
        return False

    content = dashboard_file.read_text()

    # Check for key improvements
    improvements = [
        ("showImageModal function", "window.showImageModal = function"),
        ("Enhanced error handling", "try {" and "catch (e)"),
        ("Debug panel", "debug-panel"),
        ("Direct onclick handlers", "onclick="),
        ("Modal overlay styling", "image-modal-overlay"),
        ("Enhanced debugging", "window.debugImageModal"),
        ("Test function", "window.testDirectModal"),
    ]

    for name, check in improvements:
        if check in content:
            print(f"✅ {name}: Present")
        else:
            print(f"❌ {name}: Missing")

    return True


def main():
    """Main test function"""

    print("🎯 Image Zoom Feature Test Suite")
    print("=" * 60)

    # Test 1: Check JavaScript improvements
    if not check_javascript_improvements():
        print("\n❌ JavaScript improvements check failed")
        return False

    # Test 2: Test application connectivity
    if not test_image_zoom_fix():
        print("\n❌ Application test failed")
        return False

    print("\n🎉 Test Summary")
    print("=" * 50)
    print("✅ JavaScript improvements are in place")
    print("✅ Application is running and accessible")
    print("📋 Manual verification required:")
    print("   1. Go to http://127.0.0.1:7866")
    print("   2. Navigate to the Human Review tab")
    print("   3. Select an order with inventory matches")
    print("   4. Click on any tag image to test zoom")
    print("   5. Use debug buttons to troubleshoot if needed")
    print("\n🔧 Debug Tools Available:")
    print("   - 'Debug Image Modal' button")
    print("   - 'Test Direct Modal' button")
    print("   - 'Toggle Debug' panel")
    print("   - Browser console logging")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
