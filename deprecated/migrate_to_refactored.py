#!/usr/bin/env python3
"""Migration script to switch to refactored orchestrators with shared tools"""

import os
import shutil
from datetime import datetime

def backup_original_files():
    """Backup original orchestrator files"""
    backup_dir = f"backups/orchestrators_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "factory_automation/factory_agents/orchestrator_v3_agentic.py",
        "factory_automation/factory_agents/orchestrator_v4_proposal.py",
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            dest = os.path.join(backup_dir, os.path.basename(file))
            shutil.copy2(file, dest)
            print(f"✅ Backed up {file} to {dest}")
    
    return backup_dir

def update_imports_in_files():
    """Update import statements in files that use the orchestrators"""
    
    files_to_update = [
        "run_factory_automation.py",
        "factory_automation/factory_ui/gradio_app_live.py",
        "factory_automation/factory_ui/proposal_review_dashboard.py",
    ]
    
    replacements = [
        # Keep the same import names but point to refactored versions
        ("from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3",
         "from factory_automation.factory_agents.orchestrator_v3_agentic_refactored import AgenticOrchestratorV3"),
        
        ("from factory_automation.factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4",
         "from factory_automation.factory_agents.orchestrator_v4_proposal_refactored import ProposalOrchestratorV4"),
         
        # Alternative import patterns
        ("from ..factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3",
         "from ..factory_agents.orchestrator_v3_agentic_refactored import AgenticOrchestratorV3"),
         
        ("from ..factory_agents.orchestrator_v4_proposal import ProposalOrchestratorV4",
         "from ..factory_agents.orchestrator_v4_proposal_refactored import ProposalOrchestratorV4"),
    ]
    
    for file_path in files_to_update:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        for old, new in replacements:
            content = content.replace(old, new)
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Updated imports in {file_path}")
        else:
            print(f"ℹ️  No changes needed in {file_path}")

def create_compatibility_wrappers():
    """Create wrapper files that redirect to refactored versions"""
    
    # Create wrapper for v3
    v3_wrapper = '''"""Compatibility wrapper for refactored orchestrator_v3_agentic"""

# Import from refactored version
from .orchestrator_v3_agentic_refactored import AgenticOrchestratorV3

# Re-export for backward compatibility
__all__ = ['AgenticOrchestratorV3']

# Add deprecation warning
import warnings
warnings.warn(
    "Importing from orchestrator_v3_agentic.py is deprecated. "
    "Please import from orchestrator_v3_agentic_refactored.py directly.",
    DeprecationWarning,
    stacklevel=2
)
'''
    
    # Create wrapper for v4
    v4_wrapper = '''"""Compatibility wrapper for refactored orchestrator_v4_proposal"""

# Import from refactored version
from .orchestrator_v4_proposal_refactored import ProposalOrchestratorV4

# Re-export for backward compatibility
__all__ = ['ProposalOrchestratorV4']

# Add deprecation warning
import warnings
warnings.warn(
    "Importing from orchestrator_v4_proposal.py is deprecated. "
    "Please import from orchestrator_v4_proposal_refactored.py directly.",
    DeprecationWarning,
    stacklevel=2
)
'''
    
    # Save original files with .original extension
    shutil.copy2(
        "factory_automation/factory_agents/orchestrator_v3_agentic.py",
        "factory_automation/factory_agents/orchestrator_v3_agentic.py.original"
    )
    shutil.copy2(
        "factory_automation/factory_agents/orchestrator_v4_proposal.py",
        "factory_automation/factory_agents/orchestrator_v4_proposal.py.original"
    )
    
    # Write wrappers
    with open("factory_automation/factory_agents/orchestrator_v3_agentic.py", 'w') as f:
        f.write(v3_wrapper)
    print("✅ Created compatibility wrapper for orchestrator_v3_agentic.py")
    
    with open("factory_automation/factory_agents/orchestrator_v4_proposal.py", 'w') as f:
        f.write(v4_wrapper)
    print("✅ Created compatibility wrapper for orchestrator_v4_proposal.py")

def verify_shared_tools():
    """Verify that shared tools are properly set up"""
    try:
        from factory_automation.factory_agents.tools import (
            EmailTools,
            InventoryTools,
            OrderTools,
            DocumentTools,
            CustomerTools,
            PaymentTools,
            SupplierTools,
            AttachmentTools
        )
        from factory_automation.factory_agents.tools.tool_factory import ToolFactory
        print("✅ All shared tool modules are importable")
        return True
    except ImportError as e:
        print(f"❌ Error importing shared tools: {e}")
        return False

def main():
    print("=" * 60)
    print("Migration to Refactored Orchestrators")
    print("=" * 60)
    
    # Step 1: Verify shared tools
    print("\n1. Verifying shared tools setup...")
    if not verify_shared_tools():
        print("Please ensure shared tools are properly installed")
        return 1
    
    # Step 2: Backup original files
    print("\n2. Backing up original files...")
    backup_dir = backup_original_files()
    print(f"   Backups saved to: {backup_dir}")
    
    # Step 3: Create compatibility wrappers
    print("\n3. Creating compatibility wrappers...")
    create_compatibility_wrappers()
    
    # Step 4: Update imports (optional - can be skipped if using wrappers)
    print("\n4. Update imports? (y/n)")
    response = input("   This will directly update import statements in your files: ").lower()
    if response == 'y':
        update_imports_in_files()
    else:
        print("   Skipped import updates - using compatibility wrappers")
    
    print("\n" + "=" * 60)
    print("✅ Migration Complete!")
    print("\nThe refactored orchestrators are now in place with:")
    print("- Shared tools architecture for code reuse")
    print("- Compatibility wrappers for backward compatibility")
    print("- Original files backed up to:", backup_dir)
    print("\nYou can now:")
    print("1. Test the application with: python3 run_factory_automation.py")
    print("2. Remove compatibility wrappers once all imports are updated")
    print("3. Delete .original files once migration is verified")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())