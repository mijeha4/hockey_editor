"""History System - паттерн Command для Undo/Redo."""

from .command_interface import Command
from .history_manager import HistoryManager

__all__ = ['Command', 'HistoryManager']
