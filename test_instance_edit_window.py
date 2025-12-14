#!/usr/bin/env python3
"""
Тестовый скрипт для проверки InstanceEditWindow отдельно от основного приложения.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from hockey_editor.models.marker import Marker
from hockey_editor.core.video_controller import VideoController
from hockey_editor.ui.instance_edit_window import InstanceEditWindow


def test_instance_edit_window():
    """Тестирование InstanceEditWindow с mock данными."""

    # Создаем QApplication если его нет
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Создаем mock VideoController
    class MockVideoController:
        def __init__(self):
            self.current_frame = 100
            self.total_frames = 1000
            self.fps = 30.0

        def get_current_frame_idx(self):
            return self.current_frame

        def get_total_frames(self):
            return self.total_frames

        def get_fps(self):
            return self.fps

        def seek_frame(self, frame):
            self.current_frame = frame
            print(f"Seek to frame: {frame}")

        class MockProcessor:
            def get_current_frame(self):
                # Возвращаем None для теста (без реального видео)
                return None

            def advance_frame(self):
                pass

        processor = MockProcessor()

    # Создаем тестовый маркер
    marker = Marker(
        start_frame=50,
        end_frame=200,
        event_name="Goal",
        note="Тестовый гол"
    )

    # Создаем контроллер
    controller = MockVideoController()

    # Создаем и показываем окно
    window = InstanceEditWindow(marker, controller)
    window.show()

    print("InstanceEditWindow создан и показан")
    print(f"Маркер: {marker.start_frame}-{marker.end_frame}, событие: {marker.event_name}")

    # Запускаем приложение
    return app.exec()


if __name__ == "__main__":
    sys.exit(test_instance_edit_window())
