# IMPLEMENTATION PLAN LOCK - DO NOT MODIFY WITHOUT APPROVAL

## Active Plan: Two-Tier Action System for V3 Orchestrator
**Status**: ACTIVE  
**Started**: 2025-01-23  
**Owner**: Samar Singh  
**Lock Version**: 1.0  
**Plan ID**: PLAN-2025-01-TWOTIER  

---

## 🎯 Plan Objective
Transform V3 orchestrator to automatically execute reversible actions while requiring human approval for irreversible business actions. Remove V4 proposal system entirely.

## 🔒 Core Principles (IMMUTABLE - NO CHANGES WITHOUT OWNER APPROVAL)

1. **Customer Communications**: ALL emails to customers MUST require human approval
2. **Inventory Commitments**: Final inventory reservations MUST require human approval  
3. **Analysis Operations**: AI analysis (OpenAI, Together.ai) CAN auto-execute
4. **Internal Operations**: Database updates, calculations CAN auto-execute with rollback capability
5. **V4 Removal**: V4 proposal system MUST be completely removed
6. **Safety First**: When in doubt, require approval

## 📋 Implementation Phases

### Phase 1: Database Foundation (2-3 hours) ✅ COMPLETED
- [x] Create `action_audit` table in models.py
- [x] Add migration script
- [x] Test database changes don't break existing functionality
- [x] Verify audit insertion works
**Deliverable**: Database ready to track actions

### Phase 2: Action Classification System (3-4 hours) ✅ COMPLETED
- [x] Create `action_classifier.py` with irreversible actions list
- [x] Update `tool_factory.py` to mark action types
- [x] Add unit tests for classification logic
- [x] Document classification rules
**Deliverable**: All actions classified, existing flow unchanged

### Phase 3: Orchestrator Enhancement (4-5 hours) ✅ COMPLETED & TESTED
- [x] Modify `orchestrator_v3_agentic.py` to track actions
- [x] Import reasoning generation from `proposal_engine.py`
- [x] Add workflow ID generation
- [x] Store actions in audit log
- [x] Integration testing with Playwright MCP
- [x] Standard test case created for consistency
**Deliverable**: V3 tracks all actions in database
**Test File**: `/test_phase_integration.py` with standard email scenario

### Phase 4: Two-Tier Execution Logic (4-5 hours) ✅ COMPLETED
- [x] Implement auto-execute for reversible actions
- [x] Queue irreversible actions for approval
- [x] Add approval mechanism
- [x] Test execution flow
- [x] Fixed extract_excel_data classification to be reversible
**Deliverable**: Two-tier execution working

### Phase 5: UI Updates - Display Two Tiers (3-4 hours) ✅ COMPLETED
- [x] Update `human_review_dashboard.py` with two-tier display
- [x] Add green bullets for executed actions
- [x] Add orange bullets for pending actions
- [x] Implement expandable email preview using HTML `<details>`
- [x] Add Approve/Reject/Modify buttons
**Deliverable**: UI shows two-tier actions clearly

### Phase 6: Approval Flow Implementation (3-4 hours) ✅ COMPLETED
- [x] Create approval endpoints in orchestrator
- [x] Wire up UI buttons to actions
- [x] Implement email modification capability
- [x] Add status updates and loading states
**Deliverable**: Full approval flow working

### Phase 7: Cleanup & Deprecation (2 hours) ✅ COMPLETED
- [x] Move `orchestrator_v4_proposal.py` to `/deprecated/`
- [x] Move `proposal_review_dashboard.py` to `/deprecated/`
- [x] Remove V4 imports from `run_factory_automation.py`
- [x] Remove V4 button from UI
- [x] Update documentation
**Deliverable**: Clean codebase with V4 removed

### Phase 8: Integration Testing (2-3 hours) ✅ COMPLETED
- [x] Test high confidence orders (>80%)
- [x] Test medium confidence (60-80%)
- [x] Test low confidence (<60%)
- [x] Verify emails not sent without approval
- [x] Check audit trail completeness
**Deliverable**: Fully tested system
**Note**: SDK limitation confirmed - tools execute before interception possible

### Phase 9: Production Preparation (2 hours)
- [ ] Update `config.yaml` with thresholds
- [ ] Add monitoring and logging
- [ ] Create user documentation
- [ ] Update CLAUDE.md
**Deliverable**: Production-ready system

