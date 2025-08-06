#!/usr/bin/env python3
"""Debug tool calls tracking"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import logging

from agents import Agent, Runner, function_tool

from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def debug_tool_calls():
    """Debug how tool calls are tracked"""

    print("\n" + "=" * 60)
    print("DEBUGGING TOOL CALLS TRACKING")
    print("=" * 60)

    # Initialize
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = AgenticOrchestratorV3(chroma_client)

    # Create a simple test
    print("\n📧 Processing test email...")

    # Directly test the runner
    runner = Runner()

    # Create a simple agent with one tool
    @function_tool
    def test_tool(message: str) -> str:
        """A simple test tool"""
        return f"Processed: {message}"

    agent = Agent(
        name="TestAgent",
        model="gpt-4o",
        instructions="Use the test_tool to process the message.",
        tools=[test_tool],
    )

    # Run the agent
    result = await runner.run(agent, "Please process this message: Hello World")

    print("\n🔍 Inspecting result object:")
    print(f"Type: {type(result)}")
    print(f"Attributes: {dir(result)}")

    # Check for tool calls
    print("\n📊 Checking for tool calls:")

    # Try different attributes
    attrs_to_check = [
        "tool_calls",
        "tools",
        "calls",
        "function_calls",
        "history",
        "messages",
    ]
    for attr in attrs_to_check:
        if hasattr(result, attr):
            value = getattr(result, attr)
            print(f"✅ Found '{attr}': {type(value)}")
            if value:
                print(f"   Content: {value}")
        else:
            print(f"❌ No attribute '{attr}'")

    # Check if result is iterable
    if hasattr(result, "__iter__"):
        print("\n📋 Result is iterable, contents:")
        try:
            for item in result:
                print(f"   - {type(item)}: {item}")
                if hasattr(item, "tool_calls"):
                    print(f"     Found tool_calls: {item.tool_calls}")
        except:
            print("   Could not iterate")

    # Print the full result
    print("\n📄 Full result:")
    print(str(result))

    # Check raw_responses
    print("\n🔍 Checking raw_responses:")
    if hasattr(result, "raw_responses") and result.raw_responses:
        print(f"Found {len(result.raw_responses)} raw responses")
        for i, resp in enumerate(result.raw_responses):
            print(f"\nResponse {i+1}:")
            print(f"  Type: {type(resp)}")
            if hasattr(resp, "choices") and resp.choices:
                for choice in resp.choices:
                    if hasattr(choice, "message"):
                        msg = choice.message
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            print(f"  ✅ Found tool calls: {len(msg.tool_calls)}")
                            for tc in msg.tool_calls:
                                print(
                                    f"     - {tc.function.name if hasattr(tc, 'function') else tc}"
                                )

    # Now test with the orchestrator
    print("\n\n" + "=" * 60)
    print("TESTING WITH ORCHESTRATOR")
    print("=" * 60)

    test_email = {
        "from": "test@example.com",
        "subject": "Test Order",
        "body": "Need 100 tags",
        "message_id": "test_debug",
    }

    result2 = await orchestrator.process_email(test_email)

    print("\n📊 Orchestrator result:")
    print(f"Success: {result2['success']}")
    print(f"Tool calls tracked: {len(result2.get('tool_calls', []))}")
    print(f"Autonomous actions: {result2.get('autonomous_actions', 0)}")


if __name__ == "__main__":
    asyncio.run(debug_tool_calls())
