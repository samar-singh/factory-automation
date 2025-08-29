# Validation Agent Design for Orchestrator Tool Calls

## Overview

A validation agent that acts as a gatekeeper between the orchestrator and tool execution, ensuring tools are called in the correct order and with proper dependencies satisfied.

## Architecture

```
Orchestrator → Proposes Tool Call → Validation Agent → Validates Against Rules
                                           ↓
                                    Valid? → Execute Tool
                                           ↓
                                    Invalid? → Return Feedback → Force Replan
```

## Implementation Components

### 1. Validation Rules Configuration (`validation_rules.py`)

```python
"""
Validation rules for tool execution order and dependencies.
Defines which tools must be called first and their dependencies.
"""

from typing import Dict, List, Optional
from enum import Enum

class ToolCategory(Enum):
    """Categories of tools for validation purposes"""
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    PROCESSING = "processing"
    SEARCH = "search"
    RESPONSE = "response"
    DECISION = "decision"

# Core validation rules
VALIDATION_RULES = {
    # Email Classification - MUST BE FIRST
    "classify_email_intent": {
        "must_be_first": True,
        "dependencies": [],
        "category": ToolCategory.CLASSIFICATION,
        "required_params": ["email_subject", "email_body", "sender_email"],
        "description": "Email classification must always be performed first"
    },
    
    # Attachment Processing - Requires classification
    "extract_pdf_data": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.EXTRACTION,
        "required_params": ["filename"],
        "optional_params": ["content"],
        "description": "PDF extraction requires email classification first"
    },
    
    "extract_excel_data": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.EXTRACTION,
        "required_params": ["filename"],
        "optional_params": ["content"],
        "description": "Excel extraction requires email classification first"
    },
    
    "process_tag_image": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.EXTRACTION,
        "required_params": ["image_path"],
        "description": "Image processing requires email classification first"
    },
    
    # Order Processing - Requires classification
    "process_complete_order": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["email_data"],
        "conditional_dependencies": {
            "if_has_attachments": ["extract_pdf_data", "extract_excel_data"]
        },
        "description": "Order processing requires classification and attachment extraction"
    },
    
    # Search Operations - Can be done after classification
    "search_inventory": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.SEARCH,
        "required_params": ["query"],
        "description": "Inventory search requires classification"
    },
    
    "search_visual": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.SEARCH,
        "required_params": ["image_data"],
        "description": "Visual search requires classification"
    },
    
    # Customer Context - Can be done after classification
    "get_customer_context": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.SEARCH,
        "required_params": ["customer_email"],
        "description": "Customer context requires classification"
    },
    
    # Document Generation - Requires processing
    "generate_document": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent", "process_complete_order"],
        "category": ToolCategory.RESPONSE,
        "required_params": ["document_type", "order_data"],
        "description": "Document generation requires order processing"
    },
    
    # Email Response - Should be last
    "send_email_response": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.RESPONSE,
        "should_be_last": True,
        "required_params": ["to_email", "subject", "body"],
        "description": "Email response should be sent after all processing"
    },
    
    # Payment Tracking
    "track_payment": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["payment_info"],
        "description": "Payment tracking requires classification"
    },
    
    # Order Status Updates
    "update_order_status": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["order_id", "status"],
        "description": "Order updates require classification"
    },
    
    # Supplier Handling
    "handle_supplier_inquiry": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["inquiry_data"],
        "description": "Supplier inquiries require classification"
    },
    
    # Human Review Creation
    "create_human_review": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent", "process_complete_order"],
        "category": ToolCategory.DECISION,
        "required_params": ["order_id", "reason"],
        "description": "Human review requires order processing"
    }
}

# Workflow patterns for different email types
WORKFLOW_PATTERNS = {
    "NEW_ORDER": [
        "classify_email_intent",
        "extract_pdf_data",  # if attachments
        "extract_excel_data",  # if attachments
        "process_complete_order",
        "search_inventory",
        "generate_document",
        "send_email_response"
    ],
    "PAYMENT": [
        "classify_email_intent",
        "track_payment",
        "update_order_status",
        "send_email_response"
    ],
    "INQUIRY": [
        "classify_email_intent",
        "get_customer_context",
        "search_inventory",
        "send_email_response"
    ],
    "SUPPLIER": [
        "classify_email_intent",
        "handle_supplier_inquiry",
        "send_email_response"
    ]
}
```

