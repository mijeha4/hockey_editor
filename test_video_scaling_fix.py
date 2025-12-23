#!/usr/bin/env python3
"""
Простой тест исправления проблемы масштабирования видео в PreviewWindow.
Проверяет, что изменения применены корректно.
"""

import sys
import os
import ast

def test_code_changes():
    """Проверяем, что изменения в коде применены корректно."""

    print("Проверка изменений в коде...")

    # Проверяем main_window.py
    main_window_path = os.path.join(os.path.dirname(__file__), 'hockey_editor', 'ui', 'main_window.py')

    with open(main_window_path, 'r', encoding='utf-8') as f:
        main_window_code = f.read()

    # Проверяем наличие QTimer.singleShot в _on_preview_clicked
    if 'QTimer.singleShot(0, lambda: (' in main_window_code and 'self.preview_window.layout().activate()' in main_window_code:
        print("✓ QTimer.singleShot добавлен в main_window.py")
    else:
        print("✗ QTimer.singleShot не найден в main_window.py")
        return False

    # Проверяем preview_window.py
    preview_window_path = os.path.join(os.path.dirname(__file__), 'hockey_editor', 'ui', 'preview_window.py')

    with open(preview_window_path, 'r', encoding='utf-8') as f:
        preview_window_code = f.read()

    # Проверяем sizePolicy
    if 'self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)' in preview_window_code:
        print("✓ sizePolicy установлен на Expanding в preview_window.py")
    else:
        print("✗ sizePolicy не установлен правильно в preview_window.py")
        return False

    # Проверяем minimumSize
    if 'self.video_container.setMinimumSize(1, 1)' in preview_window_code:
        print("✓ minimumSize установлен на (1, 1) в preview_window.py")
    else:
        print("✗ minimumSize не установлен правильно в preview_window.py")
        return False

    # Проверяем, что код компилируется
    try:
        ast.parse(main_window_code)
        print("✓ main_window.py компилируется без ошибок")
    except SyntaxError as e:
        print(f"✗ Ошибка синтаксиса в main_window.py: {e}")
        return False

    try:
        ast.parse(preview_window_code)
        print("✓ preview_window.py компилируется без ошибок")
    except SyntaxError as e:
        print(f"✗ Ошибка синтаксиса в preview_window.py: {e}")
        return False

    return True

def test_imports():
    """Проверяем, что все импорты работают."""

    print("\nПроверка импортов...")

    try:
        # Проверяем импорт QTimer
        from PySide6.QtCore import QTimer
        print("✓ QTimer импортируется корректно")

        # Проверяем импорт QSizePolicy
        from PySide6.QtWidgets import QSizePolicy
        print("✓ QSizePolicy импортируется корректно")

        return True
    except ImportError as e:
        print(f"✗ Ошибка импорта: {e}")
        return False

if __name__ == "__main__":
    print("Тестирование исправления проблемы масштабирования видео...")
    print("=" * 60)

    success1 = test_code_changes()
    success2 = test_imports()

    print()
    print("=" * 60)
    if success1 and success2:
        print("✓ Все проверки пройдены! Исправление масштабирования видео применено корректно.")
        print()
        print("Исправление включает:")
        print("1. QTimer.singleShot после show() для обновления геометрии")
        print("2. sizePolicy = Expanding для video_container")
        print("3. minimumSize = (1, 1) вместо фиксированного размера")
        print()
        print("Теперь видео должно масштабироваться правильно при первом открытии окна.")
        sys.exit(0)
    else:
        print("✗ Некоторые проверки не пройдены.")
        sys.exit(1)
