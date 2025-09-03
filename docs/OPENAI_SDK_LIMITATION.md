# OpenAI Agents SDK Limitation - Tool Execution Control

**Discovery Date**: January 24, 2025  
**Discovered During**: Phase 5 of Two-Tier Action System Implementation  
**Severity**: CRITICAL - Blocks true pre-execution approval  

## Problem Statement

The OpenAI Agents SDK's `Runner` class executes tools immediately when the LLM requests them. There is no built-in mechanism to intercept, review, or approve/reject tool calls before execution.

## Technical Details

### How the SDK Works
```python
# Current SDK behavior (simplified)
runner = Runner(client=openai_client, tools=tools)
response = runner.run(messages)  # Tools execute immediately during this call
```

When the LLM decides to use a tool during the `runner.run()` call:
1. The LLM generates a tool call request
2. The SDK's Runner immediately executes the corresponding function
3. The result is fed back to the LLM
4. The process continues until completion

### What We Need
```python
# Desired behavior (not supported by SDK)
runner = Runner(client=openai_client, tools=tools)
runner.on_tool_call = lambda tool_call: approve_or_reject(tool_call)  # NOT POSSIBLE
response = runner.run(messages)
```

## Evidence

### Test Performed
Using Playwright MCP browser automation, we tested the orchestrator with a standard email:
1. Email processed through orchestrator_v3_agentic.py
2. LLM decided to call multiple tools (search_inventory, extract_excel_data, etc.)
3. ALL tools executed immediately
4. ActionAudit database showed tools marked as both reversible and irreversible
5. UI displayed "Pending Approval" for irreversible actions
6. BUT: Actions had already executed by the time UI displayed them

### Code Analysis
Reviewed OpenAI SDK source code:
- No callbacks for pre-execution approval
- No configuration to delay execution
- Tool execution is deeply embedded in Runner.run() method
- No public API to intercept tool calls

## Impact

### Current System Behavior
1. **orchestrator_v3_agentic.py** (integrated):
   - Uses OpenAI Agents SDK
   - Tracks actions in ActionAudit database  
   - Classifies actions as reversible/irreversible
   - Shows two-tier display in UI
   - **BUT**: All actions execute immediately

2. **What Users See**:
   - Green section: "Auto-Executed Actions" (reversible)
   - Orange section: "Pending Approval" (irreversible)
   - Approve/Reject/Modify buttons
   - **Reality**: Orange "pending" actions have already executed

## Solutions

### Solution 1: Direct API Approach (Implemented in orchestrator_v3_approval.py)
```python
# Use OpenAI API directly without SDK
async def process_with_approval(messages):
    # Step 1: Get LLM response with tool calls
    response = await openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=tool_definitions,
        tool_choice="auto"
    )
    
    # Step 2: Intercept tool calls BEFORE execution
    if response.choices[0].message.tool_calls:
        for tool_call in response.choices[0].message.tool_calls:
            action_type = classify_action(tool_call.function.name)
            
            if action_type == ActionType.IRREVERSIBLE:
                # Queue for approval, don't execute
                queue_for_approval(tool_call)
            else:
                # Execute reversible actions
                result = execute_tool(tool_call)
                
    # Step 3: Continue conversation after approvals
    # ...
```

### Solution 2: Post-Execution Rollback (Current Workaround)
- Let SDK execute all actions
- Track what was executed
- For irreversible actions that shouldn't have run:
  - Attempt rollback if possible
  - Flag for manual intervention
  - Log the issue

### Solution 3: Hybrid Approach (Proposed)
- Use SDK for reversible actions (fast path)
- Switch to direct API for irreversible actions
- Maintain two orchestrator modes

## Recommendations

### Short Term (Phase 6)
1. **Option A**: Continue with current tracking-only approach
   - Pros: No refactoring needed
   - Cons: Actions execute before approval
   
2. **Option B**: Switch to orchestrator_v3_approval.py
   - Pros: True pre-execution approval
   - Cons: Requires integration refactoring

3. **Option C**: Implement hybrid approach
   - Pros: Best of both worlds
   - Cons: Most complex

### Long Term
1. Monitor OpenAI SDK for updates that might add approval hooks
2. Consider building custom SDK wrapper
3. Evaluate alternative orchestration frameworks

## Test Commands

### See the Limitation in Action
```bash
# Run the integrated orchestrator
python3 -m dotenv run -- python3 run_factory_automation.py

# Process an order that should require approval
# Paste email in Order Processing tab
# Click "Process Order"
# Notice: Orange "Pending Approval" items have already executed
# Check logs: Actions were executed immediately
```

### Test the Solution
```bash
# Test orchestrator_v3_approval.py directly
python3 test_approval_orchestrator.py

# This shows true pre-execution approval working
# Tool calls are intercepted before execution
```

## Decision Record

**Date**: January 24, 2025  
**Decision Pending**: Which approach to use for Phase 6?  
**Options**:
1. Keep v3_agentic (tracking-only)
2. Switch to v3_approval (true approval)
3. Implement hybrid approach

**Factors to Consider**:
- User expectations (seeing "Pending Approval" implies not executed)
- System complexity (refactoring required for v3_approval)
- Business risk (emails might be sent without approval in current system)
- Development time (Phase 6 estimated at 3-4 hours)

## Related Files

- `/factory_automation/factory_agents/orchestrator_v3_agentic.py` - Current integrated version
- `/factory_automation/factory_agents/orchestrator_v3_approval.py` - Solution with true approval
- `/factory_automation/factory_agents/action_classifier.py` - Classifies actions
- `/factory_automation/factory_database/models.py` - ActionAudit table
- `/docs/IMPLEMENTATION_PLAN_LOCK.md` - Current implementation plan

## Lessons Learned

1. **Assumption**: We assumed SDK would have approval hooks
2. **Reality**: SDK designed for autonomous execution
3. **Learning**: Always test core assumptions early
4. **Future**: Research SDK capabilities before architectural decisions

---

*This limitation is fundamental to the OpenAI Agents SDK design. It's not a bug, but rather a design choice that prioritizes autonomous agent operation over human-in-the-loop control.*