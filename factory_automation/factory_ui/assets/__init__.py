"""Asset management for Factory Automation UI"""

from .loader import (
    AssetLoader,
    load_css,
    load_js,
    load_multiple_css,
    load_multiple_js,
    get_themed_css
)

__all__ = [
    'AssetLoader',
    'load_css',
    'load_js', 
    'load_multiple_css',
    'load_multiple_js',
    'get_themed_css'
]