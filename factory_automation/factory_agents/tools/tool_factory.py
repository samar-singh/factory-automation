"""Tool factory for creating orchestrator tools with appropriate configuration"""

import json
import logging
from typing import Any, Dict, List, Optional

from .attachment_tools import AttachmentTools
from .customer_tools import CustomerTools
from .document_tools import DocumentTools
from .email_tools import EmailTools
from .inventory_tools import InventoryTools
from .order_tools import OrderTools
from .payment_tools import PaymentTools
from .supplier_tools import SupplierTools

# Import action classifier for Phase 2
from ..action_classifier import ActionClassifier, ActionType, ActionCategory

# Import proper ToolContext from agents SDK
from agents.tool_context import ToolContext
from agents.usage import Usage

logger = logging.getLogger(__name__)


def create_approval_wrapper(function_tool, action_classifier):
    """
    Wraps a FunctionTool object to make it callable with kwargs,
    while integrating with our approval system.
    Uses proper ToolContext from the agents SDK.
    
    Args:
        function_tool: The FunctionTool object to wrap
        action_classifier: ActionClassifier instance for determining if approval needed
        
    Returns:
        Wrapped async function that handles approval logic
    """
    async def wrapper(**kwargs):
        tool_name = function_tool.name
        
        # Classify the action
        action_type = action_classifier.classify_action(tool_name)
        
        if action_type == ActionType.IRREVERSIBLE:
            # Don't execute - return pending status for approval
            return json.dumps({
                "status": "pending_approval",
                "tool_name": tool_name,
                "message": f"❌ Action {tool_name} requires human approval before execution."
            })
        
        # For reversible actions, execute via on_invoke_tool
        try:
            # Convert kwargs to JSON string as required by on_invoke_tool
            input_json = json.dumps(kwargs)
            
            # Create proper ToolContext
            # The context parameter can be None or a minimal object
            ctx = ToolContext(
                context=None,  # Can be enhanced with session/request context later
                usage=Usage(),  # Empty usage tracking object
                tool_name=tool_name,
                tool_call_id=f"call_{tool_name}_{id(kwargs)}"  # Unique ID for this call
            )
            
            # Execute the tool using its on_invoke_tool method
            result = await function_tool.on_invoke_tool(ctx, input_json)
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return json.dumps({
                "status": "error",
                "tool_name": tool_name,
                "error": str(e)
            })
    
    # Preserve metadata so orchestrator can still identify the tool
    wrapper.name = function_tool.name
    wrapper.params_json_schema = getattr(function_tool, 'params_json_schema', {})
    wrapper.description = getattr(function_tool, 'description', '')
    wrapper.original_tool = function_tool  # Keep reference to original
    wrapper.is_wrapped = True  # Flag to identify wrapped tools
    
    return wrapper


