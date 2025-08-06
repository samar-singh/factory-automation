"""Check which port the system is running on"""

import requests

# Check common ports
ports = [7860, 7861, 7862, 8080, 8000]

for port in ports:
    try:
        response = requests.get(f"http://localhost:{port}", timeout=1)
        if response.status_code == 200:
            print(f"✅ Factory Automation is running on port {port}")
            print(f"   URL: http://localhost:{port}")
            break
    except:
        continue
else:
    print("❌ Could not find running Factory Automation on any common port")

# Also check if Safari specific issue
print("\nIf Safari still can't open the page, try:")
print("1. Use Chrome or Firefox instead")
print("2. Try http://127.0.0.1:7860 instead of localhost")
print(
    "3. Check Safari > Preferences > Privacy > Prevent cross-site tracking (disable temporarily)"
)
print("4. Clear Safari cache: Develop > Empty Caches")
