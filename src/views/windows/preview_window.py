"""
Preview Window — просмотр и анализ отрезков.
Делегирует логику PreviewController.
Использует VideoProgressBar вместо QSlider.
"""

import os
from typing import Optional, Set

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListView, QCheckBox, QComboBox, QGroupBox,
    QLineEdit, QTextEdit, QSplitter, QSizePolicy, QFileDialog, QMessageBox,
    QButtonGroup
)

from models.ui.event_list_model import MarkersListModel
from views.widgets.event_card_delegate import EventCardDelegate
from views.widgets.drawing_overlay import DrawingOverlay, DrawingTool
from views.widgets.video_progress_bar import VideoProgressBar
from controllers.preview_controller import PreviewController
from services.events.custom_event_manager import get_custom_event_manager


class PreviewWindow(QMainWindow):
    """Окно предпросмотра отрезков."""

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)
        self.main_controller = main_controller
        self.setWindowTitle("🎬 Предпросмотр событий")
        self.setGeometry(100, 100, 1400, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # ── Controller ──
        self.ctrl = PreviewController(main_controller, self)

        # ── Model / Delegate ──
        self.markers_model = MarkersListModel(self)
        self.markers_delegate = EventCardDelegate(self)
        self.markers_delegate.play_clicked.connect(self._on_card_play)
        self.markers_delegate.edit_clicked.connect(self._on_card_edit)
        self.markers_delegate.delete_clicked.connect(self._on_card_delete)

        self.event_manager = get_custom_event_manager()

        # Флаг для паузы при drag прогресс-бара
        self._was_playing_before_drag: bool = False

        # ── Build UI ──
        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()

        # ── Initial state ──
        self._update_speed_combo()
        self._refresh_marker_list()
        self._update_counter()
        self._update_nav_buttons()
        self._sync_progress_bar()
        self._adjust_window_size()

    # ══════════════════════════════════════════════════════════════════════
    #  UI Setup
    # ══════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ── LEFT: Video + Controls (70%) ──
        left = QVBoxLayout()

        # Video container
        self.video_container = QWidget()
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_container.setMinimumSize(1, 1)
        self.video_container.setStyleSheet("background-color: black; border: 1px solid #555;")

        self.video_label = QLabel(self.video_container)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.drawing_overlay = DrawingOverlay(self.video_container)
        self.drawing_overlay.raise_()

        left.addWidget(self.video_container)

        # Drawing toolbar
        left.addWidget(self._create_drawing_toolbar())

        # YouTube-style progress bar
        self.progress_bar = VideoProgressBar()
        self.progress_bar.seek_requested.connect(self._on_progress_seek)
        self.progress_bar.drag_started.connect(self._on_progress_drag_start)
        self.progress_bar.drag_ended.connect(self._on_progress_drag_end)
        left.addWidget(self.progress_bar)

        # Time label
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setMinimumWidth(100)
        self.time_label.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px; color: #aaaaaa;"
        )

        # Playback controls row
        left.addLayout(self._create_controls_row())

        main_layout.addLayout(left, 7)

        # ── RIGHT: List + Note (30%) ──
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: filters + list
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self._create_filters(top_layout)

        self.markers_list = QListView()
        self.markers_list.setModel(self.markers_model)
        self.markers_list.setItemDelegate(self.markers_delegate)
        self.markers_list.setStyleSheet("""
            QListView { background-color: #2a2a2a; border: 1px solid #444; outline: none; }
            QListView::item { border-bottom: 1px solid #333; padding: 2px; }
            QListView::item:selected { background-color: #1a4d7a; }
        """)
        self.markers_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.markers_list.setSpacing(2)
        top_layout.addWidget(self.markers_list)

        right_splitter.addWidget(top_widget)

        # Bottom: note editor
        note_widget = QWidget()
        note_layout = QVBoxLayout(note_widget)
        note_layout.setContentsMargins(0, 4, 0, 0)

        note_label = QLabel("📝 Заметка:")
        note_label.setStyleSheet("color: #aaa; font-size: 11px;")
        note_layout.addWidget(note_label)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Добавить заметку к сегменту…")
        self.note_edit.textChanged.connect(self._on_note_changed)
        note_layout.addWidget(self.note_edit)

        right_splitter.addWidget(note_widget)
        right_splitter.setStretchFactor(0, 5)
        right_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(right_splitter, 3)
        central.setLayout(main_layout)

    # ──────────────────────────────────────────────────────────────────────
    # Drawing toolbar
    # ──────────────────────────────────────────────────────────────────────

    def _create_drawing_toolbar(self) -> QWidget:
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setSpacing(4)
        layout.setContentsMargins(2, 2, 2, 2)

        self.tool_group = QButtonGroup(self)
        self.tool_group.buttonClicked.connect(self._on_tool_changed)

        tools = [
            (0, "✍", "Выбрать (отключить рисование)"),
            (1, "︳", "Линия"),
            (2, "▭", "Прямоугольник"),
            (3, "◯", "Круг"),
            (4, "➡", "Стрелка"),
        ]
        for tid, icon, tip in tools:
            btn = QPushButton(icon)
            btn.setMaximumWidth(70)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            if tid == 0:
                btn.setChecked(True)
            self.tool_group.addButton(btn, tid)
            layout.addWidget(btn)

        layout.addSpacing(8)

        layout.addWidget(QLabel("Цвет:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["Красный", "Зеленый", "Синий", "Желтый", "Белый"])
        self.color_combo.setMaximumWidth(90)
        self.color_combo.currentTextChanged.connect(self._on_color_changed)
        layout.addWidget(self.color_combo)

        layout.addWidget(QLabel("Толщ:"))
        self.thickness_combo = QComboBox()
        self.thickness_combo.addItems(["1", "2", "3", "4", "5"])
        self.thickness_combo.setCurrentText("2")
        self.thickness_combo.setMaximumWidth(65)
        self.thickness_combo.currentTextChanged.connect(self._on_thickness_changed)
        layout.addWidget(self.thickness_combo)

        layout.addStretch()

        screenshot_btn = QPushButton("📷")
        screenshot_btn.setMaximumWidth(60)
        screenshot_btn.setToolTip("Сохранить скриншот (Ctrl+Shift+S)")
        screenshot_btn.clicked.connect(self._on_screenshot)
        layout.addWidget(screenshot_btn)

        clear_btn = QPushButton("Очистить")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(lambda: self.drawing_overlay.clear_drawing_with_confirmation(self))
        layout.addWidget(clear_btn)

        return toolbar

    # ──────────────────────────────────────────────────────────────────────
    # Controls row
    # ──────────────────────────────────────────────────────────────────────

    def _create_controls_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(3)

        # ◀◀ Prev segment
        self.prev_btn = QPushButton("◀◀")
        self.prev_btn.setFixedWidth(60)
        self.prev_btn.setToolTip("Предыдущий сегмент ( [ )")
        self.prev_btn.clicked.connect(lambda: self.ctrl.previous_segment())
        row.addWidget(self.prev_btn)

        # ◀ Frame back
        self.frame_back_btn = QPushButton("◀")
        self.frame_back_btn.setFixedWidth(52)
        self.frame_back_btn.setToolTip("Кадр назад (←)")
        self.frame_back_btn.clicked.connect(lambda: self.ctrl.step_frame(-1))
        row.addWidget(self.frame_back_btn)

        # ▶ Play/Pause
        self.play_btn = QPushButton("▶ Воспр.")
        self.play_btn.setFixedWidth(100)
        self.play_btn.setToolTip("Воспроизведение/Пауза (Space)")
        self.play_btn.clicked.connect(lambda: self.ctrl.toggle_play_pause())
        row.addWidget(self.play_btn)

        # ▶ Frame forward
        self.frame_fwd_btn = QPushButton("▶")
        self.frame_fwd_btn.setFixedWidth(52)
        self.frame_fwd_btn.setToolTip("Кадр вперёд (→)")
        self.frame_fwd_btn.clicked.connect(lambda: self.ctrl.step_frame(1))
        row.addWidget(self.frame_fwd_btn)

        # ▶▶ Next segment
        self.next_btn = QPushButton("▶▶")
        self.next_btn.setFixedWidth(60)
        self.next_btn.setToolTip("Следующий сегмент ( ] )")
        self.next_btn.clicked.connect(lambda: self.ctrl.next_segment())
        row.addWidget(self.next_btn)

        row.addSpacing(8)

        # 🔁 Loop
        self.loop_btn = QPushButton("🔁")
        self.loop_btn.setFixedWidth(56)
        self.loop_btn.setCheckable(True)
        self.loop_btn.setChecked(True)
        self.loop_btn.setToolTip("Зацикленное воспроизведение (R)")
        self.loop_btn.clicked.connect(lambda: self.ctrl.toggle_loop())
        self._update_loop_style(True)
        row.addWidget(self.loop_btn)

        row.addSpacing(8)

        # Time label
        row.addWidget(self.time_label)

        row.addSpacing(8)

        # Speed
        row.addWidget(QLabel("Скорость:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems([
            "0.25x", "0.5x", "0.75x", "1.0x",
            "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"
        ])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setMaximumWidth(70)
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        row.addWidget(self.speed_combo)

        row.addStretch()

        # Counter label
        self.counter_label = QLabel("0 / 0")
        self.counter_label.setStyleSheet(
            "color: #88ccff; font-weight: bold; font-size: 12px;"
        )
        self.counter_label.setMinimumWidth(120)
        row.addWidget(self.counter_label)

        return row

    # ──────────────────────────────────────────────────────────────────────
    # Filters
    # ──────────────────────────────────────────────────────────────────────

    def _create_filters(self, parent_layout):
        layout = QVBoxLayout()
        layout.setSpacing(3)

        row1 = QHBoxLayout()
        row1.setSpacing(4)

        row1.addWidget(QLabel("Тип:"))
        self.event_filter_combo = QComboBox()
        self.event_filter_combo.setMaximumWidth(110)
        self.event_filter_combo.currentIndexChanged.connect(self._on_event_filter_changed)
        row1.addWidget(self.event_filter_combo)

        self.notes_filter_check = QCheckBox("Заметки")
        self.notes_filter_check.stateChanged.connect(
            lambda: self.ctrl.set_notes_filter(self.notes_filter_check.isChecked())
        )
        row1.addWidget(self.notes_filter_check)

        reset_btn = QPushButton("Сброс")
        reset_btn.setMaximumWidth(75)
        reset_btn.clicked.connect(self._on_reset_filters)
        row1.addWidget(reset_btn)

        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск в заметках...")
        self.search_edit.setMaximumWidth(140)
        self.search_edit.textChanged.connect(lambda t: self.ctrl.set_notes_search(t))
        row2.addWidget(self.search_edit)
        row2.addStretch()
        layout.addLayout(row2)

        parent_layout.addLayout(layout)
        self._populate_event_filter()

    def _populate_event_filter(self):
        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.clear()
        self.event_filter_combo.addItem("Все", None)
        for ev in self.event_manager.get_all_events():
            self.event_filter_combo.addItem(ev.get_localized_name(), ev.name)
        self.event_filter_combo.blockSignals(False)

    # ══════════════════════════════════════════════════════════════════════
    #  Signal Connections
    # ══════════════════════════════════════════════════════════════════════

    def _connect_signals(self):
        c = self.ctrl

        c.playback_state_changed.connect(self._on_playback_state)
        c.playback_position_changed.connect(self._on_position_changed)
        c.active_segment_changed.connect(self._on_segment_changed)
        c.segment_counter_changed.connect(self._on_counter_changed)
        c.loop_state_changed.connect(self._on_loop_state)
        c.filters_changed.connect(self._refresh_marker_list)

        try:
            self.main_controller.playback_controller.pixmap_changed.connect(
                self._on_pixmap_changed
            )
        except Exception:
            pass

        try:
            self.main_controller.timeline_controller.markers_changed.connect(
                self._refresh_marker_list
            )
        except Exception:
            pass

        self.event_manager.events_changed.connect(self._populate_event_filter)

    # ══════════════════════════════════════════════════════════════════════
    #  Shortcuts
    # ══════════════════════════════════════════════════════════════════════

    def _setup_shortcuts(self):
        shortcuts = {
            "Space": lambda: self.ctrl.toggle_play_pause(),
            "Left": lambda: self.ctrl.step_frame(-1),
            "Right": lambda: self.ctrl.step_frame(1),
            "Shift+Left": lambda: self.ctrl.step_frame(-10),
            "Shift+Right": lambda: self.ctrl.step_frame(10),
            "[": lambda: self.ctrl.previous_segment(),
            "]": lambda: self.ctrl.next_segment(),
            "R": lambda: self.ctrl.toggle_loop(),
            "I": lambda: self.ctrl.set_in_point(),
            "O": lambda: self.ctrl.set_out_point(),
            "Delete": self._on_delete_current,
            "Ctrl+Z": lambda: self.drawing_overlay.undo(),
            "Ctrl+X": lambda: self.drawing_overlay.clear_drawing_with_confirmation(self),
            "Ctrl+Shift+S": self._on_screenshot,
        }
        for key, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)

    # ══════════════════════════════════════════════════════════════════════
    #  Controller Signal Handlers
    # ══════════════════════════════════════════════════════════════════════

    def _on_playback_state(self, playing: bool):
        self.play_btn.setText("⏸ Пауза" if playing else "▶ Воспр.")

    def _on_position_changed(self, frame: int):
        self._update_progress_bar_position()
        self._update_time()

    def _on_segment_changed(self, marker_idx: int):
        row = self.markers_model.find_row_by_marker_idx(marker_idx)
        if row >= 0:
            index = self.markers_model.index(row, 0)
            self.markers_list.setCurrentIndex(index)
            self.markers_list.scrollTo(index)

        marker = self.ctrl.get_current_marker()
        self.note_edit.blockSignals(True)
        self.note_edit.setText(marker.note if marker else "")
        self.note_edit.blockSignals(False)

        self._sync_progress_bar()
        self._update_nav_buttons()

    def _on_counter_changed(self, text: str):
        self.counter_label.setText(text)

    def _on_loop_state(self, enabled: bool):
        self.loop_btn.setChecked(enabled)
        self._update_loop_style(enabled)

    def _update_loop_style(self, enabled: bool):
        if enabled:
            self.loop_btn.setStyleSheet(
                "QPushButton { background-color: #1a4d7a; border: 1px solid #4488bb; border-radius: 4px; }"
            )
        else:
            self.loop_btn.setStyleSheet(
                "QPushButton { background-color: #333; border: 1px solid #555; border-radius: 4px; }"
            )

    # ══════════════════════════════════════════════════════════════════════
    #  Progress Bar (YouTube-style)
    # ══════════════════════════════════════════════════════════════════════

    def _sync_progress_bar(self) -> None:
        """Синхронизировать прогресс-бар с текущим сегментом."""
        marker = self.ctrl.get_current_marker()
        if not marker:
            self.progress_bar.set_total_frames(0)
            return

        segment_length = marker.end_frame - marker.start_frame
        self.progress_bar.set_total_frames(segment_length)
        self.progress_bar.set_fps(self.ctrl.fps)

        current_in_segment = self.ctrl.current_frame - marker.start_frame
        self.progress_bar.set_current_frame(max(0, current_in_segment))

    def _update_progress_bar_position(self) -> None:
        """Обновить позицию прогресс-бара при воспроизведении."""
        marker = self.ctrl.get_current_marker()
        if not marker:
            return
        current_in_segment = self.ctrl.current_frame - marker.start_frame
        self.progress_bar.set_current_frame(max(0, current_in_segment))

    def _on_progress_seek(self, frame_in_segment: int) -> None:
        """Клик/drag на прогресс-баре → seek внутри сегмента."""
        marker = self.ctrl.get_current_marker()
        if not marker:
            return
        absolute_frame = marker.start_frame + frame_in_segment
        absolute_frame = max(marker.start_frame, min(absolute_frame, marker.end_frame - 1))
        self.ctrl.seek_to_frame_in_segment(absolute_frame)

    def _on_progress_drag_start(self) -> None:
        """Пауза при начале перетаскивания."""
        self._was_playing_before_drag = self.ctrl.is_playing
        if self.ctrl.is_playing:
            self.ctrl.pause()

    def _on_progress_drag_end(self) -> None:
        """Возобновление после перетаскивания."""
        if self._was_playing_before_drag:
            self.ctrl.play()

    # ══════════════════════════════════════════════════════════════════════
    #  UI Update Helpers
    # ══════════════════════════════════════════════════════════════════════

    def _update_time(self):
        self.time_label.setText(self.ctrl.get_time_text())

    def _update_counter(self):
        self.counter_label.setText(self.ctrl.get_counter_text())

    def _update_nav_buttons(self):
        self.prev_btn.setEnabled(self.ctrl.has_prev())
        self.next_btn.setEnabled(self.ctrl.has_next())

    def _update_speed_combo(self):
        speed = self.ctrl.get_speed()
        text = f"{speed:.2f}x"
        items = [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]
        if text in items:
            self.speed_combo.blockSignals(True)
            self.speed_combo.setCurrentText(text)
            self.speed_combo.blockSignals(False)

    def _refresh_marker_list(self):
        filtered = self.ctrl.get_filtered_markers()
        self.markers_model.set_fps(self.ctrl.fps)
        self.markers_model.set_filtered_segments(filtered)

        row = self.markers_model.find_row_by_marker_idx(self.ctrl.current_marker_idx)
        if row >= 0:
            self.markers_list.setCurrentIndex(self.markers_model.index(row, 0))

        self._update_counter()
        self._update_nav_buttons()
        self._sync_progress_bar()

    # ══════════════════════════════════════════════════════════════════════
    #  User Action Handlers
    # ══════════════════════════════════════════════════════════════════════

    def _on_speed_changed(self, text: str):
        try:
            speed = float(text.replace("x", ""))
            self.ctrl.set_speed(speed)
        except ValueError:
            pass

    def _on_event_filter_changed(self, index: int):
        data = self.event_filter_combo.currentData()
        if data is None:
            self.ctrl.set_event_type_filter(set())
        else:
            self.ctrl.set_event_type_filter({data})

    def _on_reset_filters(self):
        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.setCurrentIndex(0)
        self.event_filter_combo.blockSignals(False)
        self.notes_filter_check.setChecked(False)
        self.search_edit.clear()
        self.ctrl.reset_filters()

    def _on_note_changed(self, text: str):
        self.ctrl.update_note(text)

    def _on_delete_current(self):
        marker = self.ctrl.get_current_marker()
        if not marker:
            return
        self.ctrl.delete_marker(self.ctrl.current_marker_idx)
        self._refresh_marker_list()

    # ── Card actions ──

    def _on_card_play(self, marker_idx: int):
        self.ctrl.set_current_segment(marker_idx)
        if not self.ctrl.is_playing:
            self.ctrl.play()

    def _on_card_edit(self, marker_idx: int):
        self.ctrl.open_segment_editor(marker_idx)

    def _on_card_delete(self, marker_idx: int):
        self.ctrl.delete_marker(marker_idx)
        self._refresh_marker_list()

    # ── Drawing tools ──

    def _on_tool_changed(self, button):
        tid = self.tool_group.id(button)
        tool_map = {0: "none", 1: "line", 2: "rectangle", 3: "circle", 4: "arrow"}
        tool = tool_map.get(tid, "none")
        self.drawing_overlay.set_tool(tool)

        if tid > 0 and self.ctrl.is_playing:
            self.ctrl.pause()

    def _on_color_changed(self, text: str):
        colors = {
            "Красный": "#FF0000", "Зеленый": "#00FF00", "Синий": "#0000FF",
            "Желтый": "#FFFF00", "Белый": "#FFFFFF",
        }
        self.drawing_overlay.set_color(QColor(colors.get(text, "#FF0000")))

    def _on_thickness_changed(self, text: str):
        try:
            self.drawing_overlay.set_thickness(int(text))
        except ValueError:
            pass

    # ── Screenshot ──

    def _on_screenshot(self):
        suggested = self.ctrl.get_screenshot_filename()
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить скриншот", suggested,
            "Изображения PNG (*.png);;Все файлы (*)"
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"

        success = self.ctrl.take_screenshot(self.drawing_overlay, path)
        if success:
            QMessageBox.information(self, "Скриншот", f"Сохранён: {path}")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить скриншот.")

    # ══════════════════════════════════════════════════════════════════════
    #  Display
    # ══════════════════════════════════════════════════════════════════════

    def _on_pixmap_changed(self, pixmap: QPixmap, frame_idx: int):
        if frame_idx != self.main_controller.playback_controller.current_frame:
            return
        self._display_pixmap(pixmap)

    def _display_pixmap(self, pixmap: QPixmap):
        if pixmap is None or pixmap.isNull():
            return

        target = self.video_container.size()
        scaled = pixmap.scaled(
            target, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled)

        cw, ch = self.video_container.width(), self.video_container.height()
        pw, ph = scaled.width(), scaled.height()
        x, y = (cw - pw) // 2, (ch - ph) // 2

        self.video_label.setGeometry(x, y, pw, ph)
        self.drawing_overlay.setGeometry(x, y, pw, ph)

    def _display_current_frame(self):
        frame_idx = self.main_controller.playback_controller.current_frame
        pixmap = None
        if hasattr(self.main_controller.playback_controller, "get_cached_pixmap"):
            pixmap = self.main_controller.playback_controller.get_cached_pixmap(frame_idx)
        if pixmap is not None:
            self._display_pixmap(pixmap)
        else:
            try:
                self.main_controller.playback_controller.seek_to_frame_immediate(frame_idx)
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════
    #  Window Events
    # ══════════════════════════════════════════════════════════════════════

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._display_current_frame)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._display_current_frame()

    def closeEvent(self, event):
        self.ctrl.cleanup()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit)):
            super().keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def _adjust_window_size(self):
        try:
            vw = self.main_controller.get_video_width()
            vh = self.main_controller.get_video_height()
            if vw <= 0 or vh <= 0:
                return

            aspect = vw / vh
            test_w = 1200
            video_w = int(test_w * 0.7)
            video_h = int(video_w / aspect)
            final_h = video_h + 180

            screen = QApplication.primaryScreen().size()
            final_w = min(test_w, int(screen.width() * 0.9))
            final_h = min(final_h, int(screen.height() * 0.9))
            self.resize(final_w, final_h)

            geo = QApplication.primaryScreen().geometry()
            self.move(geo.center().x() - final_w // 2, geo.center().y() - final_h // 2)
        except Exception:
            pass