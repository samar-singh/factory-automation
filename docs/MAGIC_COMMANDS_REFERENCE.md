# 🎮 MAGIC COMMANDS QUICK REFERENCE

## Overview
Magic commands are special phrases you type in your prompts to control the implementation plan. They give you direct control over how the AI interprets and executes the plan.

---

## 📊 Basic Commands

### `PLAN STATUS`
**Purpose**: Check current phase and overall progress  
**Usage**: Type at the start of any message  
**Response**: Current phase, completed tasks, what's next  
**Example**:
```
You: PLAN STATUS
AI: 📊 PLAN STATUS REPORT
    Current Phase: 1 - Database Foundation
    Status: Not Started
    Next: Create action_audit table
    Plan Version: 1.0
```

### `PLAN CHECKPOINT`
**Purpose**: Validate that recent work follows the plan  
**Usage**: After making changes or completing work  
**Response**: Validation results and any deviations  
**Example**:
```
You: I've updated the orchestrator. PLAN CHECKPOINT
AI: ✅ PLAN CHECKPOINT: Validated
    - Changes align with Phase 3
    - No unauthorized deviations
    - Ready for Phase 4
```

### `OVERRIDE PLAN: [specific task]`
**Purpose**: Request permission to deviate from the plan  
**Usage**: When you need to do something outside the plan  
**Response**: Acknowledgment and request for confirmation  
**Example**:
```
You: OVERRIDE PLAN: Add error logging before proceeding
AI: ⚠️ PLAN OVERRIDE ACKNOWLEDGED
    Deviation: Adding error logging
    Reason: Not in original plan
    Type 'CONFIRM OVERRIDE' to proceed
```

### `LOCK PLAN`
**Purpose**: Prevent any changes temporarily  
**Usage**: During testing or review periods  
**Response**: Confirmation that plan is locked  
**Example**:
```
You: LOCK PLAN
AI: 🔒 PLAN LOCKED
    No changes will be made until unlocked
```

### `UNLOCK PLAN`
**Purpose**: Resume implementation after lock  
**Usage**: When ready to continue work  
**Response**: Confirmation that work can resume  
**Example**:
```
You: UNLOCK PLAN
AI: 🔓 PLAN UNLOCKED
    Ready to continue with Phase [X]
```

---

## 🚀 Advanced Commands

### `SKIP TO PHASE [number]`
**Purpose**: Jump to a different phase (requires override)  
**Usage**: When dependencies are resolved out of order  
**Example**: `SKIP TO PHASE 5`

### `PLAN RESET`
**Purpose**: Revert to original plan if things go wrong  
**Usage**: Emergency recovery  
**Example**: `PLAN RESET`

### `PLAN ROLLBACK PHASE [number]`
**Purpose**: Undo all changes from a specific phase  
**Usage**: When a phase has issues  
**Example**: `PLAN ROLLBACK PHASE 3`

### `PLAN ABORT`
**Purpose**: Stop all work immediately  
**Usage**: Critical issues  
**Example**: `PLAN ABORT`

---

## 🖥️ Terminal Commands

These run in your terminal, not in prompts to the AI:

```bash
# Check if changes follow the plan
make check-plan

# Commit with plan validation
make safe-commit

# Show current plan status
make plan-status

# Show next actions
make plan-next

# Override plan check (document reason!)
make commit-override

# Run validation script directly
python check_plan_adherence.py
```

---

## 📝 Session Management

### Starting a Session
Always begin with:
```
PLAN STATUS
```
Then:
```
Let's continue with the next task
```

### Ending a Session
Before stopping:
```
PLAN CHECKPOINT
```
Then fill out the session template.

### Quick Session Start
```
PLAN STATUS - then let's continue
```

---

## 🎯 Common Workflows

### 1. Normal Implementation Flow
```
Session Start:
You: PLAN STATUS
AI: [Shows Phase 1 incomplete]
You: Let's start Phase 1
[Work happens]
You: PLAN CHECKPOINT
AI: [Validates work]
```

### 2. Handling Deviations
```
You: We need to add logging
AI: This isn't in the plan. Use 'OVERRIDE PLAN'
You: OVERRIDE PLAN: Add logging for debugging
AI: Override acknowledged. Proceeding...
```

### 3. Testing Period
```
You: LOCK PLAN
[Run tests]
You: Tests passed. UNLOCK PLAN
You: Continue with Phase 2
```

---

## 🎨 Visual Indicators

The AI will use these indicators in responses:

- 📊 **PLAN STATUS REPORT** - Status information
- ✅ **PLAN CHECKPOINT: Validated** - Work follows plan
- ⚠️ **PLAN OVERRIDE** - Deviation active
- 🔒 **PLAN LOCKED** - No changes allowed
- 🔓 **PLAN UNLOCKED** - Work can continue
- ❌ **PLAN VIOLATION** - Unauthorized deviation

---

## ⚡ Quick Tips

1. **Always start sessions with `PLAN STATUS`**
2. **Use `PLAN CHECKPOINT` after significant changes**
3. **Document overrides in IMPLEMENTATION_PLAN_LOCK.md**
4. **Run `make check-plan` before commits**
5. **Keep the plan lock file updated**

---

## 🚨 Emergency Commands

If something goes seriously wrong:

1. **Stop Work**: `PLAN ABORT`
2. **Check Status**: `PLAN STATUS`
3. **Review Changes**: `git status`
4. **Rollback if Needed**: `PLAN ROLLBACK PHASE [X]`
5. **Reset if Critical**: `PLAN RESET`

---

## 📋 Cheat Sheet

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `PLAN STATUS` | Check progress | Start of session |
| `PLAN CHECKPOINT` | Validate work | After changes |
| `OVERRIDE PLAN` | Allow deviation | Special needs |
| `LOCK/UNLOCK` | Control changes | Testing/Review |
| `make check-plan` | Terminal validation | Before commit |
| `make safe-commit` | Commit with checks | Ready to commit |

---

## 🔗 Related Files

- **Plan Lock**: `/docs/IMPLEMENTATION_PLAN_LOCK.md`
- **Session Template**: `/docs/SESSION_TEMPLATE.md`
- **Validation Script**: `/check_plan_adherence.py`
- **Git Template**: `/.gitmessage`
- **Main Instructions**: `/CLAUDE.md`

---

**Remember**: These commands ensure the implementation stays on track across all sessions. Use them liberally to maintain control and consistency!