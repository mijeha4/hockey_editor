import vlc
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QSlider
import config

class VideoThread(QThread):
    """Встроенный видеоплеер с использованием VLC"""
    
    frame_updated = pyqtSignal(QPixmap)  # Позиция воспроизведения в сек
    playback_finished = pyqtSignal()
        self.speed_label = QLabel("1.0x")
        buttons_layout.addWidget(self.speed_label)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 400)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        
        # VLC инициализация
        self.instance = vlc.Instance()
        self.player = self.instance.media_list_player_new()
        self.media_player = self.player.get_media_player()
        self.mpv_player.path = filepath
        self.mpv_player['pause'] = True
        self.mpv_player['speed'] = 1.0
        self.duration = self.mpv_player.duration if self.mpv_player.duration else 0.0
        self.slider.setMaximum(int(self.duration * 1000))
        self.timer.timeout.connect(self._update_position)
        self.timer.start(50)  # Обновление каждые 50мс
    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.mpv_player['pause'] = not self.is_playing
        self.play_button.setText("⏸ Pause" if self.is_playing else "▶ Play")

    def stop(self):
        self.video_frame = QWidget()
        self.video_layout = QVBoxLayout()
        self.video_frame.setLayout(self.video_layout)
        layout.addWidget(self.video_frame)
    def seek(self, time_seconds: float):
        self.mpv_player['time-pos'] = time_seconds

    def frame_forward(self):
        current = self.mpv_player['time-pos'] or 0
        self.mpv_player['time-pos'] = current + 1.0 / self.playback_speed

    def frame_backward(self):
        current = self.mpv_player['time-pos'] or 0
        self.mpv_player['time-pos'] = max(0, current - 1.0 / self.playback_speed)

    def _on_speed_changed(self, value: int):
        self.playback_speed = value / 100.0
        self.mpv_player['speed'] = self.playback_speed
        self.speed_label.setText(f"{self.playback_speed:.1f}x")

    def _update_position(self):
        current = self.mpv_player['time-pos'] or 0
        self.time_label.setText(self._seconds_to_timecode(current))
        self.slider.blockSignals(True)
        self.slider.setValue(int(current * 1000))
        self.slider.blockSignals(False)
        self.playback_position_changed.emit(current)

    def _on_slider_moved(self, position: int):
        self.seek(position / 1000.0)

    @staticmethod
    def _seconds_to_timecode(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        self.frame_forward_button.clicked.connect(self.frame_forward)
        buttons_layout.addWidget(self.frame_forward_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)

    def load_video(self, filepath: str, fps: int, total_frames: int):
        """Загрузить видеофайл"""
        try:
            media = self.instance.media_new(filepath)
            self.player.media_list_new()
            self.player.media_list.add_media(media)
            self.player.play()
            self.player.pause()
            
            self.fps = fps
            self.total_frames = total_frames
            self.duration = total_frames / fps if fps > 0 else 0
            
            self.duration_label.setText(self._seconds_to_timecode(self.duration))
            self.slider.setMaximum(int(self.duration * 1000))
            
            return True
        except Exception as e:
            print(f"Error loading video: {e}")
            return False

    def toggle_play(self):
        """Переключить воспроизведение"""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.media_player.play()
            self.play_button.setText("⏸ Pause")
        else:
            self.media_player.pause()
            self.play_button.setText("▶ Play")

    def stop(self):
        """Остановить воспроизведение"""
        self.media_player.stop()
        self.is_playing = False
        self.current_time = 0.0
        self.play_button.setText("▶ Play")
        self._update_position()

    def seek(self, time_seconds: float):
        """Перейти на определенное время"""
        self.current_time = time_seconds
        self.media_player.set_time(int(time_seconds * 1000))

    def frame_forward(self):
        """На кадр вперед"""
        if self.fps > 0:
            self.seek(self.current_time + 1.0 / self.fps)

    def frame_backward(self):
        """На кадр назад"""
        if self.fps > 0:
            self.seek(max(0, self.current_time - 1.0 / self.fps))

    def set_speed(self, speed: float):
        """Установить скорость воспроизведения"""
        self.playback_speed = speed
        self.media_player.set_rate(speed)

    def _update_position(self):
        """Обновить текущую позицию"""
        if self.media_player.is_playing():
            self.current_time = self.media_player.get_time() / 1000.0
            self.time_label.setText(self._seconds_to_timecode(self.current_time))
            self.slider.blockSignals(True)
            self.slider.setValue(int(self.current_time * 1000))
            self.slider.blockSignals(False)
            self.playback_position_changed.emit(self.current_time)

    def _on_slider_moved(self, position: int):
        """Обработка перемещения слайдера"""
        time_seconds = position / 1000.0
        self.seek(time_seconds)

    @staticmethod
    def _seconds_to_timecode(seconds: float) -> str:
        """Преобразовать секунды в формат HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def closeEvent(self, event):
        """Закрытие плеера"""
        self.timer.stop()
        self.media_player.stop()
        super().closeEvent(event)
        self.total_frames = total_frames
        self.cap = cv2.VideoCapture(filepath)
        self.current_frame = 0
        self.slider.setMaximum(total_frames - 1)
        self.play_btn.setText("⏸ Pause")
        self.is_playing = False
        self._update_frame()
        print(f"Loaded {filepath}, FPS: {fps}, Frames: {total_frames}")
    
    @pyqtSlot()
    def toggle_play(self):
        """Play/Pause"""
        if self.is_playing:
            self.timer.stop()
            self.play_btn.setText("▶ Play")
            self.is_playing = False
        else:
            self.timer.start(int(1000 / self.fps))
            self.play_btn.setText("⏸ Pause")
            self.is_playing = True
    
    @pyqtSlot()
    def frame_forward(self):
        """Кадр вперед"""
        self.current_frame = min(self.current_frame + 1, self.total_frames - 1)
        self._update_frame()
    
    @pyqtSlot()
    def frame_backward(self):
        """Кадр назад"""
        self.current_frame = max(0, self.current_frame - 1)
        self._update_frame()
    
    def seek(self, frame):
        """Переход к кадру"""
        self.current_frame = frame
        self._update_frame()
    
    @property
    def current_time(self):
        """Текущее время в секундах"""
        return self.current_frame / self.fps if self.fps else 0
    
    def _update_frame(self):
        """Обновление кадра"""
        if self.cap and self.current_frame < self.total_frames:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if ret:
                # cv2 to Qt
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio))
                
                self.slider.setValue(self.current_frame)
                self.playback_position_changed.emit(self.current_time)
                
                if self.is_playing:
                    self.current_frame += 1
            else:
                self.toggle_play()
