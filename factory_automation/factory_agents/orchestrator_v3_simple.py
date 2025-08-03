"""Simplified Agentic Orchestrator for testing"""

import logging
from typing import Any, Dict

from agents import Agent, Runner, trace, function_tool

from ..factory_database.vector_db import ChromaDBClient
from ..factory_utils.trace_monitor import trace_monitor
from .mock_gmail_agent import MockGmailAgent

logger = logging.getLogger(__name__)


class SimpleAgenticOrchestrator:
    """Simplified autonomous orchestrator for testing"""

    def __init__(self, chromadb_client: ChromaDBClient):
        """Initialize with ChromaDB and create autonomous agent"""
        self.chromadb_client = chromadb_client
        self.runner = Runner()
        self.is_monitoring = False

        # Initialize mock Gmail for testing
        self.gmail_agent = MockGmailAgent()

        # Create the autonomous agent
        self.agent = Agent(
            name="SimpleFactoryOrchestrator",
            instructions="""You are an autonomous factory automation orchestrator.

When you receive an email:
1. Analyze it to understand the type (order, payment, query)
2. If it's an order, extract items and search inventory
3. Make a decision based on search results
4. Generate appropriate response

Use your tools step by step to process the email completely.""",
            tools=[
                analyze_email_tool,
                search_inventory_tool,
                make_decision_tool,
            ],
            model="gpt-4o",
        )

        logger.info("Initialized Simple Agentic Orchestrator")

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Let the agent autonomously process an email with tracing"""
        logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")

        # Create trace name
        trace_name = f"Email_{email_data.get('subject', 'Unknown')[:20]}"

        # Use trace context
        with trace(trace_name):
            try:
                # Construct prompt
                prompt = f"""
Process this email:

From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Body: {email_data.get('body', 'No body')}

Use your tools to:
1. Analyze the email type
2. Search inventory if it's an order
3. Make a decision
4. Provide a summary
"""

                # Start monitoring
                trace_monitor.start_trace(
                    trace_name,
                    {
                        "email_from": email_data.get("from"),
                        "email_subject": email_data.get("subject"),
                    },
                )

                # Run agent
                result = await self.runner.run(self.agent, prompt)

                # Log results
                logger.info(f"Processing complete for: {trace_name}")

                # End trace
                trace_monitor.end_trace("completed", str(result)[:200])

                return {
                    "success": True,
                    "trace_name": trace_name,
                    "result": str(result),
                    "summary": "Email processed successfully",
                }

            except Exception as e:
                logger.error(f"Error: {e}")
                trace_monitor.add_error(str(e))
                trace_monitor.end_trace("failed")
                return {"success": False, "error": str(e), "trace_name": trace_name}


# Define tools outside the class for simplicity


@function_tool
def analyze_email_tool(email_subject: str, email_body: str) -> str:
    """Analyze email to determine type and extract key information"""
    body_lower = email_body.lower()

    # Determine type
    if any(word in body_lower for word in ["order", "purchase", "need", "require"]):
        email_type = "order"
    elif any(word in body_lower for word in ["payment", "paid", "utr"]):
        email_type = "payment"
    else:
        email_type = "query"

    # Check urgency
    is_urgent = "urgent" in body_lower or "asap" in body_lower

    # Extract quantities if present
    import re

    quantities = re.findall(r"(\d+)\s*(?:pcs|pieces|tags|units)", body_lower)

    return f"Email type: {email_type}, Urgent: {is_urgent}, Items: {quantities}"


@function_tool
def search_inventory_tool(search_query: str) -> str:
    """Search inventory for matching items"""
    # Mock search results for testing
    results = [
        {"name": "Black Woven Tag", "code": "BWT-001", "stock": 1000, "score": 0.85},
        {"name": "Black Cotton Tag", "code": "BCT-002", "stock": 500, "score": 0.65},
    ]

    if results:
        best = results[0]
        return f"Found {len(results)} matches. Best: {best['name']} (Stock: {best['stock']}, Match: {best['score']*100:.0f}%)"
    else:
        return "No matches found in inventory"


@function_tool
def make_decision_tool(search_results: str, is_urgent: bool = False) -> str:
    """Make decision based on search results"""
    # Simple decision logic
    if "85%" in search_results or "90%" in search_results or "95%" in search_results:
        decision = "auto_approve"
        action = "Generate quotation and send to customer"
    elif "No matches" in search_results:
        decision = "no_match"
        action = "Request more details from customer"
    else:
        decision = "manual_review"
        action = "Flag for human review"

    return f"Decision: {decision}. Action: {action}"
