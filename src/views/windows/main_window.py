from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from ..components.player_controls import PlayerControls
from ..components.timeline.view import TimelineView


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Hockey Editor")
        self.setGeometry(100, 100, 1200, 800)

        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Видео экран (placeholder)
        self.video_label = QLabel("Video Screen")
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid grey;")
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label)

        # Панель управления
        self.player_controls = PlayerControls()
        layout.addWidget(self.player_controls)

        # Таймлайн
        self.timeline_view = TimelineView()
        layout.addWidget(self.timeline_view)

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
