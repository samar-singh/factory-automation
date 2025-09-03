# Claude Debugging Protocol for Factory Automation

## MANDATORY DEBUGGING CHECKLIST

### 1. 🔍 ALWAYS Check Generated Logs FIRST
```bash
# Look for the most recent app log
ls -la app_*.log | tail -1

# Check for errors/warnings/validation failures
grep -E "ERROR|WARNING|Validation failed|❌" app_*.log | tail -20

# Check what tools were actually executed
grep "Tool call requested:" app_*.log
grep "executed successfully" app_*.log
```

### 2. 📊 Verify Complete Workflow Execution
- [ ] List ALL expected tools for the workflow
- [ ] Verify EACH tool was called (not just some)
- [ ] Check the ORDER of tool calls matches expectations
- [ ] Look for validation rejections between calls

### 3. 🎯 Check Background Process Output
```bash
# ALWAYS check background bash output when running
BashOutput tool for any bash process running in background

# Look for real-time errors not yet written to log
```

### 4. 🔄 Integration Test Verification Pattern
When running ANY integration test:
1. **Before Test**: Clear old logs
2. **During Test**: Monitor background output
3. **After Test**: 
   - Check app log for validation errors
   - Verify all expected tools ran
   - Check for parameter mismatches
   - Look for embedding dimension errors

### 5. ⚠️ Common Pitfalls to Check
- [ ] Parameter name mismatches (validation_rules.py vs actual tool)
- [ ] Embedding dimension conflicts (1024 vs 384)
- [ ] Tools not being called due to validation blocks
- [ ] Async/sync mismatches
- [ ] Schema preservation issues

### 6. 📝 Required Output Format for Debugging
When debugging, ALWAYS provide:
```markdown
## Debug Analysis
1. **Log File Checked**: app_YYYYMMDD_HHMMSS.log
2. **Errors Found**: 
   - [List specific errors with line numbers]
3. **Tools Executed**: 
   - [List which tools ran successfully]
4. **Tools Failed/Blocked**:
   - [List which tools failed and why]
5. **Root Cause**: [Specific issue identified]
6. **Fix Required**: [Exact changes needed]
```

### 7. 🚨 Red Flags That Require Investigation
- "Validation failed" appears in logs
- Expected tools not in "Tool call requested" list
- Multiple attempts at same tool with same args
- "Collection expecting embedding with dimension" errors
- Empty tool results like `{"matches": []}`
- Partial workflow completion

### 8. 🔧 Debugging Commands Sequence
```bash
# Step 1: Find latest log
export LATEST_LOG=$(ls -t app_*.log | head -1)

# Step 2: Check for failures
grep -C 3 "Validation failed" $LATEST_LOG

# Step 3: Check tool execution flow
grep "Tool call requested" $LATEST_LOG | awk -F: '{print $NF}'

# Step 4: Check for parameter errors
grep "PARAMETER ERROR" $LATEST_LOG

# Step 5: Check for dimension mismatches
grep "dimension" $LATEST_LOG | grep -i error
```

## ENFORCEMENT RULES

### For Claude:
1. **MUST** check app_*.log before declaring "test successful"
2. **MUST** verify complete workflow, not partial execution
3. **MUST** report validation errors found in logs
4. **MUST** use grep/search commands on logs, not just Read
5. **MUST** check BashOutput for background processes

### For User:
When Claude says "test successful", ask:
1. "What app log did you check?"
2. "Show me the validation errors from the log"
3. "Which tools were called and in what order?"
4. "Did process_complete_order execute successfully?"

## INTEGRATION TEST VALIDATION TEMPLATE

```python
# After running any test, execute this validation:
def validate_test_results(log_file: str):
    checks = {
        "validation_errors": "grep 'Validation failed' {log_file}",
        "tools_executed": "grep 'executed successfully' {log_file}",
        "parameter_errors": "grep 'PARAMETER ERROR' {log_file}",
        "complete_workflow": "grep 'process_complete_order' {log_file}",
        "final_status": "tail -20 {log_file} | grep -E 'SUCCESS|COMPLETE|FAILED'"
    }
    
    for check_name, command in checks.items():
        result = run_command(command.format(log_file=log_file))
        print(f"{check_name}: {result}")
```

## EXAMPLE GOOD DEBUGGING

✅ **Correct Approach:**
```
1. Ran integration test
2. Checked app_20250829_102710.log
3. Found 3 validation failures for process_complete_order
4. Identified parameter mismatch: expects 'email_data', got individual params
5. Root cause: validation_rules.py line 45 vs order_tools.py line 41
```

❌ **What I Did Wrong:**
```
1. Ran integration test
2. Saw some tools executed in console
3. Declared "test successful"
4. Never checked app_*.log file
5. Missed validation errors completely
```

## REMINDER TRIGGERS

User should remind Claude to follow this protocol when:
- Running any test
- Debugging any issue  
- Claiming something "works"
- After fixing any bug
- Before declaring completion

---

**Protocol Version**: 1.0
**Created**: 2025-08-29
**Purpose**: Ensure systematic debugging and prevent oversight of critical errors in logs