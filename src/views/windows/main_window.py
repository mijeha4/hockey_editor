from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QMenuBar, QMenu, QFileDialog
)
from PySide6.QtGui import QPixmap, QKeySequence, QKeyEvent
from PySide6.QtCore import Qt, Signal
from ..components.player_controls import PlayerControls
from ..components.timeline.view import TimelineView
from ..components.segment_list import SegmentList


class MainWindow(QMainWindow):
    """Главное окно приложения с темной темой, меню и обработкой клавиш."""

    # Сигналы для меню
    open_video_triggered = Signal()
    save_project_triggered = Signal()
    load_project_triggered = Signal()
    new_project_triggered = Signal()
    open_settings_triggered = Signal()
    export_triggered = Signal()

    # Сигнал для клавиш
    key_pressed = Signal(str)  # Нажатая клавиша (например, 'G', 'H')

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Hockey Editor")
        self.setGeometry(100, 100, 1400, 900)

        # Применить темную тему
        self._apply_dark_theme()

        # Создать меню
        self._create_menu_bar()

        self._setup_ui()

    def _create_menu_bar(self):
        """Создать главное меню."""
        menubar = self.menuBar()

        # Меню File
        file_menu = menubar.addMenu("&File")

        # Меню Edit
        edit_menu = menubar.addMenu("&Edit")

        # Preferences
        preferences_action = edit_menu.addAction("&Preferences...")
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        preferences_action.triggered.connect(self._on_open_preferences)

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

    def _on_new_project(self):
        """Обработка New Project."""
        self.new_project_triggered.emit()

    def _on_open_video(self):
        """Обработка Open Video."""
        self.open_video_triggered.emit()

    def _on_load_project(self):
        """Обработка Open Project."""
        self.load_project_triggered.emit()

    def _on_save_project(self):
        """Обработка Save Project."""
        self.save_project_triggered.emit()

    def _on_save_project_as(self):
        """Обработка Save Project As."""
        # Пока просто эмитим тот же сигнал
        self.save_project_triggered.emit()

    def _on_open_preferences(self):
        """Обработка открытия настроек."""
        self.open_settings_triggered.emit()

    def _on_export(self):
        """Обработка экспорта."""
        self.export_triggered.emit()

    def keyPressEvent(self, event: QKeyEvent):
        """Обработка нажатий клавиш для горячих клавиш событий."""
        # Игнорируем, если фокус в поле ввода или другом редактируемом виджете
        if event.isAutoRepeat():
            return

        key = event.key()

        # Обычные буквы (A-Z)
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_char = chr(key).upper()
            self.key_pressed.emit(key_char)
            return

        # Специальные клавиши (если понадобятся)
        # if key == Qt.Key.Key_Space:
        #     self.key_pressed.emit('SPACE')

        # Вызываем родительский обработчик для остальных клавиш
        super().keyPressEvent(event)

    def _apply_dark_theme(self):
        """Применить темную тему ко всему приложению."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QSplitter::handle {
                background-color: #404040;
                border: 1px solid #555555;
            }
            QSplitter::handle:hover {
                background-color: #505050;
            }
            QMenuBar {
                background-color: #333333;
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #444444;
            }
            QMenu {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 4px 20px;
            }
            QMenu::item:selected {
                background-color: #444444;
            }
        """)

    def _setup_ui(self):
        """Создать интерфейс с иерархией виджетов."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Центральный сплиттер (вертикальный)
        central_splitter = QSplitter(Qt.Orientation.Vertical)

        # ===== ВЕРХНЯЯ ПАНЕЛЬ =====
        top_panel = self._create_top_panel()
        central_splitter.addWidget(top_panel)

        # ===== НИЖНЯЯ ПАНЕЛЬ (Timeline) =====
        self.timeline_view = TimelineView()
        central_splitter.addWidget(self.timeline_view)

        # Установить пропорции (70% верх, 30% низ)
        central_splitter.setSizes([630, 270])

        main_layout.addWidget(central_splitter)

    def _create_top_panel(self) -> QWidget:
        """Создать верхнюю панель с видео и списком сегментов."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Левый сплиттер (горизонтальный) для видео и списка
        left_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ===== ВИДЕО КОНТЕЙНЕР =====
        video_container = self._create_video_container()
        left_splitter.addWidget(video_container)

        # ===== СПИСОК СЕГМЕНТОВ =====
        self.segment_list = SegmentList()
        left_splitter.addWidget(self.segment_list)

        # Установить пропорции (60% видео, 40% список)
        left_splitter.setSizes([840, 560])

        layout.addWidget(left_splitter)
        return panel

    def _create_video_container(self) -> QWidget:
        """Создать контейнер для видео и управления."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Видео экран
        self.video_label = QLabel("Video Screen")
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #444444;
                color: #888888;
                font-size: 14px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)

        # Панель управления
        self.player_controls = PlayerControls()
        layout.addWidget(self.player_controls)

        return container

    def set_video_image(self, pixmap: QPixmap):
        """Установить изображение видео."""
        self.video_label.setPixmap(pixmap)

    def set_window_title(self, title: str):
        """Установить заголовок окна."""
        self.setWindowTitle(f"Hockey Editor - {title}")

    def get_player_controls(self) -> PlayerControls:
        """Получить виджет управления плеером."""
        return self.player_controls

    def get_timeline_view(self) -> TimelineView:
        """Получить виджет таймлайна."""
        return self.timeline_view

    def get_segment_list(self) -> SegmentList:
        """Получить виджет списка сегментов."""
        return self.segment_list
