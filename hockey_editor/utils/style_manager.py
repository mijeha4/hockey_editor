#!/usr/bin/env python3
"""
StyleManager - Global Design System for Hockey Editor.
Singleton class that manages application-wide styling with variable substitution.
"""

import os
from typing import Dict, Optional
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject


class StyleManager(QObject):
    """Singleton StyleManager for global application styling.

    Features:
    - Loads and caches global stylesheet
    - Supports variable substitution (@variable -> value)
    - Applies styles to QApplication instance
    - Allows dynamic style updates
    - Coexists with dynamic setStyleSheet() calls
    """

    _instance: Optional['StyleManager'] = None
    _initialized: bool = False

    def __new__(cls) -> 'StyleManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            super().__init__()
            self._stylesheet_cache: Optional[str] = None
            self._variables: Dict[str, str] = {}
            self._global_stylesheet_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'assets', 'styles', 'global.qss'
            )
            self._load_default_variables()
            self._initialized = True

    def _load_default_variables(self):
        """Load default CSS variables for the design system."""
        self._variables = {
            # Color Palette
            'primary_bg': '#1E1E1E',        # Modern dark background
            'secondary_bg': '#2A2A2A',     # Secondary panels
            'accent_bg': '#333333',        # Input fields, buttons
            'hover_bg': '#404040',         # Hover states
            'active_bg': '#505050',        # Active/pressed states
            'selected_bg': '#007ACC',      # Selection color (accent blue)

            # Text Colors
            'primary_text': '#FFFFFF',     # Main text
            'secondary_text': '#CCCCCC',   # Secondary text
            'accent_text': '#FFD700',     # Accent/highlight text
            'muted_text': '#888888',       # Muted/gray text
            'disabled_text': '#666666',   # Disabled text
            'error_text': '#FF6B6B',       # Error messages

            # Border Colors
            'border_color': '#555555',     # Standard borders
            'border_light': '#666666',    # Light borders
            'border_dark': '#333333',     # Dark borders
            'grid_color': '#444444',      # Grid lines

            # Status Colors
            'success_color': '#00AA00',    # Success green
            'warning_color': '#FFAA00',    # Warning orange
            'info_color': '#0088AA',       # Info blue

            # Timeline Colors
            'timeline_bg': '#1A1A1A',      # Timeline background
            'timeline_ruler_bg': '#2A2A2A', # Ruler background
            'timeline_track_bg': '#232323', # Track background
            'timeline_track_alt_bg': '#1E1E1E', # Alternate track background
            'playhead_color': '#FFFF00',   # Playhead yellow

            # Video Colors
            'video_bg': '#000000',         # Video background

            # Scrollbar Colors
            'scrollbar_bg': '#333333',     # Scrollbar background
            'scrollbar_handle': '#666666', # Scrollbar handle
            'scrollbar_handle_hover': '#888888', # Scrollbar handle hover

            # Dimensions
            'border_radius': '4px',        # Border radius
            'border_width': '1px',         # Border width
            'padding_small': '4px',        # Small padding
            'padding_medium': '8px',       # Medium padding
            'padding_large': '12px',       # Large padding

            # Fonts
            'font_family': '"Segoe UI", sans-serif',
            'font_family_mono': '"Consolas", "Courier New", monospace',
            'font_size_small': '9pt',
            'font_size_normal': '10pt',
            'font_size_large': '12pt',
            'font_size_xlarge': '14pt',
            'font_size_header': '13pt',

            # Effects
            'shadow_color': 'rgba(0, 0, 0, 0.3)',
            'transition_time': '0.2s'
        }

    def set_variable(self, name: str, value: str):
        """Set a CSS variable value.

        Args:
            name: Variable name without @ prefix
            value: Variable value
        """
        self._variables[name] = value
        # Invalidate cache to force reload
        self._stylesheet_cache = None

    def get_variable(self, name: str) -> Optional[str]:
        """Get a CSS variable value.

        Args:
            name: Variable name without @ prefix

        Returns:
            Variable value or None if not found
        """
        return self._variables.get(name)

    def set_variables(self, variables: Dict[str, str]):
        """Set multiple CSS variables at once.

        Args:
            variables: Dictionary of variable name -> value pairs
        """
        self._variables.update(variables)
        self._stylesheet_cache = None

    def _load_stylesheet(self) -> str:
        """Load and process the global stylesheet with variable substitution.

        Returns:
            Processed stylesheet string
        """
        try:
            with open(self._global_stylesheet_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
        except (FileNotFoundError, IOError) as e:
            print(f"Warning: Could not load global stylesheet: {e}")
            return self._get_fallback_stylesheet()

        # Perform variable substitution
        for var_name, var_value in self._variables.items():
            stylesheet = stylesheet.replace(f'@{var_name}', var_value)

        # Debug: Check for invalid color names
        if '#666666' in stylesheet:
            print("WARNING: Found '#666666' in processed stylesheet!")
            print("This indicates a variable substitution issue.")

        return stylesheet

    def _get_fallback_stylesheet(self) -> str:
        """Get fallback stylesheet if global.qss cannot be loaded."""
        return f"""
        /* Fallback Global Stylesheet */
        QApplication {{
            background-color: {self._variables['primary_bg']};
            color: {self._variables['primary_text']};
            font-family: {self._variables['font_family']};
            font-size: {self._variables['font_size_normal']};
        }}

        QWidget {{
            background-color: {self._variables['primary_bg']};
            color: {self._variables['primary_text']};
        }}

        QPushButton {{
            background-color: {self._variables['accent_bg']};
            color: {self._variables['primary_text']};
            border: {self._variables['border_width']} solid {self._variables['border_color']};
            padding: {self._variables['padding_medium']};
            border-radius: {self._variables['border_radius']};
            font-size: {self._variables['font_size_normal']};
        }}

        QPushButton:hover {{
            background-color: {self._variables['hover_bg']};
        }}

        QPushButton:pressed {{
            background-color: {self._variables['active_bg']};
        }}
        """

    def apply_global_styles(self):
        """Apply the global stylesheet to the QApplication instance."""
        if self._stylesheet_cache is None:
            self._stylesheet_cache = self._load_stylesheet()

        # Debug: Check final stylesheet for issues
        if '#666666' in self._stylesheet_cache:
            print("CRITICAL: '#666666' found in final stylesheet!")
            print("This will cause Qt CSS parser errors.")

        app = QApplication.instance()
        if app:
            app.setStyleSheet(self._stylesheet_cache)
        else:
            print("Warning: No QApplication instance found")

    def refresh_styles(self):
        """Force refresh of global styles (clears cache and reapplies)."""
        self._stylesheet_cache = None
        self.apply_global_styles()

    def get_processed_stylesheet(self) -> str:
        """Get the processed stylesheet with variables substituted.

        Returns:
            Processed stylesheet string
        """
        if self._stylesheet_cache is None:
            self._stylesheet_cache = self._load_stylesheet()
        return self._stylesheet_cache

    @classmethod
    def instance(cls) -> 'StyleManager':
        """Get the singleton instance of StyleManager."""
        return cls()


# Convenience function for easy access
def get_style_manager() -> StyleManager:
    """Get the global StyleManager instance."""
    return StyleManager.instance()
