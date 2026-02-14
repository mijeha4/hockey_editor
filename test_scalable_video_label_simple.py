#!/usr/bin/env python3
"""
Простой тест для проверки ScalableVideoLabel.
"""

import sys
import os
import cv2
import numpy as np

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

# Импортируем ScalableVideoLabel
from views.widgets.scalable_video_label import ScalableVideoLabel


def test_scalable_video_label_basic():
    """Базовый тест ScalableVideoLabel."""
    print("Тест: Базовая функциональность ScalableVideoLabel...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Создаем виджет для теста
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = ScalableVideoLabel()
    layout.addWidget(label)
    widget.show()
    
    # Создаем тестовый кадр
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:, :, 0] = 255  # Синий цвет
    
    # Устанавливаем кадр
    label.set_frame(test_frame)
    
    # Проверяем, что кадр установлен
    pixmap = label.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()
    assert pixmap.width() == 640
    assert pixmap.height() == 480
    
    print("✓ ScalableVideoLabel работает корректно")
    print(f"  - Размер кадра: {pixmap.width()}x{pixmap.height()}")
    print(f"  - Минимальный размер: {label.minimumSize()}")
    print(f"  - Стиль: {label.styleSheet()}")
    
    return True


if __name__ == "__main__":
    try:
        success = test_scalable_video_label_basic()
        if success:
            print("\n🎉 ScalableVideoLabel успешно протестирован!")
        else:
            print("\n❌ Тест ScalableVideoLabel провален")
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании ScalableVideoLabel: {e}")
        import traceback
        traceback.print_exc()