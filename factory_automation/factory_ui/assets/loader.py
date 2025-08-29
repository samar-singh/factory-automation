"""Asset loader for Gradio UI components"""

from pathlib import Path


class AssetLoader:
    """Loads CSS and JavaScript assets for Gradio interfaces"""
    
    def __init__(self):
        self.asset_dir = Path(__file__).parent
        self.styles_dir = self.asset_dir / "styles"
        self.scripts_dir = self.asset_dir / "scripts"
        
        # Cache loaded assets to avoid repeated file I/O
        self._cache = {}
    
    def load_css(self, filename: str) -> str:
        """
        Load CSS content from file
        
        Args:
            filename: Name of CSS file (without path)
            
        Returns:
            CSS content as string
        """
        cache_key = f"css_{filename}"
        
        if cache_key not in self._cache:
            css_path = self.styles_dir / filename
            
            if not css_path.exists():
                raise FileNotFoundError(f"CSS file not found: {css_path}")
            
            with open(css_path, 'r', encoding='utf-8') as f:
                self._cache[cache_key] = f.read()
        
        return self._cache[cache_key]
    
    def load_js(self, filename: str) -> str:
        """
        Load JavaScript content from file
        
        Args:
            filename: Name of JavaScript file (without path)
            
        Returns:
            JavaScript content as string
        """
        cache_key = f"js_{filename}"
        
        if cache_key not in self._cache:
            js_path = self.scripts_dir / filename
            
            if not js_path.exists():
                raise FileNotFoundError(f"JavaScript file not found: {js_path}")
            
            with open(js_path, 'r', encoding='utf-8') as f:
                self._cache[cache_key] = f.read()
        
        return self._cache[cache_key]
    
    def load_multiple_css(self, *filenames: str) -> str:
        """
        Load and concatenate multiple CSS files
        
        Args:
            *filenames: Names of CSS files to load
            
        Returns:
            Combined CSS content
        """
        css_parts = []
        for filename in filenames:
            css_parts.append(self.load_css(filename))
        return "\n\n".join(css_parts)
    
    def load_multiple_js(self, *filenames: str) -> str:
        """
        Load and concatenate multiple JavaScript files
        
        Args:
            *filenames: Names of JavaScript files to load
            
        Returns:
            Combined JavaScript content
        """
        js_parts = []
        for filename in filenames:
            js_parts.append(self.load_js(filename))
        return "\n\n".join(js_parts)
    
    def get_themed_css(self, theme: str = "default") -> str:
        """
        Load CSS with theme-specific overrides
        
        Args:
            theme: Theme name (default, dark, light)
            
        Returns:
            Themed CSS content
        """
        base_css = self.load_css("dashboard.css")
        
        # Load theme-specific CSS if it exists
        theme_file = f"theme_{theme}.css"
        theme_path = self.styles_dir / theme_file
        
        if theme_path.exists():
            theme_css = self.load_css(theme_file)
            return f"{base_css}\n\n/* Theme: {theme} */\n{theme_css}"
        
        return base_css
    
    def clear_cache(self):
        """Clear the asset cache"""
        self._cache.clear()


# Convenience functions for direct import
_loader = AssetLoader()

def load_css(filename: str) -> str:
    """Load CSS file content"""
    return _loader.load_css(filename)

def load_js(filename: str) -> str:
    """Load JavaScript file content"""
    return _loader.load_js(filename)

def load_multiple_css(*filenames: str) -> str:
    """Load and combine multiple CSS files"""
    return _loader.load_multiple_css(*filenames)

def load_multiple_js(*filenames: str) -> str:
    """Load and combine multiple JavaScript files"""
    return _loader.load_multiple_js(*filenames)

def get_themed_css(theme: str = "default") -> str:
    """Get themed CSS content"""
    return _loader.get_themed_css(theme)