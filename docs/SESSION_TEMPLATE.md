# Session Handoff Template - [DATE]

## 📊 Plan Adherence Check
- [ ] Read and followed `/docs/IMPLEMENTATION_PLAN_LOCK.md`
- [ ] No unauthorized deviations from plan
- [ ] Updated phase progress in lock file
- [ ] All changes align with current phase goals

## 🔄 Current Phase Status
**Phase**: [NUMBER] - [NAME]  
**Status**: [Not Started / In Progress / Completed]  
**Progress**: [X] of [Y] tasks completed  

## ✅ Work Completed This Session

### Tasks Completed:
1. 
2. 
3. 

### Files Modified:
- `path/to/file.py` - [Brief description of change]
- `path/to/file2.py` - [Brief description of change]

### Tests Run:
- [ ] `python run_factory_automation.py` - [Pass/Fail]
- [ ] Unit tests - [Pass/Fail]
- [ ] Integration tests - [Pass/Fail]

## 💻 Current System State
**Application Status**: [Working / Partially Working / Broken]  
**Can Start UI**: [Yes/No]  
**Database State**: [Clean / Has Test Data / Needs Migration]  
**Last Successful Run**: [Timestamp]  

### Known Working Commands:
```bash
source .venv/bin/activate
python run_factory_automation.py
```

## 📝 Next Session Should

### Continue With:
1. **Primary Task**: [Specific next task from plan]
2. **Phase Goal**: Complete Phase [X] - [Name]
3. **First Action**: [Exact first step to take]

### Commands to Run First:
```bash
# Check current state
PLAN STATUS

# Verify system works
source .venv/bin/activate
python run_factory_automation.py

# Continue with phase
[Specific command]
```

## ⚠️ Blockers/Issues

### Current Blockers:
- [ ] [Issue description] - [Impact on plan]

### Warnings for Next Session:
- 

### Dependencies Needed:
- 

## 🚫 DO NOT (Important Reminders)

- [ ] DO NOT skip to Phase [X] without completing Phase [Y]
- [ ] DO NOT modify `[specific file]` without approval
- [ ] DO NOT add new features outside the plan
- [ ] DO NOT send emails without human approval (core principle)
- [ ] DO NOT remove V4 until Phase 7

## 📊 Metrics

**Lines of Code Changed**: ~[NUMBER]  
**Test Coverage**: [X]%  
**Time Spent**: [X] hours  
**Phase Completion**: [X]%  

## 🔄 Rollback Information

If next session needs to rollback:
1. **Last Stable Commit**: [git hash]
2. **Backup Location**: [if any]
3. **Safe Revert Command**: `git checkout [hash]`

## 📝 Notes for Next Session

### Context/Background:
[Any important context that will help the next session]

### Decisions Made:
- [Decision 1 and rationale]
- [Decision 2 and rationale]

### Questions to Resolve:
- [ ] [Question that needs answering]

## ✅ Handoff Checklist

Before ending session:
- [ ] All changes committed with proper message format
- [ ] Tests passing or issues documented
- [ ] Lock file updated with progress
- [ ] This template filled out completely
- [ ] No work-in-progress left uncommitted

---

**Session Ended**: [TIMESTAMP]  
**Next Session ETA**: [When you plan to continue]  
**Handed Off By**: [Your name / AI Session ID]  

---

## Quick Start for Next Session

```bash
# 1. Start with magic command
PLAN STATUS

# 2. Read this handoff
cat docs/SESSION_[DATE].md

# 3. Check system state
source .venv/bin/activate
python run_factory_automation.py

# 4. Continue plan
# [Specific next command based on plan phase]
```