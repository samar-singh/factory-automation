# Debug Fix Plan: Two-Tier Action System Issues

## Date: 2025-01-26
## Review Score: 6.5/10 (B- Grade)

## Executive Summary
The Factory Automation System's two-tier action system is technically implemented but not displaying correctly in the UI. The core issue is that the AI model (GPT-4) is not calling the expected tools, particularly `send_email_response`, despite clear instructions in the system prompt.

## Critical Issues Identified

### 1. **Two-Tier Action System Display FAILED (0/10)**
- **Problem**: The UI shows raw JSON instead of formatted two-tier actions
- **Expected**: Green bullets for auto-executed, orange bullets for pending approval
- **Actual**: Only JSON output with tool validation errors
- **Root Cause**: AI not calling expected tools + UI not extracting action lists from result

### 2. **AI Tool Calling Issues**
- **Line 281** in `orchestrator_v3_agentic.py`: System prompt says "ALWAYS send a response email"
- **Reality**: AI only calls `extract_pdf_data` or `search_inventory` with validation errors
- **Missing Tools**: `classify_email_intent`, `send_email_response`, `create_proforma_invoice`

### 3. **Poor Error Handling (2/10)**
- Raw JSON errors displayed to users
- Tool validation errors not handled gracefully
- No user-friendly error messages

### 4. **Missing UI Integration**
- `run_factory_automation.py` doesn't extract `auto_executed_actions` and `pending_approval_actions`
- Human review dashboard has `format_two_tier_actions` method but it's never called
- No connection between orchestrator results and UI display

## Root Cause Analysis

### AI Behavior Problems
1. GPT-4 is not following the workflow instructions (lines 268-274 in orchestrator_v3_agentic.py)
2. Tool calls often have missing required parameters
3. The model doesn't call `send_email_response` despite explicit instructions

### UI Integration Problems
1. The result dictionary contains the action lists but they're not extracted in UI
2. JSON is displayed raw instead of being parsed and formatted
3. Human review dashboard is empty because no actions are being queued

## Detailed Fix Plan

### Phase 1: Fix AI Tool Calling (CRITICAL)

#### 1.1 Enhanced System Prompt
**File**: `orchestrator_v3_agentic.py`, lines 360-382

**Current prompt issues**:
- Too generic
- Doesn't provide parameter examples
- Doesn't handle errors gracefully

**Fix**:
```python
# Add after line 367 (in the prompt):
CRITICAL: You MUST follow these exact steps for EVERY email:

Step 1: Classify the email
Tool: classify_email_intent
Parameters: {
    "email_subject": "{subject}",
    "email_body": "{body}",
    "sender_email": "{from_email}",
    "recipient_email": "{to_email}"
}

Step 2: Based on classification, take action
If NEW_ORDER or contains order details:
  Tool: process_complete_order
  Parameters: {
    "email_data": {full_email_data},
    "attachments": {attachments_list}
  }

Step 3: ALWAYS send a response (MANDATORY)
Tool: send_email_response
Parameters: {
    "to_email": "{from_email}",
    "subject": "Re: {original_subject}",
    "body": "{appropriate_response}",
    "email_type": "{classification}",
    "attachments": []
}

If a tool fails with validation error, check the error message and retry with correct parameters.
```

#### 1.2 Add Tool Retry Logic
**File**: `orchestrator_v3_agentic.py`, after line 420

```python
# Add retry mechanism for failed tools
if "validation error" in str(result).lower():
    # Parse the error and retry with default parameters
    logger.warning(f"Tool {tool_name} failed with validation error, retrying with defaults")
    
    # Add default parameters based on tool name
    if tool_name == "extract_pdf_data":
        tool_args = {"filename": "document.pdf", "content": ""}
    elif tool_name == "search_inventory":
        tool_args = {"query": "Allen Solly tags"}
    
    # Retry the tool call
    result = await self.confirm_and_execute(tool_name, tool_args)
```

#### 1.3 Force Critical Tools
**File**: `orchestrator_v3_agentic.py`, after line 130 (after getting first response)

```python
# Check if send_email_response was called
email_tool_called = any(tc.get("tool") == "send_email_response" for tc in tool_calls)

if not email_tool_called and len(tool_calls) > 0:
    # Force a follow-up to send email
    logger.warning("No email response generated, forcing email send...")
    
    follow_up_prompt = """
    You processed the email but didn't send a response. 
    You MUST now use send_email_response to acknowledge the email.
    
    Use these parameters:
    - to_email: the sender's email address
    - subject: "Re: " + original subject
    - body: A professional acknowledgment of their request
    - email_type: "acknowledgment"
    """
    
    messages.append({"role": "user", "content": follow_up_prompt})
    
    # Get follow-up response
    follow_up = await self.openai_client.chat.completions.create(
        model=self.model,
        messages=messages,
        tools=self.tool_schemas,
        tool_choice="required"  # Force tool use
    )
    
    # Process the email sending tool call
    # ... (process follow_up.choices[0].message.tool_calls)
```

### Phase 2: Fix UI Display (CRITICAL)

#### 2.1 Extract and Display Actions
**File**: `run_factory_automation.py`, lines 422-435

