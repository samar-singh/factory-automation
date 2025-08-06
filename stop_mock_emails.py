"""Stop the mock email generation to prevent infinite loop"""

import os
import shutil

# Move mock emails to backup
mock_dir = "mock_emails"
backup_dir = "mock_emails_backup"

if os.path.exists(mock_dir):
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
    shutil.move(mock_dir, backup_dir)
    print(f"✅ Moved {mock_dir} to {backup_dir}")
    print("Mock emails disabled - orchestrator won't process them in loop")
else:
    print("No mock_emails directory found")

# Create empty directory so system doesn't crash
os.makedirs(mock_dir, exist_ok=True)
print(f"✅ Created empty {mock_dir} directory")
