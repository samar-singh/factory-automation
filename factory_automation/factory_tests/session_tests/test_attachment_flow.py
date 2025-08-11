#!/usr/bin/env python3
"""Test attachment flow to debug empty filepath issue"""

import asyncio
import os
import tempfile
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_attachment_processing():
    """Test the complete attachment processing flow"""

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp.write("Item,Quantity,Brand,Price\n")
        tmp.write("Blue Tag,100,Peter England,2.50\n")
        test_file = tmp.name

    logger.info(f"Created test file: {test_file}")
    logger.info(f"File exists: {os.path.exists(test_file)}")

    # Import after setup
    from factory_automation.factory_database.vector_db import ChromaDBClient
    from factory_automation.factory_agents.orchestrator_v3_agentic import (
        AgenticOrchestratorV3,
    )

    # Initialize
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=False)

    # Simulate what the UI does
    email_data = {
        "message_id": "test_001",
        "from": "test@example.com",
        "subject": "Test Order",
        "body": "Please process the attached order",
        "email_type": "order",
        "attachments": [
            {
                "filename": os.path.basename(test_file),
                "filepath": test_file,  # This is what UI should pass
                "mime_type": "text/csv",
            }
        ],
    }

    logger.info(f"Email data attachments: {email_data['attachments']}")

    # Process the email
    result = await orchestrator.process_email(email_data)

    logger.info(f"Processing result: {result}")

    # Clean up
    os.unlink(test_file)

    return result


if __name__ == "__main__":
    asyncio.run(test_attachment_processing())
