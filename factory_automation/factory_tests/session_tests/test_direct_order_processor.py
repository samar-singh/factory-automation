#!/usr/bin/env python3
"""
Direct test of OrderProcessorAgent with file path attachments
This bypasses the AI orchestrator to test the core functionality
"""

import asyncio
import os
import tempfile
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_order_processor_directly():
    """Test OrderProcessorAgent directly with file attachments"""
    
    print("\n" + "="*60)
    print("DIRECT ORDER PROCESSOR TEST")
    print("="*60 + "\n")
    
    # Create test CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("Item,Quantity,Brand,Price\n")
        f.write("Blue Shirt Tag,500,Peter England,2.50\n")
        f.write("Red Polo Tag,300,Allen Solly,3.00\n")
        csv_file = f.name
    
    print(f"Test file created: {csv_file}")
    print(f"File exists: {os.path.exists(csv_file)}")
    
    # Import and initialize
    from factory_automation.factory_database.vector_db import ChromaDBClient
    from factory_automation.factory_agents.order_processor_agent import OrderProcessorAgent
    
    chromadb_client = ChromaDBClient()
    processor = OrderProcessorAgent(chromadb_client)
    
    # Prepare email and attachments
    email_body = """
    Please process our order for:
    - 500 Blue Shirt Tags for Peter England
    - 300 Red Polo Tags for Allen Solly
    See attached CSV for details.
    """
    
    attachments = [
        {
            'filename': os.path.basename(csv_file),
            'filepath': csv_file,  # Direct file path
            'mime_type': 'text/csv'
        }
    ]
    
    print("\nAttachment structure:")
    for att in attachments:
        print(f"  - filename: {att['filename']}")
        print(f"  - filepath: {att['filepath']}")
        print(f"  - mime_type: {att['mime_type']}")
        print(f"  - file exists: {os.path.exists(att['filepath'])}")
    
    # Process the order
    print("\nProcessing order...")
    try:
        result = await processor.process_order_email(
            email_subject="Test Order",
            email_body=email_body,
            email_date=datetime.now(),
            sender_email="test@example.com",
            attachments=attachments
        )
        
        print("\n✅ Processing successful!")
        print(f"Order ID: {result.order.order_id}")
        print(f"Customer: {result.order.customer.company_name}")
        print(f"Items extracted: {len(result.order.items)}")
        print(f"Attachments processed: {len(result.order.attachments)}")
        
        # Check attachment processing
        for att in result.order.attachments:
            print(f"\nAttachment: {att.filename}")
            print(f"  Type: {att.type}")
            if att.extracted_data:
                if 'error' in att.extracted_data:
                    print(f"  ❌ Error: {att.extracted_data['error']}")
                else:
                    print("  ✅ Data extracted successfully")
                    if 'rows' in att.extracted_data:
                        print(f"     Rows: {att.extracted_data['rows']}")
        
        print(f"\nConfidence: {result.order.extraction_confidence:.2%}")
        print(f"Action: {result.recommended_action}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        os.unlink(csv_file)
        print(f"\nTest file deleted: {csv_file}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_order_processor_directly())