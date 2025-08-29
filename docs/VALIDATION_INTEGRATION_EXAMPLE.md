# Integration Example: Adding ValidationAgent to Orchestrator

## How to Integrate ValidationAgent into orchestrator_v3_agentic.py

### 1. Add Imports

```python
# Add to imports at the top
from .validation_agent import ValidationAgent
from .validation_rules import VALIDATION_RULES
```

### 2. Initialize in Constructor

```python
class AgenticOrchestratorV3:
    def __init__(self, chromadb_client: ChromaDBClient, use_mock_gmail: bool = True):
        # ... existing init code ...
        
        # Initialize validation agent (add after other initializations)
        self.validator = ValidationAgent(VALIDATION_RULES)
        self.validator.set_strict_mode(True)  # Enable strict validation
        logger.info("Initialized ValidationAgent for tool call validation")
```

### 3. Modify process_email Method

Replace the tool execution section (around lines 489-574) with validation-enabled version:

```python
async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process email with validation"""
    
    # Reset validator for new email
    self.validator.reset()
    
    # Determine validation context
    validation_context = {
        "has_attachments": bool(email_data.get("attachments")),
        "email_data": email_data
    }
    
    # ... existing setup code ...
    
    # Modified tool calling loop with validation
    max_iterations = 10
    iteration = 0
    validation_failures = 0
    max_validation_failures = 3
    
    while iteration < max_iterations:
        # Call OpenAI API with tools
        logger.info(f"Tool calling iteration {iteration}")
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tool_schemas,
            tool_choice="auto"
        )
        
        # Check if AI wants to make tool calls
        if not response.choices[0].message.tool_calls:
            # No more tools needed
            result = response.choices[0].message.content
            logger.info("AI completed tool calling - no more tools needed")
            break
        
        # Process tool calls WITH VALIDATION
        logger.info(f"AI requested {len(response.choices[0].message.tool_calls)} tool calls")
        tool_results = []
        had_validation_failure = False
        
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            logger.info(f"Tool call requested: {tool_name} with args: {tool_args}")
            
            # VALIDATE BEFORE EXECUTION
            is_valid, feedback = self.validator.validate(
                tool_name, 
                tool_args,
                validation_context
            )
            
            if is_valid:
                # Validation passed - execute the tool
                logger.info(f"✅ Validation passed for: {tool_name}")
                
                # Execute tool using existing logic
                result = await self.confirm_and_execute(tool_name, tool_args)
                
                # Record successful execution
                self.validator.record(tool_name, result)
                
                # Track execution (existing tracking logic)
                # ... (your existing tracking code) ...
                
                # Add successful result
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "result": str(result)
                })
                
            else:
                # Validation failed - send error back to AI
                logger.warning(f"❌ Validation failed for {tool_name}: {feedback}")
                had_validation_failure = True
                validation_failures += 1
                
                # Create detailed error response
                error_response = {
                    "error": "validation_failed",
                    "tool": tool_name,
                    "message": feedback,
                    "suggestions": self.validator.get_suggested_next_tools(),
                    "executed_so_far": self.validator.execution_history,
                    "guidance": (
                        "IMPORTANT: Your tool call was invalid. Please read the error message carefully. "
                        "You must follow the correct workflow order. "
                        "Always call 'classify_email_intent' first if you haven't already."
                    )
                }
                
                # Add error result
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "result": json.dumps(error_response)
                })
        
        # Add results to message history
        messages.append(response.choices[0].message)
        for tool_result in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_call_id"],
                "content": tool_result["result"]
            })
        
        # If validation failed, add strong guidance
        if had_validation_failure:
            suggestions = self.validator.get_suggested_next_tools()
            executed = self.validator.execution_history
            
            # Build guidance message
            guidance_msg = (
                "⚠️ VALIDATION FAILED - PLEASE FOLLOW THE CORRECT WORKFLOW:\n\n"
            )
            
            if not executed:
                guidance_msg += (
                    "You haven't executed any valid tools yet.\n"
                    "YOU MUST START WITH: classify_email_intent\n\n"
                    "Call it with these parameters:\n"
                    "- email_subject: The subject of the email\n"
                    "- email_body: The body of the email\n"
                    "- sender_email: The sender's email address\n"
                )
            else:
                guidance_msg += (
                    f"Tools executed so far: {executed}\n"
                    f"Suggested next tools: {suggestions}\n\n"
                    "Remember the correct order:\n"
                    "1. classify_email_intent (MUST be first)\n"
                    "2. extract attachments (if any)\n"
                    "3. process the order\n"
                    "4. generate response"
                )
            
            # Add system message with guidance
            messages.append({
                "role": "system",
                "content": guidance_msg
            })
            
            # Check if too many validation failures
            if validation_failures >= max_validation_failures:
                logger.error(f"Too many validation failures ({validation_failures})")
                result = (
                    "Workflow terminated due to repeated validation failures. "
                    "Please ensure you call 'classify_email_intent' first."
                )
                break
        
        iteration += 1
    
    # Check if we hit max iterations
    if iteration >= max_iterations:
        logger.warning(f"Hit maximum iterations ({max_iterations})")
        result = "Maximum iterations reached. Workflow may be incomplete."
    
    # Get workflow summary from validator
    workflow_summary = self.validator.get_workflow_summary()
    
    # Log validation statistics
    logger.info(f"Validation stats: {workflow_summary['validation_stats']}")
    logger.info(f"Workflow complete: {workflow_summary['is_complete']}")
    
    # Build final result with validation info
    result_dict = {
        "success": True,
        "workflow_summary": workflow_summary,
        "validation_stats": workflow_summary["validation_stats"],
        "workflow_complete": workflow_summary["is_complete"],
        "executed_tools": workflow_summary["executed_tools"],
        "email_type": workflow_summary["email_type"],
        # ... rest of your existing result ...
    }
    
    return result_dict
```