**Replace current code with**:
```python
# After line 422 (after getting result)
result = await orchestrator.process_email(email_data)

# Extract two-tier actions
auto_executed = result.get('auto_executed_actions', [])
pending_approval = result.get('pending_approval_actions', [])

# Format for display using the review dashboard's method
from factory_automation.factory_ui.human_review_dashboard import HumanReviewDashboard
dashboard = HumanReviewDashboard()
executed_html, pending_html = dashboard.format_two_tier_actions(
    [action.get('action_name') for action in auto_executed],
    pending_approval
)

# Create formatted result display (instead of raw JSON)
formatted_result = f"""
<div style="font-family: system-ui, -apple-system, sans-serif;">
    <h3>✅ Processing Complete</h3>
    <p><strong>Workflow ID:</strong> {result.get('workflow_id')}</p>
    <p><strong>Email ID:</strong> {result.get('email_id')}</p>
    
    {executed_html}
    {pending_html}
    
    <div style="margin-top: 1rem; padding: 1rem; background: #f3f4f6; border-radius: 8px;">
        <h4>Summary</h4>
        <p>{result.get('final_summary', 'Processing complete')}</p>
    </div>
</div>
"""

# Return the formatted HTML instead of JSON
return formatted_result, extracted, doc_analysis, image_summary, image_gallery
```

#### 2.2 Update UI Component Definition
**File**: `run_factory_automation.py`, line 200 (results display)

**Change from**:
```python
result_display = gr.JSON(label="Processing Result")
```

**To**:
```python
result_display = gr.HTML(label="Processing Result", elem_id="processing-result")
```

### Phase 3: Improve Error Handling

#### 3.1 Create Error Formatter
**File**: Create new `factory_automation/factory_utils/error_formatter.py`

```python
def format_tool_error(error_str: str, tool_name: str) -> str:
    """Convert tool validation errors to user-friendly messages"""
    
    if "validation error" in error_str.lower():
        if "field required" in error_str.lower():
            return f"⚠️ {tool_name}: Missing required information. Retrying with defaults..."
        elif "invalid" in error_str.lower():
            return f"⚠️ {tool_name}: Invalid data format. Adjusting and retrying..."
    
    return f"⚠️ {tool_name}: Technical issue encountered. Working on alternative approach..."

def create_error_card(error: str, suggestion: str) -> str:
    """Create a user-friendly error card HTML"""
    return f"""
    <div style="border-left: 4px solid #ef4444; padding: 1rem; background: #fee; border-radius: 4px; margin: 1rem 0;">
        <h4 style="color: #dc2626; margin: 0 0 0.5rem 0;">⚠️ Processing Issue</h4>
        <p style="color: #7f1d1d; margin: 0 0 0.5rem 0;">{error}</p>
        <p style="color: #991b1b; font-size: 0.9em; margin: 0;">
            <strong>What we're doing:</strong> {suggestion}
        </p>
    </div>
    """
```

### Phase 4: Connect Human Review Dashboard

#### 4.1 Wire Approval Buttons
**File**: `run_factory_automation.py`, add after line 500

```python
# Add handlers for approval buttons
async def approve_action(action_id: str):
    """Handle action approval from UI"""
    result = await orchestrator.approve_action(action_id)
    return f"Action {action_id} approved: {result.get('status')}"

async def reject_action(action_id: str):
    """Handle action rejection from UI"""
    result = await orchestrator.reject_action(action_id)
    return f"Action {action_id} rejected: {result.get('status')}"

# Wire up the buttons (in the UI definition section)
approve_btn.click(approve_action, inputs=[action_id_input], outputs=[status_output])
reject_btn.click(reject_action, inputs=[action_id_input], outputs=[status_output])
```

## Testing Checklist

### 1. AI Tool Calling
- [ ] Run test with standard email
- [ ] Verify `classify_email_intent` is called first
- [ ] Verify `send_email_response` is called
- [ ] Check that validation errors are retried

### 2. UI Display
- [ ] Two-tier actions show with colored bullets
- [ ] No raw JSON visible to users
- [ ] Error messages are user-friendly
- [ ] Human review dashboard populates

### 3. Approval Flow
- [ ] Pending actions appear in queue
- [ ] Approve button executes action
- [ ] Reject button removes from queue
- [ ] Status updates in real-time

### 4. Error Handling
- [ ] Validation errors show friendly messages
- [ ] System retries with defaults
- [ ] Users see recovery progress
- [ ] No stack traces in UI

## Expected Outcomes

After implementing these fixes:

1. **Reliability**: AI will consistently call all required tools
2. **Visibility**: Two-tier actions displayed with proper formatting
3. **Usability**: User-friendly error messages and recovery
4. **Functionality**: Complete approval flow working end-to-end
5. **Polish**: Professional UI without raw JSON or technical errors

## Files to Modify

1. `orchestrator_v3_agentic.py` - Enhanced prompts, retry logic, force tools
2. `run_factory_automation.py` - Extract actions, format display, wire buttons
3. `error_formatter.py` (new) - User-friendly error handling
4. `human_review_dashboard.py` - Already has formatting, just needs to be called

## Timeline

- **Phase 1**: 2-3 hours (AI prompt engineering and testing)
- **Phase 2**: 1-2 hours (UI integration)
- **Phase 3**: 1 hour (Error handling)
- **Phase 4**: 1 hour (Button wiring)

**Total**: 5-7 hours of implementation

## Notes

- The orchestrator file was recently modified (line 281 removed the explicit email requirement)
- The wrapper implementation is working correctly (blocks irreversible actions)
- The issue is primarily AI behavior and UI integration, not the core two-tier logic
- Consider using `tool_choice="required"` to force specific tool usage