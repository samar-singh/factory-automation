#!/usr/bin/env python3
"""Test agentic orchestrator with pdb debugging"""

import asyncio
import logging
import os
import pdb
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from agents import Agent, Runner, function_tool

from factory_automation.factory_agents.mock_gmail_agent import MockGmailAgent
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# Define tools with simple return types
@function_tool
def analyze_email(subject: str, body: str) -> str:
    """Analyze email to determine type and urgency"""
    body_lower = body.lower()

    # Determine type
    if any(word in body_lower for word in ["order", "need", "require", "want"]):
        email_type = "order"
    elif any(word in body_lower for word in ["payment", "paid", "utr"]):
        email_type = "payment"
    elif any(word in body_lower for word in ["sample", "catalog"]):
        email_type = "query"
    else:
        email_type = "general"

    # Check urgency
    is_urgent = any(
        word in body_lower or word in subject.lower()
        for word in ["urgent", "asap", "immediately"]
    )

    return f"Type: {email_type}, Urgent: {is_urgent}"


@function_tool
def extract_order_items(email_body: str) -> str:
    """Extract order details from email using pattern matching"""
    import re

    # Simple extraction logic
    body_lower = email_body.lower()

    # Extract quantities
    quantities = re.findall(
        r"(\d+)\s*(?:pcs|pieces|tags|units|black|red|blue|green)", body_lower
    )

    # Extract item types
    items = []
    if "tags" in body_lower or "tag" in body_lower:
        items.append("tags")
    if "label" in body_lower:
        items.append("labels")

    # Extract colors
    colors = []
    for color in ["black", "red", "blue", "green", "white", "silver"]:
        if color in body_lower:
            colors.append(color)

    # Extract features
    features = []
    if "woven" in body_lower:
        features.append("woven")
    if "printed" in body_lower:
        features.append("printed")
    if "thread" in body_lower:
        features.append("with thread")

    # Build description
    if quantities and (items or colors):
        qty = quantities[0] if quantities else "Unknown"
        color = colors[0] if colors else ""
        item_type = items[0] if items else "items"
        feature = features[0] if features else ""

        description = f"{qty} x {color} {feature} {item_type}".strip()
        return f"Extracted items: {description}"
    else:
        return "No specific items could be extracted"


@function_tool
def search_inventory(query: str) -> str:
    """Search inventory for matching items"""
    try:
        # Get ingestion client from global
        ingestion = globals().get("INGESTION_CLIENT")
        if not ingestion:
            # Fallback to simple ChromaDB search
            client = globals().get("CHROMA_CLIENT")
            if not client:
                return "Search system not available"

            # Use basic ChromaDB search
            results = client.search(query, n_results=5)

            if (
                not results
                or not results.get("documents")
                or not results["documents"][0]
            ):
                return f"No matches found for: {query}"

            # Format results
            matches = []
            for i, (doc, distance) in enumerate(
                zip(results["documents"][0][:3], results["distances"][0][:3]), 1
            ):
                # Convert distance to similarity score (1 - normalized_distance)
                score = max(0, 1 - distance)
                matches.append(f"{doc} ({score:.0%} match)")

            return f"Found {len(results['documents'][0])} matches. Top: " + ", ".join(
                matches
            )

        # Use ingestion client's search_inventory method
        results = ingestion.search_inventory(query, limit=5)

        if not results:
            return f"No matches found for: {query}"

        # Format top 3 results
        matches = []
        for i, result in enumerate(results[:3], 1):
            score = result.get("score", 0)
            name = result.get("metadata", {}).get("trim_name", "Unknown")
            matches.append(f"{name} ({score:.0%} match)")

        return f"Found {len(results)} matches. Top: " + ", ".join(matches)

    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Search failed: {str(e)}"


@function_tool
def make_decision(search_results: str, urgency: bool = False) -> str:
    """Make approval decision based on search results"""
    pdb.set_trace()  # Debug point 1 - ACTIVE

    if "No matches found" in search_results:
        return "Decision: No matches - request clarification"

    # Extract confidence scores
    import re

    scores = re.findall(r"(\d+)% match", search_results)

    if scores:
        best_score = max(int(s) for s in scores)

        if best_score > 80:
            return f"Decision: Auto-approved ({best_score}% confidence)"
        elif best_score > 60:
            return f"Decision: Manual review needed ({best_score}% confidence)"
        else:
            return f"Decision: Low confidence ({best_score}%) - suggest alternatives"

    return "Decision: Unable to determine - needs manual review"


async def test_with_pdb():
    """Test agentic flow with pdb debugging"""

    print("\n" + "=" * 60)
    print("🐛 AGENTIC TEST WITH PDB DEBUGGING")
    print("=" * 60)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ OPENAI_API_KEY not found!")
        return

    # Initialize ChromaDB
    print("\n📦 Initializing ChromaDB...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")

    # Initialize ingestion for search
    print("🔍 Initializing search system...")
    ingestion = ExcelInventoryIngestion(
        chroma_client=chroma_client, embedding_model="stella-400m"
    )

    # Store in global for tool access
    globals()["CHROMA_CLIENT"] = chroma_client
    globals()["INGESTION_CLIENT"] = ingestion

    # Create runner
    print("🔧 Creating AI agent...")
    runner = Runner()

    # Create agent with tools
    agent = Agent(
        name="FactoryAssistant",
        model="gpt-4o",
        tools=[analyze_email, extract_order_items, search_inventory, make_decision],
        instructions="""You are a factory automation assistant. When processing an email:
1. First analyze it to understand the type and urgency
2. If it's an order, extract the items mentioned
3. Search inventory for matching items
4. Make a decision based on the search results
5. Provide a summary of your actions

Use your tools step by step.""",
    )

    # Get test email
    print("📧 Getting test email...")
    mock_gmail = MockGmailAgent()
    mock_gmail.initialize_service("test@factory.com")

    messages = (
        mock_gmail.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=1)
        .execute()
    )

    if not messages.get("messages"):
        print("No mock emails found")
        return

    email_data = mock_gmail.process_order_email(messages["messages"][0]["id"])

    print("\n📧 Test Email:")
    print(f"   From: {email_data['from']}")
    print(f"   Subject: {email_data['subject']}")
    print(f"   Body: {email_data['body'][:100]}...")

    # Build prompt
    prompt = f"""Process this email step by step:

From: {email_data['from']}
Subject: {email_data['subject']}
Body: {email_data['body']}

Use your tools to analyze, extract items, search inventory, and make a decision."""

    print("\n🤖 Starting AI processing...")
    print("   (Breakpoints are set in the tools)")
    print("   Use 'c' to continue when hitting breakpoints\n")

    # pdb.set_trace()  # Debug point 2 - before AI processing

    try:
        # Run agent
        result = await runner.run(agent, prompt)

        print("\n✅ Processing Complete!")
        print("\n📊 AI Output:")
        print("-" * 40)
        print(str(result))
        print("-" * 40)

        # Check tool usage
        if hasattr(result, "tool_calls"):
            print(f"\n🔧 Tools used: {len(result.tool_calls)}")
            for call in result.tool_calls:
                print(f"   - {call.tool}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        pdb.post_mortem()  # Debug on error


if __name__ == "__main__":
    print("\n🐛 PDB DEBUGGING GUIDE:")
    print("   n - next line")
    print("   s - step into")
    print("   c - continue")
    print("   l - list code")
    print("   p <var> - print variable")
    print("   h - help\n")

    asyncio.run(test_with_pdb())
