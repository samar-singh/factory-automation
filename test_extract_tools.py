#!/usr/bin/env python3
"""Extract tool calls from raw responses"""

import asyncio
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)

import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")


def extract_tool_calls_from_result(result):
    """Extract tool calls from RunResult"""
    tool_calls = []

    if hasattr(result, "raw_responses"):
        for response in result.raw_responses:
            # Check if it's a ModelResponse
            if hasattr(response, "model_response"):
                model_resp = response.model_response
                if hasattr(model_resp, "choices"):
                    for choice in model_resp.choices:
                        if hasattr(choice, "message") and hasattr(
                            choice.message, "tool_calls"
                        ):
                            if choice.message.tool_calls:
                                for tc in choice.message.tool_calls:
                                    tool_call = {
                                        "id": tc.id if hasattr(tc, "id") else None,
                                        "tool": (
                                            tc.function.name
                                            if hasattr(tc.function, "name")
                                            else "unknown"
                                        ),
                                        "args": (
                                            json.loads(tc.function.arguments)
                                            if hasattr(tc.function, "arguments")
                                            else {}
                                        ),
                                    }
                                    tool_calls.append(tool_call)

    return tool_calls


async def test_with_extraction():
    """Test tool call extraction"""

    print("\n" + "=" * 60)
    print("TESTING TOOL CALL EXTRACTION")
    print("=" * 60)

    # Initialize
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = AgenticOrchestratorV3(chroma_client)

    # Modify the process_email method to extract tool calls
    original_process_email = orchestrator.process_email

    async def process_email_with_tracking(email_data):
        """Enhanced process_email that tracks tool calls"""
        # Call original method
        result_dict = await original_process_email(email_data)

        # Extract tool calls from the runner's last result
        # This is a bit hacky but works for testing
        try:
            # Run the agent again to get the raw result
            prompt = f"""Process this email completely using your tools:

From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Body: {email_data.get('body', 'No body')}

Use your tools to analyze, extract items, search inventory, and make decisions."""

            result = await orchestrator.runner.run(orchestrator.agent, prompt)

            # Extract tool calls
            tool_calls = extract_tool_calls_from_result(result)

            # Update the result dict
            result_dict["tool_calls"] = tool_calls
            result_dict["autonomous_actions"] = len(tool_calls)

        except Exception as e:
            print(f"Error extracting tool calls: {e}")

        return result_dict

    # Test email
    test_email = {
        "from": "customer@example.com",
        "subject": "Order 200 blue tags",
        "body": "Please send me 200 blue woven tags with our logo.",
        "message_id": "test_extraction",
    }

    print("\n📧 Test Email:")
    print(f"   From: {test_email['from']}")
    print(f"   Subject: {test_email['subject']}")
    print(f"   Body: {test_email['body']}")

    print("\n🤖 Processing with tool tracking...")

    result = await process_email_with_tracking(test_email)

    print("\n📊 Results:")
    print(f"   Success: {result['success']}")
    print(f"   Tool calls found: {len(result.get('tool_calls', []))}")

    if result.get("tool_calls"):
        print("\n🔧 Tool Usage Details:")
        for i, call in enumerate(result["tool_calls"], 1):
            print(f"\n   {i}. Tool: {call['tool']}")
            print(f"      ID: {call['id']}")
            print(f"      Args: {json.dumps(call['args'], indent=9)}")

    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_with_extraction())