class ToolFactory:
    """Factory for creating and configuring orchestrator tools"""
    
    def __init__(
        self,
        mode: str = "execute",
        chromadb_client=None,
        gmail_agent=None,
        openai_client=None,
        order_processor=None,
        image_processor=None,
        embeddings_manager=None,
        email_configs: Optional[Dict] = None,
        pattern_config: Optional[Dict] = None,
    ):
        """
        Initialize tool factory with dependencies
        
        Args:
            mode: "execute" for v3 (performs actions), "propose" for v4 (generates proposals)
            chromadb_client: ChromaDB client for vector operations
            gmail_agent: Gmail agent for email operations
            openai_client: OpenAI client for AI operations
            order_processor: Order processing agent
            image_processor: Image processing agent
            embeddings_manager: Embeddings manager (for v4)
            email_configs: Email configuration dictionary
            pattern_config: Pattern learning configuration
        """
        self.mode = mode
        self.chromadb_client = chromadb_client
        self.gmail_agent = gmail_agent
        self.openai_client = openai_client
        self.order_processor = order_processor
        self.image_processor = image_processor
        self.embeddings_manager = embeddings_manager
        self.email_configs = email_configs or {}
        self.pattern_config = pattern_config or {}
        
        # Initialize action classifier for Phase 2
        self.action_classifier = ActionClassifier()
        
        # Tool name to action type mapping
        self.tool_classifications: Dict[str, ActionType] = {}
        
        logger.info(f"Initialized ToolFactory in {mode} mode with action classifier")
    
    def create_all_tools(self) -> List:
        """Create all available tools for an orchestrator"""
        all_tools = []
        
        # Email tools - classify_email_intent is always needed even without gmail_agent
        if self.openai_client:
            email_tools = EmailTools(
                gmail_agent=self.gmail_agent,  # Can be None
                openai_client=self.openai_client,
                email_configs=self.email_configs,
                pattern_config=self.pattern_config,
                mode=self.mode
            )
            all_tools.extend(email_tools.create_tools())
            logger.info(f"Added {len(email_tools.create_tools())} email tools")
        
        # Inventory tools
        if self.chromadb_client:
            inventory_tools = InventoryTools(
                chromadb_client=self.chromadb_client,
                embeddings_manager=self.embeddings_manager,
                mode=self.mode
            )
            all_tools.extend(inventory_tools.create_tools())
            logger.info(f"Added {len(inventory_tools.create_tools())} inventory tools")
        
        # Order tools
        if self.order_processor and self.chromadb_client:
            order_tools = OrderTools(
                order_processor=self.order_processor,
                chromadb_client=self.chromadb_client,
                mode=self.mode
            )
            all_tools.extend(order_tools.create_tools())
            logger.info(f"Added {len(order_tools.create_tools())} order tools")
        
        # Document tools
        document_tools = DocumentTools(mode=self.mode)
        all_tools.extend(document_tools.create_tools())
        logger.info(f"Added {len(document_tools.create_tools())} document tools")
        
        # Customer tools
        if self.chromadb_client:
            customer_tools = CustomerTools(
                chromadb_client=self.chromadb_client,
                mode=self.mode
            )
            all_tools.extend(customer_tools.create_tools())
            logger.info(f"Added {len(customer_tools.create_tools())} customer tools")
        
        # Payment tools
        payment_tools = PaymentTools(mode=self.mode)
        all_tools.extend(payment_tools.create_tools())
        logger.info(f"Added {len(payment_tools.create_tools())} payment tools")
        
        # Supplier tools
        supplier_tools = SupplierTools(mode=self.mode)
        all_tools.extend(supplier_tools.create_tools())
        logger.info(f"Added {len(supplier_tools.create_tools())} supplier tools")
        
        # Attachment tools
        attachment_tools = AttachmentTools(
            image_processor=self.image_processor,
            mode=self.mode
        )
        all_tools.extend(attachment_tools.create_tools())
        logger.info(f"Added {len(attachment_tools.create_tools())} attachment tools")
        
        # Ensure classify_email_intent is first in the tool list for proper ordering
        sorted_tools = []
        classify_tool = None
        other_tools = []
        
        for tool in all_tools:
            if hasattr(tool, 'name') and tool.name == 'classify_email_intent':
                classify_tool = tool
            else:
                other_tools.append(tool)
        
        # Put classify_email_intent first if it exists
        if classify_tool:
            sorted_tools.append(classify_tool)
            logger.info("Placed classify_email_intent as first tool")
        sorted_tools.extend(other_tools)
        
        # Wrap all tools with approval logic
        wrapped_tools = []
        for tool in sorted_tools:
            wrapped_tool = create_approval_wrapper(tool, self.action_classifier)
            wrapped_tools.append(wrapped_tool)
        
        logger.info(f"Created {len(all_tools)} tools, wrapped {len(wrapped_tools)} with approval logic in {self.mode} mode")
        logger.info(f"First tool: {wrapped_tools[0].name if wrapped_tools and hasattr(wrapped_tools[0], 'name') else 'unknown'}")
        return wrapped_tools
    
    def create_selected_tools(self, tool_names: List[str]) -> List:
        """Create only selected tools by name"""
        tool_map = {
            "email": EmailTools,
            "inventory": InventoryTools,
            "order": OrderTools,
            "document": DocumentTools,
            "customer": CustomerTools,
            "payment": PaymentTools,
            "supplier": SupplierTools,
            "attachment": AttachmentTools,
        }
        
        selected_tools = []
        
        for name in tool_names:
            if name == "email" and self.gmail_agent and self.openai_client:
                tools = EmailTools(
                    gmail_agent=self.gmail_agent,
                    openai_client=self.openai_client,
                    email_configs=self.email_configs,
                    pattern_config=self.pattern_config,
                    mode=self.mode
                )
                selected_tools.extend(tools.create_tools())
                
            elif name == "inventory" and self.chromadb_client:
                tools = InventoryTools(
                    chromadb_client=self.chromadb_client,
                    embeddings_manager=self.embeddings_manager,
                    mode=self.mode
                )
                selected_tools.extend(tools.create_tools())
                
            elif name == "order" and self.order_processor and self.chromadb_client:
                tools = OrderTools(
                    order_processor=self.order_processor,
                    chromadb_client=self.chromadb_client,
                    mode=self.mode
                )
                selected_tools.extend(tools.create_tools())
                
            elif name == "document":
                tools = DocumentTools(mode=self.mode)
                selected_tools.extend(tools.create_tools())
                
            elif name == "customer" and self.chromadb_client:
                tools = CustomerTools(
                    chromadb_client=self.chromadb_client,
                    mode=self.mode
                )
                selected_tools.extend(tools.create_tools())
                
            elif name == "payment":
                tools = PaymentTools(mode=self.mode)
                selected_tools.extend(tools.create_tools())
                
            elif name == "supplier":
                tools = SupplierTools(mode=self.mode)
                selected_tools.extend(tools.create_tools())
                
            elif name == "attachment":
                tools = AttachmentTools(
                    image_processor=self.image_processor,
                    mode=self.mode
                )
                selected_tools.extend(tools.create_tools())
            else:
                logger.warning(f"Tool category '{name}' not found or dependencies missing")
        
        logger.info(f"Created {len(selected_tools)} selected tools in {self.mode} mode")
        return selected_tools
    
    def get_tools_for_v3(self) -> List:
        """Get tools configured for V3 orchestrator (execution mode)"""
        if self.mode != "execute":
            logger.warning("Factory not in execute mode, switching for V3")
            self.mode = "execute"
        
        # V3 needs all tools for autonomous execution
        return self.create_all_tools()
    
    def get_tools_for_v4(self) -> List:
        """Get tools configured for V4 orchestrator (proposal mode)"""
        if self.mode != "propose":
            logger.warning("Factory not in propose mode, switching for V4")
            self.mode = "propose"
        
        # V4 needs proposal-oriented tools
        # Can customize which tools are needed
        return self.create_selected_tools([
            "email",
            "inventory",
            "order",
            "document",
            "customer",
            "attachment"
        ])
    
    def get_tools_for_custom(self, tool_categories: List[str]) -> List:
        """Get tools for a custom orchestrator configuration"""
        return self.create_selected_tools(tool_categories)
    
    def classify_tool(self, tool_name: str, category: Optional[ActionCategory] = None) -> ActionType:
        """
        Classify a tool as reversible or irreversible.
        Phase 2 - Action Classification System
        
        Args:
            tool_name: Name of the tool
            category: Optional category for context
            
        Returns:
            ActionType.REVERSIBLE or ActionType.IRREVERSIBLE
        """
        # Check if already classified
        if tool_name in self.tool_classifications:
            return self.tool_classifications[tool_name]
        
        # Use action classifier
        classification = self.action_classifier.classify_action(tool_name, category)
        
        # Cache the classification
        self.tool_classifications[tool_name] = classification
        
        logger.info(f"Tool '{tool_name}' classified as {classification.value}")
        return classification
    
    def get_tool_requirements(self, tool_name: str) -> Dict[str, Any]:
        """
        Get requirements for a specific tool.
        
        Returns:
            Dictionary with tool requirements including approval needs
        """
        return self.action_classifier.get_action_requirements(tool_name)
    
    def is_tool_irreversible(self, tool_name: str) -> bool:
        """Check if a tool action is irreversible and requires approval"""
        return self.classify_tool(tool_name) == ActionType.IRREVERSIBLE
    
    def is_tool_reversible(self, tool_name: str) -> bool:
        """Check if a tool action is reversible and can auto-execute"""
        return self.classify_tool(tool_name) == ActionType.REVERSIBLE
    
    def get_tool_classifications_summary(self) -> Dict[str, List[str]]:
        """
        Get a summary of all classified tools.
        
        Returns:
            Dictionary with reversible and irreversible tool lists
        """
        reversible = []
        irreversible = []
        
        # Classify common tools
        common_tools = [
            # Email tools
            "check_emails", "classify_email_intent", "send_email_response",
            "generate_email_response",
            
            # Inventory tools
            "search_inventory", "search_visual", "reserve_inventory_final",
            
            # Order tools
            "process_complete_order", "update_order_status", "confirm_order",
            
            # Document tools
            "generate_document", "send_invoice",
            
            # Customer tools
            "get_customer_context", "update_customer_info",
            
            # Payment tools
            "track_payment", "process_payment",
            
            # Supplier tools
            "handle_supplier_inquiry", "send_supplier_order",
            
            # Attachment tools
            "extract_excel_data", "extract_pdf_data", "process_tag_image",
        ]
        
        for tool in common_tools:
            classification = self.classify_tool(tool)
            if classification == ActionType.REVERSIBLE:
                reversible.append(tool)
            else:
                irreversible.append(tool)
        
        return {
            "reversible": reversible,
            "irreversible": irreversible,
            "total_reversible": len(reversible),
            "total_irreversible": len(irreversible),
        }
    
    def wrap_tool_with_classification(self, tool, tool_name: str):
        """
        Wrap a tool with classification metadata.
        This helps the orchestrator know if approval is needed.
        
        Args:
            tool: The tool function
            tool_name: Name of the tool
            
        Returns:
            Tool with classification metadata
        """
        classification = self.classify_tool(tool_name)
        
        # Add metadata to the tool
        if hasattr(tool, '__dict__'):
            tool.action_type = classification
            tool.requires_approval = classification == ActionType.IRREVERSIBLE
            tool.can_auto_execute = classification == ActionType.REVERSIBLE
            
        logger.debug(f"Wrapped tool '{tool_name}' with classification: {classification.value}")
        return tool