### 2. Validation Agent (`validation_agent.py`)

```python
"""
Validation Agent that enforces tool execution order and dependencies.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class ValidationAgent:
    """Agent that validates tool calls against predefined rules"""
    
    def __init__(self, validation_rules: Dict[str, Dict]):
        """
        Initialize validation agent with rules.
        
        Args:
            validation_rules: Dictionary of tool validation rules
        """
        self.rules = validation_rules
        self.execution_history = []  # Track what tools have been executed
        self.current_workflow = []  # Current workflow execution
        self.email_type = None  # Classified email type
        self.validation_stats = defaultdict(int)  # Track validation statistics
        self.last_error = None
        
        logger.info(f"Initialized ValidationAgent with {len(self.rules)} rules")
    
    def validate(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Validate if a tool call is allowed based on rules and execution history.
        
        Args:
            tool_name: Name of the tool to validate
            tool_args: Arguments for the tool
            context: Optional context (e.g., email data, attachments)
            
        Returns:
            Tuple of (is_valid, feedback_message)
        """
        logger.info(f"Validating tool call: {tool_name}")
        
        # Check if tool exists in rules
        if tool_name not in self.rules:
            self.validation_stats["unknown_tool"] += 1
            return False, f"Unknown tool: {tool_name}. Please use only available tools."
        
        rule = self.rules[tool_name]
        
        # Check if this must be the first tool
        if rule.get("must_be_first", False):
            if len(self.execution_history) > 0:
                self.validation_stats["wrong_first_tool"] += 1
                already_called = ", ".join(self.execution_history)
                return False, (
                    f"❌ VALIDATION ERROR: '{tool_name}' must be called FIRST!\n"
                    f"You already called: [{already_called}]\n"
                    f"Please restart the workflow with '{tool_name}' as the first tool."
                )
        
        # Check if first tool requirement is satisfied
        if len(self.execution_history) == 0:
            # First tool call - check if it should be a specific tool
            first_required_tools = [
                name for name, r in self.rules.items() 
                if r.get("must_be_first", False)
            ]
            if first_required_tools and tool_name not in first_required_tools:
                self.validation_stats["missing_first_tool"] += 1
                return False, (
                    f"❌ VALIDATION ERROR: First tool must be one of: {first_required_tools}\n"
                    f"You tried to call: '{tool_name}'\n"
                    f"Please call 'classify_email_intent' first to determine the email type."
                )
        
        # Check dependencies
        dependencies = rule.get("dependencies", [])
        missing_deps = []
        for dep in dependencies:
            if dep not in self.execution_history:
                missing_deps.append(dep)
        
        if missing_deps:
            self.validation_stats["missing_dependencies"] += 1
            return False, (
                f"❌ DEPENDENCY ERROR: '{tool_name}' requires these tools to be called first:\n"
                f"Missing: {missing_deps}\n"
                f"Already executed: {self.execution_history}\n"
                f"Please call the missing dependencies before '{tool_name}'."
            )
        
        # Check conditional dependencies
        conditional_deps = rule.get("conditional_dependencies", {})
        if conditional_deps and context:
            for condition, deps in conditional_deps.items():
                if condition == "if_has_attachments" and context.get("has_attachments"):
                    missing_conditional = []
                    for dep in deps:
                        if dep not in self.execution_history:
                            missing_conditional.append(dep)
                    if missing_conditional:
                        self.validation_stats["missing_conditional_deps"] += 1
                        return False, (
                            f"❌ CONDITIONAL DEPENDENCY ERROR: Since email has attachments,\n"
                            f"'{tool_name}' requires: {missing_conditional} to be called first.\n"
                            f"Please extract attachments before processing the order."
                        )
        
        # Check required parameters
        required_params = rule.get("required_params", [])
        missing_params = []
        for param in required_params:
            if param not in tool_args or tool_args[param] is None:
                missing_params.append(param)
        
        if missing_params:
            self.validation_stats["missing_parameters"] += 1
            return False, (
                f"❌ PARAMETER ERROR: '{tool_name}' is missing required parameters:\n"
                f"Missing: {missing_params}\n"
                f"Provided: {list(tool_args.keys())}\n"
                f"Please provide all required parameters."
            )
        
        # Check if tool should be last
        if rule.get("should_be_last", False):
            # Warn if there might be more tools to call
            logger.warning(f"Tool '{tool_name}' is typically called last in the workflow")
        
        # Validation passed
        self.validation_stats["valid"] += 1
        return True, f"✅ Tool '{tool_name}' validated successfully"
    
    def record(self, tool_name: str, result: Any = None):
        """
        Record that a tool has been executed.
        
        Args:
            tool_name: Name of the executed tool
            result: Optional result from tool execution
        """
        self.execution_history.append(tool_name)
        self.current_workflow.append({
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "result_summary": str(result)[:100] if result else None
        })
        
        # Track email type if classification tool
        if tool_name == "classify_email_intent" and result:
            try:
                if isinstance(result, str):
                    result_data = json.loads(result)
                    self.email_type = result_data.get("intent", "UNKNOWN")
                    logger.info(f"Email classified as: {self.email_type}")
            except:
                pass
        
        logger.info(f"Recorded tool execution: {tool_name} (Total: {len(self.execution_history)})")
    
    def get_suggested_next_tools(self) -> List[str]:
        """
        Suggest next tools based on current state and email type.
        
        Returns:
            List of suggested tool names
        """
        if not self.execution_history:
            return ["classify_email_intent"]
        
        # Get workflow pattern for email type
        from validation_rules import WORKFLOW_PATTERNS
        
        if self.email_type and self.email_type in WORKFLOW_PATTERNS:
            pattern = WORKFLOW_PATTERNS[self.email_type]
            # Find next tools in pattern not yet executed
            suggestions = []
            for tool in pattern:
                if tool not in self.execution_history:
                    # Check if dependencies are met
                    rule = self.rules.get(tool, {})
                    deps = rule.get("dependencies", [])
                    if all(dep in self.execution_history for dep in deps):
                        suggestions.append(tool)
            return suggestions[:3]  # Return top 3 suggestions
        
        return []
    
    def reset(self):
        """Reset validation state for new workflow"""
        self.execution_history = []
        self.current_workflow = []
        self.email_type = None
        self.last_error = None
        logger.info("ValidationAgent state reset")
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get summary of current workflow execution"""
        return {
            "executed_tools": self.execution_history,
            "email_type": self.email_type,
            "total_tools_executed": len(self.execution_history),
            "workflow_details": self.current_workflow,
            "validation_stats": dict(self.validation_stats),
            "suggested_next": self.get_suggested_next_tools()
        }
    
    def is_workflow_complete(self) -> bool:
        """
        Check if the current workflow is complete.
        
        Returns:
            True if workflow appears complete, False otherwise
        """
        # Check if email response has been sent (typical end of workflow)
        if "send_email_response" in self.execution_history:
            return True
        
        # Check if human review was created (alternative end)
        if "create_human_review" in self.execution_history:
            return True
        
        return False
```