### 4. Add Helper Method for Validation Monitoring

```python
def get_validation_stats(self) -> Dict[str, Any]:
    """Get validation statistics for monitoring"""
    if hasattr(self, 'validator'):
        return self.validator.get_workflow_summary()
    return {}
```

## Testing the Integration

Create a test script to verify validation is working:

```python
# test_validation.py
import asyncio
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_database.vector_db import ChromaDBClient

async def test_validation():
    # Initialize orchestrator with validation
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=False)
    
    # Test email data
    email_data = {
        "message_id": "test_123",
        "from": "trimsblr@yahoo.co.in",
        "to": "orders@factory.com",
        "subject": "Allen Solly Order",
        "body": "Please process this order...",
        "attachments": [
            {"filename": "order.pdf", "filepath": "/path/to/order.pdf"}
        ]
    }
    
    # Process with validation
    result = await orchestrator.process_email(email_data)
    
    # Check validation stats
    print("Validation Statistics:")
    print(f"- Valid calls: {result['validation_stats'].get('valid', 0)}")
    print(f"- Invalid calls: {result['validation_stats'].get('wrong_first_tool', 0) + result['validation_stats'].get('missing_dependencies', 0)}")
    print(f"- Executed tools: {result['executed_tools']}")
    print(f"- Workflow complete: {result['workflow_complete']}")

if __name__ == "__main__":
    asyncio.run(test_validation())
```

## Benefits of This Integration

1. **Enforced Workflow Order**: The AI cannot skip `classify_email_intent`
2. **Clear Error Messages**: The AI gets specific feedback about what went wrong
3. **Guided Recovery**: Suggestions help the AI correct its mistakes
4. **Monitoring**: Track validation success/failure rates
5. **Flexible**: Can toggle strict mode for testing vs production

## Configuration Options

```python
# In orchestrator __init__
self.validator = ValidationAgent(VALIDATION_RULES)

# Configuration options
self.validator.set_strict_mode(True)  # Strict validation
# or
self.validator.set_strict_mode(False)  # Lenient mode for testing
```

## Monitoring Validation Performance

The validation stats will show:
- How often tools are called in wrong order
- Which dependencies are commonly missed
- Success rate of validation
- Most common workflow patterns

This data can be used to:
1. Improve AI prompts
2. Adjust validation rules
3. Identify training needs
4. Optimize workflows