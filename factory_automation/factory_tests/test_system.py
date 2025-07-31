#!/usr/bin/env python3
"""Test the complete system with sample data."""

import asyncio
import sys
sys.path.append('./factory_automation')

from factory_automation.factory_rag.chromadb_client import ChromaDBClient
from factory_automation.factory_config.settings import settings

async def test_system():
    """Test the complete system workflow."""
    print("Factory Automation System Test")
    print("=" * 50)
    
    # 1. Initialize ChromaDB
    print("\n1. Testing ChromaDB Connection...")
    client = ChromaDBClient()
    await client.initialize()
    
    if client.is_connected():
        print("✓ ChromaDB connected successfully")
        info = await client.get_collection_info()
        print(f"  - Inventory items: {info['inventory_items']}")
        print(f"  - Order history: {info['order_history']}")
    else:
        print("✗ ChromaDB connection failed")
        return
    
    # 2. Test inventory search
    print("\n2. Testing Inventory Search...")
    from sentence_transformers import SentenceTransformer
    
    text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
    query = "blue cotton tag 2x3"
    query_embedding = text_encoder.encode(query).tolist()
    
    results = await client.search_inventory(
        query_embedding=query_embedding,
        n_results=3
    )
    
    print(f"Search results for '{query}':")
    for i, result in enumerate(results):
        metadata = result['metadata']
        # Handle different metadata structures
        tag_name = metadata.get('tag_code', metadata.get('trim_name', 'Unknown'))
        brand = metadata.get('brand', metadata.get('description', 'N/A'))
        stock = metadata.get('stock', 'N/A')
        
        print(f"  {i+1}. {tag_name} - {brand}")
        print(f"     Similarity: {result['similarity']:.3f}")
        print(f"     Stock: {stock}")
        if 'excel_source' in metadata:
            print(f"     Source: {metadata['excel_source']}")
    
    # 3. Test configuration
    print("\n3. Testing Configuration...")
    print(f"✓ App Environment: {settings.app_env}")
    print(f"✓ App Port: {settings.app_port}")
    print(f"✓ Gradio Port: {settings.gradio_port}")
    print(f"✓ OpenAI API Key: {'✓ Set' if settings.openai_api_key else '✗ Missing'}")
    print(f"✓ Together API Key: {'✓ Set' if settings.together_api_key else '✗ Missing'}")
    
    # 4. Test agent creation (without running them)
    print("\n4. Testing Agent Creation...")
    try:
        from factory_automation.factory_agents.email_monitor_agent import EmailMonitorAgent
        from factory_automation.factory_agents.order_interpreter_agent import OrderInterpreterAgent
        from factory_automation.factory_agents.inventory_matcher_agent import InventoryMatcherAgent
        
        email_agent = EmailMonitorAgent()
        print("✓ Email Monitor Agent created")
        
        order_agent = OrderInterpreterAgent()
        print("✓ Order Interpreter Agent created")
        
        inventory_agent = InventoryMatcherAgent(chromadb_client=client)
        print("✓ Inventory Matcher Agent created")
        
    except Exception as e:
        print(f"✗ Agent creation failed: {str(e)}")
    
    print("\n" + "="*50)
    print("System test completed!")
    print("\nNext steps:")
    print("1. Install PostgreSQL for order/customer database")
    print("2. Implement missing agents (document creator, payment tracker)")
    print("3. Set up Gmail integration")
    print("4. Launch Gradio dashboard")

if __name__ == "__main__":
    asyncio.run(test_system())