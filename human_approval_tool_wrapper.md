
# Human-in-the-Loop Tool Execution in OpenAI Agentic Architecture

This document describes how to enable **human approval before tool execution** in OpenAI’s `@function_tool` agentic architecture.  
The main issue arises because `@function_tool` creates a **`FunctionTool` object**, which is **not directly callable**.  
Instead, tools must be executed via their `.on_invoke_tool(ctx, input_json)` method.

---

## ✅ Problem Recap

- `@function_tool` returns a **FunctionTool** (not a plain function)
- Orchestrator code was doing:
  ```python
  result = await tool(**kwargs)
  ```
  → This fails with `'FunctionTool' object is not callable`

- Correct way is:
  ```python
  result = await tool.on_invoke_tool(ctx, input_json)
  ```

---

## 🔧 Solution: Human-Approval Wrapper

We create a **universal wrapper** that:
1. Asks for human approval before executing a tool.
2. Adapts `FunctionTool` to look like a callable async function.
3. Converts kwargs → JSON before execution.

### `tool_factory.py`

```python
import json
from openai.types.beta import ToolContext  # Required for tool invocation

def with_human_approval(function_tool):
    """
    Wraps a FunctionTool object to make it callable with kwargs,
    while also asking for human approval before execution.
    """
    async def wrapper(*args, **kwargs):
        print(f"\n🔔 Tool requested: {function_tool.name}")
        print(f"   Args: {args}, Kwargs: {kwargs}")

        approval = input("Do you approve this action? (yes/no): ").strip().lower()
        if approval != "yes":
            return {"error": f"❌ Action {function_tool.name} denied by user."}

        # Convert kwargs → JSON string
        input_json = json.dumps(kwargs)

        # Execute the underlying tool
        result = await function_tool.on_invoke_tool(
            ToolContext(id="manual-approval"),  # Stub context, can be extended
            input_json
        )
        return result

    # Preserve metadata so orchestrator recognizes the tool
    wrapper.name = function_tool.name
    wrapper.params_json_schema = function_tool.params_json_schema
    wrapper.original_tool = function_tool

    return wrapper
```

---

## 🔄 Orchestrator Changes

### `orchestrator_v3_agentic.py`

When registering tools, wrap them:

```python
from tool_factory import with_human_approval
from email_tools import EmailTools

# Create tool instances
email_tools = EmailTools()

# Wrap them with approval logic
tools = [
    with_human_approval(email_tools.send_email_response),
    with_human_approval(email_tools.search_inventory),
]

# Map for orchestrator
tool_map = {tool.name: tool for tool in tools}
```

### Executing Tool Calls

```python
tool = tool_map[tool_name]
result = await tool(**tool_args)   # ✅ Works now (wrapper adapts it)
```

---

## 🔑 Benefits

- Human approval enforced before every tool run.
- Orchestrator does not need to know about `.on_invoke_tool` details.
- Tools still expose metadata (`name`, `params_json_schema`) for LLM planning.
- Extensible: approval step can later be replaced with UI confirmation, logging, or policy checks.

---

## 🚀 Next Steps

- Extend `ToolContext` with request/session metadata.
- Replace `input()` with chat-based approval flow.
- Add audit logging for approved/denied actions.

---

**End of Solution**
