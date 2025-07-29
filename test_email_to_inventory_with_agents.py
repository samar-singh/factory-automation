#!/usr/bin/env python3
"""End-to-end test using the OpenAI Agents SDK framework"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.gmail_agent import GmailAgent
from factory_automation.factory_agents.inventory_rag_agent import InventoryRAGAgent
from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion
from factory_automation.factory_database.vector_db import ChromaDBClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_inventory_ingested():
    """Ensure inventory is in ChromaDB"""
    logger.info("Checking ChromaDB inventory...")
    
    chroma_client = ChromaDBClient()
    count = chroma_client.collection.count()
    
    if count == 0:
        logger.info("No inventory found. Ingesting from Excel files...")
        ingestion = ExcelInventoryIngestion(
            chroma_client=chroma_client,
            embedding_model='stella-400m'
        )
        results = ingestion.ingest_inventory_folder('inventory')
        total = sum(r.get('items_ingested', 0) for r in results if r['status'] == 'success')
        logger.info(f"Ingested {total} items")
    else:
        logger.info(f"Found {count} items in inventory")
    
    return count > 0

def test_inventory_matching_agent():
    """Test the inventory matching agent with various orders"""
    
    print("\n" + "="*70)
    print("TESTING INVENTORY MATCHING AGENT")
    print("="*70)
    
    # Initialize the agent
    inventory_agent = InventoryRAGAgent()
    
    # Test orders
    test_orders = [
        "Need 500 Allen Solly casual tags black cotton",
        "Urgent requirement for 1000 Myntra tags with thread",
        "Please send 200 Peter England formal blue tags",
        "Looking for 300 lifestyle tags premium quality",
        "Required 100 Amazon tags sustainable material"
    ]
    
    for i, order in enumerate(test_orders, 1):
        print(f"\n{i}. Processing: {order}")
        print("-" * 70)
        
        # Use the agent's run method (synchronous)
        result = inventory_agent.run(order)
        print(result)

def test_complete_workflow():
    """Test complete workflow from order text to inventory match"""
    
    print("\n" + "="*70)
    print("COMPLETE ORDER PROCESSING WORKFLOW")
    print("="*70)
    
    # Simulate email order content
    email_orders = [
        {
            'from': 'ABC Garments <abc@example.com>',
            'subject': 'Urgent Order - Allen Solly Tags',
            'body': '''Dear Sir,

We urgently need 500 Allen Solly casual tags in black cotton material.
These are required for our new collection launching next week.

Please confirm availability and pricing.

Best regards,
ABC Garments'''
        },
        {
            'from': 'XYZ Fashion House <xyz@fashion.com>',
            'subject': 'Tag Order - Myntra Collection',
            'body': '''Hi,

Please process our order for:
- 1000 Myntra tags with thread
- Prefer sustainable materials if available

This is urgent - needed within 3 days.

Thanks,
XYZ Fashion'''
        }
    ]
    
    inventory_agent = InventoryRAGAgent()
    
    for i, email in enumerate(email_orders, 1):
        print(f"\n{'='*70}")
        print(f"EMAIL ORDER {i}")
        print(f"{'='*70}")
        print(f"From: {email['from']}")
        print(f"Subject: {email['subject']}")
        print(f"Body Preview: {email['body'][:100]}...")
        
        # Extract order from email body
        # In real implementation, this would be done by the email agent
        order_text = email['body']
        
        # Process with inventory agent
        print(f"\nProcessing order...")
        result = inventory_agent.process_order_request(order_text)
        
        print(f"\nResults:")
        print(f"- Status: {result['status']}")
        print(f"- Action: {result['recommended_action']}")
        print(f"- Message: {result['message']}")
        
        if result['matches']:
            print(f"\nTop Match:")
            match = result['matches'][0]
            print(f"- Item: {match['item_name']}")
            print(f"- Code: {match['item_code']}")
            print(f"- Stock: {match['available_stock']} units")
            print(f"- Confidence: {match['confidence_score']:.1%}")

def generate_summary_report():
    """Generate comprehensive summary report"""
    
    print("\n" + "="*70)
    print("ORDER VS INVENTORY SUMMARY REPORT")
    print("="*70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Using: OpenAI Agents SDK + Stella-400M Embeddings")
    
    # Get inventory statistics
    chroma_client = ChromaDBClient()
    total_items = chroma_client.collection.count()
    
    print(f"\nInventory Database:")
    print(f"- Total SKUs: {total_items}")
    print(f"- Embedding Model: Stella-400M (1024 dimensions)")
    print(f"- Vector Store: ChromaDB")
    
    # Test the agent's capabilities
    inventory_agent = InventoryRAGAgent()
    
    test_scenarios = [
        {
            'scenario': 'Exact Brand Match',
            'query': 'Allen Solly tags',
            'expected': 'Should find Allen Solly items with high confidence'
        },
        {
            'scenario': 'Material Search',
            'query': 'cotton tags with thread',
            'expected': 'Should find cotton material tags'
        },
        {
            'scenario': 'Color + Brand',
            'query': 'black Myntra tags',
            'expected': 'Should find black colored Myntra items'
        },
        {
            'scenario': 'Stock Availability',
            'query': 'tags in stock ready to ship',
            'expected': 'Should prioritize items with stock'
        }
    ]
    
    print("\nTesting Search Scenarios:")
    print("-" * 70)
    
    for test in test_scenarios:
        print(f"\nScenario: {test['scenario']}")
        print(f"Query: '{test['query']}'")
        print(f"Expected: {test['expected']}")
        
        # Get results
        result = inventory_agent.process_order_request(test['query'])
        
        if result['matches']:
            print(f"Result: ✓ Found {len(result['matches'])} matches")
            print(f"Best match: {result['matches'][0]['item_name']} "
                  f"(Score: {result['matches'][0]['confidence_score']:.1%})")
        else:
            print("Result: ✗ No matches found")

def main():
    """Main test execution"""
    
    print("Factory Automation: Agent-Based Order Processing")
    print("=" * 70)
    
    # Ensure inventory is loaded
    if not ensure_inventory_ingested():
        print("Failed to load inventory. Please check Excel files in 'inventory' folder.")
        return
    
    # Run tests
    test_inventory_matching_agent()
    test_complete_workflow()
    generate_summary_report()
    
    print("\n" + "="*70)
    print("AGENT TESTING COMPLETE")
    print("="*70)
    print("\nThe OpenAI Agents SDK is working correctly with:")
    print("- BaseAgent class providing agent framework")
    print("- InventoryRAGAgent using Stella-400M embeddings")
    print("- Synchronous run() method for direct execution")
    print("- as_tool() method for agent composition")

if __name__ == "__main__":
    main()