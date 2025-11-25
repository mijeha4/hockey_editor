"""
ShortcutManager - управление глобальными горячими клавишами через QShortcut.
Позволяет переназначить клавиши и применить их без перезагрузки приложения.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt
from typing import Callable, Dict, List, Optional


class ShortcutManager:
    """
    Менеджер для управления QShortcut'ами.
    Позволяет динамически переподключать горячие клавиши.
    """
    
    def __init__(self, parent: QWidget):
        """
        Инициализировать менеджер.
        
        Args:
            parent: Виджет, к которому привязаны shortcuts
        """
        self.parent = parent
        self.shortcuts: Dict[str, tuple] = {}  # {name: (QShortcut, callback)}
    
    def register_shortcut(self, name: str, key: str, callback: Callable) -> None:
        """
        Зарегистрировать новый shortcut.
        
        Args:
            name: Уникальное имя shortcut'а (например, 'ATTACK', 'PLAY', 'EXPORT')
            key: Клавиша или комбинация (например, 'A', 'Ctrl+S', 'F11')
            callback: Функция обратного вызова
        """
        # Если shortcut с таким именем уже существует, удалить его
        self.unregister_shortcut(name)
        
        # Создать новый shortcut
        from PySide6.QtGui import QShortcut
        shortcut = QShortcut(QKeySequence(key), self.parent)
        shortcut.activated.connect(callback)
        
        self.shortcuts[name] = (shortcut, callback)
    
    def unregister_shortcut(self, name: str) -> None:
        """
        Удалить shortcut по имени.
        
        Args:
            name: Имя shortcut'а
        """
        if name in self.shortcuts:
            shortcut, _ = self.shortcuts[name]
            shortcut.setEnabled(False)
            del self.shortcuts[name]
    
    def rebind_shortcut(self, name: str, new_key: str) -> None:
        """
        Переподключить shortcut на новую клавишу.
        
        Args:
            name: Имя shortcut'а
            new_key: Новая клавиша или комбинация
        """
        if name not in self.shortcuts:
            return
        
        _, callback = self.shortcuts[name]
        self.register_shortcut(name, new_key, callback)
    
    def rebind_multiple(self, hotkeys: Dict[str, str]) -> None:
        """
        Переподключить несколько shortcut'ов сразу.
        
        Args:
            hotkeys: Словарь {name: key}
                    Пример: {'ATTACK': 'A', 'DEFENSE': 'D', 'EXPORT': 'Ctrl+E'}
        """
        for name, key in hotkeys.items():
            if name in self.shortcuts:
                self.rebind_shortcut(name, key)
    
    def enable_shortcut(self, name: str) -> None:
        """Включить shortcut."""
        if name in self.shortcuts:
            shortcut, _ = self.shortcuts[name]
            shortcut.setEnabled(True)
    
    def disable_shortcut(self, name: str) -> None:
        """Отключить shortcut."""
        if name in self.shortcuts:
            shortcut, _ = self.shortcuts[name]
            shortcut.setEnabled(False)
    
    def enable_all(self) -> None:
        """Включить все shortcuts."""
        for name in self.shortcuts:
            self.enable_shortcut(name)
    
    def disable_all(self) -> None:
        """Отключить все shortcuts."""
        for name in self.shortcuts:
            self.disable_shortcut(name)
    
    def get_shortcut_key(self, name: str) -> Optional[str]:
        """
        Получить текущую клавишу для shortcut'а.
        
        Args:
            name: Имя shortcut'а
            
        Returns:
            Строка с клавишей или None если not found
        """
        if name not in self.shortcuts:
            return None
        
        shortcut, _ = self.shortcuts[name]
        return shortcut.key().toString()
    
    def list_shortcuts(self) -> Dict[str, str]:
        """
        Получить список всех shortcuts и их клавиш.
        
        Returns:
            Словарь {name: key}
        """
        result = {}
        for name, (shortcut, _) in self.shortcuts.items():
            result[name] = shortcut.key().toString()
        return result
    
    def clear_all(self) -> None:
        """Удалить все shortcuts."""
        for name in list(self.shortcuts.keys()):
            self.unregister_shortcut(name)
