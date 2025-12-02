#!/usr/bin/env python3
"""
Тесты функционала экспорта видео.
Тестирует VideoExporter и связанные компоненты.
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
sys.path.insert(0, 'hockey_editor')

from hockey_editor.core.exporter import VideoExporter
from hockey_editor.models.marker import Marker


class TestVideoExporter(unittest.TestCase):
    """Тесты для VideoExporter."""

    def setUp(self):
        """Подготовка тестовых данных."""
        self.temp_dir = tempfile.mkdtemp()

        # Создаем тестовые маркеры
        self.markers = [
            Marker(start_frame=0, end_frame=100, event_name="Attack", note="First attack"),
            Marker(start_frame=200, end_frame=300, event_name="Defense", note="Defense action"),
            Marker(start_frame=400, end_frame=500, event_name="Shift", note="Team shift")
        ]

        # Параметры видео
        self.video_path = "test_video.mp4"
        self.total_frames = 600
        self.fps = 30.0
        self.output_path = os.path.join(self.temp_dir, "export_test.mp4")

    def tearDown(self):
        """Очистка после тестов."""
        # Удаляем временные файлы
        if os.path.exists(self.output_path):
            os.remove(self.output_path)
        os.rmdir(self.temp_dir)

    @patch('os.path.exists')
    @patch('moviepy.VideoFileClip')
    @patch('moviepy.concatenate_videoclips')
    def test_export_basic_functionality(self, mock_concatenate, mock_video_clip, mock_exists):
        """Тест базовой функциональности экспорта."""
        print("🧪 Тестирование базовой функциональности экспорта...")

        # Mock объекты
        mock_video = MagicMock()
        mock_video_clip.return_value = mock_video

        mock_clip1 = MagicMock()
        mock_clip2 = MagicMock()
        mock_clip3 = MagicMock()
        mock_video.subclip.side_effect = [mock_clip1, mock_clip2, mock_clip3]

        mock_final = MagicMock()
        mock_concatenate.return_value = mock_final

        # Вызываем экспорт
        VideoExporter.export(
            self.video_path,
            self.markers,
            self.total_frames,
            self.fps,
            self.output_path
        )

        # Проверяем, что VideoFileClip был вызван с правильным путем
        mock_video_clip.assert_called_once_with(self.video_path)

        # Проверяем, что subclip был вызван для каждого маркера
        expected_calls = [
            ((0.0, 100.0/30.0),),  # 0-3.33 сек
            ((200.0/30.0, 300.0/30.0),),  # 6.67-10 сек
            ((400.0/30.0, 500.0/30.0),)   # 13.33-16.67 сек
        ]
        self.assertEqual(mock_video.subclip.call_count, 3)
        mock_video.subclip.assert_has_calls(expected_calls, any_order=False)

        # Проверяем, что concatenate_videoclips был вызван с правильными клипами
        mock_concatenate.assert_called_once_with([mock_clip1, mock_clip2, mock_clip3])

        # Проверяем, что write_videofile был вызван с правильными параметрами
        mock_final.write_videofile.assert_called_once_with(
            self.output_path,
            codec="libx264",
            audio_codec="aac",
            threads=4
        )

        # Проверяем, что video.close() был вызван
        mock_video.close.assert_called_once()

        print("✅ Базовая функциональность экспорта работает корректно!")

    @patch('os.path.exists')
    @patch('moviepy.VideoFileClip')
    def test_export_with_empty_markers(self, mock_video_clip, mock_exists):
        """Тест экспорта с пустым списком маркеров."""
        print("\n🧪 Тестирование экспорта с пустыми маркерами...")

        mock_video = MagicMock()
        mock_video_clip.return_value = mock_video

        mock_empty_clip = MagicMock()
        mock_video.subclip.return_value = mock_empty_clip

        # Вызываем экспорт с пустым списком
        VideoExporter.export(
            self.video_path,
            [],  # Пустой список маркеров
            self.total_frames,
            self.fps,
            self.output_path
        )

        # Проверяем, что VideoFileClip все равно был вызван
        mock_video_clip.assert_called_once_with(self.video_path)

        # Проверяем, что subclip был вызван для создания пустого клипа
        mock_video.subclip.assert_called_once_with(0, 0.1)

        # Проверяем, что write_videofile был вызван для пустого клипа
        mock_empty_clip.write_videofile.assert_called_once_with(
            self.output_path,
            codec="libx264",
            audio_codec="aac",
            threads=4
        )

        print("✅ Экспорт с пустыми маркерами обрабатывается корректно!")

    @patch('os.path.exists')
    @patch('moviepy.VideoFileClip')
    @patch('moviepy.concatenate_videoclips')
    def test_export_marker_boundaries(self, mock_concatenate, mock_video_clip, mock_exists):
        """Тест правильности границ маркеров."""
        print("\n🧪 Тестирование границ маркеров...")

        mock_video = MagicMock()
        mock_video_clip.return_value = mock_video

        # Маркеры на границах видео
        boundary_markers = [
            Marker(start_frame=0, end_frame=50, event_name="Start", note=""),
            Marker(start_frame=550, end_frame=600, event_name="End", note="")
        ]

        mock_clip1 = MagicMock()
        mock_clip2 = MagicMock()
        mock_video.subclip.side_effect = [mock_clip1, mock_clip2]

        mock_final = MagicMock()
        mock_concatenate.return_value = mock_final

        VideoExporter.export(
            self.video_path,
            boundary_markers,
            600,  # total_frames
            30.0,  # fps
            self.output_path
        )

        # Проверяем правильность временных границ
        expected_calls = [
            ((0.0, 50.0/30.0),),      # 0-1.67 сек
            ((550.0/30.0, 600.0/30.0),) # 18.33-20 сек
        ]
        mock_video.subclip.assert_has_calls(expected_calls, any_order=False)

        print("✅ Границы маркеров рассчитываются правильно!")

    def test_marker_model(self):
        """Тест модели Marker."""
        print("\n🧪 Тестирование модели Marker...")

        # Создаем маркер
        marker = Marker(
            start_frame=100,
            end_frame=200,
            event_name="Test Event",
            note="Test note"
        )

        # Проверяем атрибуты
        self.assertEqual(marker.start_frame, 100)
        self.assertEqual(marker.end_frame, 200)
        self.assertEqual(marker.event_name, "Test Event")
        self.assertEqual(marker.note, "Test note")

        # Тест сериализации
        data = marker.to_dict()
        expected_data = {
            "start_frame": 100,
            "end_frame": 200,
            "event_name": "Test Event",
            "note": "Test note"
        }
        self.assertEqual(data, expected_data)

        # Тест десериализации
        new_marker = Marker.from_dict(data)
        self.assertEqual(new_marker.start_frame, marker.start_frame)
        self.assertEqual(new_marker.end_frame, marker.end_frame)
        self.assertEqual(new_marker.event_name, marker.event_name)
        self.assertEqual(new_marker.note, marker.note)

        print("✅ Модель Marker работает корректно!")

    def test_marker_backwards_compatibility(self):
        """Тест обратной совместимости Marker с старым форматом."""
        print("\n🧪 Тестирование обратной совместимости Marker...")

        # Старый формат с полем "type"
        old_data = {
            "start_frame": 50,
            "end_frame": 150,
            "type": "Атака",  # Старый enum формат
            "note": "Old format"
        }

        marker = Marker.from_dict(old_data)

        # Должен конвертироваться в новый формат
        self.assertEqual(marker.start_frame, 50)
        self.assertEqual(marker.end_frame, 150)
        self.assertEqual(marker.event_name, "Attack")  # Конвертировано из "Атака"
        self.assertEqual(marker.note, "Old format")

        print("✅ Обратная совместимость Marker работает!")


class TestExportIntegration(unittest.TestCase):
    """Интеграционные тесты экспорта."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Очистка
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('os.path.exists')
    @patch('moviepy.VideoFileClip')
    def test_export_workflow(self, mock_video_clip, mock_exists):
        """Тест полного workflow экспорта."""
        print("\n🧪 Тестирование полного workflow экспорта...")

        # Mock видео
        mock_video = MagicMock()
        mock_video_clip.return_value = mock_video

        # Создаем маркеры
        markers = [
            Marker(start_frame=0, end_frame=90, event_name="Goal", note=""),
            Marker(start_frame=180, end_frame=270, event_name="Save", note="")
        ]

        output_path = os.path.join(self.temp_dir, "workflow_test.mp4")

        # Имитируем успешный экспорт
        with patch('moviepy.concatenate_videoclips') as mock_concat:
            mock_final = MagicMock()
            mock_concat.return_value = mock_final

            VideoExporter.export(
                "input.mp4",
                markers,
                300,  # total_frames
                30.0, # fps
                output_path
            )

            # Проверяем, что все компоненты были вызваны
            self.assertTrue(mock_video_clip.called)
            self.assertTrue(mock_concat.called)
            self.assertTrue(mock_final.write_videofile.called)
            self.assertTrue(mock_video.close.called)

        print("✅ Полный workflow экспорта работает!")


if __name__ == "__main__":
    print("🚀 Запуск тестов функционала экспорта...\n")

    try:
        # Запускаем тесты
        unittest.main(verbosity=2)

    except Exception as e:
        print(f"\n❌ Ошибка при запуске тестов: {e}")
        sys.exit(1)
