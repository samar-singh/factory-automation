"""Base tool functionality with conditional agents import"""

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Try to import agents module, fall back to mock if not available
try:
    from agents import function_tool
    AGENTS_AVAILABLE = True
    logger.info("OpenAI Agents SDK is available")
except ImportError:
    logger.warning("OpenAI Agents SDK not available, using mock function_tool decorator")
    AGENTS_AVAILABLE = False
    
    # Create a mock function_tool decorator for testing
    def function_tool(
        name_override: Optional[str] = None,
        description_override: Optional[str] = None,
    ):
        """Mock function_tool decorator for when agents module is not available"""
        def decorator(func: Callable) -> Callable:
            # Add metadata to function for identification
            func._tool_name = name_override or func.__name__
            func._tool_description = description_override or func.__doc__
            func._is_tool = True
            return func
        return decorator

# Export for use in other modules
__all__ = ['function_tool', 'AGENTS_AVAILABLE']