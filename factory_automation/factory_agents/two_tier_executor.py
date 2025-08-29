"""
Two-Tier Execution System for Actions
Phase 4 - PLAN-2025-01-TWOTIER

Implements automatic execution for reversible actions and queuing for irreversible actions.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from ..factory_database.connection import get_db
from ..factory_database.models import ActionAudit
from .action_classifier import ActionClassifier, ActionType

logger = logging.getLogger(__name__)


class PendingAction:
    """Represents an action pending approval"""
    
    def __init__(
        self,
        action_id: str,
        action_name: str,
        action_type: ActionType,
        tool_function: Callable,
        args: Dict[str, Any],
        workflow_id: str,
        reasoning: str = ""
    ):
        self.action_id = action_id
        self.action_name = action_name
        self.action_type = action_type
        self.tool_function = tool_function
        self.args = args
        self.workflow_id = workflow_id
        self.reasoning = reasoning
        self.created_at = datetime.now()
        self.status = "pending"
        self.result = None
        self.error = None


class TwoTierExecutor:
    """
    Manages two-tier execution of actions:
    - Reversible actions execute automatically
    - Irreversible actions queue for approval
    """
    
    def __init__(self, action_classifier: ActionClassifier):
        self.action_classifier = action_classifier
        self.pending_actions: Dict[str, PendingAction] = {}
        self.executed_actions: List[str] = []
        self.current_workflow_id: Optional[str] = None
        
        logger.info("Initialized Two-Tier Executor")
    
    def set_workflow_id(self, workflow_id: str):
        """Set the current workflow ID"""
        self.current_workflow_id = workflow_id
        self.executed_actions = []
        self.pending_actions = {}
    
    async def execute_action(
        self,
        action_name: str,
        tool_function: Callable,
        args: Dict[str, Any],
        category: Optional[str] = None,
        reasoning: str = ""
    ) -> Dict[str, Any]:
        """
        Execute or queue an action based on its classification.
        
        Args:
            action_name: Name of the action/tool
            tool_function: The actual function to execute
            args: Arguments for the function
            category: Optional category for classification
            reasoning: Explanation for the action
            
        Returns:
            Result dict with execution status
        """
        # Classify the action
        action_type = self.action_classifier.classify_action(action_name, category)
        action_id = f"ACT-{uuid4().hex[:12]}"
        
        # Track in database
        await self._track_action_in_db(
            action_id=action_id,
            action_name=action_name,
            action_type=action_type,
            args=args,
            executed=(action_type == ActionType.REVERSIBLE)
        )
        
        if action_type == ActionType.REVERSIBLE:
            # Execute immediately
            logger.info(f"🟢 Auto-executing reversible action: {action_name}")
            
            try:
                # Execute the tool function
                if asyncio.iscoroutinefunction(tool_function):
                    result = await tool_function(**args)
                else:
                    result = tool_function(**args)
                
                self.executed_actions.append(action_id)
                
                # Update database with execution result
                await self._update_action_result(action_id, True, result)
                
                return {
                    "action_id": action_id,
                    "action_name": action_name,
                    "status": "executed",
                    "type": "reversible",
                    "result": result
                }
                
            except Exception as e:
                logger.error(f"Error executing {action_name}: {e}")
                await self._update_action_result(action_id, False, str(e))
                
                return {
                    "action_id": action_id,
                    "action_name": action_name,
                    "status": "error",
                    "type": "reversible",
                    "error": str(e)
                }
        
        else:
            # Queue for approval
            logger.info(f"🟠 Queuing irreversible action for approval: {action_name}")
            
            pending_action = PendingAction(
                action_id=action_id,
                action_name=action_name,
                action_type=action_type,
                tool_function=tool_function,
                args=args,
                workflow_id=self.current_workflow_id,
                reasoning=reasoning
            )
            
            self.pending_actions[action_id] = pending_action
            
            return {
                "action_id": action_id,
                "action_name": action_name,
                "status": "pending_approval",
                "type": "irreversible",
                "reasoning": reasoning,
                "preview": self._generate_preview(action_name, args)
            }
    
    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """
        Approve and execute a pending action.
        
        Args:
            action_id: ID of the action to approve
            
        Returns:
            Execution result
        """
        if action_id not in self.pending_actions:
            return {"error": f"Action {action_id} not found in pending queue"}
        
        pending_action = self.pending_actions[action_id]
        logger.info(f"✅ Approving action: {pending_action.action_name}")
        
        try:
            # Execute the tool function
            if asyncio.iscoroutinefunction(pending_action.tool_function):
                result = await pending_action.tool_function(**pending_action.args)
            else:
                result = pending_action.tool_function(**pending_action.args)
            
            pending_action.status = "approved_executed"
            pending_action.result = result
            
            # Update database
            await self._update_action_result(action_id, True, result, approved=True)
            
            # Remove from pending queue
            del self.pending_actions[action_id]
            self.executed_actions.append(action_id)
            
            return {
                "action_id": action_id,
                "action_name": pending_action.action_name,
                "status": "executed_after_approval",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error executing approved action {pending_action.action_name}: {e}")
            pending_action.status = "error"
            pending_action.error = str(e)
            
            await self._update_action_result(action_id, False, str(e))
            
            return {
                "action_id": action_id,
                "action_name": pending_action.action_name,
                "status": "error",
                "error": str(e)
            }
    
    async def reject_action(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Reject a pending action.
        
        Args:
            action_id: ID of the action to reject
            reason: Reason for rejection
            
        Returns:
            Rejection confirmation
        """
        if action_id not in self.pending_actions:
            return {"error": f"Action {action_id} not found in pending queue"}
        
        pending_action = self.pending_actions[action_id]
        logger.info(f"❌ Rejecting action: {pending_action.action_name}")
        
        pending_action.status = "rejected"
        
        # Update database
        await self._update_action_result(action_id, False, f"Rejected: {reason}", approved=False)
        
        # Remove from pending queue
        del self.pending_actions[action_id]
        
        return {
            "action_id": action_id,
            "action_name": pending_action.action_name,
            "status": "rejected",
            "reason": reason
        }
    
    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get all pending actions for the current workflow"""
        return [
            {
                "action_id": action.action_id,
                "action_name": action.action_name,
                "type": action.action_type.value,
                "args": action.args,
                "reasoning": action.reasoning,
                "created_at": action.created_at.isoformat(),
                "preview": self._generate_preview(action.action_name, action.args)
            }
            for action in self.pending_actions.values()
        ]
    
    def get_executed_actions(self) -> List[str]:
        """Get list of executed action IDs"""
        return self.executed_actions
    
    async def _track_action_in_db(
        self,
        action_id: str,
        action_name: str,
        action_type: ActionType,
        args: Dict[str, Any],
        executed: bool
    ):
        """Track action in the database"""
        with get_db() as db:
            action = ActionAudit(
                action_id=action_id,
                workflow_id=self.current_workflow_id or "unknown",
                action_name=action_name,
                action_type=action_type.value,
                action_category="two_tier_execution",
                details=json.dumps(args),
                confidence=1.0,  # Two-tier doesn't use confidence
                executed=executed,
                requires_approval=(action_type == ActionType.IRREVERSIBLE),
                can_rollback=(action_type == ActionType.REVERSIBLE),
                created_at=datetime.now()
            )
            db.add(action)
            db.commit()
    
    async def _update_action_result(
        self,
        action_id: str,
        success: bool,
        result: Any,
        approved: Optional[bool] = None
    ):
        """Update action result in database"""
        with get_db() as db:
            action = db.query(ActionAudit).filter_by(action_id=action_id).first()
            if action:
                action.executed = success
                action.execution_result = json.dumps(result) if success else result
                action.executed_at = datetime.now() if success else None
                if approved is not None:
                    action.approved = approved
                    action.approved_at = datetime.now() if approved else None
                db.commit()
    
    def _generate_preview(self, action_name: str, args: Dict[str, Any]) -> str:
        """Generate a human-readable preview of the action"""
        previews = {
            "send_email_response": lambda a: f"Send email to {a.get('to', 'customer')}",
            "create_proforma_invoice": lambda a: f"Create invoice #{a.get('invoice_number', 'new')}",
            "reserve_inventory_final": lambda a: f"Reserve {a.get('quantity', 0)} items",
            "process_payment": lambda a: f"Process payment of {a.get('amount', 0)}",
            "send_customer_email": lambda a: f"Email customer: {a.get('subject', 'Update')}",
        }
        
        if action_name in previews:
            return previews[action_name](args)
        
        return f"Execute {action_name}"
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get summary of current workflow execution"""
        return {
            "workflow_id": self.current_workflow_id,
            "executed_actions": len(self.executed_actions),
            "pending_actions": len(self.pending_actions),
            "actions": {
                "executed": self.executed_actions,
                "pending": self.get_pending_actions()
            }
        }