from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
import vlc

class SeparateVideoWindow(QMainWindow):
    """Отдельное полноэкранное окно для видео"""
    
    closed = pyqtSignal()
    position_changed = pyqtSignal(float)
    
    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Video Player - Fullscreen")
        self.setGeometry(0, 0, 1280, 720)
        
        # VLC инициализация
        self.instance = vlc.Instance()
        self.player = self.instance.media_list_player_new()
        self.media_player = self.player.get_media_player()
        
        # Загрузка видео
        media = self.instance.media_new(video_path)
        self.player.media_list_new()
        self.player.media_list.add_media(media)
        
        # UI
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Встраивание видеоплеера
        self.video_widget = QWidget()
        self.media_player.set_xwindow(int(self.video_widget.winId()))
        
        layout.addWidget(self.video_widget)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def play(self):
        """Начать воспроизведение"""
        self.player.play()

    def pause(self):
        """Остановить воспроизведение"""
        self.player.pause()

    def toggle_fullscreen(self):
        """Переключить полноэкранный режим"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event: QKeyEvent):
        """Обработка нажатия клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            if self.media_player.is_playing():
                self.pause()
            else:
                self.play()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Закрытие окна"""
        self.media_player.stop()
        self.closed.emit()
        super().closeEvent(event)
