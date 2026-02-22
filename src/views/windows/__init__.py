"""Main application windows.

Ленивые импорты для предотвращения циклических зависимостей.
"""

__all__ = ['MainWindow', 'PreviewWindow', 'InstanceEditWindow', 'ExportDialog', 'SettingsDialog']


def __getattr__(name: str):
    if name == 'MainWindow':
        from .main_window import MainWindow
        return MainWindow
    if name == 'PreviewWindow':
        from .preview_window import PreviewWindow
        return PreviewWindow
    if name == 'InstanceEditWindow':
        from .instance_edit import InstanceEditWindow
        return InstanceEditWindow
    if name == 'ExportDialog':
        from .export_dialog import ExportDialog
        return ExportDialog
    if name == 'SettingsDialog':
        from .settings_dialog import SettingsDialog
        return SettingsDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")