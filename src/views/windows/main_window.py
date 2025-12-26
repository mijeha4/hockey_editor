"""
Main Window - Primary application window for Hockey Editor.

Provides the main UI layout with video player, timeline, segment list,
event shortcuts panel, advanced filtering, and comprehensive menu system.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QMenuBar, QMenu, QStatusBar, QComboBox, QCheckBox, QPushButton,
    QMessageBox, QFileDialog, QSpinBox
)
from PySide6.QtGui import QPixmap, QKeySequence, QKeyEvent, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, Signal, QTimer

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from views.widgets.player_controls import PlayerControls
from views.widgets.segment_list import SegmentListWidget
# Используем новую профессиональную timeline
from hockey_editor.ui.timeline_graphics import TimelineWidget
from views.styles import get_application_stylesheet
# Импортируем EventShortcutListWidget
from hockey_editor.ui.event_shortcut_list_widget import EventShortcutListWidget


class MainWindow(QMainWindow):
    """Main application window with video editing interface."""

    # Signals for menu actions
    open_video_triggered = Signal()
    save_project_triggered = Signal()
    load_project_triggered = Signal()
    new_project_triggered = Signal()
    open_settings_triggered = Signal()
    export_triggered = Signal()
    open_preview_triggered = Signal()

    # Signal for keyboard shortcuts
    key_pressed = Signal(str)  # Pressed key (e.g., 'G', 'H')

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Хоккейный Редактор")
        self.setGeometry(0, 0, 1800, 1000)

        # Поддержка drag-drop для видео
        self.setAcceptDrops(True)

        # Apply application stylesheet
        self.setStyleSheet(get_application_stylesheet())

        # Create menu bar
        self._create_menu_bar()

        # Setup UI
        self._setup_ui()

    def _create_menu_bar(self) -> None:
        """Create the main menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # New Project
        new_action = file_menu.addAction("&New Project")
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_project)

        # Open Video
        open_video_action = file_menu.addAction("&Open Video...")
        open_video_action.setShortcut(QKeySequence.StandardKey.Open)
        open_video_action.triggered.connect(self._on_open_video)

        file_menu.addSeparator()

        # Open Project
        open_project_action = file_menu.addAction("Open &Project...")
        open_project_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_project_action.triggered.connect(self._on_load_project)

        # Save Project
        save_action = file_menu.addAction("&Save Project")
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save_project)

        # Save Project As
        save_as_action = file_menu.addAction("Save Project &As...")
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._on_save_project_as)

        file_menu.addSeparator()

        # Export
        export_action = file_menu.addAction("&Export...")
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._on_export)

        file_menu.addSeparator()

        # Exit
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        # Preferences
        preferences_action = edit_menu.addAction("&Preferences...")
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        preferences_action.triggered.connect(self._on_open_preferences)

        # View menu
        view_menu = menubar.addMenu("&View")

        # Preview Window
        preview_action = view_menu.addAction("&Preview Window")
        preview_action.setShortcut(QKeySequence("Ctrl+P"))
        preview_action.triggered.connect(self._on_open_preview)

    def _setup_ui(self) -> None:
        """Setup the main user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Create main vertical splitter
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # Top section (70% height) - Video and segments
        top_section = self._create_top_section()
        main_splitter.addWidget(top_section)

        # Bottom section - Timeline (будет установлен позже через set_timeline_controller)
        # self.timeline_widget = TimelineWidget()
        # main_splitter.addWidget(self.timeline_widget)

        # Set splitter proportions (70% top, 30% bottom)
        main_splitter.setSizes([630, 270])

        # Add main splitter to layout
        main_layout.addWidget(main_splitter)

        # Create footer (status bar and shortcuts)
        self._create_footer(main_layout)

    def _create_top_section(self) -> QWidget:
        """Create the top section with video player and segment list."""
        top_widget = QWidget()

        # Horizontal splitter for video/segments
        horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Video container
        video_container = self._create_video_container()
        horizontal_splitter.addWidget(video_container)

        # Right side - Segment list
        self.segment_list_widget = SegmentListWidget()
        horizontal_splitter.addWidget(self.segment_list_widget)

        # Set proportions (60% video, 40% segments)
        horizontal_splitter.setSizes([840, 560])

        # Layout for top widget
        layout = QHBoxLayout(top_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(horizontal_splitter)

        return top_widget

    def _create_video_container(self) -> QWidget:
        """Create the video container with video display and controls."""
        container = QWidget()

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video display (placeholder QLabel)
        self.video_label = QLabel("Video Display")
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                color: #666666;
                border: 2px solid #444444;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.video_label)

        # Player controls
        self.player_controls = PlayerControls()
        layout.addWidget(self.player_controls)

        return container

    def _create_footer(self, parent_layout: QVBoxLayout) -> None:
        """Create the footer with status bar and shortcuts panel."""
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        self.setStatusBar(self.status_bar)

        # Shortcuts panel
        try:
            from hockey_editor.ui.event_shortcut_list_widget import EventShortcutListWidget
            self.shortcuts_widget = EventShortcutListWidget()
            parent_layout.addWidget(self.shortcuts_widget)
        except ImportError:
            # Fallback if import fails
            self.shortcuts_widget = QLabel("Event Shortcuts (Import failed)")
            self.shortcuts_widget.setStyleSheet("color: #888888; padding: 5px;")
            parent_layout.addWidget(self.shortcuts_widget)

    # Menu action handlers
    def _on_new_project(self) -> None:
        """Handle new project action."""
        self.new_project_triggered.emit()

    def _on_open_video(self) -> None:
        """Handle open video action."""
        self.open_video_triggered.emit()

    def _on_load_project(self) -> None:
        """Handle load project action."""
        self.load_project_triggered.emit()

    def _on_save_project(self) -> None:
        """Handle save project action."""
        self.save_project_triggered.emit()

    def _on_save_project_as(self) -> None:
        """Handle save project as action."""
        # For now, emit the same signal as save
        self.save_project_triggered.emit()

    def _on_open_preferences(self) -> None:
        """Handle open preferences action."""
        self.open_settings_triggered.emit()

    def _on_export(self) -> None:
        """Handle export action."""
        self.export_triggered.emit()

    def _on_open_preview(self) -> None:
        """Handle open preview window action."""
        self.open_preview_triggered.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for shortcuts."""
        # Ignore auto-repeats
        if event.isAutoRepeat():
            return

        key = event.key()

        # Handle letter keys (A-Z)
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_char = chr(key).upper()
            self.key_pressed.emit(key_char)
            return

        # Handle other keys if needed
        super().keyPressEvent(event)

    # Public interface methods
    def set_video_image(self, pixmap: QPixmap) -> None:
        """Set the video display image."""
        self.video_label.setPixmap(pixmap)

    def set_window_title(self, title: str) -> None:
        """Set the window title with project name."""
        if title:
            self.setWindowTitle(f"Hockey Editor - {title}")
        else:
            self.setWindowTitle("Hockey Editor")

    def update_status_bar(self, message: str) -> None:
        """Update the status bar message."""
        self.status_bar.showMessage(message)

    def get_player_controls(self) -> PlayerControls:
        """Get the player controls widget."""
        return self.player_controls

    def get_segment_list_widget(self) -> SegmentListWidget:
        """Get the segment list widget."""
        return self.segment_list_widget

    def get_timeline_widget(self) -> TimelineWidget:
        """Get the timeline widget."""
        return self.timeline_widget

    def get_shortcuts_widget(self) -> Optional[QWidget]:
        """Get the shortcuts widget."""
        return getattr(self, 'shortcuts_widget', None)

    def set_timeline_controller(self, controller) -> None:
        """Set the timeline controller and create timeline widget.

        Args:
            controller: TimelineController instance
        """
        # Создать timeline widget с controller
        self.timeline_widget = TimelineWidget(controller)

        # Добавить timeline widget в splitter
        central_widget = self.centralWidget()
        main_layout = central_widget.layout()
        main_splitter = main_layout.itemAt(0).widget()  # QSplitter

        # Добавить timeline widget как второй элемент splitter
        main_splitter.addWidget(self.timeline_widget)

    def open_segment_editor(self, segment_idx: int) -> None:
        """Открыть редактор сегмента.

        Args:
            segment_idx: Индекс сегмента для редактирования
        """
        # Получить маркер по индексу
        if hasattr(self, '_timeline_controller') and segment_idx < len(self._timeline_controller.markers):
            marker = self._timeline_controller.markers[segment_idx]

            # Получить MainController через TimelineController
            # MainController сохраняет ссылку на себя в TimelineController
            main_controller = getattr(self._timeline_controller, '_main_controller', None)

            if main_controller:
                from src.views.windows.instance_edit import InstanceEditWindow
                dialog = InstanceEditWindow(marker, main_controller, parent=self)
                dialog.exec()
            else:
                # Fallback: показать сообщение об ошибке
                QMessageBox.warning(self, "Error", "Cannot open segment editor: controller not available")

    # Drag and drop support
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Обработка входа drag-drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Обработка drop видеофайла."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                # Emit signal for video loading
                self.open_video_triggered.emit()
                break

    # Extended status bar methods
    def update_extended_status_bar(self, fps: float, current_frame: int, total_frames: int, speed: float, segment_count: int) -> None:
        """Обновить расширенный статус-бар с подробной информацией."""
        if fps > 0 and total_frames > 0:
            current_time = self._format_time_single(current_frame / fps)
            total_time = self._format_time_single(total_frames / fps)

            status = f"{current_time}/{total_time} | {segment_count} отрезков | FPS: {fps:.2f} | Speed: {speed:.2f}x"

            # Если воспроизведение, добавить индикатор
            if hasattr(self, '_is_playing') and self._is_playing:
                status = "▶ " + status

            self.status_bar.showMessage(status)
        else:
            self.status_bar.showMessage("Готов")

    def _format_time_single(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    # Filter methods
    def setup_filters(self) -> None:
        """Настроить фильтры для сегментов."""
        # Этот метод будет вызываться из контроллера
        pass

    def update_event_filter(self) -> None:
        """Обновить список доступных типов событий в фильтре."""
        # Этот метод будет реализован в контроллере
        pass

    # Additional signals
    video_dropped = Signal(str)  # Signal emitted when video is dropped (file_path)