### 3. Integration in Orchestrator (`orchestrator_v3_agentic.py`)

```python
# Add to imports
from .validation_agent import ValidationAgent
from .validation_rules import VALIDATION_RULES

class AgenticOrchestratorV3:
    def __init__(self, chromadb_client: ChromaDBClient, use_mock_gmail: bool = True):
        # ... existing init code ...
        
        # Initialize validation agent
        self.validator = ValidationAgent(VALIDATION_RULES)
        logger.info("Initialized ValidationAgent for tool call validation")
        
    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email with validation"""
        
        # Reset validator for new email
        self.validator.reset()
        
        # Determine if email has attachments for validation context
        validation_context = {
            "has_attachments": bool(email_data.get("attachments")),
            "email_data": email_data
        }
        
        # Modified tool calling loop with validation
        max_iterations = 10
        iteration = 0
        messages = [...]  # Initial messages
        
        while iteration < max_iterations:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_schemas,
                tool_choice="auto"
            )
            
            if not response.choices[0].message.tool_calls:
                # No more tools needed
                result = response.choices[0].message.content
                break
            
            # Process tool calls WITH VALIDATION
            tool_results = []
            for tool_call in response.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # VALIDATE BEFORE EXECUTION
                is_valid, feedback = self.validator.validate(
                    tool_name, 
                    tool_args,
                    validation_context
                )
                
                if is_valid:
                    # Execute the tool
                    logger.info(f"✅ Validation passed, executing: {tool_name}")
                    result = await self.confirm_and_execute(tool_name, tool_args)
                    
                    # Record successful execution
                    self.validator.record(tool_name, result)
                    
                    # Add to results
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "result": str(result)
                    })
                else:
                    # Validation failed - send error back
                    logger.warning(f"❌ Validation failed: {feedback}")
                    
                    # Create error response
                    error_response = {
                        "error": "validation_failed",
                        "message": feedback,
                        "suggestions": self.validator.get_suggested_next_tools()
                    }
                    
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
            
            # Check if we should add guidance
            if any("validation_failed" in r["result"] for r in tool_results):
                # Add system message to guide the AI
                suggestions = self.validator.get_suggested_next_tools()
                guidance = (
                    "IMPORTANT: Your previous tool call was invalid. "
                    f"Please follow the correct workflow. "
                    f"Suggested next tools: {suggestions}"
                )
                messages.append({
                    "role": "system",
                    "content": guidance
                })
            
            iteration += 1
        
        # Get workflow summary from validator
        workflow_summary = self.validator.get_workflow_summary()
        
        # Build final result with validation info
        result_dict = {
            "success": True,
            "workflow_summary": workflow_summary,
            "validation_stats": workflow_summary["validation_stats"],
            # ... rest of result ...
        }
        
        return result_dict
```

