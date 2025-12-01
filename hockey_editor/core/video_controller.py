from PySide6.QtCore import QObject, Signal, QTimer
from typing import List, Optional, Dict
from enum import Enum
import json
import os
from .video_processor import VideoProcessor
from ..models.marker import Marker, EventType
from ..utils.settings_manager import get_settings_manager
from ..utils.custom_events import get_custom_event_manager


class RecordingMode(Enum):
    """Режимы расстановки отрезков."""
    DYNAMIC = "dynamic"          # Два нажатия = начало и конец
    FIXED_LENGTH = "fixed_length"  # Одно нажатие = отрезок фиксированной длины


class VideoController(QObject):
    """Главный контроллер видео с синхронизацией воспроизведения."""
    
    # Сигналы
    playback_time_changed = Signal(int)  # frame_idx
    markers_changed = Signal()
    recording_status_changed = Signal(str, str)  # event_type (A/D/S), status (Recording/Complete)
    timeline_update = Signal()
    current_frame_update = Signal(int)  # frame_idx
    frame_ready = Signal(object)  # np.ndarray (текущий кадр)

    def __init__(self):
        super().__init__()

        self.processor = VideoProcessor()
        self.markers: List[Marker] = []

        # SettingsManager для персистентности
        self.settings = get_settings_manager()

        # CustomEventManager - менеджер событий
        self.event_manager = get_custom_event_manager()

        # UndoRedoManager
        from ..utils.undo_redo import UndoRedoManager
        self.undo_redo = UndoRedoManager()

        # Параметры воспроизведения
        self.playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.frame_time_ms = 33  # ~30 FPS (рассчитывается на основе FPS видео)

        # Параметры расстановки отрезков (загрузить из QSettings)
        mode_str = self.settings.load_recording_mode()
        self.recording_mode = RecordingMode(mode_str)
        self.fixed_duration_sec = self.settings.load_fixed_duration()
        self.pre_roll_sec = self.settings.load_pre_roll()
        self.post_roll_sec = self.settings.load_post_roll()

        # Состояние текущей записи (динамический режим)
        self.is_recording = False
        self.recording_event_name: Optional[str] = None  # Имя события вместо EventType
        self.recording_start_frame: Optional[int] = None

    def load_video(self, video_path: str) -> bool:
        """Загрузить видеофайл (ПАУЗИРОВАН!)."""
        success = self.processor.load(video_path)
        if success:
            # Рассчитать frame_time_ms на основе FPS видео
            fps = self.processor.get_fps()
            if fps > 0:
                self.frame_time_ms = int(1000 / fps)
            
            # Убедиться, что видео на паузе
            self.playing = False
            self.playback_timer.stop()
            
            # Обновить маркеры и UI
            self.markers = []
            self.markers_changed.emit()
            self.playback_time_changed.emit(0)
            self.current_frame_update.emit(0)
            self.timeline_update.emit()
            
            # Отправить первый кадр на UI
            frame = self.processor.get_current_frame()
            if frame is not None:
                self.frame_ready.emit(frame)
        
        return success

    def play(self):
        """Начать воспроизведение."""
        if self.processor.cap is None or self.playing:
            return
        
        self.playing = True
        self.playback_timer.start(self.frame_time_ms)

    def pause(self):
        """Пауза."""
        self.playing = False
        self.playback_timer.stop()

    def toggle_play_pause(self):
        """Переключить Play/Pause."""
        if self.playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        """Остановка и возврат в начало."""
        self.pause()
        self.seek_frame(0)

    def seek_frame(self, frame_idx: int):
        """Перемотать на кадр (НЕ запускает воспроизведение)."""
        if self.processor.cap is None:
            return
        
        self.processor.seek(frame_idx)
        
        # Отправить сигналы об обновлении
        self.playback_time_changed.emit(frame_idx)
        self.current_frame_update.emit(frame_idx)
        self.timeline_update.emit()
        
        # Отправить кадр на UI
        frame = self.processor.get_current_frame()
        if frame is not None:
            self.frame_ready.emit(frame)

    def _on_playback_tick(self):
        """Таймер воспроизведения - вызывается каждый frame_time_ms."""
        if not self.processor.cap or not self.playing:
            return
        
        # Переместиться на следующий кадр
        success = self.processor.advance_frame()
        if not success:
            # Конец видео
            self.pause()
            return
        
        # Получить текущий индекс кадра
        current_frame_idx = self.processor.get_current_frame_idx()
        
        # Эмит сигналов об обновлении
        self.playback_time_changed.emit(current_frame_idx)
        self.current_frame_update.emit(current_frame_idx)
        self.timeline_update.emit()
        
        # Отправить текущий кадр на UI
        frame = self.processor.get_current_frame()
        if frame is not None:
            self.frame_ready.emit(frame)

    def on_hotkey_pressed(self, key: str):
        """Обработка нажатия горячей клавиши."""
        # Найти событие по клавише
        event = self.event_manager.get_event_by_hotkey(key)
        if not event:
            return  # Нет события для этой клавиши

        current_frame = self.processor.get_current_frame_idx()
        event_name = event.name

        if self.recording_mode == RecordingMode.DYNAMIC:
            self._handle_dynamic_mode(event_name, current_frame)
        elif self.recording_mode == RecordingMode.FIXED_LENGTH:
            self._handle_fixed_length_mode(event_name, current_frame)

    def _handle_dynamic_mode(self, event_name: str, current_frame: int):
        """Динамический режим: два нажатия = начало и конец."""
        if not self.is_recording:
            # Начало записи
            self.is_recording = True
            self.recording_event_name = event_name
            self.recording_start_frame = current_frame
            self.recording_status_changed.emit(event_name, "Recording")
            self.timeline_update.emit()
        elif self.recording_event_name == event_name:
            # Конец записи
            pre_roll_frames = max(0, int(self.pre_roll_sec * self.processor.fps))
            start_frame = max(0, self.recording_start_frame - pre_roll_frames)

            marker = Marker(
                start_frame=start_frame,
                end_frame=current_frame,
                event_name=event_name,
                note=""
            )
            self.markers.append(marker)

            # Автооткат начала отрезка
            self.seek_frame(start_frame)

            self.is_recording = False
            self.recording_event_name = None
            self.recording_start_frame = None

            self.recording_status_changed.emit(event_name, "Complete")
            self.markers_changed.emit()
            self.timeline_update.emit()

    def _handle_fixed_length_mode(self, event_name: str, current_frame: int):
        """Фиксированная длина: одно нажатие = отрезок фиксированной длины."""
        # Рассчитать границы
        fixed_frames = int(self.fixed_duration_sec * self.processor.fps)
        pre_roll_frames = max(0, int(self.pre_roll_sec * self.processor.fps))

        start_frame = max(0, current_frame - pre_roll_frames)
        end_frame = min(self.processor.total_frames - 1, current_frame + fixed_frames - pre_roll_frames)

        # Создать отрезок
        marker = Marker(
            start_frame=start_frame,
            end_frame=end_frame,
            event_name=event_name,
            note=""
        )
        self.markers.append(marker)

        # Визуальная обратная связь
        self.recording_status_changed.emit(event_name, "Fixed")

        # Автооткат начала отрезка
        self.seek_frame(start_frame)

        self.markers_changed.emit()
        self.timeline_update.emit()

    def cancel_recording(self):
        """Отменить текущую запись."""
        if self.is_recording:
            self.is_recording = False
            self.recording_event_name = None
            self.recording_start_frame = None
            self.recording_status_changed.emit("", "Cancelled")
            self.timeline_update.emit()

    def delete_marker(self, idx: int):
        """Удалить отрезок (с undo/redo)."""
        if 0 <= idx < len(self.markers):
            from ..utils.undo_redo import DeleteMarkerCommand
            command = DeleteMarkerCommand(self.markers, idx)
            self.undo_redo.push_command(command)
            self.markers_changed.emit()
            self.timeline_update.emit()

    def clear_markers(self):
        """Удалить все отрезки (с undo/redo)."""
        from ..utils.undo_redo import ClearMarkersCommand
        command = ClearMarkersCommand(self.markers)
        self.undo_redo.push_command(command)
        self.markers_changed.emit()
        self.timeline_update.emit()

    def set_recording_mode(self, mode: RecordingMode):
        """Установить режим расстановки отрезков."""
        self.recording_mode = mode
        self.settings.save_recording_mode(mode.value)

    def set_fixed_duration(self, seconds: int):
        """Установить фиксированную длину отрезка."""
        self.fixed_duration_sec = seconds
        self.settings.save_fixed_duration(seconds)

    def set_pre_roll(self, seconds: float):
        """Установить откат перед началом отрезка."""
        self.pre_roll_sec = seconds
        self.settings.save_pre_roll(seconds)

    def set_post_roll(self, seconds: float):
        """Установить добавление в конец отрезка."""
        self.post_roll_sec = seconds
        self.settings.save_post_roll(seconds)

    # Метод update_hotkeys убран - hotkeys теперь управляются через CustomEventManager

    def get_current_frame_idx(self) -> int:
        """Получить текущий индекс кадра."""
        return self.processor.get_current_frame_idx()

    def get_fps(self) -> float:
        """Получить FPS видео."""
        return self.processor.get_fps()

    def get_total_frames(self) -> int:
        """Получить общее количество кадров."""
        return self.processor.get_total_frames()

    def cleanup(self):
        """Очистить ресурсы."""
        self.pause()
        self.processor.cleanup()
        self.markers.clear()

    # ===== ПРОЕКТЫ =====
    
    def save_project(self, file_path: str) -> bool:
        """Сохранить проект в файл."""
        from .project_manager import ProjectManager, Project

        project = Project(
            name=os.path.basename(self.processor.video_path) if self.processor.video_path else "Untitled",
            video_path=self.processor.video_path,
            fps=self.get_fps()
        )
        project.markers = self.markers.copy()
        
        success = ProjectManager.save_project(project, file_path)
        if success:
            ProjectManager.add_to_recent(file_path)
        return success
    
    def load_project(self, file_path: str) -> bool:
        """Загрузить проект из файла."""
        from .project_manager import ProjectManager
        
        project = ProjectManager.load_project(file_path)
        if not project:
            return False
        
        # Загрузить видео
        if project.video_path and os.path.exists(project.video_path):
            if not self.load_video(project.video_path):
                return False
        
        # Загрузить маркеры
        self.markers = project.markers.copy()
        self.markers_changed.emit()
        
        ProjectManager.add_to_recent(file_path)
        return True
    
    def get_recent_projects(self) -> List[str]:
        """Получить список недавних проектов."""
        from .project_manager import ProjectManager
        return ProjectManager.get_recent_projects()
    
    # ===== UNDO/REDO =====
    
    def undo(self):
        """Отменить последнюю операцию."""
        self.undo_redo.undo()
        self.markers_changed.emit()
    
    def redo(self):
        """Повторить последнюю отменённую операцию."""
        self.undo_redo.redo()
        self.markers_changed.emit()
    
    def can_undo(self) -> bool:
        """Проверить, можно ли отменить."""
        return self.undo_redo.can_undo()
    
    def can_redo(self) -> bool:
        """Проверить, можно ли повторить."""
        return self.undo_redo.can_redo()
