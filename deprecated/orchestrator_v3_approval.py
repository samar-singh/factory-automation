"""
Orchestrator V3 with Proper Approval Flow
Based on user's example - intercepts tool calls BEFORE execution
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict
import uuid

from openai import AsyncOpenAI

from ..factory_config.settings import settings
from ..factory_database.connection import get_db
from ..factory_database.models import ActionAudit
from .action_classifier import ActionClassifier, ActionType

logger = logging.getLogger(__name__)


class OrchestratorV3WithApproval:
    """Orchestrator that implements proper approval flow for irreversible actions"""
    
    def __init__(self, chromadb_client, tool_factory):
        """Initialize orchestrator with approval capabilities"""
        self.chromadb_client = chromadb_client
        self.tool_factory = tool_factory
        self.action_classifier = ActionClassifier()
        
        # Get tools and build tool map
        self.tools = tool_factory.get_tools_for_v3()
        self.tool_map = {}
        for tool in self.tools:
            self.tool_map[tool.name] = tool.function if hasattr(tool, 'function') else tool
        
        # OpenAI client
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Tracking
        self.current_workflow_id = None
        self.pending_actions = []
        self.auto_executed_actions = []
        
        logger.info(f"Initialized Orchestrator with Approval Flow - {len(self.tools)} tools")
    
    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"WF-{timestamp}-{unique_id}"
    
    def _generate_action_id(self) -> str:
        """Generate unique action ID"""
        return f"ACT-{uuid.uuid4().hex[:12]}"
    
    async def confirm_and_execute(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Confirm and execute a tool call based on approval logic.
        This is the key method from the user's example.
        """
        # Get the tool function
        tool_func = self.tool_map.get(tool_name)
        if not tool_func:
            return json.dumps({"error": f"Tool {tool_name} not found"})
        
        # Classify the action
        action_type = self.action_classifier.classify_action(tool_name)
        action_id = self._generate_action_id()
        
        # Log the intended tool call
        logger.info(f"🔔 Agent wants to call tool: {tool_name} with args: {tool_args}")
        
        if action_type == ActionType.IRREVERSIBLE:
            # For irreversible actions, queue for approval
            logger.warning(f"🟠 IRREVERSIBLE ACTION - REQUIRES APPROVAL: {tool_name}")
            
            # Store pending action
            pending_action = {
                "action_id": action_id,
                "action_name": tool_name,
                "parameters": tool_args,
                "status": "pending_approval",
                "type": "irreversible",
                "queued_at": datetime.now().isoformat()
            }
            self.pending_actions.append(pending_action)
            
            # Track in database
            await self._track_action(
                action_id=action_id,
                action_name=tool_name,
                action_type="irreversible",
                parameters=tool_args,
                executed=False,
                result={"status": "pending_approval"}
            )
            
            # Return message indicating approval needed (not executing)
            return json.dumps({
                "status": "pending_approval",
                "action_id": action_id,
                "message": f"❌ Action {tool_name} was denied by policy. Requires human approval.",
                "instruction": "Please review and approve this action in the UI."
            })
            
        else:
            # For reversible actions, execute immediately
            logger.info(f"🟢 AUTO-EXECUTING REVERSIBLE ACTION: {tool_name}")
            
            try:
                # Execute the tool
                if asyncio.iscoroutinefunction(tool_func):
                    result = await tool_func(**tool_args)
                else:
                    result = tool_func(**tool_args)
                
                # Track execution
                self.auto_executed_actions.append({
                    "action_id": action_id,
                    "action_name": tool_name,
                    "status": "executed",
                    "type": "reversible",
                    "executed_at": datetime.now().isoformat()
                })
                
                await self._track_action(
                    action_id=action_id,
                    action_name=tool_name,
                    action_type="reversible",
                    parameters=tool_args,
                    executed=True,
                    result=result
                )
                
                logger.info(f"✅ Result: {tool_name} executed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Error executing {tool_name}: {e}")
                return json.dumps({"error": f"Error executing {tool_name}: {str(e)}"})
    
    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email using custom execution loop with approval flow.
        This follows the pattern from the user's example.
        """
        logger.info(f"Processing email with approval flow: {email_data.get('subject', 'No subject')}")
        
        # Generate workflow ID
        self.current_workflow_id = self._generate_workflow_id()
        self.pending_actions = []
        self.auto_executed_actions = []
        
        # Prepare context
        email_body = email_data.get("body", "")
        attachments = email_data.get("attachments", [])
        
        # Build prompt
        prompt = f"""