## Benefits

1. **Enforced Tool Order**: Ensures `classify_email_intent` is always called first
2. **Dependency Management**: Tools can only be called after their dependencies
3. **Parameter Validation**: Ensures required parameters are provided
4. **Helpful Feedback**: Provides clear error messages and suggestions
5. **Workflow Tracking**: Maintains execution history for debugging
6. **Statistics**: Tracks validation success/failure rates
7. **Guided Recovery**: Suggests next valid tools when validation fails

## Testing the Validation Agent

```python
# Test script
async def test_validation():
    validator = ValidationAgent(VALIDATION_RULES)
    
    # Test 1: Try to call extract_pdf_data first (should fail)
    is_valid, feedback = validator.validate(
        "extract_pdf_data",
        {"filename": "test.pdf"}
    )
    print(f"Test 1 - {is_valid}: {feedback}")
    
    # Test 2: Call classify_email_intent first (should pass)
    is_valid, feedback = validator.validate(
        "classify_email_intent",
        {
            "email_subject": "Test",
            "email_body": "Test body",
            "sender_email": "test@example.com"
        }
    )
    print(f"Test 2 - {is_valid}: {feedback}")
    
    if is_valid:
        validator.record("classify_email_intent", '{"intent": "NEW_ORDER"}')
    
    # Test 3: Now try extract_pdf_data (should pass)
    is_valid, feedback = validator.validate(
        "extract_pdf_data",
        {"filename": "test.pdf"}
    )
    print(f"Test 3 - {is_valid}: {feedback}")
    
    # Get workflow summary
    summary = validator.get_workflow_summary()
    print(f"Workflow Summary: {json.dumps(summary, indent=2)}")
```

## Deployment Strategy

1. **Phase 1**: Deploy with logging only (don't block execution)
2. **Phase 2**: Enable blocking for critical tools only
3. **Phase 3**: Full validation enforcement
4. **Phase 4**: Add machine learning to improve rules based on patterns

## Monitoring and Metrics

Track these metrics:
- Validation success rate
- Most common validation errors
- Tools that frequently fail validation
- Average workflow completion time
- Workflows that required manual intervention

## Future Enhancements

1. **Dynamic Rule Learning**: Learn optimal tool sequences from successful workflows
2. **Context-Aware Validation**: Adjust rules based on email content
3. **Parallel Execution Support**: Allow certain tools to run in parallel
4. **Rollback Support**: Track reversible actions for undo capability
5. **A/B Testing**: Compare different validation strategies