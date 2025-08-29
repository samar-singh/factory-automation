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
        self.strict_mode = True  # Can be toggled for testing
        
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
        logger.debug(f"Execution history: {self.execution_history}")
        logger.debug(f"Tool args: {tool_args}")
        
        # Check if tool exists in rules
        if tool_name not in self.rules:
            # Check for special cases
            if tool_name == "check_emails":
                # Allow check_emails without restrictions
                self.validation_stats["valid"] += 1
                return True, f"✅ Tool '{tool_name}' validated successfully"
            
            self.validation_stats["unknown_tool"] += 1
            self.last_error = f"Unknown tool: {tool_name}"
            
            if not self.strict_mode:
                logger.warning(f"Unknown tool {tool_name} - allowing in non-strict mode")
                return True, f"⚠️ Unknown tool '{tool_name}' - proceeding with caution"
            
            return False, (
                f"❌ VALIDATION ERROR: Unknown tool: '{tool_name}'.\n"
                f"Available tools: {list(self.rules.keys())}\n"
                f"Please use only available tools."
            )
        
        rule = self.rules[tool_name]
        
        # Check if this must be the first tool
        if rule.get("must_be_first", False):
            if len(self.execution_history) > 0:
                self.validation_stats["wrong_first_tool"] += 1
                self.last_error = f"{tool_name} must be first but {len(self.execution_history)} tools already called"
                already_called = ", ".join(self.execution_history[-3:])  # Show last 3 tools
                
                return False, (
                    f"❌ VALIDATION ERROR: '{tool_name}' must be called FIRST!\n"
                    f"You already called: [{already_called}]\n"
                    f"Please restart the workflow with '{tool_name}' as the first tool.\n"
                    f"Hint: For processing emails, always start with 'classify_email_intent'."
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
                self.last_error = f"First tool must be {first_required_tools} but got {tool_name}"
                
                # Special case: if trying to process attachments first
                if tool_name in ["extract_pdf_data", "extract_excel_data", "process_tag_image"]:
                    return False, (
                        f"❌ VALIDATION ERROR: Cannot extract attachments before classification!\n"
                        f"You tried to call: '{tool_name}' as the first tool.\n"
                        f"You MUST call 'classify_email_intent' FIRST to determine the email type.\n"
                        f"Correct order: classify_email_intent → extract attachments → process order"
                    )
                
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
            self.last_error = f"Missing dependencies for {tool_name}: {missing_deps}"
            
            # Provide specific guidance based on the tool
            guidance = ""
            if tool_name == "process_complete_order":
                guidance = "\n💡 Tip: For order processing, follow this sequence:\n1. classify_email_intent\n2. extract attachments (if any)\n3. process_complete_order"
            elif tool_name in ["generate_document", "send_email_response"]:
                guidance = "\n💡 Tip: Complete all processing before generating responses."
            
            return False, (
                f"❌ DEPENDENCY ERROR: '{tool_name}' requires these tools to be called first:\n"
                f"Missing: {missing_deps}\n"
                f"Already executed: {self.execution_history[-3:] if self.execution_history else []}\n"
                f"Please call the missing dependencies before '{tool_name}'.{guidance}"
            )
        
        # Check conditional dependencies
        conditional_deps = rule.get("conditional_dependencies", {})
        if conditional_deps and context:
            for condition, deps in conditional_deps.items():
                if condition == "if_has_attachments" and context.get("has_attachments"):
                    # Check if ANY attachment extraction tool has been called
                    extraction_tools = ["extract_pdf_data", "extract_excel_data", "process_tag_image"]
                    if not any(tool in self.execution_history for tool in extraction_tools):
                        self.validation_stats["missing_conditional_deps"] += 1
                        self.last_error = f"Has attachments but no extraction done for {tool_name}"
                        
                        return False, (
                            f"❌ CONDITIONAL DEPENDENCY ERROR: Since email has attachments,\n"
                            f"'{tool_name}' requires attachment extraction first.\n"
                            f"Please call one of: {extraction_tools}\n"
                            f"Already executed: {self.execution_history[-3:] if self.execution_history else []}"
                        )
        
        # Check required parameters (relaxed for now as tools handle this)
        required_params = rule.get("required_params", [])
        if self.strict_mode and required_params:
            missing_params = []
            for param in required_params:
                if param not in tool_args or tool_args.get(param) is None:
                    missing_params.append(param)
            
            if missing_params:
                self.validation_stats["missing_parameters"] += 1
                self.last_error = f"Missing params for {tool_name}: {missing_params}"
                
                return False, (
                    f"❌ PARAMETER ERROR: '{tool_name}' is missing required parameters:\n"
                    f"Missing: {missing_params}\n"
                    f"Provided: {list(tool_args.keys())}\n"
                    f"Please provide all required parameters."
                )
        
        # Check if tool should be last
        if rule.get("should_be_last", False):
            # Just log a warning, don't block
            logger.info(f"Note: Tool '{tool_name}' is typically called last in the workflow")
        
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
                    # Try to parse JSON result
                    if result.startswith('{'):
                        result_data = json.loads(result)
                        self.email_type = result_data.get("intent", result_data.get("classification", "UNKNOWN"))
                    else:
                        # Plain text result
                        self.email_type = result.upper() if result else "UNKNOWN"
                    logger.info(f"Email classified as: {self.email_type}")
            except Exception as e:
                logger.warning(f"Could not parse classification result: {e}")
        
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
        from .validation_rules import WORKFLOW_PATTERNS
        
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
                        if len(suggestions) >= 3:
                            break
            return suggestions
        
        # Generic suggestions based on what's been done
        suggestions = []
        
        # If classified but no extraction, suggest extraction
        if "classify_email_intent" in self.execution_history:
            if "extract_pdf_data" not in self.execution_history:
                suggestions.append("extract_pdf_data")
            if "extract_excel_data" not in self.execution_history:
                suggestions.append("extract_excel_data")
            if "process_complete_order" not in self.execution_history:
                suggestions.append("process_complete_order")
        
        return suggestions[:3]
    
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
            "suggested_next": self.get_suggested_next_tools(),
            "last_error": self.last_error,
            "is_complete": self.is_workflow_complete()
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
        
        # Check if document was generated (might be enough)
        if "generate_document" in self.execution_history:
            return True
        
        return False
    
    def set_strict_mode(self, strict: bool):
        """
        Set validation strictness.
        
        Args:
            strict: If True, enforce all rules strictly. If False, be more lenient.
        """
        self.strict_mode = strict
        logger.info(f"ValidationAgent strict mode set to: {strict}")