Analyze and process this business email:

From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Body: {email_body}
Attachments: {len(attachments)} files

Your workflow:
1. First classify the email intent
2. Process based on classification
3. Generate appropriate responses
"""
        
        # Get tool schemas for OpenAI
        tools_schema = []
        for tool in self.tools:
            tool_schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": getattr(tool, 'description', ''),
                    "parameters": getattr(tool, 'parameters', {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            }
            tools_schema.append(tool_schema)
        
        # Initial messages
        messages = [
            {"role": "system", "content": "You are a factory automation orchestrator."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # Get initial response from model
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools_schema,
                tool_choice="auto"
            )
            
            # Process tool calls with approval logic (key part from example)
            if response.choices[0].message.tool_calls:
                tool_results = []
                
                for tool_call in response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # THIS IS THE KEY: Intercept and apply approval logic
                    result = await self.confirm_and_execute(tool_name, tool_args)
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "result": result
                    })
                    
                    # Add to message history
                    messages.append(response.choices[0].message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
                
                # Get final response after tools
                final_response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                
                return {
                    "status": "success",
                    "workflow_id": self.current_workflow_id,
                    "auto_executed": len(self.auto_executed_actions),
                    "pending_approval": len(self.pending_actions),
                    "actions": {
                        "executed": self.auto_executed_actions,
                        "pending": self.pending_actions
                    },
                    "message": final_response.choices[0].message.content
                }
            else:
                # No tools needed
                return {
                    "status": "success",
                    "workflow_id": self.current_workflow_id,
                    "message": response.choices[0].message.content
                }
                
        except Exception as e:
            logger.error(f"Error in approval flow: {e}")
            return {
                "status": "error",
                "error": str(e),
                "workflow_id": self.current_workflow_id
            }
    
    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """Approve and execute a pending action"""
        # Find pending action
        pending_action = None
        for action in self.pending_actions:
            if action.get("action_id") == action_id:
                pending_action = action
                break
        
        if not pending_action:
            return {"error": f"Action {action_id} not found"}
        
        # Get tool function
        tool_name = pending_action["action_name"]
        tool_func = self.tool_map.get(tool_name)
        
        if not tool_func:
            return {"error": f"Tool {tool_name} not found"}
        
        logger.info(f"✅ APPROVING ACTION: {tool_name} ({action_id})")
        
        try:
            # Execute the approved action
            params = pending_action.get("parameters", {})
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**params)
            else:
                result = tool_func(**params)
            
            # Update status
            pending_action["status"] = "approved_and_executed"
            pending_action["executed_at"] = datetime.now().isoformat()
            
            # Remove from pending
            self.pending_actions.remove(pending_action)
            
            # Track execution
            await self._track_action(
                action_id=action_id,
                action_name=tool_name,
                action_type="irreversible",
                parameters=params,
                executed=True,
                result=result
            )
            
            return {
                "status": "success",
                "action_id": action_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error executing approved action: {e}")
            return {"error": str(e)}
    
    async def _track_action(
        self,
        action_id: str,
        action_name: str,
        action_type: str,
        parameters: Dict[str, Any],
        executed: bool,
        result: Any = None
    ):
        """Track action in database"""
        try:
            with get_db() as db:
                audit = ActionAudit(
                    workflow_id=self.current_workflow_id,
                    action_id=action_id,
                    action_name=action_name,
                    action_type=action_type,
                    action_category="orchestrator",  # Add required field
                    details=parameters,  # Use details instead of parameters
                    executed=1 if executed else 0,  # Convert to integer
                    execution_result=result,  # Use correct field name
                    executed_at=datetime.now() if executed else None,
                    created_at=datetime.now()
                )
                db.add(audit)
                db.commit()
        except Exception as e:
            logger.error(f"Error tracking action: {e}")