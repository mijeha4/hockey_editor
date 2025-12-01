#!/usr/bin/env python3
"""
Тесты для ExportDialog UI компонента.
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
sys.path.insert(0, 'hockey_editor')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from hockey_editor.ui.export_dialog import ExportDialog
from hockey_editor.core.video_controller import VideoController
from hockey_editor.models.marker import Marker


class TestExportDialog(unittest.TestCase):
    """Тесты для ExportDialog."""

    @classmethod
    def setUpClass(cls):
        """Создаем QApplication для тестов Qt."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        """Подготовка тестовых данных."""
        self.temp_dir = tempfile.mkdtemp()

        # Создаем mock контроллер
        self.controller = MagicMock(spec=VideoController)
        self.controller.markers = [
            Marker(start_frame=0, end_frame=100, event_name="Attack", note=""),
            Marker(start_frame=200, end_frame=300, event_name="Defense", note=""),
            Marker(start_frame=400, end_frame=500, event_name="Shift", note="")
        ]
        self.controller.get_fps.return_value = 30.0

        # Настраиваем processor как mock объект
        self.controller.processor = MagicMock()
        self.controller.processor.video_path = "test_video.mp4"

    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dialog_creation(self):
        """Тест создания диалога экспорта."""
        print("🧪 Тестирование создания диалога экспорта...")

        # Создаем диалог без родительского окна
        dialog = ExportDialog(self.controller)

        # Проверяем основные свойства
        self.assertEqual(dialog.windowTitle(), "Export Segments")
        self.assertEqual(len(dialog.segment_checkboxes), 3)  # Три маркера

        # Проверяем, что все checkbox выбраны по умолчанию
        for cb in dialog.segment_checkboxes:
            self.assertTrue(cb.isChecked())

        dialog.deleteLater()
        print("✅ Диалог экспорта создается корректно!")

    def test_segment_population(self):
        """Тест заполнения списка сегментов."""
        print("\n🧪 Тестирование заполнения сегментов...")

        dialog = ExportDialog(self.controller)

        # Проверяем количество checkbox
        self.assertEqual(len(dialog.segment_checkboxes), 3)

        # Проверяем текст checkbox
        # 200/30 = 6.67 сек (округляется до 6), 300/30 = 10 сек
        # 400/30 = 13.33 сек (округляется до 13), 500/30 = 16.67 сек (округляется до 16)
        expected_texts = [
            "1. Attack (00:00–00:03) [3.3s]",
            "2. Defense (00:06–00:10) [3.3s]",  # 200/30 = 6.67 -> 00:06
            "3. Shift (00:13–00:16) [3.3s]"     # 500/30 = 16.67 -> 00:16
        ]

        for i, cb in enumerate(dialog.segment_checkboxes):
            self.assertEqual(cb.text(), expected_texts[i])

        dialog.deleteLater()
        print("✅ Сегменты заполняются корректно!")

    def test_select_all_deselect_all(self):
        """Тест функций Select All / Deselect All."""
        print("\n🧪 Тестирование Select All / Deselect All...")

        dialog = ExportDialog(self.controller)

        # Сначала все выбраны
        for cb in dialog.segment_checkboxes:
            self.assertTrue(cb.isChecked())

        # Deselect All
        dialog._deselect_all_segments()
        for cb in dialog.segment_checkboxes:
            self.assertFalse(cb.isChecked())

        # Select All
        dialog._select_all_segments()
        for cb in dialog.segment_checkboxes:
            self.assertTrue(cb.isChecked())

        dialog.deleteLater()
        print("✅ Select All / Deselect All работают корректно!")

    def test_quality_settings(self):
        """Тест настроек качества."""
        print("\n🧪 Тестирование настроек качества...")

        dialog = ExportDialog(self.controller)

        # Проверяем доступные опции качества
        quality_options = []
        for i in range(dialog.quality_combo.count()):
            quality_options.append(dialog.quality_combo.itemText(i))

        expected_options = ["High (CRF 18)", "Medium (CRF 23)", "Low (CRF 28)", "Custom"]
        self.assertEqual(quality_options, expected_options)

        # По умолчанию Medium (CRF 23)
        self.assertEqual(dialog.quality_combo.currentIndex(), 1)  # Medium
        self.assertEqual(dialog.quality_spin.value(), 23)
        self.assertFalse(dialog.quality_spin.isVisible())

        # Меняем на High
        dialog.quality_combo.setCurrentIndex(0)  # High
        dialog._on_quality_changed()  # Вызываем обработчик
        self.assertEqual(dialog.quality_spin.value(), 18)
        self.assertFalse(dialog.quality_spin.isVisible())

        dialog.deleteLater()
        print("✅ Настройки качества работают корректно!")

    def test_format_settings(self):
        """Тест настроек формата."""
        print("\n🧪 Тестирование настроек формата...")

        dialog = ExportDialog(self.controller)

        # Проверяем доступные форматы
        formats = []
        for i in range(dialog.format_combo.count()):
            formats.append(dialog.format_combo.itemText(i))

        expected_formats = ["MP4 (.mp4)", "MOV (.mov)", "MKV (.mkv)", "WebM (.webm)"]
        self.assertEqual(formats, expected_formats)

        dialog.deleteLater()
        print("✅ Настройки формата работают корректно!")

    @patch('hockey_editor.ui.export_dialog.QFileDialog.getSaveFileName')
    def test_browse_output(self, mock_get_save_file):
        """Тест выбора пути сохранения."""
        print("\n🧪 Тестирование выбора пути сохранения...")

        dialog = ExportDialog(self.controller)

        # Mock выбор файла
        mock_get_save_file.return_value = ("/path/to/export.mp4", "MP4 (*.mp4)")

        # Вызываем browse
        dialog._on_browse_output()

        # Проверяем, что путь сохранен
        self.assertEqual(dialog.output_path, "/path/to/export.mp4")

        dialog.deleteLater()
        print("✅ Выбор пути сохранения работает корректно!")

    @patch('hockey_editor.ui.export_dialog.QMessageBox.warning')
    def test_export_validation(self, mock_warning):
        """Тест валидации перед экспортом."""
        print("\n🧪 Тестирование валидации экспорта...")

        dialog = ExportDialog(self.controller)

        # Тест без выбранных сегментов
        for cb in dialog.segment_checkboxes:
            cb.setChecked(False)

        dialog._on_export_clicked()
        mock_warning.assert_called_with(dialog, "No Segments", "Please select at least one segment to export")

        # Тест без пути сохранения
        dialog.segment_checkboxes[0].setChecked(True)  # Выбираем один сегмент
        dialog.output_path = None

        dialog._on_export_clicked()
        mock_warning.assert_called_with(dialog, "No Output Path", "Please select output file")

        dialog.deleteLater()
        print("✅ Валидация экспорта работает корректно!")

    def test_time_formatting(self):
        """Тест форматирования времени."""
        print("\n🧪 Тестирование форматирования времени...")

        dialog = ExportDialog(self.controller)

        # Тест различных значений времени
        test_cases = [
            (0, "00:00"),      # 0 секунд
            (59, "00:59"),     # 59 секунд
            (60, "01:00"),     # 1 минута
            (125, "02:05"),    # 2 минуты 5 секунд
            (3661, "61:01")    # 61 минута 1 секунда
        ]

        for seconds, expected in test_cases:
            result = dialog._format_time(seconds)
            self.assertEqual(result, expected, f"Failed for {seconds} seconds")

        dialog.deleteLater()
        print("✅ Форматирование времени работает корректно!")

    def test_resolution_mapping(self):
        """Тест маппинга разрешений."""
        print("\n🧪 Тестирование маппинга разрешений...")

        dialog = ExportDialog(self.controller)

        # Тест различных индексов
        test_cases = [
            (0, "source"),   # Source
            (1, "2160p"),    # 4K
            (2, "1080p"),    # Full HD
            (3, "720p"),     # HD
            (4, "480p"),     # SD
            (5, "360p")      # 360p
        ]

        for index, expected in test_cases:
            dialog.resolution_combo.setCurrentIndex(index)
            result = dialog._get_resolution_value()
            self.assertEqual(result, expected, f"Failed for index {index}")

        dialog.deleteLater()
        print("✅ Маппинг разрешений работает корректно!")


if __name__ == "__main__":
    print("🚀 Запуск тестов ExportDialog...\n")

    try:
        # Запускаем тесты
        unittest.main(verbosity=2)

    except Exception as e:
        print(f"\n❌ Ошибка при запуске тестов: {e}")
        sys.exit(1)
