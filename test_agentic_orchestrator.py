#!/usr/bin/env python3
"""Test the Agentic Orchestrator V3"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.mock_gmail_agent import MockGmailAgent
from factory_automation.factory_utils.trace_monitor import trace_monitor
from factory_automation.factory_ui.trace_dashboard import create_trace_dashboard

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_autonomous_email_processing():
    """Test autonomous email processing"""
    print("\n" + "=" * 60)
    print("TESTING AUTONOMOUS EMAIL PROCESSING")
    print("=" * 60)

    # Initialize components
    print("\n🔧 Initializing Agentic Orchestrator...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = AgenticOrchestratorV3(chroma_client)

    # Get a sample email
    mock_agent = MockGmailAgent()
    mock_agent.initialize_service("test@factory.com")

    # Get first mock email
    messages = (
        mock_agent.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=1)
        .execute()
    )

    if messages.get("messages"):
        email_data = mock_agent.process_order_email(messages["messages"][0]["id"])

        print("\n📧 Processing Email:")
        print(f"From: {email_data.get('from', 'Unknown')}")
        print(f"Subject: {email_data.get('subject', 'No subject')}")
        print(f"Type: {email_data.get('email_type', 'unknown')}")

        print("\n🤖 Letting AI process autonomously...")
        print("(AI will decide which tools to use)\n")

        # Process autonomously
        result = await orchestrator.process_email(email_data)

        print("\n" + "-" * 50)
        print("AUTONOMOUS PROCESSING RESULTS")
        print("-" * 50)

        if result["success"]:
            print("✅ Processing successful!")
            print(f"🔧 Tools called: {result.get('autonomous_actions', 0)}")

            # Show tool calls
            if result.get("tool_calls"):
                print("\n📊 Tool Usage Sequence:")
                for i, call in enumerate(result["tool_calls"], 1):
                    print(f"\n{i}. Tool: {call['tool']}")
                    print(f"   Args: {json.dumps(call['args'], indent=2)}")
                    if isinstance(call["result"], (dict, list)):
                        print(
                            f"   Result: {json.dumps(call['result'], indent=2)[:200]}..."
                        )
                    else:
                        print(f"   Result: {call['result']}")

            print("\n📝 Final Summary:")
            print(result.get("final_summary", "No summary"))

            # Show generated documents
            if result.get("documents_generated"):
                print(f"\n📄 Documents Generated: {len(result['documents_generated'])}")
                for doc in result["documents_generated"]:
                    print(f"- {doc}")
        else:
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
    else:
        print("No mock emails found")


async def test_tool_functionality():
    """Test individual tools"""
    print("\n" + "=" * 60)
    print("TESTING INDIVIDUAL TOOL FUNCTIONALITY")
    print("=" * 60)

    # Initialize orchestrator
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = AgenticOrchestratorV3(chroma_client)

    print("\n✅ Orchestrator initialized with the following tools:")
    for i, tool in enumerate(orchestrator.tools, 1):
        print(f"   {i}. {tool.name} - {tool.description}")

    print("\n📝 To test tools, we'll process a sample email that will use them:")

    # Create a test email that will trigger tool usage
    test_email = {
        "from": "customer@example.com",
        "subject": "Urgent Order - 500 Black Tags",
        "body": "We urgently need 500 black woven tags with silver thread. Please send quotation ASAP.",
        "message_id": "test_tool_functionality",
    }

    print("\nTest Email:")
    print(f"  From: {test_email['from']}")
    print(f"  Subject: {test_email['subject']}")
    print(f"  Body: {test_email['body']}")

    print("\n🤖 Processing email (AI will use tools autonomously)...")

    # Process the email - the AI will use tools
    result = await orchestrator.process_email(test_email)

    if result["success"]:
        print("\n✅ Processing successful!")

        # Show which tools were used
        if result.get("tool_calls"):
            print(f"\n🔧 Tools used ({len(result['tool_calls'])} total):")
            for i, call in enumerate(result["tool_calls"], 1):
                print(f"\n{i}. Tool: {call['tool']}")
                print(f"   Args: {json.dumps(call['args'], indent=6)}")
                print(f"   Result: {str(call['result'])[:200]}...")
        else:
            print("\n⚠️  No tool calls recorded")

        # Show final summary
        print("\n📊 Final Summary:")
        print(result.get("final_summary", "No summary")[:500])
    else:
        print(f"\n❌ Processing failed: {result.get('error', 'Unknown error')}")


async def test_autonomous_monitoring():
    """Test autonomous email monitoring"""
    print("\n" + "=" * 60)
    print("TESTING AUTONOMOUS EMAIL MONITORING")
    print("=" * 60)

    # Initialize
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = AgenticOrchestratorV3(chroma_client)

    print("\n🔄 Starting autonomous monitoring (3 cycles, 10s apart)...")
    print("AI will autonomously check and process emails\n")

    # Override poll interval for testing
    orchestrator.is_monitoring = True

    for cycle in range(3):
        print(f"\n--- Monitoring Cycle {cycle + 1} ---")

        # Run one monitoring cycle
        check_prompt = """
