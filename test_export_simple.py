#!/usr/bin/env python3
"""
Простой тест экспорта для проверки работоспособности.
"""

import sys
import os
import tempfile
sys.path.insert(0, 'hockey_editor')

from hockey_editor.core.exporter import VideoExporter
from hockey_editor.models.marker import Marker

def test_export():
    """Простой тест экспорта."""
    print("🧪 Тестирование простого экспорта...")

    # Создаем тестовые маркеры
    markers = [
        Marker(start_frame=0, end_frame=30, event_name="Test Segment", note="Test note")
    ]

    # Параметры
    video_path = "nonexistent.mp4"  # Не существующий файл
    total_frames = 100
    fps = 30.0

    # Создаем временный файл для вывода
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        output_path = tmp.name

    try:
        # Пытаемся экспортировать (должен упасть из-за несуществующего видео)
        result = VideoExporter.export(
            video_path,
            markers,
            total_frames,
            fps,
            output_path
        )
        print("❌ Ожидалась ошибка, но экспорт прошел успешно")
        return False

    except FileNotFoundError as e:
        print(f"✅ Корректно обработана ошибка несуществующего файла: {e}")
        return True

    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

    finally:
        # Удаляем временный файл
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == "__main__":
    print("🚀 Запуск простого теста экспорта...\n")

    success = test_export()

    if success:
        print("\n✅ Тест прошел успешно!")
    else:
        print("\n❌ Тест провален!")
        sys.exit(1)
