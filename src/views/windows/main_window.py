from __future__ import annotations

from pathlib import Path
from typing import Optional, Set, TYPE_CHECKING

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QComboBox, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtGui import QPixmap, QKeyEvent, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, Signal

from views.widgets.player_controls import PlayerControls
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline import TimelineWidget
from views.styles import get_application_stylesheet
from views.widgets.event_shortcut_list_widget import EventShortcutListWidget

from services.serialization.settings_manager import get_settings_manager
from services.events.custom_event_manager import get_custom_event_manager

if TYPE_CHECKING:
    from controllers.filter_controller import FilterController
    from controllers.timeline_controller import TimelineController


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    # Menu actions
    open_video_triggered = Signal()
    save_project_triggered = Signal()
    load_project_triggered = Signal()
    new_project_triggered = Signal()
    open_settings_triggered = Signal()
    export_triggered = Signal()
    open_preview_triggered = Signal()

    # Keyboard
    key_pressed = Signal(str)
    video_dropped = Signal(str)

    # Close lifecycle
    window_closing = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.settings_manager = get_settings_manager()
        self.event_manager = get_custom_event_manager()
        self.event_manager.setParent(self)

        self.main_controller = None
        self.filter_controller: Optional["FilterController"] = None
        self._timeline_controller: Optional["TimelineController"] = None

        # UI state
        self.event_filter_combo: Optional[QComboBox] = None
        self.notes_filter_checkbox: Optional[QCheckBox] = None

        self.setWindowTitle("Хоккейный Редактор")
        self.setGeometry(0, 0, 1800, 1000)

        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)

        self.setStyleSheet(get_application_stylesheet())

        self._create_menu()
        self._setup_ui()

        self._populate_event_filter_combo()
        self.event_manager.events_changed.connect(self._populate_event_filter_combo)

    # ──────────────────────────────────────────────────────────────────────────
    # UI building
    # ──────────────────────────────────────────────────────────────────────────

    def _create_menu(self) -> None:
        menubar = self.menuBar()
        menubar.clear()

        file_menu = menubar.addMenu("Файл")

        action_new = file_menu.addAction("Новый проект")
        action_new.setShortcut("Ctrl+N")
        action_new.triggered.connect(self.new_project_triggered.emit)

        action_open_project = file_menu.addAction("Открыть проект")
        action_open_project.setShortcut("Ctrl+O")
        action_open_project.triggered.connect(self.load_project_triggered.emit)

        action_open_video = file_menu.addAction("Открыть видео")
        action_open_video.triggered.connect(self.open_video_triggered.emit)

        action_save = file_menu.addAction("Сохранить проект")
        action_save.setShortcut("Ctrl+S")
        action_save.triggered.connect(self.save_project_triggered.emit)

        file_menu.addSeparator()

        action_exit = file_menu.addAction("Выход")
        action_exit.triggered.connect(self.close)

        action_preview = menubar.addAction("Предпросмотр")
        action_preview.setShortcut("Ctrl+P")
        action_preview.triggered.connect(self.open_preview_triggered.emit)

        action_settings = menubar.addAction("Настройки")
        action_settings.setShortcut("Ctrl+,")
        action_settings.triggered.connect(self.open_settings_triggered.emit)

        action_export = menubar.addAction("Экспорт")
        action_export.setShortcut("Ctrl+E")
        action_export.triggered.connect(self.export_triggered.emit)

        help_menu = menubar.addMenu("Справка")
        action_about = help_menu.addAction("О программе")
        action_about.triggered.connect(
            lambda: QMessageBox.about(self, "О программе", "Hockey Editor Pro")
        )

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #333333; border: 1px solid #555555; }
            QSplitter::handle:hover { background-color: #444444; }
        """)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #333333; border: 1px solid #555555; }
            QSplitter::handle:hover { background-color: #444444; }
        """)

        # Video container
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)

        from views.widgets.scalable_video_label import ScalableVideoLabel
        self.video_label = ScalableVideoLabel()
        self.video_label.setMinimumSize(320, 180)
        self.video_label.setStyleSheet("background-color: black;")
        video_layout.addWidget(self.video_label, 1)

        self.player_controls = PlayerControls()
        video_layout.addWidget(self.player_controls, 0, Qt.AlignBottom)

        self.top_splitter.addWidget(video_container)

        # Segment list container
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.addWidget(QLabel("Отрезки:"))

        self._setup_filters(list_layout)

        self.segment_list_widget = SegmentListWidget()
        list_layout.addWidget(self.segment_list_widget)

        self.top_splitter.addWidget(list_container)
        self.top_splitter.setSizes([600, 400])

        self.main_splitter.addWidget(self.top_splitter)

        # Timeline container
        self.timeline_container = QWidget()
        tl_layout = QVBoxLayout(self.timeline_container)
        tl_layout.setContentsMargins(0, 0, 0, 0)
        tl_layout.addWidget(QLabel("Таймлайн:"))

        self.timeline_widget: Optional[TimelineWidget] = None

        self.main_splitter.addWidget(self.timeline_container)
        self.main_splitter.setSizes([630, 270])

        main_layout.addWidget(self.main_splitter)

        # Bottom row
        bottom_layout = QHBoxLayout()

        self.event_shortcut_list_widget = EventShortcutListWidget()
        bottom_layout.addWidget(self.event_shortcut_list_widget)
        bottom_layout.addStretch()

        self.status_label = QLabel("Готов")
        self.status_label.setStyleSheet("color: #ffcc00;")
        self.status_label.setMinimumWidth(400)
        self.status_label.setFixedHeight(22)
        bottom_layout.addWidget(self.status_label)

        self.mode_indicator = QLabel("Режим: Фиксированная длина")
        self.mode_indicator.setStyleSheet("color: #00ccff; font-weight: bold;")
        self.mode_indicator.setMinimumWidth(250)
        self.mode_indicator.setFixedHeight(22)
        bottom_layout.addWidget(self.mode_indicator)

        main_layout.addLayout(bottom_layout)

    # ──────────────────────────────────────────────────────────────────────────
    # MVC integration
    # ──────────────────────────────────────────────────────────────────────────

    def set_controller(self, controller) -> None:
        self.main_controller = controller
        self.filter_controller = controller.filter_controller

        self.filter_controller.filters_changed.connect(self._on_filters_changed)

        if hasattr(self.segment_list_widget, "set_filter_controller"):
            self.segment_list_widget.set_filter_controller(self.filter_controller)

        self._on_filters_changed()

    def set_timeline_controller(self, controller) -> None:
        self._timeline_controller = controller

        self.timeline_widget = TimelineWidget(controller) if self._ctor_accepts_controller() else TimelineWidget()
        if hasattr(self.timeline_widget, "set_controller"):
            self.timeline_widget.set_controller(controller)

        layout = self.timeline_container.layout()
        layout.addWidget(self.timeline_widget)

        if hasattr(controller, "set_main_window"):
            controller.set_main_window(self)

    def _ctor_accepts_controller(self) -> bool:
        try:
            TimelineWidget.__init__.__code__.co_argcount
            return True
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Filters UI
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_filters(self, parent_layout: QVBoxLayout) -> None:
        filters_layout = QVBoxLayout()
        filters_layout.setSpacing(3)

        row = QHBoxLayout()
        row.setSpacing(5)

        event_label = QLabel("Тип:")
        event_label.setMaximumWidth(25)
        row.addWidget(event_label)

        self.event_filter_combo = QComboBox()
        self.event_filter_combo.setToolTip("Фильтр по типу события")
        self.event_filter_combo.setMaximumWidth(140)
        self.event_filter_combo.currentIndexChanged.connect(self._on_event_filter_changed)
        row.addWidget(self.event_filter_combo)

        self.notes_filter_checkbox = QCheckBox("Заметки")
        self.notes_filter_checkbox.setToolTip("Показывать только отрезки с заметками")
        self.notes_filter_checkbox.stateChanged.connect(self._on_notes_filter_changed)
        row.addWidget(self.notes_filter_checkbox)

        reset_btn = QPushButton("Сброс")
        reset_btn.setMaximumWidth(80)
        reset_btn.clicked.connect(self._on_reset_filters)
        row.addWidget(reset_btn)

        filters_layout.addLayout(row)
        parent_layout.addLayout(filters_layout)

    def _populate_event_filter_combo(self) -> None:
        if not self.event_filter_combo:
            return

        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.clear()
        self.event_filter_combo.addItem("Все", None)

        for event in self.event_manager.get_all_events():
            self.event_filter_combo.addItem(event.get_localized_name(), event.name)

        self.event_filter_combo.blockSignals(False)

    def _on_event_filter_changed(self, index: int = 0) -> None:
        if not self.filter_controller:
            return
        data = self.event_filter_combo.currentData()
        self.filter_controller.set_event_type_filter(set() if data is None else {data})

    def _on_notes_filter_changed(self) -> None:
        if not self.filter_controller:
            return
        self.filter_controller.set_notes_filter(self.notes_filter_checkbox.isChecked())

    def _on_reset_filters(self) -> None:
        if self.filter_controller:
            self.filter_controller.reset_all_filters()

    def _on_filters_changed(self) -> None:
        self._sync_filter_ui_with_controller()
        self._update_segment_list_with_filters()

    def _sync_filter_ui_with_controller(self) -> None:
        if not self.filter_controller:
            return

        self.event_filter_combo.blockSignals(True)
        try:
            active = self.filter_controller.filter_event_types
            if not active:
                self.event_filter_combo.setCurrentIndex(0)
            else:
                target = next(iter(active))
                for i in range(self.event_filter_combo.count()):
                    if self.event_filter_combo.itemData(i) == target:
                        self.event_filter_combo.setCurrentIndex(i)
                        break
        finally:
            self.event_filter_combo.blockSignals(False)

        self.notes_filter_checkbox.blockSignals(True)
        try:
            self.notes_filter_checkbox.setChecked(self.filter_controller.filter_has_notes)
        finally:
            self.notes_filter_checkbox.blockSignals(False)

    def _update_segment_list_with_filters(self) -> None:
        if not self.filter_controller or not self._timeline_controller:
            return

        all_markers = self._timeline_controller.markers
        segments_with_idx = self.filter_controller.filter_markers(all_markers)
        self.segment_list_widget.set_segments(segments_with_idx)

    # ──────────────────────────────────────────────────────────────────────────
    # Keyboard / Drag&Drop
    # ──────────────────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return

        key = event.key()
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            self.key_pressed.emit(chr(key).upper())
            return

        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        file_path = urls[0].toLocalFile()
        if file_path.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv")):
            self.video_dropped.emit(file_path)

    # ──────────────────────────────────────────────────────────────────────────
    # Public helpers
    # ──────────────────────────────────────────────────────────────────────────

    def set_video_image(self, pixmap: QPixmap) -> None:
        self.video_label.setPixmap(pixmap)

    def get_player_controls(self) -> PlayerControls:
        return self.player_controls

    def get_segment_list_widget(self) -> SegmentListWidget:
        return self.segment_list_widget

    def get_timeline_widget(self) -> Optional[TimelineWidget]:
        return self.timeline_widget

    def set_window_title(self, title: str) -> None:
        self.setWindowTitle(f"Hockey Editor - {title}" if title else "Hockey Editor")

    def update_mode_indicator(self, recording_mode: str, fixed_duration: int, pre_roll: float, post_roll: float) -> None:
        if recording_mode == "fixed_length":
            mode_text = "Режим: Фиксированная длина"
            params_text = f"Длительность: {fixed_duration}с | Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
        else:
            mode_text = "Режим: Динамический"
            params_text = f"Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
        self.mode_indicator.setText(f"{mode_text} | {params_text}")

    def open_segment_editor(self, marker_idx: int) -> None:
        """Открыть редактор сегмента — делегирует main_controller."""
        if self.main_controller and hasattr(self.main_controller, 'open_segment_editor'):
            self.main_controller.open_segment_editor(marker_idx)

    # ──────────────────────────────────────────────────────────────────────────
    # Close event
    # ──────────────────────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        self.window_closing.emit(event)
        if event.isAccepted():
            super().closeEvent(event)