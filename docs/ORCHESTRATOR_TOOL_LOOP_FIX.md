# Orchestrator Tool Execution Loop Fix

## Problem Identified

The current orchestrator implementation has a critical flaw in how it handles tool execution that prevents the AI from correcting mistakes or making multiple tool calls.

### Current Broken Flow

```python
# Line 479: First API call - WITH tools
response = await self.openai_client.chat.completions.create(
    model=self.model,
    messages=messages,
    tools=self.tool_schemas,  # ← Tools available!
    tool_choice="auto"
)

# Tools get executed...

# Line 563: Second API call - WITHOUT tools
final_response = await self.openai_client.chat.completions.create(
    model=self.model,
    messages=messages
    # No tools parameter! ← This is the problem
)
```

### What Happens

1. **First Call**: AI makes initial tool calls (e.g., `extract_pdf_data`)
2. **Tool Execution**: Tool gets executed and returns results (potentially with errors)
3. **Second Call**: AI sees the results and realizes it made a mistake
4. **AI Response**: "Let me fix that by calling `classify_email_intent` first..."
5. **Problem**: AI can't actually make new tool calls because the second API call doesn't include tools!

### Example Error Message

```
'I noticed an error in processing the email. As per instructions, I should have first classified the email, 
not directly processed the attachment. Allow me to fix that by following the correct procedure.

Let's start by classifying the email intent.

### Step 1: Classify Email Intent
1. **Call `classify_email_intent`:** 
   - **email_subject:** "Order Request"
   - **email_body:** "..."
   - **sender_email:** "trimsblr@yahoo.co.in"
   - **recipient_email:** "trimsblr@yahoo.co.in"'
```

The AI wants to call the tool but can't because tools aren't available in the second call!

## Solution: Implement Tool-Calling Loop

Replace the current two-call pattern with a proper loop that allows multiple rounds of tool calling.

### Implementation

Replace lines 489-574 in `/factory_automation/factory_agents/orchestrator_v3_agentic.py`:

```python
# Process tool calls with TRUE approval capability
tool_calls = []
auto_executed = []
pending_approval = []

# Allow multiple rounds of tool calling
max_iterations = 10
iteration = 0
result = None

while iteration < max_iterations:
    # Call API with tools enabled
    if iteration == 0:
        # First call
        logger.info("Calling OpenAI API with tools...")
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tool_schemas,
            tool_choice="auto"
        )
    else:
        # Subsequent calls - AI can correct mistakes or continue workflow
        logger.info(f"Tool calling iteration {iteration} - allowing AI to continue...")
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tool_schemas,
            tool_choice="auto"  # Let AI decide if more tools needed
        )
    
    # Check if AI wants to make tool calls
    if not response.choices[0].message.tool_calls:
        # No more tools needed - get final response
        result = response.choices[0].message.content
        logger.info("AI completed tool calling - no more tools needed")
        break
    
    # Process tool calls
    logger.info(f"AI requested {len(response.choices[0].message.tool_calls)} tool calls in iteration {iteration}")
    tool_results = []
    
    for tool_call in response.choices[0].message.tool_calls:
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        logger.info(f"Tool call requested: {tool_name} with args: {tool_args}")
        
        # Execute tool with approval logic
        result = await self.confirm_and_execute(tool_name, tool_args)
        
        # Track execution (same as before)
        try:
            result_dict = json.loads(result) if isinstance(result, str) else result
            if isinstance(result_dict, dict) and result_dict.get("status") == "pending_approval":
                pending_approval.append({
                    "action_id": result_dict.get("action_id"),
                    "action_name": tool_name,
                    "type": "irreversible",
                    "status": "pending_approval"
                })
            else:
                auto_executed.append({
                    "action_name": tool_name,
                    "type": "reversible",
                    "status": "executed"
                })
        except:
            auto_executed.append({
                "action_name": tool_name,
                "type": "unknown",
                "status": "executed"
            })
        
        tool_results.append({
            "tool_call_id": tool_call.id,
            "result": str(result)
        })
        
        tool_calls.append({
            "tool": tool_name,
            "args": tool_args,
            "result": str(result)[:200]
        })
        
        trace_monitor.add_tool_call(
            tool_name=tool_name,
            args=tool_args,
            result=str(result)[:200]
        )
    
    # Add this round's results to message history
    messages.append(response.choices[0].message)
    for tool_result in tool_results:
        messages.append({
            "role": "tool",
            "tool_call_id": tool_result["tool_call_id"],
            "content": tool_result["result"]
        })
    
    iteration += 1

# Check if we hit max iterations
if iteration >= max_iterations:
    logger.warning(f"Hit maximum iterations ({max_iterations}) for tool calling")
    result = "Maximum tool calling iterations reached. Please review the actions taken."
```

## Benefits

1. **Error Recovery**: AI can recognize mistakes and call the correct tools
2. **Multi-Step Workflows**: AI can execute complex sequences of tool calls
3. **Proper Tool Ordering**: AI can call `classify_email_intent` after realizing it should be first
4. **Flexible Execution**: AI decides when it's done, not hardcoded to 2 calls
5. **Safety**: Maximum iteration limit prevents infinite loops

## Testing

After implementing, test with the Allen Solly email:
1. AI might initially call wrong tool
2. AI should recognize the error
3. AI should then call `classify_email_intent`
4. AI should continue with proper workflow

## Alternative Quick Fix

If you want a minimal change, just add tools to the second call:

```python
# Line 563: Add tools parameter to final response
final_response = await self.openai_client.chat.completions.create(
    model=self.model,
    messages=messages,
    tools=self.tool_schemas,  # ← Add this!
    tool_choice="auto"  # ← And this!
)
```

However, this only allows one correction. The loop solution is more robust.