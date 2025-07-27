"""Base agent implementation using OpenAI Agents SDK."""
from typing import List, Optional, Dict, Any, Callable
from openai_agents import Agent, Runner, tool
import logging

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        name: str,
        instructions: str,
        tools: Optional[List] = None,
        handoffs: Optional[List[Agent]] = None
    ):
        """Initialize base agent.
        
        Args:
            name: Agent name
            instructions: Agent instructions
            tools: List of tools available to the agent
            handoffs: List of agents this agent can hand off to
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=instructions,
            tools=tools or [],
            handoffs=handoffs or []
        )
        self.runner = Runner()
        
    async def run(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the agent with a message.
        
        Args:
            message: Input message
            context: Optional context dictionary
            
        Returns:
            Agent response dictionary
        """
        try:
            logger.info(f"Running {self.name} with message: {message[:100]}...")
            
            # Run the agent
            result = await self.runner.run(
                self.agent,
                message,
                context=context
            )
            
            # Extract response
            response = {
                "agent": self.name,
                "message": result.final_output,
                "context": result.context,
                "success": True
            }
            
            logger.info(f"{self.name} completed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {str(e)}")
            return {
                "agent": self.name,
                "error": str(e),
                "success": False
            }
    
    def add_tool(self, tool):
        """Add a tool to the agent."""
        self.agent.tools.append(tool)
        
    def add_handoff(self, agent: Agent):
        """Add a handoff agent."""
        self.agent.handoffs.append(agent)
    
    def as_tool(self, tool_name: Optional[str] = None, 
                tool_description: Optional[str] = None) -> Callable:
        """Convert this agent to a function tool for use by other agents.
        
        Args:
            tool_name: Optional custom tool name (defaults to agent name)
            tool_description: Optional custom description
            
        Returns:
            Function tool that can be used by other agents
        """
        name = tool_name or self.name.lower().replace(" ", "_")
        description = tool_description or f"Use the {self.name} agent to {self.agent.instructions[:100]}..."
        
        @tool(name=name, description=description)
        async def agent_tool(prompt: str, **kwargs) -> Dict[str, Any]:
            """Execute the agent with the given prompt and any additional context."""
            context = kwargs.get('context', {})
            result = await self.run(prompt, context)
            return result
        
        return agent_tool