Check for new emails and process any that you find.
Use your tools to:
1. Check for new emails
2. Process each email completely
3. Take all necessary actions
4. Provide a summary of what was done
"""

        result = await orchestrator.runner.run(orchestrator.agent, check_prompt)

        # Show what happened
        if hasattr(result, "tool_calls") and result.tool_calls:
            print(f"🔧 AI used {len(result.tool_calls)} tools")
            for call in result.tool_calls:
                print(f"  - {call.tool}")
        else:
            print("🔧 No tools were called")

        print("\n📝 AI Summary:")
        print(result.final_output[:500] if result.final_output else "No summary")

        if cycle < 2:
            print("\nWaiting 10 seconds...")
            await asyncio.sleep(10)

    orchestrator.is_monitoring = False


async def compare_approaches():
    """Compare workflow vs agentic approach"""
    print("\n" + "=" * 60)
    print("COMPARING WORKFLOW VS AGENTIC APPROACHES")
    print("=" * 60)

    # Get a sample email
    email_data = {
        "from": "allen.solly@example.com",
        "subject": "Order for 500 Black Tags",
        "body": "We need 500 black woven tags with silver thread. Size 2x1 inches. Urgent delivery needed.",
        "message_id": "test_001",
    }

    print("\n📧 Test Email:")
    print(f"Subject: {email_data['subject']}")
    print(f"Body: {email_data['body']}")

    # Agentic approach
    print("\n🤖 AGENTIC APPROACH (Autonomous)")
    print("-" * 40)

    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    agentic_orchestrator = AgenticOrchestratorV3(chroma_client)

    result = await agentic_orchestrator.process_email(email_data)

    print(f"Tools autonomously called: {result.get('autonomous_actions', 0)}")
    print(f"Processing complete: {result.get('processing_complete', False)}")

    print("\n🔄 WORKFLOW APPROACH (Fixed sequence)")
    print("-" * 40)
    print("Would follow fixed steps:")
    print("1. Analyze email (hardcoded)")
    print("2. Extract order (regex patterns)")
    print("3. Search inventory (direct DB call)")
    print("4. Make decision (if-else rules)")
    print("5. Generate document (template)")

    print("\n📊 KEY DIFFERENCES:")
    print("Agentic: AI decides tool usage dynamically")
    print("Workflow: Follows predetermined sequence")


async def view_trace_results():
    """View trace monitoring results"""
    print("\n" + "=" * 60)
    print("TRACE MONITORING RESULTS")
    print("=" * 60)

    # Get trace summary
    summary = trace_monitor.get_trace_summary()

    print("\n📊 Overall Statistics:")
    print(f"Total Traces: {summary['total_traces']}")
    print(f"Total Tool Calls: {summary['tool_usage']}")
    print(f"Total Decisions: {summary['decision_count']}")
    print(f"Total Errors: {summary['error_count']}")

    print("\n🔧 Tool Usage:")
    for tool, count in summary["tool_usage"].items():
        print(f"  - {tool}: {count} calls")

    print("\n📝 Recent Traces:")
    for trace in summary["recent_traces"]:
        print(f"\n  {trace['name']}")
        print(f"    Status: {trace['status']}")
        print(f"    Duration: {trace['duration']:.2f}s")
        print(f"    Tools: {trace['tool_count']}")
        print(f"    Sequence: {' → '.join(trace['tool_sequence'][:5])}")

    # View specific trace
    if summary["total_traces"] > 0:
        print("\n" + "-" * 40)
        choice = input("\nEnter trace name to view details (or press Enter to skip): ")
        if choice:
            details = trace_monitor.visualize_trace(choice)
            print(details)

    # View trace in OpenAI platform
    print("\n💡 View traces in OpenAI platform:")
    print("   https://platform.openai.com/traces")
    print("\n   Your traces will appear there with names like:")
    print("   - Email_Processing_[subject]")
    print("   - Email_Monitoring_Cycle_[number]")


async def launch_trace_ui():
    """Launch the trace monitoring UI"""
    print("\n" + "=" * 60)
    print("LAUNCHING TRACE MONITORING UI")
    print("=" * 60)

    print("\n🚀 Starting Gradio Trace Dashboard...")
    print("   This will open in your browser")
    print("   URL: http://localhost:7861")

    dashboard = create_trace_dashboard()
    dashboard.launch(share=False, server_port=7861, inbrowser=True)


async def main():
    """Main test menu"""
    while True:
        print("\n" + "=" * 60)
        print("AGENTIC ORCHESTRATOR V3 TEST MENU")
        print("=" * 60)
        print("1. Test autonomous email processing")
        print("2. Test individual tool functionality")
        print("3. Test autonomous monitoring")
        print("4. Compare workflow vs agentic approaches")
        print("5. View trace results")
        print("6. Launch trace monitoring UI")
        print("7. Exit")

        choice = input("\nSelect option (1-7): ")

        if choice == "1":
            await test_autonomous_email_processing()
        elif choice == "2":
            await test_tool_functionality()
        elif choice == "3":
            await test_autonomous_monitoring()
        elif choice == "4":
            await compare_approaches()
        elif choice == "5":
            await view_trace_results()
        elif choice == "6":
            await launch_trace_ui()
        elif choice == "7":
            print("\nExiting...")
            break
        else:
            print("Invalid choice")

        if choice != "7":
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    print("\n🚀 AGENTIC ORCHESTRATOR V3")
    print("This system uses autonomous AI agents with tool calling")
    print("The AI decides which tools to use and when")

    # Check if running in non-interactive mode
    import sys

    if len(sys.argv) > 1:
        # Run specific test based on argument
        test_num = sys.argv[1]
        if test_num == "1":
            asyncio.run(test_autonomous_email_processing())
        elif test_num == "2":
            asyncio.run(test_tool_functionality())
        elif test_num == "3":
            asyncio.run(test_autonomous_monitoring())
        elif test_num == "4":
            asyncio.run(compare_approaches())
        elif test_num == "5":
            asyncio.run(view_trace_results())
        else:
            print(f"Invalid test number: {test_num}")
    else:
        try:
            asyncio.run(main())
        except (EOFError, KeyboardInterrupt):
            print("\nRunning test 1 automatically...")
            asyncio.run(test_autonomous_email_processing())
