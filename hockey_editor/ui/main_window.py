from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QListWidget, QListWidgetItem, QFileDialog, QComboBox, QSpinBox,
    QMessageBox, QSpinBox
)
import cv2
import numpy as np
from .timeline import TimelineWidget
from .segment_editor import SegmentEditorDialog
from .settings_dialog import SettingsDialog
from ..models.marker import EventType


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.setWindowTitle("Hockey Editor Pro - Professional Video Analysis")
        self.setGeometry(0, 0, 1800, 1000)
        self.setStyleSheet(self._get_dark_stylesheet())
        
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Создать UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # ===== ВЕРХНЯЯ ЧАСТЬ (видео + список справа) =====
        top_layout = QHBoxLayout()
        
        # Видео (70%)
        video_layout = QVBoxLayout()
        
        # Видео виджет
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 450)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid grey;")
        video_layout.addWidget(self.video_label)
        
        # Контролы видео
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMaximumWidth(80)
        self.play_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)
        
        # Ползунок прогресса
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.sliderMoved.connect(self._on_progress_slider_moved)
        controls_layout.addWidget(self.progress_slider)
        
        # Время
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMaximumWidth(100)
        controls_layout.addWidget(self.time_label)
        
        # Скорость (всегда 1x)
        speed_label = QLabel("1.0x")
        speed_label.setMaximumWidth(40)
        controls_layout.addWidget(speed_label)
        
        # Открыть видео
        open_btn = QPushButton("📁 Open")
        open_btn.setMaximumWidth(70)
        open_btn.clicked.connect(self._on_open_video)
        controls_layout.addWidget(open_btn)
        
        video_layout.addLayout(controls_layout)
        top_layout.addLayout(video_layout, 7)
        
        # Список отрезков (30%)
        list_layout = QVBoxLayout()
        list_layout.addWidget(QLabel("Segments:"))
        
        self.markers_list = QListWidget()
        self.markers_list.itemDoubleClicked.connect(self._on_marker_double_clicked)
        list_layout.addWidget(self.markers_list)
        
        # Кнопки управления списком
        marker_btn_layout = QHBoxLayout()
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self._on_delete_marker)
        marker_btn_layout.addWidget(delete_btn)
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self._on_clear_markers)
        marker_btn_layout.addWidget(clear_btn)
        
        list_layout.addLayout(marker_btn_layout)
        
        top_layout.addLayout(list_layout, 3)
        
        main_layout.addLayout(top_layout)
        
        # ===== ТАЙМЛАЙН =====
        main_layout.addWidget(QLabel("Timeline:"))
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.set_controller(self.controller)
        main_layout.addWidget(self.timeline_widget)
        
        # ===== КНОПКИ СОБЫТИЙ (A/D/S) И НАСТРОЙКИ =====
        event_layout = QHBoxLayout()
        
        # Кнопки A/D/S
        self.attack_btn = self._create_event_button("A\nATTACK", "#8b0000")
        self.attack_btn.clicked.connect(lambda: self._on_event_btn_clicked(EventType.ATTACK))
        event_layout.addWidget(self.attack_btn)
        
        self.defense_btn = self._create_event_button("D\nDEFENSE", "#000080")
        self.defense_btn.clicked.connect(lambda: self._on_event_btn_clicked(EventType.DEFENSE))
        event_layout.addWidget(self.defense_btn)
        
        self.shift_btn = self._create_event_button("S\nSHIFT", "#006400")
        self.shift_btn.clicked.connect(lambda: self._on_event_btn_clicked(EventType.SHIFT))
        event_layout.addWidget(self.shift_btn)
        
        event_layout.addStretch()
        
        # Кнопка настроек
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self._on_settings_clicked)
        event_layout.addWidget(settings_btn)
        
        # Кнопка экспорта
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self._on_export_clicked)
        event_layout.addWidget(export_btn)
        
        # Статус
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #ffcc00;")
        event_layout.addWidget(self.status_label)
        
        main_layout.addLayout(event_layout)
        
        central.setLayout(main_layout)
        
        # Подключить сигнал frame_ready для обновления видео
        self.controller.frame_ready.connect(self._on_frame_ready)

    def _create_event_button(self, text: str, color: str) -> QPushButton:
        """Создать кнопку события."""
        btn = QPushButton(text)
        btn.setMinimumSize(120, 90)
        btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid {color};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton:pressed {{
                border: 3px solid yellow;
                background-color: {self._lighten_color(color)};
            }}
        """)
        return btn

    def _lighten_color(self, color_hex: str) -> str:
        """Светлая версия цвета для hover."""
        # Простая реализация
        return color_hex.replace("00", "33").replace("8b", "bb")

    def connect_signals(self):
        """Подключить сигналы контроллера."""
        self.controller.playback_time_changed.connect(self._on_playback_time_changed)
        self.controller.markers_changed.connect(self._on_markers_changed)
        self.controller.recording_status_changed.connect(self._on_recording_status_changed)
        self.controller.timeline_update.connect(self._on_timeline_update)

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш."""
        if event.isAutoRepeat():
            return
        
        key = event.text().upper()
        
        # Горячие клавиши событий
        if key in self.controller.hotkeys:
            event_type = self.controller.hotkeys[key]
            self.controller.on_hotkey_pressed(event_type)
        
        # Space = Play/Pause
        elif key == ' ':
            self.controller.toggle_play_pause()
            self._update_play_btn_text()
        
        # Escape = отмена записи
        elif event.key() == Qt.Key.Key_Escape:
            self.controller.cancel_recording()
        
        # Ctrl+O = открыть видео
        elif event.key() == Qt.Key.Key_O and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._on_open_video()
        
        super().keyPressEvent(event)

    def _on_play_pause_clicked(self):
        """Кнопка Play/Pause - переключение."""
        self.controller.toggle_play_pause()
        self._update_play_btn_text()

    def _update_play_btn_text(self):
        """Обновить текст кнопки Play/Pause."""
        if self.controller.playing:
            self.play_btn.setText("⏸ Pause")
        else:
            self.play_btn.setText("▶ Play")

    def _on_progress_slider_moved(self):
        """Движение ползунка прогресса."""
        frame_idx = self.progress_slider.value()
        self.controller.seek_frame(frame_idx)

    def _on_open_video(self):
        """Открыть видео."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "", "Videos (*.mp4 *.avi *.mov *.mkv);;All (*.*)"
        )
        if path:
            if self.controller.load_video(path):
                self.status_label.setText(f"✓ Loaded: {path.split('/')[-1]}")
                self._update_play_btn_text()
                self.progress_slider.setMaximum(self.controller.get_total_frames())
            else:
                QMessageBox.critical(self, "Error", "Failed to load video")

    def _on_event_btn_clicked(self, event_type: EventType):
        """Нажатие кнопки события."""
        self.controller.on_hotkey_pressed(event_type)

    def _on_settings_clicked(self):
        """Открыть настройки."""
        dialog = SettingsDialog(self.controller, self)
        dialog.exec()

    def _on_export_clicked(self):
        """Экспортировать видео."""
        if not self.controller.markers:
            QMessageBox.warning(self, "Warning", "No segments to export")
            return
        
        QMessageBox.information(self, "Export", "Export functionality coming soon")

    def _on_marker_double_clicked(self, item: QListWidgetItem):
        """Двойной клик на отрезок = редактирование."""
        idx = self.markers_list.row(item)
        dialog = SegmentEditorDialog(self.controller, idx, self)
        dialog.exec()

    def _on_delete_marker(self):
        """Удалить выбранный отрезок."""
        current_idx = self.markers_list.currentRow()
        if current_idx >= 0:
            self.controller.delete_marker(current_idx)

    def _on_clear_markers(self):
        """Удалить все отрезки."""
        reply = QMessageBox.question(self, "Confirm", "Delete all segments?")
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.clear_markers()

    def _on_playback_time_changed(self, frame_idx: int):
        """Обновление при изменении времени воспроизведения."""
        fps = self.controller.get_fps()
        total_frames = self.controller.get_total_frames()
        
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(frame_idx)
        self.progress_slider.blockSignals(False)
        
        # Обновить время
        if fps > 0:
            current_sec = frame_idx / fps
            total_sec = total_frames / fps
            self.time_label.setText(self._format_time(current_sec, total_sec))

    def _on_markers_changed(self):
        """Обновление списка отрезков."""
        self.markers_list.clear()
        fps = self.controller.get_fps()
        
        for idx, marker in enumerate(self.controller.markers):
            start_time = self._format_time_single(marker.start_frame / fps if fps > 0 else 0)
            end_time = self._format_time_single(marker.end_frame / fps if fps > 0 else 0)
            text = f"{idx+1}. {marker.type.name} ({start_time}–{end_time})"
            self.markers_list.addItem(text)

    def _on_recording_status_changed(self, event_type: str, status: str):
        """Изменение статуса записи."""
        if status == "Recording":
            self.status_label.setText(f"🔴 Recording: {event_type}")
            self.status_label.setStyleSheet("color: #ff0000;")
        elif status == "Complete":
            self.status_label.setText(f"✓ Complete: {event_type}")
            self.status_label.setStyleSheet("color: #00ff00;")
        elif status == "Fixed":
            self.status_label.setText(f"✓ Fixed: {event_type}")
            self.status_label.setStyleSheet("color: #00ff00;")
        elif status == "Cancelled":
            self.status_label.setText("⏹️ Cancelled")
            self.status_label.setStyleSheet("color: #ffcc00;")
        else:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: #ffcc00;")

    def _on_timeline_update(self):
        """Обновление таймлайна."""
        pass  # TimelineWidget обновляется через сигналы

    def _update_video_frame(self):
        """Обновить видео кадр на экране (через сигнал frame_ready)."""
        pass  # Видео обновляется через frame_ready сигнал

    def _on_frame_ready(self, frame):
        """Обработка готового кадра из контроллера."""
        if frame is None:
            return
        
        # Конвертировать BGR в RGB
        import cv2
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Масштабировать под размер label
        pixmap = QPixmap.fromImage(qt_image)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(pixmap)

    def _format_time(self, current_sec: float, total_sec: float) -> str:
        """Форматировать время MM:SS / MM:SS."""
        def fmt(s):
            m = int(s) // 60
            s = int(s) % 60
            return f"{m:02d}:{s:02d}"
        return f"{fmt(current_sec)} / {fmt(total_sec)}"

    def _format_time_single(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _get_dark_stylesheet(self) -> str:
        """Тёмный стиль."""
        return """
        QMainWindow, QWidget {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        QPushButton {
            background-color: #333333;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #444444;
        }
        QSlider::groove:horizontal {
            background: #333333;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #ffcc00;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QListWidget {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QLabel {
            color: #ffffff;
        }
        QComboBox {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
        }
        """

    def closeEvent(self, event):
        """Закрытие окна."""
        self.controller.cleanup()
        event.accept()
