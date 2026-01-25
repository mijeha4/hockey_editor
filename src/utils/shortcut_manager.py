from typing import Dict, Callable, Optional
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QObject

class ShortcutManager:
    """Manages keyboard shortcuts for the application."""
    
    def __init__(self, parent_window: QObject):
        self.parent_window = parent_window
        self.shortcuts: Dict[str, QShortcut] = {}

    def register_shortcut(self, name: str, key_sequence: str, callback: Callable):
        """Register a new shortcut."""
        shortcut = QShortcut(QKeySequence(key_sequence), self.parent_window)
        shortcut.activated.connect(callback)
        self.shortcuts[name] = shortcut

    def get_shortcut(self, name: str) -> Optional[QShortcut]:
        """Get a shortcut by name."""
        return self.shortcuts.get(name)
