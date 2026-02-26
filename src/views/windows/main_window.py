# src/views/windows/main_window.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Set, TYPE_CHECKING

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QComboBox, QCheckBox, QPushButton, QMessageBox, QFrame, QTabWidget
)
from PySide6.QtGui import QPixmap, QKeyEvent, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, Signal

from views.widgets.player_controls import PlayerControls
from views.widgets.segment_list import SegmentListWidget
from views.widgets.stats_widget import StatsWidget
from views.widgets.timeline import TimelineWidget
from views.styles import get_application_stylesheet
from views.widgets.event_shortcut_list_widget import EventShortcutListWidget
from views.widgets.toast_notification import get_toast_manager, ToastManager
from views.widgets.history_panel import HistoryPanel
from views.widgets.video_progress_bar import VideoProgressBar

from services.serialization.settings_manager import get_settings_manager
from services.events.custom_event_manager import get_custom_event_manager
from services.history.history_manager import get_history_manager, HistoryManager
from services.autosave.autosave_service import AutoSaveService

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

        self.history_manager: HistoryManager = get_history_manager()
        self._toast: Optional[ToastManager] = None
        self._autosave: Optional[AutoSaveService] = None

        self.main_controller = None
        self.filter_controller: Optional["FilterController"] = None
        self._timeline_controller: Optional["TimelineController"] = None

        # UI state
        self.event_filter_combo: Optional[QComboBox] = None
        self.notes_filter_checkbox: Optional[QCheckBox] = None
        self._filter_indicator: Optional[QLabel] = None
        self._filter_reset_btn: Optional[QPushButton] = None
        self._segments_header_label: Optional[QLabel] = None
        self._stats_widget: Optional[StatsWidget] = None
        self._history_panel: Optional[HistoryPanel] = None
        self._right_tabs: Optional[QTabWidget] = None

        self.setWindowTitle("Хоккейный Редактор")
        self.setGeometry(0, 0, 1800, 1000)

        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)

        self.setStyleSheet(get_application_stylesheet())

        # ── Иконка окна ──
        self._set_window_icon()

        self._create_menu()
        self._setup_ui()

        self._populate_event_filter_combo()
        self.event_manager.events_changed.connect(self._populate_event_filter_combo)

        # Toast-уведомления для undo/redo
        self.history_manager.command_undone.connect(
            lambda desc: self.toast.info(f"↩ Отмена: {desc}", duration_ms=2000)
        )
        self.history_manager.command_redone.connect(
            lambda desc: self.toast.info(f"↪ Повтор: {desc}", duration_ms=2000)
        )

        # Dirty tracking
        self.history_manager.state_changed.connect(self._on_history_changed)

        # Авто-сохранение
        self._init_autosave()

        # Восстановить геометрию окна
        self._restore_window_geometry()

    # ──────────────────────────────────────────────────────────────────────────
    # Toast manager (lazy property)
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def toast(self) -> ToastManager:
        if self._toast is None:
            self._toast = get_toast_manager(self)
        return self._toast

    # ──────────────────────────────────────────────────────────────────────────
    # Auto-save
    # ──────────────────────────────────────────────────────────────────────────

    def _init_autosave(self) -> None:
        settings = self.settings_manager.load_autosave_settings()

        self._autosave = AutoSaveService(
            interval_ms=settings["interval_minutes"] * 60 * 1000,
            max_backups=settings["max_backups"],
            parent=self,
        )
        self._autosave.enabled = settings["enabled"]

        self._autosave.auto_saved.connect(
            lambda path: self.toast.success(
                "Авто-сохранение выполнено", duration_ms=2000
            )
        )
        self._autosave.auto_save_failed.connect(
            lambda err: self.toast.error(f"Ошибка авто-сохранения: {err}")
        )

        if settings["enabled"]:
            self._autosave.start()

    def set_autosave_callback(self, callback) -> None:
        if self._autosave:
            self._autosave.set_save_callback(callback)

    def set_autosave_project_dir(self, directory: str) -> None:
        if self._autosave:
            self._autosave.project_dir = directory

    def _on_history_changed(self) -> None:
        if self._autosave:
            self._autosave.mark_dirty()
        self._update_title_modified_indicator()

    def _update_title_modified_indicator(self) -> None:
        title = self.windowTitle()
        has_star = title.startswith("* ")
        if self.history_manager.is_modified and not has_star:
            self.setWindowTitle(f"* {title}")
        elif not self.history_manager.is_modified and has_star:
            self.setWindowTitle(title[2:])

    # ──────────────────────────────────────────────────────────────────────────
    # Window geometry persistence
    # ──────────────────────────────────────────────────────────────────────────

    def _save_window_geometry(self) -> None:
        geo = self.geometry()
        data = {
            "x": geo.x(),
            "y": geo.y(),
            "width": geo.width(),
            "height": geo.height(),
            "maximized": self.isMaximized(),
            "main_splitter": self.main_splitter.sizes(),
            "top_splitter": self.top_splitter.sizes(),
            "active_tab": self._right_tabs.currentIndex() if self._right_tabs else 0,
        }
        self.settings_manager.save_window_geometry(data)

    def _restore_window_geometry(self) -> None:
        data = self.settings_manager.load_window_geometry()
        if not data:
            return
        try:
            if data.get("maximized"):
                self.showMaximized()
            else:
                self.setGeometry(
                    data.get("x", 0),
                    data.get("y", 0),
                    data.get("width", 1800),
                    data.get("height", 1000),
                )
            if "main_splitter" in data:
                self.main_splitter.setSizes(data["main_splitter"])
            if "top_splitter" in data:
                self.top_splitter.setSizes(data["top_splitter"])
            if "active_tab" in data and self._right_tabs:
                tab_idx = data["active_tab"]
                if 0 <= tab_idx < self._right_tabs.count():
                    self._right_tabs.setCurrentIndex(tab_idx)
        except Exception as e:
            print(f"Error restoring window geometry: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # UI building
    # ──────────────────────────────────────────────────────────────────────────

    def _set_window_icon(self) -> None:
        """Установить иконку окна из ассетов."""
        import os
        from PySide6.QtGui import QIcon

        # Попробовать загрузить из файла
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base, '..', '..', '..', 'assets', 'icons', 'app_icon.png'),
            os.path.join(base, '..', '..', '..', 'assets', 'icons', 'app_icon.ico'),
        ]
        for path in candidates:
            abs_path = os.path.normpath(path)
            if os.path.exists(abs_path):
                self.setWindowIcon(QIcon(abs_path))
                return

        # Fallback: из QApplication (установлена в main.py)
        app = QApplication.instance()
        if app and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())

    def _create_menu(self) -> None:
        menubar = self.menuBar()
        menubar.clear()

        # ── Файл ──
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

        # ── Редактирование (Undo/Redo) ──
        edit_menu = menubar.addMenu("Редактирование")

        self._action_undo = edit_menu.addAction("↩ Отменить")
        self._action_undo.setShortcut("Ctrl+Z")
        self._action_undo.triggered.connect(self._on_undo)
        self._action_undo.setEnabled(False)

        self._action_redo = edit_menu.addAction("↪ Повторить")
        self._action_redo.setShortcut("Ctrl+Y")
        self._action_redo.triggered.connect(self._on_redo)
        self._action_redo.setEnabled(False)

        edit_menu.addSeparator()

        action_clear_history = edit_menu.addAction("Очистить историю")
        action_clear_history.triggered.connect(self._on_clear_history)

        self.history_manager.state_changed.connect(self._update_undo_redo_menu)

        # ── Остальное ──
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

        # ── Video container ──
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)

        from views.widgets.scalable_video_label import ScalableVideoLabel
        self.video_label = ScalableVideoLabel()
        self.video_label.setMinimumSize(320, 180)
        self.video_label.setStyleSheet("background-color: black;")
        video_layout.addWidget(self.video_label, 1)

        self.tracking_overlay = None
        try:
            from views.widgets.tracking_overlay import TrackingOverlay
            self.tracking_overlay = TrackingOverlay(self.video_label)
            self.tracking_overlay.setGeometry(self.video_label.rect())
        except ImportError:
            pass

        # ── YouTube-style progress bar ──
        self.video_progress_bar = VideoProgressBar()
        video_layout.addWidget(self.video_progress_bar, 0)

        self.player_controls = PlayerControls()
        video_layout.addWidget(self.player_controls, 0, Qt.AlignBottom)

        self.top_splitter.addWidget(video_container)

        # ══════════════════════════════════════════════════════════════════════
        # CHANGED: Правая панель — QTabWidget вместо вертикального стека
        # ══════════════════════════════════════════════════════════════════════

        self._right_tabs = QTabWidget()
        self._right_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444444;
                background-color: #2a2a2a;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #aaaaaa;
                border: 1px solid #444444;
                border-bottom: none;
                padding: 6px 14px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #2a2a2a;
                color: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #333333;
                color: #ffffff;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
        """)

        # ── Tab 0: Маркеры ──
        markers_tab = QWidget()
        markers_layout = QVBoxLayout(markers_tab)
        markers_layout.setContentsMargins(4, 4, 4, 4)
        markers_layout.setSpacing(2)

        self._segments_header_label = QLabel("Отрезки:")
        self._segments_header_label.setStyleSheet(
            "color: #ffffff; font-weight: bold; font-size: 12px;"
        )
        markers_layout.addWidget(self._segments_header_label)

        self._setup_filters(markers_layout)

        self.segment_list_widget = SegmentListWidget()
        markers_layout.addWidget(self.segment_list_widget, 1)

        self._right_tabs.addTab(markers_tab, "📋 Маркеры")

        # ── Tab 1: Статистика ──
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.setContentsMargins(4, 4, 4, 4)
        stats_layout.setSpacing(0)

        self._stats_widget = StatsWidget()
        stats_layout.addWidget(self._stats_widget, 1)

        self._right_tabs.addTab(stats_tab, "📊 Статистика")

        # ── Tab 2: История ──
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(4, 4, 4, 4)
        history_layout.setSpacing(0)

        self._history_panel = HistoryPanel(self.history_manager)
        history_layout.addWidget(self._history_panel, 1)

        self._right_tabs.addTab(history_tab, "📜 История")

        self.top_splitter.addWidget(self._right_tabs)
        self.top_splitter.setSizes([600, 400])

        self.main_splitter.addWidget(self.top_splitter)

        # ── Timeline container ──
        self.timeline_container = QWidget()
        tl_layout = QVBoxLayout(self.timeline_container)
        tl_layout.setContentsMargins(0, 0, 0, 0)
        tl_layout.addWidget(QLabel("Таймлайн:"))

        self.timeline_widget: Optional[TimelineWidget] = None

        self.main_splitter.addWidget(self.timeline_container)
        self.main_splitter.setSizes([630, 270])

        main_layout.addWidget(self.main_splitter)

        # ── Bottom row ──
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
    # Undo / Redo / Clear actions
    # ──────────────────────────────────────────────────────────────────────────

    def _on_undo(self) -> None:
        if self._timeline_controller:
            self._timeline_controller.undo()
        elif self.history_manager.can_undo:
            self.history_manager.undo()
        else:
            self.toast.warning("Нечего отменять")

    def _on_redo(self) -> None:
        if self._timeline_controller:
            self._timeline_controller.redo()
        elif self.history_manager.can_redo:
            self.history_manager.redo()
        else:
            self.toast.warning("Нечего повторять")

    def _on_clear_history(self) -> None:
        self.history_manager.clear()
        self.toast.info("История очищена")

    def _update_undo_redo_menu(self) -> None:
        self._action_undo.setEnabled(self.history_manager.can_undo)
        self._action_redo.setEnabled(self.history_manager.can_redo)

        if self.history_manager.can_undo:
            self._action_undo.setText(f"↩ Отменить: {self.history_manager.undo_text}")
        else:
            self._action_undo.setText("↩ Отменить")

        if self.history_manager.can_redo:
            self._action_redo.setText(f"↪ Повторить: {self.history_manager.redo_text}")
        else:
            self._action_redo.setText("↪ Повторить")

    # ──────────────────────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────────────────────

    def _update_stats(self) -> None:
        if not self._stats_widget:
            return
        if not self._timeline_controller:
            self._stats_widget.clear()
            return
        all_markers = self._timeline_controller.markers
        self._stats_widget.set_markers(all_markers)

    # ──────────────────────────────────────────────────────────────────────────
    # Markers tab title badge
    # ──────────────────────────────────────────────────────────────────────────

    def _update_markers_tab_title(self) -> None:
        """Обновить заголовок вкладки маркеров с количеством."""
        if not self._right_tabs or not self._timeline_controller:
            return
        total = len(self._timeline_controller.markers)
        if total > 0:
            self._right_tabs.setTabText(0, f"📋 Маркеры ({total})")
        else:
            self._right_tabs.setTabText(0, "📋 Маркеры")

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

        if hasattr(controller, "save_project_silent"):
            self.set_autosave_callback(controller.save_project_silent)

    def set_timeline_controller(self, controller) -> None:
        self._timeline_controller = controller

        self.timeline_widget = (
            TimelineWidget(controller)
            if self._ctor_accepts_controller()
            else TimelineWidget()
        )
        if hasattr(self.timeline_widget, "set_controller"):
            self.timeline_widget.set_controller(controller)

        layout = self.timeline_container.layout()
        layout.addWidget(self.timeline_widget)

        if hasattr(controller, "set_main_window"):
            controller.set_main_window(self)

        if hasattr(controller, "markers_changed"):
            controller.markers_changed.connect(self._update_stats)
            controller.markers_changed.connect(self._update_markers_tab_title)

        if self._stats_widget and hasattr(controller, "fps"):
            self._stats_widget.set_fps(controller.fps)

        self._update_stats()
        self._update_markers_tab_title()

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
        self.event_filter_combo.currentIndexChanged.connect(
            self._on_event_filter_changed
        )
        row.addWidget(self.event_filter_combo)

        self.notes_filter_checkbox = QCheckBox("Заметки")
        self.notes_filter_checkbox.setToolTip("Показывать только отрезки с заметками")
        self.notes_filter_checkbox.stateChanged.connect(self._on_notes_filter_changed)
        row.addWidget(self.notes_filter_checkbox)

        self._filter_reset_btn = QPushButton("Сброс")
        self._filter_reset_btn.setMaximumWidth(80)
        self._filter_reset_btn.clicked.connect(self._on_reset_filters)
        self._filter_reset_btn.setToolTip("Сбросить все фильтры")
        row.addWidget(self._filter_reset_btn)

        self._filter_indicator = QLabel("")
        self._filter_indicator.setMinimumWidth(140)
        self._filter_indicator.setFixedHeight(20)
        row.addWidget(self._filter_indicator)

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
        self._update_filter_indicator()
        self._update_stats()
        self._update_markers_tab_title()

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

    def _update_filter_indicator(self) -> None:
        if not self.filter_controller:
            return

        is_filtered = self.filter_controller.has_active_filters
        total = 0
        filtered = 0

        if self._timeline_controller:
            all_markers = self._timeline_controller.markers
            total = len(all_markers)
            if is_filtered:
                filtered = len(self.filter_controller.filter_markers(all_markers))
            else:
                filtered = total

        if self._segments_header_label:
            if is_filtered:
                self._segments_header_label.setText(f"Отрезки: {filtered} из {total}")
                self._segments_header_label.setStyleSheet(
                    "color: #ff9900; font-weight: bold; font-size: 12px;"
                )
            else:
                if total > 0:
                    self._segments_header_label.setText(f"Отрезки: {total}")
                else:
                    self._segments_header_label.setText("Отрезки:")
                self._segments_header_label.setStyleSheet(
                    "color: #ffffff; font-weight: bold; font-size: 12px;"
                )

        if self._filter_indicator:
            if is_filtered:
                filter_parts = []
                event_types = self.filter_controller.filter_event_types
                if event_types:
                    type_name = next(iter(event_types))
                    event = self.event_manager.get_event(type_name)
                    display_name = event.get_localized_name() if event else type_name
                    filter_parts.append(display_name)
                if self.filter_controller.filter_has_notes:
                    filter_parts.append("с заметками")

                filter_desc = " + ".join(filter_parts)
                self._filter_indicator.setText(f"🔍 {filter_desc}")
                self._filter_indicator.setStyleSheet(
                    "color: #ff9900; font-weight: bold; font-size: 11px;"
                )
                self._filter_indicator.setToolTip(
                    f"Активные фильтры: {filter_desc}\n"
                    f"Показано {filtered} из {total} отрезков"
                )
            else:
                self._filter_indicator.setText("")
                self._filter_indicator.setToolTip("")

        if self._filter_reset_btn:
            if is_filtered:
                self._filter_reset_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #cc6600;
                        color: #ffffff;
                        border: 1px solid #ff9900;
                        border-radius: 3px;
                        font-weight: bold;
                        padding: 2px 8px;
                    }
                    QPushButton:hover {
                        background-color: #ff8800;
                        border: 1px solid #ffaa00;
                    }
                    QPushButton:pressed {
                        background-color: #aa5500;
                    }
                """)
                self._filter_reset_btn.setToolTip(
                    f"Сбросить фильтры (показано {filtered} из {total})"
                )
            else:
                self._filter_reset_btn.setStyleSheet("")
                self._filter_reset_btn.setToolTip("Сбросить все фильтры")

    # ──────────────────────────────────────────────────────────────────────────
    # Keyboard / Drag&Drop
    # ──────────────────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return

        key = event.key()
        modifiers = event.modifiers()

        if modifiers == Qt.ControlModifier:
            if key == Qt.Key.Key_Z:
                self._on_undo()
                return
            elif key == Qt.Key.Key_Y:
                self._on_redo()
                return

        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            self.key_pressed.emit(chr(key).upper())
            return

        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # ── Подсветить заглушку при drag ──
            if hasattr(self, 'video_label') and hasattr(self.video_label, 'set_drag_hovering'):
                self.video_label.set_drag_hovering(True)
    
    def dragLeaveEvent(self, event) -> None:
        # ── Снять подсветку заглушки ──
        if hasattr(self, 'video_label') and hasattr(self.video_label, 'set_drag_hovering'):
            self.video_label.set_drag_hovering(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        # ── Снять подсветку заглушки ──
        if hasattr(self, 'video_label') and hasattr(self.video_label, 'set_drag_hovering'):
            self.video_label.set_drag_hovering(False)

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

    def get_progress_bar(self) -> Optional[VideoProgressBar]:    # ← ДОБАВИТЬ
        return getattr(self, 'video_progress_bar', None)

    def get_segment_list_widget(self) -> SegmentListWidget:
        return self.segment_list_widget

    def get_timeline_widget(self) -> Optional[TimelineWidget]:
        return self.timeline_widget

    def get_stats_widget(self) -> Optional[StatsWidget]:
        return self._stats_widget

    def get_history_panel(self) -> Optional[HistoryPanel]:
        return self._history_panel

    def set_window_title(self, title: str) -> None:
        self.setWindowTitle(f"Hockey Editor - {title}" if title else "Hockey Editor")

    def update_mode_indicator(
        self,
        recording_mode: str,
        fixed_duration: int,
        pre_roll: float,
        post_roll: float,
    ) -> None:
        if recording_mode == "fixed_length":
            mode_text = "Режим: Фиксированная длина"
            params_text = (
                f"Длительность: {fixed_duration}с | "
                f"Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
            )
        else:
            mode_text = "Режим: Динамический"
            params_text = f"Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
        self.mode_indicator.setText(f"{mode_text} | {params_text}")

    def open_segment_editor(self, marker_idx: int) -> None:
        if self.main_controller and hasattr(self.main_controller, "open_segment_editor"):
            self.main_controller.open_segment_editor(marker_idx)

    # ── Convenience toast methods ──

    def show_toast_success(self, message: str, **kw) -> None:
        self.toast.success(message, **kw)

    def show_toast_error(self, message: str, **kw) -> None:
        self.toast.error(message, **kw)

    def show_toast_warning(self, message: str, **kw) -> None:
        self.toast.warning(message, **kw)

    def show_toast_info(self, message: str, **kw) -> None:
        self.toast.info(message, **kw)

    # ── Переключение на вкладку ──

    def switch_to_tab(self, tab_name: str) -> None:
        """Программно переключиться на вкладку по ключевому слову."""
        if not self._right_tabs:
            return
        tab_map = {
            "markers": 0, "маркеры": 0,
            "stats": 1, "статистика": 1,
            "history": 2, "история": 2,
            "tracking": 3, "трекинг": 3,
        }
        idx = tab_map.get(tab_name.lower())
        if idx is not None and idx < self._right_tabs.count():
            self._right_tabs.setCurrentIndex(idx)

    # ──────────────────────────────────────────────────────────────────────────
    # Close event — FIX: убрана дублирующая проверка несохранённых изменений.
    # Проверка остаётся ТОЛЬКО в MainController._on_window_closing()
    # ──────────────────────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        # Остановить авто-сохранение
        if self._autosave:
            self._autosave.stop()

        # Сохранить геометрию окна
        self._save_window_geometry()

        # Делегировать проверку несохранённых изменений контроллеру
        # (MainController._on_window_closing покажет диалог, если нужно)
        self.window_closing.emit(event)

        if event.isAccepted():
            super().closeEvent(event)