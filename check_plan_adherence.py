#!/usr/bin/env python3
"""
Plan Adherence Validator
Ensures all changes follow the locked implementation plan
Run this before commits to validate changes
"""

import sys
from pathlib import Path
from typing import List


class PlanValidator:
    """Validates that changes adhere to the locked implementation plan"""
    
    def __init__(self):
        self.plan_lock_file = Path("docs/IMPLEMENTATION_PLAN_LOCK.md")
        self.violations: List[str] = []
        self.warnings: List[str] = []
        self.current_phase = None
        self.load_plan_status()
    
    def load_plan_status(self):
        """Load current phase from plan lock file"""
        if not self.plan_lock_file.exists():
            self.violations.append(f"❌ Plan lock file not found: {self.plan_lock_file}")
            return
        
        with open(self.plan_lock_file, 'r') as f:
            content = f.read()
            
        # Extract current phase
        if "**Current Phase**:" in content:
            phase_line = [line for line in content.split('\n') if "**Current Phase**:" in line]
            if phase_line:
                # Parse phase from line like "**Current Phase**: Phase 1 - Database Foundation"
                # or "**Current Phase**: Phase 1 COMPLETED → Ready for Phase 2"
                phase_text = phase_line[0].split("**Current Phase**:")[1].strip()
                if "Not Started" in phase_text:
                    self.current_phase = 0
                elif "Phase" in phase_text:
                    # Extract just the phase number
                    import re
                    phase_match = re.search(r'Phase (\d+)', phase_text)
                    if phase_match:
                        phase_num = int(phase_match.group(1))
                        # If it says COMPLETED, we're ready for the next phase
                        if "COMPLETED" in phase_text and "Ready for Phase" in phase_text:
                            next_match = re.search(r'Ready for Phase (\d+)', phase_text)
                            if next_match:
                                self.current_phase = int(next_match.group(1)) - 1  # We completed the previous
                        else:
                            self.current_phase = phase_num
    
    def check_v4_removal_status(self):
        """Ensure V4 files are handled according to current phase"""
        v4_files = {
            # V4 files moved to deprecated in Phase 7
            "deprecated/orchestrators/orchestrator_v4_proposal.py": "Orchestrator V4",
            "deprecated/ui/proposal_review_dashboard.py": "Proposal Review Dashboard"
        }
        
        # V4 should only be removed in Phase 7
        if self.current_phase and self.current_phase < 7:
            # Check that V4 files still exist (shouldn't be removed yet)
            for file_path, name in v4_files.items():
                if not Path(file_path).exists():
                    if Path(f"deprecated/{Path(file_path).name}").exists():
                        self.violations.append(
                            f"❌ {name} moved to deprecated too early (Phase 7 required, current: Phase {self.current_phase})"
                        )
        elif self.current_phase == 7:
            # Check that V4 files are being moved to deprecated
            for file_path, name in v4_files.items():
                if Path(file_path).exists():
                    if not Path(f"deprecated/{Path(file_path).name}").exists():
                        self.warnings.append(
                            f"⚠️ Phase 7: {name} should be moved to deprecated/"
                        )
    
    def check_irreversible_actions(self):
        """Verify that email sending and inventory reservation require approval"""
        critical_patterns = {
            "send_email": ["gmail", "send", "email"],
            "reserve_inventory": ["inventory", "reserve", "commit"]
        }
        
        # Check tool factory for proper classification
        tool_factory_path = Path("factory_automation/factory_agents/tools/tool_factory.py")
        if tool_factory_path.exists():
            with open(tool_factory_path, 'r') as f:
                content = f.read()
                
            # Check for irreversible action markers
            if "send_email_response" in content:
                if "irreversible" not in content.lower() and self.current_phase >= 2:
                    self.warnings.append(
                        "⚠️ Email sending should be marked as irreversible action (Phase 2)"
                    )
    
    def check_database_schema(self):
        """Check if action_audit table is added when in Phase 1"""
        if self.current_phase == 1:
            models_path = Path("factory_automation/factory_database/models.py")
            if models_path.exists():
                with open(models_path, 'r') as f:
                    content = f.read()
                
                if "class ActionAudit" not in content:
                    self.warnings.append(
                        "⚠️ Phase 1: ActionAudit table should be added to models.py"
                    )
    
    def check_phase_alignment(self):
        """Check if changes align with current phase"""
        phase_files = {
            1: ["factory_database/models.py"],  # Database changes
            2: ["action_classifier.py", "tools/tool_factory.py"],  # Classification
            3: ["orchestrator_v3_agentic.py"],  # Orchestrator enhancement
            4: ["orchestrator_v3_agentic.py"],  # Two-tier logic
            5: ["human_review_dashboard.py"],  # UI updates
            6: ["orchestrator_v3_agentic.py", "human_review_dashboard.py"],  # Approval flow
            7: ["deprecated/"],  # V4 removal
            8: ["tests/"],  # Testing
            9: ["config.yaml", "CLAUDE.md"]  # Production prep
        }
        
        if self.current_phase and self.current_phase in phase_files:
            expected_files = phase_files[self.current_phase]
            # This is informational - actual file checking would need git diff
            print(f"📋 Phase {self.current_phase} focuses on: {', '.join(expected_files)}")
    
    def check_core_principles(self):
        """Ensure core principles are not violated"""
        # Check that customer emails always require approval
        orchestrator_path = Path("factory_automation/factory_agents/orchestrator_v3_agentic.py")
        if orchestrator_path.exists() and self.current_phase >= 4:
            with open(orchestrator_path, 'r') as f:
                content = f.read()
            
            # Look for automatic email sending without approval
            dangerous_patterns = [
                ("await.*send.*email", "Emails should require approval"),
                ("auto.*send", "Auto-sending emails violates core principle"),
            ]
            
            for pattern, message in dangerous_patterns:
                if pattern in content.lower() and "approval" not in content.lower():
                    self.warnings.append(f"⚠️ Potential violation: {message}")
    
    def validate(self) -> bool:
        """Run all validation checks"""
        print("🔍 Validating changes against Implementation Plan...")
        print(f"📊 Current Phase: {self.current_phase if self.current_phase else 'Not Started'}\n")
        
        # Run all checks
        self.check_v4_removal_status()
        self.check_irreversible_actions()
        self.check_database_schema()
        self.check_phase_alignment()
        self.check_core_principles()
        
        # Report results
        if self.violations:
            print("❌ PLAN VIOLATIONS DETECTED:")
            for violation in self.violations:
                print(f"  {violation}")
            print("\n🛑 Commit blocked. Fix violations or use 'OVERRIDE PLAN' command.")
            return False
        
        if self.warnings:
            print("⚠️ WARNINGS (review but not blocking):")
            for warning in self.warnings:
                print(f"  {warning}")
            print()
        
        print("✅ Changes adhere to implementation plan")
        print("📋 Plan ID: PLAN-2025-01-TWOTIER")
        return True
    
    def get_next_actions(self):
        """Suggest next actions based on current phase"""
        next_actions = {
            0: "Start Phase 1: Create action_audit table in models.py",
            1: "Complete Phase 1: Test database changes, then start Phase 2",
            2: "Complete Phase 2: Create action classifier, then start Phase 3",
            3: "Complete Phase 3: Enhance orchestrator, then start Phase 4",
            4: "Complete Phase 4: Implement two-tier logic, then start Phase 5",
            5: "Complete Phase 5: Update UI, then start Phase 6",
            6: "Complete Phase 6: Implement approval flow, then start Phase 7",
            7: "Complete Phase 7: Remove V4 components, then start Phase 8",
            8: "Complete Phase 8: Run integration tests, then start Phase 9",
            9: "Complete Phase 9: Prepare for production deployment"
        }
        
        if self.current_phase is not None and self.current_phase in next_actions:
            print(f"\n📍 Next Action: {next_actions[self.current_phase]}")


def main():
    """Main entry point"""
    validator = PlanValidator()
    
    # Check for override flag
    if len(sys.argv) > 1 and sys.argv[1] == "--override":
        print("⚠️ OVERRIDE MODE - Skipping plan validation")
        print("📝 Remember to document this deviation in IMPLEMENTATION_PLAN_LOCK.md")
        return 0
    
    # Run validation
    if validator.validate():
        validator.get_next_actions()
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())