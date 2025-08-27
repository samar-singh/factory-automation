#!/usr/bin/env python3
"""
Test calling the on_invoke_tool function
"""

import asyncio
import json
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.tools.tool_factory import ToolFactory

async def test_on_invoke_tool():
    # Create tools
    chromadb = ChromaDBClient()
    tf = ToolFactory(mode='execute', chromadb_client=chromadb)
    tools = tf.create_all_tools()
    
    # Find search_inventory tool
    search_tool = None
    for tool in tools:
        if tool.name == 'search_inventory':
            search_tool = tool
            break
    
    if search_tool:
        print(f"Found tool: {search_tool.name}")
        print(f"Has on_invoke_tool: {hasattr(search_tool, 'on_invoke_tool')}")
        
        if hasattr(search_tool, 'on_invoke_tool'):
            func = search_tool.on_invoke_tool
            print(f"on_invoke_tool type: {type(func)}")
            print(f"Is callable: {callable(func)}")
            print(f"Is coroutine: {asyncio.iscoroutinefunction(func)}")
            
            # Try to call it
            test_args = {
                "query": "Allen Solly tags",
                "max_results": 5,
                "confidence_threshold": 0.7
            }
            
            print(f"\nCalling with args: {test_args}")
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(**test_args)
                else:
                    result = func(**test_args)
                    
                print(f"✅ Success! Result type: {type(result)}")
                if isinstance(result, str):
                    try:
                        result_dict = json.loads(result)
                        print(f"Parsed result: Found {result_dict.get('count', 0)} matches")
                    except:
                        print(f"Result string: {result[:200]}...")
                else:
                    print(f"Result: {result}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("search_inventory tool not found")

if __name__ == "__main__":
    asyncio.run(test_on_invoke_tool())