## 🚦 Current Status

**Current Phase**: Phase 8 ✅ COMPLETED → Ready for Phase 9  
**Next Action**: Begin Phase 9 - Production Preparation  
**Blockers**: None  
**Last Updated**: 2025-08-26 (Phase 8 completed - Integration testing done, SDK limitation confirmed)  
**Standard Test Case**: `/factory_automation/factory_tests/standard_test_case.py`  

## ⚠️ Deviation Rules

### Allowed WITHOUT Approval:
- Bug fixes that don't change architecture
- Adding comments/documentation
- Improving error messages
- Performance optimizations that don't change behavior

### REQUIRES Explicit Approval:
- Changing any core principle
- Skipping or reordering phases
- Adding new features not in plan
- Modifying phase deliverables
- Changing irreversible action classifications
- Any modification to email sending logic

### How to Request Deviation:
1. Use magic command: `OVERRIDE PLAN: [specific change]`
2. Provide justification
3. Wait for explicit approval
4. Document deviation in this file

## 📝 Change Log

| Date | Phase | Change | Approved By |
|------|-------|--------|-------------|
| 2025-01-23 | Initial | Plan created and locked | Samar Singh |
| 2025-01-23 | Phase 1 | Completed database foundation - ActionAudit table created | System |
| 2025-01-23 | Phase 2 | Completed action classification - All tools classified | System |
| 2025-01-23 | Phase 3 | Completed orchestrator enhancement - Action tracking active | System |
| 2025-01-23 | Phase 3 | Integration testing with Playwright MCP - Standard test case created | System |
| 2025-01-24 | Phase 4 | Completed two-tier execution logic - Auto-execute and approval mechanism | System |
| 2025-01-24 | Phase 5 | Completed UI updates - Two-tier actions display with colored bullets | System |
| 2025-01-24 | Phase 5 | Discovered OpenAI SDK limitation - tools execute immediately, created v3_approval.py workaround | System |
| 2025-01-25 | Phase 6 | Completed approval flow implementation - Option B integrated, UI buttons wired, emails blocked | System |
| 2025-01-25 | Phase 7 | Completed cleanup - V4 orchestrator and dashboard moved to deprecated, UI simplified | System |
| 2025-08-26 | Phase 8 | Completed integration testing - All tests passed, SDK limitation confirmed | System |
| 2025-08-27 | Override | Integrated ValidationAgent for tool order enforcement | Samar Singh |
| 2025-08-27 | Override | Implemented tool-calling loop for error recovery (max 10 iterations) | Samar Singh |

## 🔑 Magic Commands

- `PLAN STATUS` - Check current phase and progress
- `PLAN CHECKPOINT` - Validate work against plan
- `OVERRIDE PLAN: [task]` - Request deviation
- `LOCK PLAN` - Prevent changes
- `UNLOCK PLAN` - Resume work

## 📊 Success Metrics

- [ ] No customer emails sent without approval
- [ ] All analysis APIs execute automatically  
- [ ] Clear visual separation of executed vs pending
- [x] Complete audit trail for all actions (Phase 3 ✅)
- [ ] V4 completely removed from codebase
- [ ] All tests passing
- [ ] Performance maintained or improved

## 🔄 Rollback Plan

If implementation fails at any phase:
1. Git revert to last stable commit
2. Restore database to backup
3. Document lessons learned
4. Adjust plan based on findings
5. Restart from safe point

## 📌 Important Notes

- **Testing Required**: After EVERY phase, run `python3 -m dotenv run -- python3 run_factory_automation.py` to verify system works
- **Standard Test Case**: Use `uv run python test_phase_integration.py` for consistent testing
- **Validation Test**: Use `uv run python test_validation_integration.py` to test tool order enforcement
- **Test Email**: Allen Solly order with Pro-Forma Invoice #1542 (see standard_test_case.py)
- **No Parallel Work**: Complete phases sequentially
- **Documentation**: Update docs as you go, not at the end
- **Communication**: Any blockers should be raised immediately
- **Environment**: Using `uv` for package management and virtual environment

---

**This plan is LOCKED. Any modifications require explicit approval from the plan owner.**

**To modify this plan**: Use `OVERRIDE PLAN` command and wait for approval.