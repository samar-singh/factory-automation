"""Inventory matching agent using RAG."""
from agents.base import BaseAgent
from rag.chromadb_client import ChromaDBClient

class InventoryMatcherAgent(BaseAgent):
    """Agent for matching orders with inventory using RAG."""
    
    def __init__(self, chromadb_client: ChromaDBClient):
        """Initialize inventory matcher agent."""
        self.chromadb_client = chromadb_client
        super().__init__(
            name="Inventory Matcher",
            instructions="""You match customer tag requests with existing inventory.
            Use vector similarity search to find matches.
            Return ranked results with confidence scores."""
        )