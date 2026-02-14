#!/usr/bin/env python3
"""
Тест для проверки рефакторинга MainWindow.

Проверяет:
1. Создание ScalableVideoLabel вместо QLabel
2. Отсутствие масштабирования в _on_frame_ready
3. Корректную работу set_frame метода
"""

import sys
import os
import cv2
import numpy as np

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage

# Импортируем рефакторинговые классы
from views.widgets.scalable_video_label import ScalableVideoLabel
from views.windows.main_window import MainWindow


def test_scalable_video_label_creation():
    """Тест создания ScalableVideoLabel."""
    print("Тест 1: Создание ScalableVideoLabel...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    label = ScalableVideoLabel()
    
    # Проверяем, что виджет создан
    assert label is not None
    assert label.minimumSize() == (320, 180)
    assert "background-color: black;" in label.styleSheet()
    
    print("✓ ScalableVideoLabel успешно создан")
    return True


def test_scalable_video_label_set_frame():
    """Тест установки кадра в ScalableVideoLabel."""
    print("Тест 2: Установка кадра в ScalableVideoLabel...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    label = ScalableVideoLabel()
    
    # Создаем тестовый кадр OpenCV (BGR)
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:, :, 2] = 255  # Красный цвет
    
    # Устанавливаем кадр
    label.set_frame(test_frame)
    
    # Проверяем, что кадр установлен
    assert label.pixmap() is not None
    assert not label.pixmap().isNull()
    assert label.pixmap().width() == 640
    assert label.pixmap().height() == 480
    
    print("✓ Кадр успешно установлен в ScalableVideoLabel")
    return True


def test_main_window_video_label_type():
    """Тест типа video_label в MainWindow."""
    print("Тест 3: Проверка типа video_label в MainWindow...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    window = MainWindow()
    
    # Проверяем, что video_label - это ScalableVideoLabel
    from views.widgets.scalable_video_label import ScalableVideoLabel
    assert isinstance(window.video_label, ScalableVideoLabel)
    
    print("✓ MainWindow использует ScalableVideoLabel")
    return True


def test_main_window_on_frame_ready():
    """Тест метода _on_frame_ready в MainWindow."""
    print("Тест 4: Проверка метода _on_frame_ready...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    window = MainWindow()
    
    # Создаем тестовый кадр
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:, :, 1] = 255  # Зеленый цвет
    
    # Вызываем _on_frame_ready
    window._on_frame_ready(test_frame)
    
    # Проверяем, что кадр установлен в ScalableVideoLabel
    assert window.video_label.pixmap() is not None
    assert not window.video_label.pixmap().isNull()
    
    print("✓ Метод _on_frame_ready работает корректно")
    return True


def test_imports_clean():
    """Тест проверки чистоты импортов."""
    print("Тест 5: Проверка импортов в MainWindow...")
    
    # Проверяем, что в файле нет ненужных импортов
    with open('src/views/windows/main_window.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем отсутствие ненужных импортов
    assert 'QTimer' not in content or 'from PySide6.QtCore import Qt, Signal, QTimer, QMimeData' not in content
    assert 'QEvent' not in content or 'from PySide6.QtCore import Qt, Signal, QTimer, QEvent, QMimeData' not in content
    
    # Проверяем наличие нужных импортов
    assert 'from views.widgets.scalable_video_label import ScalableVideoLabel' in content
    assert 'from PySide6.QtCore import Qt, Signal, QMimeData' in content
    
    print("✓ Импорты очищены корректно")
    return True


def main():
    """Запуск всех тестов."""
    print("Запуск тестов рефакторинга MainWindow...")
    print("=" * 50)
    
    tests = [
        test_scalable_video_label_creation,
        test_scalable_video_label_set_frame,
        test_main_window_video_label_type,
        test_main_window_on_frame_ready,
        test_imports_clean
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Тест {test.__name__} провален: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Результаты: {passed} пройдено, {failed} провалено")
    
    if failed == 0:
        print("🎉 Все тесты пройдены! Рефакторинг успешен!")
        return True
    else:
        print("❌ Некоторые тесты провалены. Проверьте изменения.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)