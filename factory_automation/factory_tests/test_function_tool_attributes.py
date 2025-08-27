#!/usr/bin/env python3
"""
Inspect FunctionTool to understand how to call it
"""

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.tools.tool_factory import ToolFactory

# Create tools
chromadb = ChromaDBClient()
tf = ToolFactory(mode='execute', chromadb_client=chromadb)
tools = tf.create_all_tools()

if tools:
    tool = tools[0]
    print(f"Tool type: {type(tool)}")
    print(f"Tool name: {tool.name}")
    
    print("\nAll attributes and methods:")
    for attr in dir(tool):
        if not attr.startswith('__'):
            attr_value = getattr(tool, attr, None)
            print(f"  {attr}: {type(attr_value)}")
            if callable(attr_value) and not attr.startswith('_'):
                print("    -> This is callable!")
    
    print("\nChecking for special attributes:")
    special_attrs = ['__call__', '__func__', 'func', '_func', '_function', '__wrapped__']
    for attr in special_attrs:
        if hasattr(tool, attr):
            print(f"  Has {attr}: {type(getattr(tool, attr))}")
    
    # Try to understand the internal structure
    if hasattr(tool, '__dict__'):
        print(f"\nTool.__dict__ keys: {tool.__dict__.keys()}")
    
    # Check if there's a way to get the original function
    print("\nLooking for the actual function...")
    
    # The tools are created with @function_tool decorator
    # Let's try to understand how they're structured
    import inspect
    
    print(f"\nIs it a coroutine? {inspect.iscoroutinefunction(tool)}")
    print(f"Is it callable? {callable(tool)}")
    
    # Try to access the schema
    if hasattr(tool, 'params_json_schema'):
        print("\nHas params_json_schema")
    if hasattr(tool, 'strict_json_schema'):
        print("Has strict_json_schema")