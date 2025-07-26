"""Order interpretation agent for extracting order details."""
from agents.base import BaseAgent

class OrderInterpreterAgent(BaseAgent):
    """Agent for interpreting order details from emails."""
    
    def __init__(self):
        """Initialize order interpreter agent."""
        super().__init__(
            name="Order Interpreter",
            instructions="""You extract order information from emails.
            Extract: tag details, quantities, customer info, delivery requirements.
            Handle attachments and images using vision capabilities."""
        )