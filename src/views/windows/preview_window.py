"""
Preview Window - просмотр и воспроизведение отрезков (PySide6).
"""

import cv2
import numpy as np
from typing import Optional, Set
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage, QFont, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QListView,
    QCheckBox, QComboBox, QGroupBox, QSpinBox, QLineEdit, QButtonGroup,
    QTextEdit, QTimeEdit, QFormLayout,
    QFrame, QSizePolicy, QSplitter
)

# FIX: убраны все префиксы src. — они не нужны когда src в sys.path
from models.ui.event_list_model import MarkersListModel
from views.widgets.event_card_delegate import EventCardDelegate
from models.domain.marker import Marker
from views.widgets.drawing_overlay import DrawingOverlay, DrawingTool
from services.events.custom_event_manager import get_custom_event_manager


class PreviewWindow(QMainWindow):
    """Окно предпросмотра отрезков."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("🎬 Кинотеатр событий - Презентация тренерам")
        self.setGeometry(100, 100, 1400, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # ─── FIX: Инициализация атрибутов фильтров (ранее отсутствовали) ───
        self.filter_event_types: Set[str] = set()
        self.filter_has_notes: bool = False
        self.filter_notes_search: str = ""

        # Параметры воспроизведения
        self.current_marker_idx = 0
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.frame_time_ms = 33

        # Модель и делегат
        self.markers_model = MarkersListModel(self)
        self.markers_delegate = EventCardDelegate(self)
        self.markers_delegate.play_clicked.connect(self._on_card_play_requested)
        self.markers_delegate.edit_clicked.connect(self._on_card_edit_requested)
        self.markers_delegate.delete_clicked.connect(self._on_card_delete_requested)

        self.event_manager = get_custom_event_manager()

        self._setup_ui()
        self._setup_shortcuts()
        self._update_speed_combo()
        self._update_marker_list()
        self._adjust_window_size_for_video()

        self.event_manager.events_changed.connect(self._on_events_changed)

        # FIX: Подписаться на изменения маркеров, чтобы список обновлялся
        # когда пользователь добавляет/удаляет маркеры
        try:
            self.controller.timeline_controller.markers_changed.connect(
                self._update_marker_list
            )
        except Exception:
            pass

        try:
            self.controller.playback_controller.pixmap_changed.connect(
                self._on_main_pixmap_changed
            )
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # Filters
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_filters(self, parent_layout):
        filters_layout = QVBoxLayout()
        filters_layout.setSpacing(3)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(5)

        event_label = QLabel("Тип:")
        event_label.setMaximumWidth(25)
        row1_layout.addWidget(event_label)

        self.event_filter_combo = QComboBox()
        self.event_filter_combo.setToolTip("Фильтр по типу события")
        self.event_filter_combo.setMaximumWidth(100)
        self.event_filter_combo.currentIndexChanged.connect(self._on_event_filter_changed)
        row1_layout.addWidget(self.event_filter_combo)

        self.notes_filter_checkbox = QCheckBox("Заметки")
        self.notes_filter_checkbox.setToolTip("Показывать только отрезки с заметками")
        self.notes_filter_checkbox.stateChanged.connect(self._on_notes_filter_changed)
        row1_layout.addWidget(self.notes_filter_checkbox)

        reset_btn = QPushButton("Сброс")
        reset_btn.setMaximumWidth(80)
        reset_btn.setToolTip("Сбросить все фильтры")
        reset_btn.clicked.connect(self._on_reset_filters)
        row1_layout.addWidget(reset_btn)

        filters_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(5)

        search_label = QLabel("Поиск:")
        search_label.setMaximumWidth(40)
        row2_layout.addWidget(search_label)

        self.notes_search_edit = QLineEdit()
        self.notes_search_edit.setPlaceholderText("Поиск в заметках...")
        self.notes_search_edit.setToolTip("Поиск по тексту заметок")
        self.notes_search_edit.setMaximumWidth(120)
        self.notes_search_edit.textChanged.connect(self._on_notes_search_changed)
        row2_layout.addWidget(self.notes_search_edit)

        row2_layout.addStretch()
        filters_layout.addLayout(row2_layout)

        parent_layout.addLayout(filters_layout)
        self._update_event_filter()

    def _update_event_filter(self):
        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.clear()
        self.event_filter_combo.addItem("Все", None)
        for event in self.event_manager.get_all_events():
            self.event_filter_combo.addItem(event.get_localized_name(), event.name)
        self.event_filter_combo.blockSignals(False)

    def _on_event_filter_changed(self, index=None):
        current_data = self.event_filter_combo.currentData()
        if current_data is None:
            self.filter_event_types = set()
        else:
            self.filter_event_types = {current_data}
        self._update_marker_list()

    def _on_notes_filter_changed(self):
        self.filter_has_notes = self.notes_filter_checkbox.isChecked()
        self._update_marker_list()

    def _on_notes_search_changed(self):
        self.filter_notes_search = self.notes_search_edit.text().strip().lower()
        self._update_marker_list()

    def _on_reset_filters(self):
        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.setCurrentIndex(0)
        self.event_filter_combo.blockSignals(False)

        self.notes_filter_checkbox.setChecked(False)
        self.notes_search_edit.clear()

        self.filter_event_types = set()
        self.filter_has_notes = False
        self.filter_notes_search = ""
        self._update_marker_list()

    def _on_events_changed(self):
        self._update_event_filter()

    def _passes_filters(self, marker: Marker) -> bool:
        if self.filter_event_types and marker.event_name not in self.filter_event_types:
            return False
        if self.filter_has_notes and not (marker.note or "").strip():
            return False
        if self.filter_notes_search and self.filter_notes_search not in (marker.note or "").lower():
            return False
        return True

    # ──────────────────────────────────────────────────────────────────────────
    # Marker list — FIX: корректная фильтрация и формат данных
    # ──────────────────────────────────────────────────────────────────────────

    def _update_marker_list(self):
        """Обновить список карточек событий с локальной фильтрацией."""
        all_markers = self.controller.project.markers  # FIX: через project напрямую
        fps = self.controller.get_fps()

        filtered_segments = [
            (idx, marker)
            for idx, marker in enumerate(all_markers)
            if self._passes_filters(marker)
        ]

        self.markers_model.set_fps(fps)
        self.markers_model.set_filtered_segments(filtered_segments)
        self._update_active_card_highlight()

    def set_filtered_markers(self, markers):
        """Set filtered markers directly (external call)."""
        fps = self.controller.get_fps() if self.controller else 30.0
        self.markers_model.set_fps(fps)
        if markers and isinstance(markers[0], tuple):
            self.markers_model.set_filtered_segments(markers)
        else:
            self.markers_model.set_markers(markers)
        self._update_active_card_highlight()

    # ──────────────────────────────────────────────────────────────────────────
    # Shortcuts
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self._on_undo_drawing)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        clear_shortcut.activated.connect(self._on_clear_drawing_shortcut)

    def _on_undo_drawing(self):
        if self.drawing_overlay.undo():
            pass

    def _on_clear_drawing_shortcut(self):
        self.drawing_overlay.clear_drawing_with_confirmation(self)

    # ──────────────────────────────────────────────────────────────────────────
    # UI Setup
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # LEFT: VIDEO (70%)
        video_layout = QVBoxLayout()

        self.video_container = QWidget()
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_container.setMinimumSize(1, 1)
        self.video_container.setStyleSheet("background-color: black; border: 1px solid #555555;")

        self.video_label = QLabel(self.video_container)
        self.video_label.setGeometry(0, 0, 800, 450)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.drawing_overlay = DrawingOverlay(self.video_container)
        self.drawing_overlay.setGeometry(0, 0, 800, 450)
        self.drawing_overlay.raise_()

        video_layout.addWidget(self.video_container)

        self._setup_drawing_toolbar(video_layout)

        controls_layout = QHBoxLayout()

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMaximumWidth(80)
        self.play_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        controls_layout.addWidget(self.progress_slider)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMaximumWidth(120)
        controls_layout.addWidget(self.time_label)

        speed_label = QLabel("Speed:")
        controls_layout.addWidget(speed_label)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setMaximumWidth(80)
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        controls_layout.addWidget(self.speed_combo)

        controls_layout.addStretch()
        video_layout.addLayout(controls_layout)

        main_layout.addLayout(video_layout, 7)

        # RIGHT: MARKER LIST (30%)
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self._setup_filters(top_layout)

        self.markers_list = QListView()
        self.markers_list.setModel(self.markers_model)
        self.markers_list.setItemDelegate(self.markers_delegate)
        self.markers_list.setStyleSheet("""
            QListView {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                outline: none;
            }
            QListView::item {
                border-bottom: 1px solid #333333;
                padding: 2px;
            }
            QListView::item:selected {
                background-color: #1a4d7a;
            }
        """)
        self.markers_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.markers_list.setSpacing(2)
        self.markers_list.setUniformItemSizes(True)

        top_layout.addWidget(self.markers_list)
        right_splitter.addWidget(top_widget)

        self._setup_marker_editing_shortcuts()

        main_layout.addWidget(right_splitter, 3)
        central.setLayout(main_layout)

    def _setup_drawing_toolbar(self, parent_layout):
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("drawing_toolbar")
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setSpacing(5)

        self.drawing_tool_group = QButtonGroup(self)
        self.drawing_tool_group.buttonClicked.connect(self._on_drawing_tool_changed)

        cursor_btn = QPushButton("✍")
        cursor_btn.setMaximumWidth(65)
        cursor_btn.setToolTip("Выбрать (отключить рисование)")
        cursor_btn.setCheckable(True)
        cursor_btn.setChecked(True)
        self.drawing_tool_group.addButton(cursor_btn, 0)
        toolbar_layout.addWidget(cursor_btn)

        line_btn = QPushButton("︳")
        line_btn.setMaximumWidth(65)
        line_btn.setToolTip("Линия")
        line_btn.setCheckable(True)
        self.drawing_tool_group.addButton(line_btn, 1)
        toolbar_layout.addWidget(line_btn)

        rect_btn = QPushButton("▭")
        rect_btn.setMaximumWidth(65)
        rect_btn.setToolTip("Прямоугольник")
        rect_btn.setCheckable(True)
        self.drawing_tool_group.addButton(rect_btn, 2)
        toolbar_layout.addWidget(rect_btn)

        circle_btn = QPushButton("◯")
        circle_btn.setMaximumWidth(65)
        circle_btn.setToolTip("Круг")
        circle_btn.setCheckable(True)
        self.drawing_tool_group.addButton(circle_btn, 3)
        toolbar_layout.addWidget(circle_btn)

        arrow_btn = QPushButton("➡")
        arrow_btn.setMaximumWidth(65)
        arrow_btn.setToolTip("Стрелка")
        arrow_btn.setCheckable(True)
        self.drawing_tool_group.addButton(arrow_btn, 4)
        toolbar_layout.addWidget(arrow_btn)

        toolbar_layout.addSpacing(10)

        color_label = QLabel("Цвет:")
        color_label.setMaximumWidth(35)
        toolbar_layout.addWidget(color_label)

        self.color_combo = QComboBox()
        self.color_combo.addItems(["Красный", "Зеленый", "Синий", "Желтый", "Белый", "Черный"])
        self.color_combo.setCurrentText("Красный")
        self.color_combo.setMaximumWidth(80)
        self.color_combo.currentTextChanged.connect(self._on_color_changed)
        toolbar_layout.addWidget(self.color_combo)

        thickness_label = QLabel("Толщ:")
        thickness_label.setMaximumWidth(35)
        toolbar_layout.addWidget(thickness_label)

        self.thickness_combo = QComboBox()
        self.thickness_combo.addItems(["1", "2", "3", "4", "5"])
        self.thickness_combo.setCurrentText("2")
        self.thickness_combo.setMaximumWidth(50)
        self.thickness_combo.currentTextChanged.connect(self._on_thickness_changed)
        toolbar_layout.addWidget(self.thickness_combo)

        toolbar_layout.addStretch()

        clear_btn = QPushButton("Очистить")
        clear_btn.setMaximumWidth(120)
        clear_btn.clicked.connect(self._on_clear_drawing)
        toolbar_layout.addWidget(clear_btn)

        parent_layout.addWidget(toolbar_widget)

    def _on_drawing_tool_changed(self, button):
        tool_id = self.drawing_tool_group.id(button)
        if tool_id == 0:
            self.drawing_overlay.set_tool(DrawingTool.NONE.value)
        elif tool_id == 1:
            self.drawing_overlay.set_tool(DrawingTool.LINE.value)
            if self.is_playing: self._on_play_pause_clicked()
        elif tool_id == 2:
            self.drawing_overlay.set_tool(DrawingTool.RECTANGLE.value)
            if self.is_playing: self._on_play_pause_clicked()
        elif tool_id == 3:
            self.drawing_overlay.set_tool(DrawingTool.CIRCLE.value)
            if self.is_playing: self._on_play_pause_clicked()
        elif tool_id == 4:
            self.drawing_overlay.set_tool(DrawingTool.ARROW.value)
            if self.is_playing: self._on_play_pause_clicked()

    def _on_color_changed(self):
        color_map = {
            "Красный": QColor("#FF0000"), "Зеленый": QColor("#00FF00"),
            "Синий": QColor("#0000FF"), "Желтый": QColor("#FFFF00"),
            "Белый": QColor("#FFFFFF"), "Черный": QColor("#000000")
        }
        self.drawing_overlay.set_color(color_map.get(self.color_combo.currentText(), QColor("#FF0000")))

    def _on_thickness_changed(self):
        self.drawing_overlay.set_thickness(int(self.thickness_combo.currentText()))

    def _on_clear_drawing(self):
        self.drawing_overlay.clear_drawing_with_confirmation(self)

    # ──────────────────────────────────────────────────────────────────────────
    # Card actions
    # ──────────────────────────────────────────────────────────────────────────

    def _on_card_play_requested(self, marker_idx: int):
        self.current_marker_idx = marker_idx
        marker = self.controller.markers[marker_idx]
        self.controller.playback_controller.seek_to_frame(marker.start_frame)
        self._display_current_frame()
        self._update_slider()
        self._update_active_card_highlight()
        if not self.is_playing:
            self._on_play_pause_clicked()

    def _on_card_edit_requested(self, marker_idx: int):
        if self.is_playing:
            self._on_play_pause_clicked()

        # FIX: делегируем MainController
        if hasattr(self.controller, 'open_segment_editor'):
            self.controller.open_segment_editor(marker_idx)
            return

        # Fallback
        marker = self.controller.markers[marker_idx]
        filtered_markers = [
            (idx, m) for idx, m in enumerate(self.controller.markers)
            if self._passes_filters(m)
        ]
        current_filtered_idx = None
        for i, (orig_idx, m) in enumerate(filtered_markers):
            if orig_idx == marker_idx:
                current_filtered_idx = i
                break

        try:
            from views.windows.instance_edit import InstanceEditWindow
            self.instance_edit_window = InstanceEditWindow(
                marker, self.controller, filtered_markers, current_filtered_idx, self
            )
            self.instance_edit_window.marker_updated.connect(self._on_instance_updated_externally)
            self.instance_edit_window.show()
        except Exception as e:
            print(f"ERROR: Failed to open edit window: {e}")

    def _on_card_delete_requested(self, marker_idx: int):
        self.controller.delete_marker(marker_idx)
        self._update_marker_list()

    def _update_active_card_highlight(self):
        row = self.markers_model.find_row_by_marker_idx(self.current_marker_idx)
        if row >= 0:
            index = self.markers_model.index(row, 0)
            self.markers_list.setCurrentIndex(index)
            self.markers_list.scrollTo(index)

    # ──────────────────────────────────────────────────────────────────────────
    # Playback
    # ──────────────────────────────────────────────────────────────────────────

    def _on_play_pause_clicked(self):
        if not self.controller.markers:
            return
        if self.is_playing:
            self.playback_timer.stop()
            self.is_playing = False
            self.play_btn.setText("▶ Play")
        else:
            fps = self.controller.get_fps()
            speed = self.controller.get_playback_speed()
            if fps > 0:
                self.frame_time_ms = int(1000 / (fps * speed))
            self.is_playing = True
            self.play_btn.setText("⏸ Pause")
            self.playback_timer.start(self.frame_time_ms)

    def _on_playback_tick(self):
        if not self.controller.markers:
            self.is_playing = False
            self.play_btn.setText("▶ Play")
            self.playback_timer.stop()
            return

        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.playback_controller.current_frame

        if current_frame >= marker.end_frame:
            next_marker_idx = self._find_next_filtered_marker(self.current_marker_idx)
            if next_marker_idx is not None:
                self.current_marker_idx = next_marker_idx
                next_marker = self.controller.markers[next_marker_idx]
                self.controller.playback_controller.seek_to_frame_immediate(next_marker.start_frame)
                self._update_active_card_highlight()
                self._update_slider()
            else:
                self.is_playing = False
                self.play_btn.setText("▶ Play")
                self.playback_timer.stop()
            return

        next_frame = current_frame + 1
        if next_frame <= marker.end_frame:
            self.controller.playback_controller.seek_to_frame_immediate(next_frame)
        self._update_slider()

    def _find_next_filtered_marker(self, current_idx: int) -> Optional[int]:
        for idx in range(current_idx + 1, len(self.controller.markers)):
            if self._passes_filters(self.controller.markers[idx]):
                return idx
        return None

    def _go_to_next_marker(self):
        next_marker_idx = self._find_next_filtered_marker(self.current_marker_idx)
        if next_marker_idx is not None:
            self.current_marker_idx = next_marker_idx
            marker = self.controller.markers[next_marker_idx]
            self.controller.playback_controller.seek_to_frame(marker.start_frame)
            self._display_current_frame()
            self._update_slider()
            self._update_active_card_highlight()
            return
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.playback_timer.stop()

    def _on_slider_moved(self):
        frame_idx = self.progress_slider.value()
        self.controller.playback_controller.seek_to_frame(frame_idx)
        self._update_slider()

    def _display_current_frame(self):
        """Отобразить текущий кадр."""
        frame_idx = self.controller.playback_controller.current_frame

        # Попробовать кэш PlaybackController
        pixmap = None
        if hasattr(self.controller.playback_controller, "get_cached_pixmap"):
            pixmap = self.controller.playback_controller.get_cached_pixmap(frame_idx)
        if pixmap is not None:
            self._display_pixmap(pixmap)
            return

        # Fallback: попросить PlaybackController декодировать кадр.
        # Он вызовет pixmap_changed, который мы уже слушаем.
        try:
            self.controller.playback_controller.seek_to_frame_immediate(frame_idx)
        except Exception as e:
            print(f"Preview: failed to display frame {frame_idx}: {e}")

    def _on_main_pixmap_changed(self, pixmap: QPixmap, frame_idx: int):
        if frame_idx != self.controller.playback_controller.current_frame:
            return
        self._display_pixmap(pixmap)

    def _update_slider(self):
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            return
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.playback_controller.current_frame
        fps = self.controller.get_fps()

        self.progress_slider.blockSignals(True)
        self.progress_slider.setMinimum(marker.start_frame)
        self.progress_slider.setMaximum(marker.end_frame)
        self.progress_slider.setValue(current_frame)
        self.progress_slider.blockSignals(False)

        if fps > 0:
            current_time = current_frame / fps
            end_time = marker.end_frame / fps
            self.time_label.setText(f"{self._format_time(current_time)} / {self._format_time(end_time)}")

    def _on_speed_changed(self):
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        if hasattr(self.controller, 'set_playback_speed'):
            self.controller.set_playback_speed(speed)
        fps = self.controller.get_fps()
        if fps > 0:
            self.frame_time_ms = int(1000 / (fps * speed))
        if self.is_playing:
            self.playback_timer.start(self.frame_time_ms)

    def _update_speed_combo(self):
        current_speed = self.controller.get_playback_speed()
        speed_text = f"{current_speed:.2f}x"
        items = [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]
        if speed_text in items:
            self.speed_combo.setCurrentText(speed_text)
        else:
            closest_item = min(items, key=lambda x: abs(float(x.replace('x', '')) - current_speed))
            self.speed_combo.setCurrentText(closest_item)

    # ──────────────────────────────────────────────────────────────────────────
    # Marker editing shortcuts
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_marker_editing_shortcuts(self):
        self.i_shortcut = QShortcut(QKeySequence("I"), self)
        self.i_shortcut.activated.connect(self._on_set_marker_start)
        self.o_shortcut = QShortcut(QKeySequence("O"), self)
        self.o_shortcut.activated.connect(self._on_set_marker_end)
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.delete_shortcut.activated.connect(self._on_delete_current_marker)

    def _get_selected_marker(self):
        current_index = self.markers_list.currentIndex()
        if current_index.isValid():
            return self.markers_model.get_marker_at(current_index.row())
        return None, None

    def _on_set_marker_start(self):
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            return
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.playback_controller.current_frame
        marker.start_frame = current_frame
        if marker.start_frame > marker.end_frame:
            marker.end_frame = marker.start_frame + int(self.controller.get_fps())
        self.controller.timeline_controller.markers_changed.emit()
        self._update_marker_list()

    def _on_set_marker_end(self):
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            return
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.playback_controller.current_frame
        marker.end_frame = current_frame
        if marker.end_frame < marker.start_frame:
            marker.start_frame = max(0, marker.end_frame - int(self.controller.get_fps()))
        self.controller.timeline_controller.markers_changed.emit()
        self._update_marker_list()

    def _on_delete_current_marker(self):
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            return
        self.controller.delete_marker(self.current_marker_idx)
        self._update_marker_list()

    def keyPressEvent(self, event):
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit)):
            super().keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def _on_instance_updated_externally(self):
        self._update_marker_list()

    # ──────────────────────────────────────────────────────────────────────────
    # Window events
    # ──────────────────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._display_current_frame)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "controller"):
            self._display_current_frame()

    # ──────────────────────────────────────────────────────────────────────────
    # Display helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _format_time(self, seconds: float) -> str:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _display_pixmap(self, pixmap: QPixmap):
        if pixmap is None or pixmap.isNull():
            return
        target_size = self.video_container.size()
        scaled_pixmap = pixmap.scaled(
            target_size, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

        container_width = self.video_container.width()
        container_height = self.video_container.height()
        pixmap_width = scaled_pixmap.width()
        pixmap_height = scaled_pixmap.height()

        x = (container_width - pixmap_width) // 2
        y = (container_height - pixmap_height) // 2

        self.video_label.setGeometry(x, y, pixmap_width, pixmap_height)
        self.drawing_overlay.setGeometry(x, y, pixmap_width, pixmap_height)

    def _display_frame(self, frame):
        if frame is None:
            return
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        q_img = q_img.rgbSwapped()

        target_size = self.video_container.size()
        scaled_pixmap = QPixmap.fromImage(q_img).scaled(
            target_size, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

        container_width = self.video_container.width()
        container_height = self.video_container.height()
        pixmap_width = scaled_pixmap.width()
        pixmap_height = scaled_pixmap.height()

        x = (container_width - pixmap_width) // 2
        y = (container_height - pixmap_height) // 2

        self.video_label.setGeometry(x, y, pixmap_width, pixmap_height)
        self.drawing_overlay.setGeometry(x, y, pixmap_width, pixmap_height)

    def _adjust_window_size_for_video(self):
        try:
            video_width = self.controller.get_video_width()
            video_height = self.controller.get_video_height()
            if video_width <= 0 or video_height <= 0:
                return

            video_aspect_ratio = video_width / video_height
            controls_height = 50
            margins = 20

            test_width = 1200
            video_w = int(test_width * 0.7)
            video_h = int(video_w / video_aspect_ratio)
            final_height = video_h + controls_height + margins + 100

            screen = QApplication.primaryScreen().size()
            final_width = min(test_width, int(screen.width() * 0.9))
            final_height = min(final_height, int(screen.height() * 0.9))

            self.resize(final_width, final_height)

            screen_geometry = QApplication.primaryScreen().geometry()
            x = screen_geometry.center().x() - final_width // 2
            y = screen_geometry.center().y() - final_height // 2
            self.move(x, y)
        except Exception:
            pass