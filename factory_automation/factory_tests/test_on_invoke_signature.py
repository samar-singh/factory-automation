#!/usr/bin/env python3
"""
Check the signature of on_invoke_tool
"""

import inspect
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.tools.tool_factory import ToolFactory

# Create tools
chromadb = ChromaDBClient()
tf = ToolFactory(mode='execute', chromadb_client=chromadb)
tools = tf.create_all_tools()

if tools:
    tool = tools[0]
    print(f"Tool: {tool.name}")
    
    if hasattr(tool, 'on_invoke_tool'):
        func = tool.on_invoke_tool
        print("\non_invoke_tool signature:")
        
        # Get signature
        sig = inspect.signature(func)
        print(f"  Signature: {sig}")
        
        # Get parameters
        print("  Parameters:")
        for name, param in sig.parameters.items():
            print(f"    - {name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'no type'}")
            if param.default != inspect.Parameter.empty:
                print(f"      default: {param.default}")
        
        # Get source if possible
        try:
            source = inspect.getsource(func)
            print("\nFirst few lines of source:")
            for line in source.split('\n')[:10]:
                print(f"  {line}")
        except:
            print("\nCouldn't get source code")