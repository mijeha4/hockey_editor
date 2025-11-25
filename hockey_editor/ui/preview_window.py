"""
Preview Window - просмотр и воспроизведение отрезков (PySide6).
Немодальное окно с видеоплеером и списком отрезков.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage, QFont, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QListWidget, QListWidgetItem, QCheckBox, QComboBox, QGroupBox
)
import cv2
import numpy as np
from typing import Optional
from ..models.marker import Marker, EventType


class PreviewWindow(QMainWindow):
    """
    Окно предпросмотра отрезков.
    Содержит видеоплеер и список отрезков с фильтрацией.
    """
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Preview - Segments")
        self.setGeometry(100, 100, 1400, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # Немодальное окно
        self.setStyleSheet(self._get_dark_stylesheet())
        
        # Параметры воспроизведения
        self.current_marker_idx = 0
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.frame_time_ms = 33  # ~30 FPS
        
        self._create_filter_checkboxes()
        self._setup_ui()
        self._update_marker_list()

    def _create_filter_checkboxes(self):
        """Создать динамические checkbox для фильтрации событий."""
        # Получить все доступные события из CustomEventManager
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        events = event_manager.get_all_events()

        # Очистить существующие checkbox
        self.filter_checkboxes = {}

        for event in events:
            checkbox = QCheckBox(f"{event.name} ({event.shortcut})")
            checkbox.setChecked(True)
            checkbox.setToolTip(f"Show/hide {event.name} events")
            checkbox.stateChanged.connect(self._update_marker_list)

            # Установить цвет текста как цвет события
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {event.color};
                }}
            """)

            self.filter_checkboxes[event.name] = checkbox

    def _setup_ui(self):
        """Создать интерфейс."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ===== ЛЕВАЯ ЧАСТЬ: ВИДЕОПЛЕЕР (70%) =====
        video_layout = QVBoxLayout()
        
        # Видео
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 450)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid #555555;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setToolTip("Preview video player")
        video_layout.addWidget(self.video_label)
        
        # Контролы видео
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMaximumWidth(80)
        self.play_btn.setToolTip("Play/Pause preview (Space)")
        self.play_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)
        
        # Ползунок
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setToolTip("Seek within current segment")
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        controls_layout.addWidget(self.progress_slider)
        
        # Время
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMaximumWidth(120)
        self.time_label.setToolTip("Current time / Segment duration")
        controls_layout.addWidget(self.time_label)
        
        # Скорость
        speed_label = QLabel("Speed:")
        controls_layout.addWidget(speed_label)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1.0x", "2.0x"])
        self.speed_combo.setCurrentIndex(1)
        self.speed_combo.setMaximumWidth(80)
        self.speed_combo.setToolTip("Playback speed")
        self.speed_combo.currentIndexChanged.connect(self._update_frame_time)
        controls_layout.addWidget(self.speed_combo)
        
        controls_layout.addStretch()
        video_layout.addLayout(controls_layout)
        
        main_layout.addLayout(video_layout, 7)
        
        # ===== ПРАВАЯ ЧАСТЬ: СПИСОК ОТРЕЗКОВ (30%) =====
        list_layout = QVBoxLayout()
        
        # Фильтры (динамические из CustomEventManager)
        filter_group = QGroupBox("Filter Events")
        self.filter_layout = QVBoxLayout()
        
        # Добавить чекбоксы в layout
        for event_name, checkbox in self.filter_checkboxes.items():
            self.filter_layout.addWidget(checkbox)
        
        filter_group.setLayout(self.filter_layout)
        list_layout.addWidget(filter_group)
        
        # Список отрезков
        self.markers_list = QListWidget()
        self.markers_list.setToolTip("Click to preview segment")
        self.markers_list.itemClicked.connect(self._on_marker_selected)
        list_layout.addWidget(self.markers_list)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        edit_btn = QPushButton("✎ Edit")
        edit_btn.setToolTip("Edit selected segment")
        edit_btn.clicked.connect(self._on_edit_marker)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setToolTip("Delete selected segment")
        delete_btn.clicked.connect(self._on_delete_marker)
        btn_layout.addWidget(delete_btn)
        
        list_layout.addLayout(btn_layout)
        
        main_layout.addLayout(list_layout, 3)
        
        central.setLayout(main_layout)

    def _update_marker_list(self):
        """Обновить список отрезков с фильтрацией."""
        self.markers_list.clear()

        fps = self.controller.get_fps()

        # Получить активные фильтры
        active_filters = {}
        for event_name, checkbox in self.filter_checkboxes.items():
            active_filters[event_name] = checkbox.isChecked()

        for idx, marker in enumerate(self.controller.markers):
            # Фильтрация по событиям
            if not active_filters.get(marker.event_name, True):
                continue

            start_time = self._format_time(marker.start_frame / fps if fps > 0 else 0)
            end_time = self._format_time(marker.end_frame / fps if fps > 0 else 0)
            duration_frames = marker.end_frame - marker.start_frame
            duration_sec = duration_frames / fps if fps > 0 else 0

            text = f"{idx+1}. {marker.event_name} ({start_time}–{end_time}) [{duration_sec:.1f}s]"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, idx)  # Сохранить оригинальный индекс

            # Получить цвет события из CustomEventManager
            from ..utils.custom_events import get_custom_event_manager
            event_manager = get_custom_event_manager()
            event = event_manager.get_event(marker.event_name)
            if event:
                item.setForeground(event.get_qcolor())
            else:
                item.setForeground(QColor(150, 150, 150))  # Серый по умолчанию

            self.markers_list.addItem(item)

    def _on_marker_selected(self, item: QListWidgetItem):
        """Клик на отрезок = воспроизведение с начала."""
        marker_idx = item.data(Qt.ItemDataRole.UserRole)
        self.current_marker_idx = marker_idx
        
        marker = self.controller.markers[marker_idx]
        self.controller.seek_frame(marker.start_frame)
        self._display_current_frame()
        self._update_slider()
        
        # Автоматически начать воспроизведение
        if not self.is_playing:
            self._on_play_pause_clicked()

    def _on_play_pause_clicked(self):
        """Кнопка Play/Pause."""
        if not self.controller.markers:
            return
        
        if self.is_playing:
            self.playback_timer.stop()
            self.is_playing = False
            self.play_btn.setText("▶ Play")
        else:
            self.is_playing = True
            self.play_btn.setText("⏸ Pause")
            self.playback_timer.start(self.frame_time_ms)

    def _on_playback_tick(self):
        """Таймер воспроизведения."""
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            self.is_playing = False
            self.play_btn.setText("▶ Play")
            self.playback_timer.stop()
            return
        
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.processor.get_current_frame_idx()
        
        # Если достигли конца отрезка
        if current_frame >= marker.end_frame:
            # Переместиться на следующий отрезок (с фильтрацией)
            self._go_to_next_marker()
            return
        
        # Воспроизвести следующий кадр
        self.controller.processor.advance_frame()
        self._display_current_frame()
        self._update_slider()

    def _go_to_next_marker(self):
        """Перейти на следующий отрезок (с фильтрацией)."""
        # Найти следующий отрезок, соответствующий фильтру
        for idx in range(self.current_marker_idx + 1, len(self.controller.markers)):
            marker = self.controller.markers[idx]
            # Получить активные фильтры
            active_filters = {}
            for event_name, checkbox in self.filter_checkboxes.items():
                active_filters[event_name] = checkbox.isChecked()
            
            if active_filters.get(marker.event_name, True):
                self.current_marker_idx = idx
                self.controller.seek_frame(marker.start_frame)
                self.markers_list.setCurrentRow(idx)
                self._display_current_frame()
                self._update_slider()
                return
        
        # Конец списка
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.playback_timer.stop()

    def _on_slider_moved(self):
        """Движение ползунка."""
        frame_idx = self.progress_slider.value()
        self.controller.seek_frame(frame_idx)
        self._display_current_frame()
        self._update_slider()

    def _on_edit_marker(self):
        """Отредактировать выбранный отрезок."""
        current_idx = self.markers_list.currentRow()
        if current_idx < 0:
            return
        
        marker_idx = self.markers_list.item(current_idx).data(Qt.ItemDataRole.UserRole)
        from .edit_segment_dialog import EditSegmentDialog
        marker = self.controller.markers[marker_idx]
        dialog = EditSegmentDialog(marker, self.controller.get_fps(), self)
        if dialog.exec():
            self.controller.markers[marker_idx] = dialog.get_marker()
            self.controller.markers_changed.emit()
        self._update_marker_list()

    def _on_delete_marker(self):
        """Удалить выбранный отрезок."""
        current_idx = self.markers_list.currentRow()
        if current_idx < 0:
            return
        
        marker_idx = self.markers_list.item(current_idx).data(Qt.ItemDataRole.UserRole)
        self.controller.delete_marker(marker_idx)
        self._update_marker_list()

    def _display_current_frame(self):
        """Отобразить текущий кадр."""
        frame = self.controller.processor.get_current_frame()
        if frame is None:
            return
        
        # Конвертировать BGR в RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Масштабировать
        pixmap = QPixmap.fromImage(qt_image)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(pixmap)

    def _update_slider(self):
        """Обновить ползунок и время."""
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            return
        
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.processor.get_current_frame_idx()
        fps = self.controller.get_fps()
        
        # Ползунок
        self.progress_slider.blockSignals(True)
        self.progress_slider.setMinimum(marker.start_frame)
        self.progress_slider.setMaximum(marker.end_frame)
        self.progress_slider.setValue(current_frame)
        self.progress_slider.blockSignals(False)
        
        # Время
        if fps > 0:
            current_time = current_frame / fps
            end_time = marker.end_frame / fps
            self.time_label.setText(f"{self._format_time(current_time)} / {self._format_time(end_time)}")

    def _update_frame_time(self):
        """Обновить frame_time_ms в зависимости от скорости."""
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', '')) 
        fps = self.controller.get_fps()
        if fps > 0:
            self.frame_time_ms = int(1000 / (fps * speed))

    def _format_time(self, seconds: float) -> str:
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
        QLabel, QCheckBox {
            color: #ffffff;
        }
        QComboBox {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        """
