# Hockey Editor Pro - Полная структура программы и исходный код

## Описание проекта

**Hockey Editor Pro** - профессиональный видеомонтажер для анализа хоккейных матчей. Аналог SportCode, LongoMatch, Hudl.

**Ключевые особенности:**
- Горячие клавиши A/D/S для создания отрезков (Атака/Защита/Смена)
- Профессиональный таймлайн с 3 цветными дорожками
- Визуальная обратная связь в реальном времени
- Видео НЕ паузируется при создании отрезков
- Экспорт в MP4, JSON, CSV
- Поддержка видео: MP4, AVI, MOV, MKV через ffmpeg

## Архитектура программы

Программа построена на основе паттерна MVC (Model-View-Controller) с использованием PySide6 (Qt6 для Python).

### Основные компоненты:
- **main.py** - точка входа
- **core/** - бизнес-логика (контроллеры, процессоры)
- **models/** - модели данных
- **ui/** - пользовательский интерфейс
- **utils/** - вспомогательные классы

## Структура проекта

```
hockey_editor/
├── main.py                          # Точка входа
├── requirements.txt                 # Зависимости Python
├── config.json                      # Конфигурация
├── hockey_editor/
│   ├── core/
│   │   ├── video_controller.py      # Главный контроллер видео
│   │   ├── video_processor.py       # Обработка видео через OpenCV
│   │   ├── event_creation_controller.py  # Управление событиями
│   │   ├── exporter.py              # Экспорт видео
│   │   ├── project_manager.py       # Управление проектами
│   │   └── video_reader_thread.py   # Поток чтения видео
│   ├── models/
│   │   └── marker.py                # Модель маркера/отрезка
│   ├── ui/
│   │   ├── main_window.py           # Главное окно
│   │   ├── timeline.py              # Таймлайн виджет
│   │   ├── timeline_graphics.py     # Графические элементы таймлайна
│   │   ├── video_window.py          # Окно видео
│   │   ├── settings_dialog.py       # Диалог настроек
│   │   ├── export_dialog.py         # Диалог экспорта
│   │   ├── segment_editor.py        # Редактор сегментов
│   │   ├── edit_segment_dialog.py   # Диалог редактирования
│   │   ├── preview_window.py        # Окно предпросмотра
│   │   └── custom_event_dialog.py   # Диалог кастомных событий
│   └── utils/
│       ├── settings_manager.py      # Менеджер настроек
│       ├── custom_events.py         # Кастомные типы событий
│       ├── undo_redo.py             # Отмена/повтор операций
│       ├── autosave.py              # Автосохранение
│       ├── shortcut_manager.py      # Менеджер горячих клавиш
│       └── time_utils.py            # Утилиты времени
├── assets/                          # Ресурсы (иконки)
├── docs/                            # Документация
├── projects/                        # Сохраненные проекты
└── README.md                        # Описание проекта
```

## Зависимости (requirements.txt)

```
PySide6>=6.6.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
openpyxl>=3.1.0
setuptools>=65.0.0
wheel>=0.40.0
pandas>=2.0.0
reportlab>=4.0.0
```

## Исходный код программы

### 1. main.py - Точка входа

```python
#!/usr/bin/env python3
"""
Hockey Editor Pro - Professional Video Analysis Tool
Main entry point
"""

import sys
import os

# Добавить hockey_editor в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hockey_editor'))

from PySide6.QtWidgets import QApplication
from hockey_editor.core.video_controller import VideoController
from hockey_editor.ui.main_window import MainWindow


def main():
    """Запуск приложения."""
    app = QApplication(sys.argv)
    app.setApplicationName("Hockey Editor Pro")
    app.setApplicationVersion("2.0.0")

    # Создать контроллер
    controller = VideoController()

    # Создать главное окно
    window = MainWindow(controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

### 2. core/video_controller.py - Главный контроллер видео

```python
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
            name=self.processor.filename or "Untitled",
            video_path=self.processor.path,
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
```

### 3. core/video_processor.py - Обработчик видео

```python
import cv2
import numpy as np
from typing import Optional, Tuple
import os


class VideoProcessor:
    """Управление видео через OpenCV (cv2.VideoCapture) с буферизацией текущего кадра."""

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_path: Optional[str] = None
        self.fps: float = 0.0
        self.total_frames: int = 0
        self.current_frame_idx: int = 0
        self.frame_width: int = 0
        self.frame_height: int = 0
        self._current_frame_buffer: Optional[np.ndarray] = None  # Буфер текущего кадра

    def load(self, video_path: str) -> bool:
        """Загрузить видеофайл."""
        if not os.path.exists(video_path):
            return False

        # Закрыть предыдущее видео
        self.cleanup()

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.cap = None
            return False

        self.video_path = video_path
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.current_frame_idx = 0

        # Загрузить первый кадр в буфер
        self._read_and_buffer_frame()

        return True

    def seek(self, frame_idx: int) -> bool:
        """Перемотать на кадр (БЕЗ воспроизведения)."""
        if not self.cap:
            return False

        frame_idx = max(0, min(frame_idx, self.total_frames - 1))
        ret = self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        if ret:
            self.current_frame_idx = frame_idx
            self._read_and_buffer_frame()
        return ret

    def advance_frame(self) -> bool:
        """Перейти на следующий кадр (для воспроизведения)."""
        if not self.cap:
            return False

        # Просто читаем следующий кадр
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self._current_frame_buffer = frame
            return True
        return False

    def _read_and_buffer_frame(self) -> bool:
        """Прочитать кадр с текущей позиции и сохранить в буфер."""
        if not self.cap:
            return False

        ret, frame = self.cap.read()
        if ret:
            self._current_frame_buffer = frame
            return True
        return False

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Получить текущий кадр из буфера (БЕЗ чтения)."""
        return self._current_frame_buffer

    def get_frame_at(self, frame_idx: int) -> Optional[np.ndarray]:
        """Получить кадр по индексу (вспомогательный метод)."""
        if not self.cap:
            return None

        self.seek(frame_idx)
        return self.get_current_frame()

    def get_current_time(self) -> float:
        """Получить текущее время (секунды)."""
        if self.fps == 0:
            return 0.0
        return self.current_frame_idx / self.fps

    def get_fps(self) -> float:
        """Получить FPS видео."""
        return self.fps

    def get_total_frames(self) -> int:
        """Получить общее количество кадров."""
        return self.total_frames

    def get_total_time(self) -> float:
        """Получить общую длину видео (секунды)."""
        if self.fps == 0:
            return 0.0
        return self.total_frames / self.fps

    def get_current_frame_idx(self) -> int:
        """Получить индекс текущего кадра."""
        return self.current_frame_idx

    def get_resolution(self) -> Tuple[int, int]:
        """Получить разрешение (width, height)."""
        return self.frame_width, self.frame_height

    def cleanup(self):
        """Закрыть видеофайл."""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_path = None
        self.fps = 0.0
        self.total_frames = 0
        self.current_frame_idx = 0
        self._current_frame_buffer = None

    def __del__(self):
        self.cleanup()
```

### 4. models/marker.py - Модель данных маркера

```python
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    """Устаревший enum - для backwards compatibility."""
    ATTACK = "Атака"
    DEFENSE = "Защита"
    SHIFT = "Смена"

@dataclass
class Marker:
    start_frame: int
    end_frame: int
    event_name: str  # Новое поле: имя события (например, "Attack", "Defense", "MyCustomEvent")
    note: str = ""

    def to_dict(self):
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "event_name": self.event_name,  # Сохраняем имя события
            "note": self.note
        }

    @classmethod
    def from_dict(cls, data):
        # Backwards compatibility: если есть поле "type" вместо "event_name"
        if "type" in data and "event_name" not in data:
            # Конвертировать старый enum value в имя события
            event_type_value = data["type"]
            # Маппинг старых значений на имена
            type_to_name = {
                "Атака": "Attack",
                "Защита": "Defense",
                "Смена": "Shift"
            }
            event_name = type_to_name.get(event_type_value, event_type_value)
        else:
            event_name = data.get("event_name", "Attack")  # Default to Attack

        return cls(
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            event_name=event_name,
            note=data.get("note", "")
        )
```

### 5. ui/main_window.py - Главное окно приложения

```python
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QListWidget, QListWidgetItem, QFileDialog, QComboBox, QSpinBox,
    QMessageBox, QSpinBox
)
import cv2
import numpy as np
from pathlib import Path
from .timeline_graphics import TimelineGraphicsView
from .segment_editor import SegmentEditorDialog
from .settings_dialog import SettingsDialog
from ..models.marker import EventType
from ..utils.settings_manager import get_settings_manager
from ..utils.custom_events import get_custom_event_manager
from ..utils.shortcut_manager import ShortcutManager



class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.settings_manager = get_settings_manager()
        self.event_manager = get_custom_event_manager()
        self.event_manager.setParent(self)  # Ensure proper Qt object ownership
        self.shortcut_manager = ShortcutManager(self)

        # Автосохранение
        from ..utils.autosave import AutosaveManager
        self.autosave_manager = AutosaveManager(controller)
        self.autosave_manager.autosave_completed.connect(self._on_autosave_completed)

        self.setWindowTitle("Hockey Editor Pro - Professional Video Analysis")
        self.setGeometry(0, 0, 1800, 1000)
        self.setStyleSheet(self._get_dark_stylesheet())

        # Поддержка drag-drop для видео
        self.setAcceptDrops(True)

        self.setup_ui()
        self.connect_signals()
        self._setup_shortcuts()
        self._create_menu()

    def _create_menu(self):
        """Создать меню приложения."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_action = file_menu.addAction("New Project")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_project)

        open_action = file_menu.addAction("Open Project")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_project)

        save_action = file_menu.addAction("Save Project")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_project)

        save_as_action = file_menu.addAction("Save Project As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_action.triggered.connect(self._on_save_project_as)

        file_menu.addSeparator()

        # Recent projects
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self._update_recent_menu()

        file_menu.addSeparator()

        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._on_about)

    def setup_ui(self):
        """Создать UI."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # ===== ВЕРХНЯЯ ЧАСТЬ (видео + список справа) =====
        top_layout = QHBoxLayout()

        # Видео (70%)
        video_layout = QVBoxLayout()

        # Видео виджет
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 450)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid grey;")
        video_layout.addWidget(self.video_label)

        # Контролы видео
        controls_layout = QHBoxLayout()

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMaximumWidth(80)
        self.play_btn.setToolTip("Play/Pause video (Space)")
        self.play_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)

        # Ползунок прогресса
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setToolTip("Seek to frame")
        self.progress_slider.sliderMoved.connect(self._on_progress_slider_moved)
        controls_layout.addWidget(self.progress_slider)

        # Время
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMaximumWidth(100)
        self.time_label.setToolTip("Current time / Total duration")
        controls_layout.addWidget(self.time_label)

        # Скорость (всегда 1x)
        speed_label = QLabel("1.0x")
        speed_label.setMaximumWidth(40)
        controls_layout.addWidget(speed_label)

        # Открыть видео
        open_btn = QPushButton("📁 Open")
        open_btn.setMaximumWidth(70)
        open_btn.setToolTip("Open video file (Ctrl+O)")
        open_btn.clicked.connect(self._on_open_video)
        controls_layout.addWidget(open_btn)

        video_layout.addLayout(controls_layout)
        top_layout.addLayout(video_layout, 7)

        # Список отрезков (30%)
        list_layout = QVBoxLayout()
        list_layout.addWidget(QLabel("Segments:"))

        self.markers_list = QListWidget()
        self.markers_list.itemDoubleClicked.connect(self._on_marker_double_clicked)
        list_layout.addWidget(self.markers_list)

        # Кнопки управления списком
        marker_btn_layout = QHBoxLayout()

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self._on_delete_marker)
        marker_btn_layout.addWidget(delete_btn)

        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self._on_clear_markers)
        marker_btn_layout.addWidget(clear_btn)

        list_layout.addLayout(marker_btn_layout)

        top_layout.addLayout(list_layout, 3)

        main_layout.addLayout(top_layout)

        # ===== ТАЙМЛАЙН =====
        main_layout.addWidget(QLabel("Timeline:"))
        self.timeline_widget = TimelineGraphicsView()
        self.timeline_widget.main_window = self  # Set reference for double-click
        self.timeline_widget.set_controller(self.controller)
        main_layout.addWidget(self.timeline_widget)

        # ===== КНОПКИ СОБЫТИЙ (динамические) И НАСТРОЙКИ =====
        event_layout = QHBoxLayout()

        # Контейнер для динамических кнопок событий
        self.event_buttons_layout = QHBoxLayout()
        event_layout.addLayout(self.event_buttons_layout)

        # Обновить кнопки из event_manager
        self._update_event_buttons()

        event_layout.addStretch()

        # Кнопки undo/redo
        undo_btn = QPushButton("↶ Undo")
        undo_btn.setMaximumWidth(80)
        undo_btn.setToolTip("Undo last operation (Ctrl+Z)")
        undo_btn.clicked.connect(self._on_undo_clicked)
        event_layout.addWidget(undo_btn)

        redo_btn = QPushButton("↷ Redo")
        redo_btn.setMaximumWidth(80)
        redo_btn.setToolTip("Redo last operation (Ctrl+Shift+Z)")
        redo_btn.clicked.connect(self._on_redo_clicked)
        event_layout.addWidget(redo_btn)

        # Кнопка просмотра
        preview_btn = QPushButton("👁️ Preview")
        preview_btn.setToolTip("Preview and filter segments")
        preview_btn.clicked.connect(self._on_preview_clicked)
        event_layout.addWidget(preview_btn)

        # Кнопка настроек
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.setToolTip("Open settings dialog (Ctrl+,)")
        settings_btn.clicked.connect(self._on_settings_clicked)
        event_layout.addWidget(settings_btn)

        # Кнопка экспорта
        export_btn = QPushButton("💾 Export")
        export_btn.setToolTip("Export segments to video (Ctrl+E)")
        export_btn.clicked.connect(self._on_export_clicked)
        event_layout.addWidget(export_btn)

        event_layout.addStretch()

        # Расширенный статус-бар
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #ffcc00;")
        self.status_label.setMinimumWidth(400)
        event_layout.addWidget(self.status_label)

        main_layout.addLayout(event_layout)

        central.setLayout(main_layout)

        # Подключить сигнал frame_ready для обновления видео
        self.controller.frame_ready.connect(self._on_frame_ready)

    def _create_event_button(self, text: str, color: str) -> QPushButton:
        """Создать кнопку события."""
        btn = QPushButton(text)
        btn.setMinimumSize(120, 90)
        btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid {color};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton:pressed {{
                border: 3px solid yellow;
                background-color: {self._lighten_color(color)};
            }}
        """)
        return btn

    def _lighten_color(self, color_hex: str) -> str:
        """Светлая версия цвета для hover."""
        # Простая реализация
        return color_hex.replace("00", "33").replace("8b", "bb")

    def connect_signals(self):
        """Подключить сигналы контроллера."""
        self.controller.playback_time_changed.connect(self._on_playback_time_changed)
        self.controller.markers_changed.connect(self._on_markers_changed)
        self.controller.recording_status_changed.connect(self._on_recording_status_changed)
        self.controller.timeline_update.connect(self._on_timeline_update)
        self.controller.frame_ready.connect(self._on_frame_ready)

        # Подключить сигнал изменения событий
        self.event_manager.events_changed.connect(self._on_events_changed)
        self.event_manager.events_changed.connect(self._on_events_changed_timeline)

        # Запустить автосохранение
        self.autosave_manager.start()

    def _on_play_pause_clicked(self):
        """Кнопка Play/Pause - переключение."""
        self.controller.toggle_play_pause()
        self._update_play_btn_text()

    def _update_play_btn_text(self):
        """Обновить текст кнопки Play/Pause."""
        if self.controller.playing:
            self.play_btn.setText("⏸ Pause")
        else:
            self.play_btn.setText("▶ Play")

    def _on_progress_slider_moved(self):
        """Движение ползунка прогресса."""
        frame_idx = self.progress_slider.value()
        self.controller.seek_frame(frame_idx)

    def _on_open_video(self):
        """Открыть видео."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "", "Videos (*.mp4 *.avi *.mov *.mkv);;All (*.*)"
        )
        if path:
            if self.controller.load_video(path):
                self.status_label.setText(f"✓ Loaded: {path.split('/')[-1]}")
                self._update_play_btn_text()
                self.progress_slider.setMaximum(self.controller.get_total_frames())
            else:
                QMessageBox.critical(self, "Error", "Failed to load video")

    def _on_event_btn_clicked(self, event_name: str):
        """Нажатие кнопки события."""
        self.controller.on_hotkey_pressed(event_name.upper())  # Контроллер ожидает key (строка)

    def _on_undo_clicked(self):
        """Отменить операцию."""
        self.controller.undo()
        self._on_markers_changed()

    def _on_redo_clicked(self):
        """Повторить операцию."""
        self.controller.redo()
        self._on_markers_changed()

    def _on_preview_clicked(self):
        """Открыть окно предпросмотра отрезков."""
        if not self.controller.markers:
            QMessageBox.warning(self, "Warning", "No segments to preview")
            return

        from .preview_window import PreviewWindow
        self.preview_window = PreviewWindow(self.controller, self)
        self.preview_window.show()

    def _on_settings_clicked(self):
        """Открыть настройки."""
        dialog = SettingsDialog(self.controller, self)
        if dialog.exec():
            # Переподключить горячие клавиши, если они изменились
            self._rebind_hotkeys()

    def _on_export_clicked(self):
        """Экспортировать видео."""
        if not self.controller.markers:
            QMessageBox.warning(self, "Warning", "No segments to export")
            return

        from .export_dialog import ExportDialog
        dialog = ExportDialog(self.controller, self)
        dialog.exec()

    def _on_marker_double_clicked(self, item: QListWidgetItem):
        """Двойной клик на отрезок = редактирование."""
        idx = self.markers_list.row(item)
        dialog = SegmentEditorDialog(self.controller, idx, self)
        dialog.exec()

    def _on_delete_marker(self):
        """Удалить выбранный отрезок."""
        current_idx = self.markers_list.currentRow()
        if current_idx >= 0:
            self.controller.delete_marker(current_idx)

    def _on_clear_markers(self):
        """Удалить все отрезки."""
        reply = QMessageBox.question(self, "Confirm", "Delete all segments?")
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.clear_markers()

    def _on_playback_time_changed(self, frame_idx: int):
        """Обновление при изменении времени воспроизведения."""
        fps = self.controller.get_fps()
        total_frames = self.controller.get_total_frames()

        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(frame_idx)
        self.progress_slider.blockSignals(False)

        # Обновить время
        if fps > 0:
            current_sec = frame_idx / fps
            total_sec = total_frames / fps
            self.time_label.setText(self._format_time(current_sec, total_sec))

        # Обновить расширенный статус-бар
        self._update_status_bar()

    def _on_markers_changed(self):
        """Обновление списка отрезков."""
        self.markers_list.clear()
        fps = self.controller.get_fps()

        for idx, marker in enumerate(self.controller.markers):
            start_time = self._format_time_single(marker.start_frame / fps if fps > 0 else 0)
            end_time = self._format_time_single(marker.end_frame / fps if fps > 0 else 0)
            text = f"{idx+1}. {marker.event_name} ({start_time}–{end_time})"
            self.markers_list.addItem(text)

        # Обновить расширенный статус-бар
        self._update_status_bar()

    def _on_recording_status_changed(self, event_type: str, status: str):
        """Изменение статуса записи."""
        if status == "Recording":
            self.status_label.setText(f"🔴 Recording: {event_type}")
            self.status_label.setStyleSheet("color: #ff0000;")
        elif status == "Complete":
            self.status_label.setText(f"✓ Complete: {event_type}")
            self.status_label.setStyleSheet("color: #00ff00;")
        elif status == "Fixed":
            self.status_label.setText(f"✓ Fixed: {event_type}")
            self.status_label.setStyleSheet("color: #00ff00;")
        elif status == "Cancelled":
            self.status_label.setText("⏹️ Cancelled")
            self.status_label.setStyleSheet("color: #ffcc00;")
        else:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: #ffcc00;")

    def _on_timeline_update(self):
        """Обновление таймлайна при изменении фрейма."""
        if hasattr(self.timeline_widget, 'scene_obj'):
            current_frame = self.controller.get_current_frame_idx()
            self.timeline_widget.scene_obj.update_playhead(current_frame)

    # ИСПРАВЛЕНО: удален дублированный метод _setup_shortcuts с EventType

    def _on_events_changed(self):
        """Обработка изменения событий - обновить кнопки и shortcuts."""
        self._update_event_buttons()
        self._setup_event_shortcuts()

    def _on_events_changed_timeline(self):
        """Обработка изменения событий для таймлайна."""
        if hasattr(self.timeline_widget, 'scene_obj'):
            self.timeline_widget.scene_obj.update_scene()

    def _update_event_buttons(self):
        """Обновить кнопки событий на основе CustomEventManager."""
        # Очистить существующие кнопки
        for i in reversed(range(self.event_buttons_layout.count())):
            widget = self.event_buttons_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Создать новые кнопки для каждого события
        events = self.event_manager.get_all_events()
        for event in events:
            text = f"{event.shortcut.upper()}\n{event.name}"
            btn = self._create_event_button(text, event.color)
            btn.clicked.connect(lambda checked, e=event.name: self._on_event_btn_clicked(e))
            btn.setToolTip(f"Add {event.name} event ({event.shortcut.upper()})")
            self.event_buttons_layout.addWidget(btn)

    def _setup_shortcuts(self):
        """Инициализировать горячие клавиши через ShortcutManager."""
        # Очистить старые shortcuts для событий (если есть)
        for event in self.event_manager.get_all_events():
            self.shortcut_manager.unregister_shortcut(event.name.upper())

        # Зарегистрировать shortcuts для всех событий
        self._setup_event_shortcuts()

        # Регистрировать shortcuts для основных функций
        self.shortcut_manager.register_shortcut('PLAY_PAUSE', 'Space', self._on_play_pause_clicked)
        self.shortcut_manager.register_shortcut('OPEN_VIDEO', 'Ctrl+O', self._on_open_video)
        self.shortcut_manager.register_shortcut('CANCEL', 'Escape', self._on_cancel_recording)
        self.shortcut_manager.register_shortcut('SETTINGS', 'Ctrl+,', self._on_settings_clicked)
        self.shortcut_manager.register_shortcut('EXPORT', 'Ctrl+E', self._on_export_clicked)
        self.shortcut_manager.register_shortcut('UNDO', 'Ctrl+Z', self._on_undo_clicked)
        self.shortcut_manager.register_shortcut('REDO', 'Ctrl+Shift+Z', self._on_redo_clicked)

    def _setup_event_shortcuts(self):
        """Создаёт глобальные горячие клавиши для всех событий."""
        # Очищаем старые (на всякий случай)
        if hasattr(self, '_event_shortcuts'):
            for s in self._event_shortcuts:
                s.activated.disconnect()
                s.setParent(None)
            self._event_shortcuts.clear()
        else:
            self._event_shortcuts = []

        for event in self.event_manager.get_all_events():
            if not event.shortcut:
                continue

            # Правильно захватываем переменную!
            shortcut = QShortcut(QKeySequence(event.shortcut.upper()), self)
            shortcut.activated.connect(
                lambda checked=False, ev=event: self._on_event_hotkey_pressed(ev)
            )
            self._event_shortcuts.append(shortcut)

    def _rebind_hotkeys(self):
        """Переподключить горячие клавиши после изменений в настройках."""
        # Перерегистрировать все shortcuts
        self._setup_shortcuts()

    def _on_cancel_recording(self):
        """Отмена записи (Escape)."""
        self.controller.cancel_recording()
        self._update_play_btn_text()

    def _on_event_hotkey_pressed(self, event):
        """Обрабатывает нажатие горячей клавиши события."""
        current = self.controller.active_event

        if current and current.name == event.name:
            # Это второе нажатие — завершаем отрезок
            self.controller.finish_recording()
            self._update_recording_indicator(None)
        else:
            # Первое нажатие — начинаем запись
            self.controller.start_recording(event)
            self._update_recording_indicator(event)

    def _update_recording_indicator(self, event):
        """Подсвечивает активную кнопку и статус."""
        # Сброс всех кнопок
        for btn in self.event_buttons.values():
            btn.setStyleSheet("")

        if event:
            if event.name in self.event_buttons:
                self.event_buttons[event.name].setStyleSheet(
                    "background-color: #00ff00; color: black; font-weight: bold;"
                )
            self.statusBar().showMessage(f"ЗАПИСЬ: {event.name} (нажмите {event.shortcut} снова для завершения)")
        else:
            self.statusBar().showMessage("Готов")

    def _on_selection_changed(self) -> None:
        """Handle event selection change."""
        selected = self.event_list.selectedItems()
        has_selection = len(selected) > 0

        self.edit_btn.setEnabled(has_selection)

        # Can only delete non-default events
        if has_selection:
            event_name = selected[0].data(Qt.UserRole)
            event = self.manager.get_event(event_name)

            # Проверка на None
            if event is None:
                self.delete_btn.setEnabled(False)
                return

            is_default = event.name in {e.name for e in self.manager.DEFAULT_EVENTS}
            self.delete_btn.setEnabled(has_selection and not is_default)
        else:
            self.delete_btn.setEnabled(False)

    def _update_video_frame(self):
        """Обновить видео кадр на экране (через сигнал frame_ready)."""
        pass  # Видео обновляется через frame_ready сигнал

    def _on_frame_ready(self, frame):
        """Обработка готового кадра из контроллера."""
        if frame is None:
            return

        # Конвертировать BGR в RGB
        import cv2
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Масштабировать под размер label
        pixmap = QPixmap.fromImage(qt_image)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(pixmap)

    def _format_time(self, current_sec: float, total_sec: float) -> str:
        """Форматировать время MM:SS / MM:SS."""
        def fmt(s):
            m = int(s) // 60
            s = int(s) % 60
            return f"{m:02d}:{s:02d}"
        return f"{fmt(current_sec)} / {fmt(total_sec)}"

    def _format_time_single(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _get_dark_stylesheet(self) -> str:
        """Тёмный стиль."""
        return """
        QMainWindow, QWidget {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        QPushButton {
            background-color: #333333;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #444444;
        }
        QSlider::groove:horizontal {
            background: #333333;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #ffcc00;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QListWidget {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QLabel {
            color: #ffffff;
        }
        QComboBox {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
        }
        """

    # ===== MENU HANDLERS =====

    def _on_new_project(self):
        """Создать новый проект."""
        self.controller.markers.clear()
        self.controller.markers_changed.emit()
        QMessageBox.information(self, "New Project", "Project cleared")

    def _on_open_project(self):
        """Открыть сохраненный проект."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "Hockey Editor Projects (*.hep);;All Files (*)"
        )

        if path:
            if self.controller.load_project(path):
                QMessageBox.information(self, "Success", f"Project loaded: {path}")
            else:
                QMessageBox.critical(self, "Error", f"Failed to load project: {path}")

    def _on_save_project(self):
        """Сохранить проект."""
        if not hasattr(self, 'current_project_path') or not self.current_project_path:
            self._on_save_project_as()
        else:
            if self.controller.save_project(self.current_project_path):
                QMessageBox.information(self, "Success", "Project saved")
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")

    def _on_save_project_as(self):
        """Сохранить проект как новый файл."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "Hockey Editor Projects (*.hep);;All Files (*)"
        )

        if path:
            if self.controller.save_project(path):
                self.current_project_path = path
                self.setWindowTitle(f"Hockey Editor Pro - {Path(path).name}")
                QMessageBox.information(self, "Success", "Project saved")
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")

    def _update_recent_menu(self):
        """Обновить меню недавних проектов."""
        self.recent_menu.clear()

        recent_projects = self.controller.get_recent_projects()
        if not recent_projects:
            self.recent_menu.addAction("(No recent projects)")
            return

        for path in recent_projects:
            action = self.recent_menu.addAction(Path(path).name)
            action.triggered.connect(lambda checked, p=path: self._on_recent_project(p))

    def _on_recent_project(self, path: str):
        """Открыть недавний проект."""
        if self.controller.load_project(path):
            QMessageBox.information(self, "Success", f"Project loaded: {path}")
            self._update_recent_menu()
        else:
            QMessageBox.critical(self, "Error", f"Failed to load project: {path}")

    def _on_about(self):
        """О приложении."""
        QMessageBox.information(
            self, "About Hockey Editor Pro",
            "Hockey Editor Pro v1.0\n"
            "Professional Video Analysis Tool\n\n"
            "Hotkeys:\n"
            "A - Attack\n"
            "D - Defense\n"
            "S - Shift\n"
            "Space - Play/Pause\n"
            "Ctrl+O - Open Video\n"
            "Ctrl+E - Export\n"
            "Ctrl+, - Settings"
        )

    def _on_autosave_completed(self, success: bool, message: str):
        """Обработка завершения автосохранения."""
        if success:
            self.status_label.setText(f"✓ {message}")
        else:
            print(f"Autosave error: {message}")

    def dragEnterEvent(self, event):
        """Обработка входа drag-drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Обработка drop видеофайла."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                self.controller.load_video(file_path)
                break

    def open_segment_editor(self, marker_idx: int):
        """Открыть редактор сегмента (вызывается из timeline при double-click)."""
        if 0 <= marker_idx < len(self.controller.markers):
            dialog = SegmentEditorDialog(self.controller, marker_idx, self)
            dialog.exec()

    def _update_status_bar(self):
        """Обновить расширенный статус-бар с подробной информацией."""
        fps = self.controller.get_fps()
        current_frame = self.controller.get_current_frame_idx()
        total_frames = self.controller.get_total_frames()

        if fps > 0 and total_frames > 0:
            current_time = self._format_time_single(current_frame / fps)
            total_time = self._format_time_single(total_frames / fps)
            segment_count = len(self.controller.markers)

            status = f"{current_time}/{total_time} | {segment_count} segments | FPS: {fps:.2f}"

            # Если воспроизведение, добавить индикатор
            if self.controller.playing:
                status = "▶ " + status

            self.status_label.setText(status)
        else:
            self.status_label.setText("Ready")

    def closeEvent(self, event):
        """Закрытие окна."""
        self.autosave_manager.stop()
        self.controller.cleanup()
        event.accept()
```

### 6. utils/custom_events.py - Менеджер кастомных событий

```python
"""
Custom event types manager for user-defined event categories.

Allows users to define their own event types (Attack, Defense, Shift, etc.)
with custom names and colors. Events are stored in QSettings and used
throughout the application for marker categorization.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QColor
from .settings_manager import get_settings_manager


@dataclass
class CustomEventType:
    """Represents a custom event type with metadata."""

    name: str
    color: str  # Hex color (e.g., "#FF0000")
    shortcut: str = ""  # Keyboard shortcut (e.g., "A", "Ctrl+X")
    description: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'color': self.color,
            'shortcut': self.shortcut,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CustomEventType':
        """Create from dictionary (deserialization)."""
        return cls(
            name=data.get('name', ''),
            color=data.get('color', '#CCCCCC'),
            shortcut=data.get('shortcut', ''),
            description=data.get('description', '')
        )

    def get_qcolor(self) -> QColor:
        """Get Qt color object."""
        color = QColor(self.color)
        return color if color.isValid() else QColor('#CCCCCC')


class CustomEventManager(QObject):
    """Manages user-defined event types with persistence."""

    # Сигнал об изменении событий - для обновления UI
    events_changed = Signal()

    # Default event types (always available)
    DEFAULT_EVENTS = [
        CustomEventType(name='Attack', color='#EF5350', shortcut='A', description='Offensive play'),
        CustomEventType(name='Defense', color='#42A5F5', shortcut='D', description='Defensive play'),
        CustomEventType(name='Shift', color='#66BB6A', shortcut='S', description='Line change/shift'),
    ]

    def __init__(self):
        """Initialize manager and load settings."""
        super().__init__()  # Initialize QObject base class
        self.settings = get_settings_manager()
        self._custom_events: Dict[str, CustomEventType] = {}
        self._load_events()

    def _load_events(self) -> None:
        """Load custom events from settings."""
        events_data = self.settings.load_custom_events()
        self._custom_events = {}

        # Load from settings
        for event_dict in events_data:
            event = CustomEventType.from_dict(event_dict)
            self._custom_events[event.name] = event

        # Ensure defaults exist (in case not in settings)
        for default_event in self.DEFAULT_EVENTS:
            if default_event.name not in self._custom_events:
                self._custom_events[default_event.name] = default_event

    def get_all_events(self) -> List[CustomEventType]:
        """Get all event types (sorted by name)."""
        return sorted(self._custom_events.values(), key=lambda e: e.name)

    def get_event(self, name: str) -> Optional[CustomEventType]:
        """Get specific event type by name."""
        return self._custom_events.get(name)

    def add_event(self, event: CustomEventType) -> bool:
        """Add new custom event. Returns False if name already exists."""
        if event.name in self._custom_events:
            return False

        # Validate color
        if not event.get_qcolor().isValid():
            return False

        self._custom_events[event.name] = event
        self._save_events()
        return True

    def update_event(self, old_name: str, new_event: CustomEventType) -> bool:
        """Update existing event. Returns False if new name already exists (and differs from old)."""
        if old_name not in self._custom_events:
            return False

        # Check if trying to rename to existing name
        if old_name != new_event.name and new_event.name in self._custom_events:
            return False

        # Validate color
        if not new_event.get_qcolor().isValid():
            return False

        # Remove old entry if renaming
        if old_name != new_event.name:
            del self._custom_events[old_name]

        self._custom_events[new_event.name] = new_event
        self._save_events()
        return True

    def delete_event(self, name: str) -> bool:
        """Delete custom event. Cannot delete default events."""
        if name not in self._custom_events:
            return False

        # Protect default events
        default_names = {e.name for e in self.DEFAULT_EVENTS}
        if name in default_names:
            return False

        del self._custom_events[name]
        self._save_events()
        return True

    def reset_to_defaults(self) -> None:
        """Reset all events to defaults."""
        self._custom_events = {e.name: e for e in self.DEFAULT_EVENTS}
        self._save_events()

    def _save_events(self) -> None:
        """Save custom events to settings."""
        events_data = [event.to_dict() for event in self.get_all_events()]
        self.settings.save_custom_events(events_data)
        self.events_changed.emit()  # Уведомить UI об изменениях

    def get_event_by_hotkey(self, hotkey: str) -> Optional[CustomEventType]:
        """Get event by keyboard shortcut."""
        for event in self._custom_events.values():
            if event.shortcut.upper() == hotkey.upper():
                return event
        return None

    def get_event_color(self, name: str) -> QColor:
        """Get color for event type (or gray if not found)."""
        event = self.get_event(name)
        if event:
            return event.get_qcolor()
        return QColor('#CCCCCC')  # Gray fallback

    def get_event_hotkey(self, name: str) -> str:
        """Get keyboard shortcut for event type."""
        event = self.get_event(name)
        return event.shortcut if event else ""


# Global instance
_manager: Optional[CustomEventManager] = None


def get_custom_event_manager() -> CustomEventManager:
    """Get or create global CustomEventManager instance."""
    global _manager
    if _manager is None:
        _manager = CustomEventManager()
    return _manager


def reset_custom_event_manager() -> None:
    """Reset global manager (for testing)."""
    global _manager
    _manager = None
```

### 7. utils/settings_manager.py - Менеджер настроек

```python
class SettingsManager:
    """
    Менеджер настроек приложения с использованием QSettings.
    Сохраняет все настройки в системном реестре/конфигурационных файлах.
    """

    def __init__(self):
        from PySide6.QtCore import QSettings
        self.settings = QSettings("HockeyEditor", "HockeyEditorPro")

    # ===== РЕЖИМ РАССТАНОВКИ ОТРЕЗКОВ =====

    def load_recording_mode(self) -> str:
        """Загрузить режим расстановки отрезков."""
        return self.settings.value("recording_mode", "dynamic")

    def save_recording_mode(self, mode: str):
        """Сохранить режим расстановки отрезков."""
        self.settings.setValue("recording_mode", mode)

    def load_fixed_duration(self) -> int:
        """Загрузить фиксированную длину отрезка (секунды)."""
        return int(self.settings.value("fixed_duration", 5))

    def save_fixed_duration(self, seconds: int):
        """Сохранить фиксированную длину отрезка."""
        self.settings.setValue("fixed_duration", seconds)

    def load_pre_roll(self) -> float:
        """Загрузить откат перед началом отрезка (секунды)."""
        return float(self.settings.value("pre_roll", 3.0))

    def save_pre_roll(self, seconds: float):
        """Сохранить откат перед началом отрезка."""
        self.settings.setValue("pre_roll", seconds)

    def load_post_roll(self) -> float:
        """Загрузить добавление в конец отрезка (секунды)."""
        return float(self.settings.value("post_roll", 0.0))

    def save_post_roll(self, seconds: float):
        """Сохранить добавление в конец отрезка."""
        self.settings.setValue("post_roll", seconds)

    # ===== КАСТОМНЫЕ СОБЫТИЯ =====

    def load_custom_events(self) -> list:
        """Загрузить список кастомных событий."""
        events_json = self.settings.value("custom_events", "[]")
        try:
            import json
            return json.loads(events_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def save_custom_events(self, events_data: list):
        """Сохранить список кастомных событий."""
        import json
        self.settings.setValue("custom_events", json.dumps(events_data))

    # ===== НЕДАВНИЕ ПРОЕКТЫ =====

    def load_recent_projects(self) -> list:
        """Загрузить список недавних проектов."""
        projects_json = self.settings.value("recent_projects", "[]")
        try:
            import json
            return json.loads(projects_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def save_recent_projects(self, projects: list):
        """Сохранить список недавних проектов."""
        import json
        self.settings.setValue("recent_projects", json.dumps(projects))

    # ===== НАСТРОЙКИ ЭКСПОРТА =====

    def load_export_format(self) -> str:
        """Загрузить формат экспорта."""
        return self.settings.value("export_format", "mp4")

    def save_export_format(self, format: str):
        """Сохранить формат экспорта."""
        self.settings.setValue("export_format", format)

    def load_export_quality(self) -> str:
        """Загрузить качество экспорта."""
        return self.settings.value("export_quality", "high")

    def save_export_quality(self, quality: str):
        """Сохранить качество экспорта."""
        self.settings.setValue("export_quality", quality)

    # ===== НАСТРОЙКИ ИНТЕРФЕЙСА =====

    def load_theme(self) -> str:
        """Загрузить тему интерфейса."""
        return self.settings.value("theme", "dark")

    def save_theme(self, theme: str):
        """Сохранить тему интерфейса."""
        self.settings.setValue("theme", theme)

    def load_window_geometry(self) -> bytes:
        """Загрузить геометрию окна."""
        return self.settings.value("window_geometry", b"")

    def save_window_geometry(self, geometry: bytes):
        """Сохранить геометрию окна."""
        self.settings.setValue("window_geometry", geometry)

    def load_window_state(self) -> bytes:
        """Загрузить состояние окна."""
        return self.settings.value("window_state", b"")

    def save_window_state(self, state: bytes):
        """Сохранить состояние окна."""
        self.settings.setValue("window_state", state)


# Global instance
_settings_manager = None


def get_settings_manager() -> SettingsManager:
    """Получить глобальный экземпляр SettingsManager."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
```

### 8. utils/undo_redo.py - Система отмены/повтора операций

```python
from PySide6.QtCore import QObject
from typing import List, Any
from abc import ABC, abstractmethod


class QUndoCommand(ABC):
    """Базовый класс для команд undo/redo."""

    def __init__(self):
        self.description = ""

    @abstractmethod
    def undo(self):
        """Отменить операцию."""
        pass

    @abstractmethod
    def redo(self):
        """Повторить операцию."""
        pass


class MarkerCommand(QUndoCommand):
    """Базовый класс для команд операций с маркерами."""

    def __init__(self, markers_list: List):
        super().__init__()
        self.markers = markers_list


class AddMarkerCommand(MarkerCommand):
    """Команда добавления маркера."""

    def __init__(self, markers_list: List, marker):
        super().__init__(markers_list)
        self.marker = marker
        self.description = f"Add {marker.event_name} marker"

    def undo(self):
        """Удалить маркер."""
        if self.marker in self.markers:
            self.markers.remove(self.marker)

    def redo(self):
        """Добавить маркер."""
        if self.marker not in self.markers:
            self.markers.append(self.marker)


class DeleteMarkerCommand(MarkerCommand):
    """Команда удаления маркера."""

    def __init__(self, markers_list: List, index: int):
        super().__init__(markers_list)
        self.index = index
        if 0 <= index < len(markers_list):
            self.marker = markers_list[index]
            self.description = f"Delete {self.marker.event_name} marker"
        else:
            self.marker = None

    def undo(self):
        """Восстановить маркер."""
        if self.marker and self.marker not in self.markers:
            self.markers.insert(self.index, self.marker)

    def redo(self):
        """Удалить маркер."""
        if self.marker and self.marker in self.markers:
            self.markers.remove(self.marker)


class ModifyMarkerCommand(MarkerCommand):
    """Команда изменения маркера."""

    def __init__(self, markers_list: List, index: int, old_marker, new_marker):
        super().__init__(markers_list)
        self.index = index
        self.old_marker = old_marker
        self.new_marker = new_marker
        self.description = f"Modify {old_marker.event_name} marker"

    def undo(self):
        """Восстановить старый маркер."""
        if 0 <= self.index < len(self.markers):
            self.markers[self.index] = self.old_marker

    def redo(self):
        """Применить новый маркер."""
        if 0 <= self.index < len(self.markers):
            self.markers[self.index] = self.new_marker


class ClearMarkersCommand(MarkerCommand):
    """Команда очистки всех маркеров."""

    def __init__(self, markers_list: List):
        super().__init__(markers_list)
        self.saved_markers = markers_list.copy()
        self.description = "Clear all markers"

    def undo(self):
        """Восстановить все маркеры."""
        self.markers.clear()
        self.markers.extend(self.saved_markers)

    def redo(self):
        """Удалить все маркеры."""
        self.markers.clear()


class UndoRedoManager(QObject):
    """Менеджер undo/redo операций."""

    def __init__(self, max_history: int = 50):
        super().__init__()
        self.history: List[QUndoCommand] = []
        self.current_index = -1
        self.max_history = max_history

    def push_command(self, command: QUndoCommand):
        """Добавить команду в историю."""
        # Удалить все команды после текущей позиции
        self.history = self.history[:self.current_index + 1]

        # Добавить новую команду
        self.history.append(command)
        self.current_index += 1

        # Ограничить размер истории
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.current_index -= 1

    def undo(self):
        """Отменить последнюю операцию."""
        if self.can_undo():
            command = self.history[self.current_index]
            command.undo()
            self.current_index -= 1

    def redo(self):
        """Повторить последнюю отменённую операцию."""
        if self.can_redo():
            self.current_index += 1
            command = self.history[self.current_index]
            command.redo()

    def can_undo(self) -> bool:
        """Проверить, можно ли отменить."""
        return self.current_index >= 0

    def can_redo(self) -> bool:
        """Проверить, можно ли повторить."""
        return self.current_index < len(self.history) - 1

    def clear_history(self):
        """Очистить историю команд."""
        self.history.clear()
        self.current_index = -1

    def get_undo_description(self) -> str:
        """Получить описание операции для отмены."""
        if self.can_undo():
            return self.history[self.current_index].description
        return ""

    def get_redo_description(self) -> str:
        """Получить описание операции для повтора."""
        if self.can_redo():
            return self.history[self.current_index + 1].description
        return ""
```

### 9. ui/timeline_graphics.py - Графические элементы таймлайна

```python
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem, QGraphicsScene, QGraphicsView, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PySide6.QtGui import QPen, QBrush, QColor, QFont
from typing import List, Optional
import math


class SegmentGraphicsItem(QGraphicsRectItem):
    """Интерактивный сегмент на таймлайне."""

    def __init__(self, marker, timeline_scene):
        super().__init__()
        self.marker = marker
        self.timeline_scene = timeline_scene
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsRectItem.ItemIsSelectable)

        # Цвет сегмента
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(marker.event_name)
        if event:
            color = QColor(event.color)
        else:
            color = QColor('#CCCCCC')

        # Полупрозрачный белый для завершенных сегментов
        self.setBrush(QBrush(QColor(255, 255, 255, 180)))
        self.setPen(QPen(color, 2))

        # Текст с именем события
        self.text_item = QGraphicsTextItem(marker.event_name, self)
        self.text_item.setDefaultTextColor(color)
        font = QFont("Arial", 8)
        self.text_item.setFont(font)

        # Позиционирование текста
        self.update_text_position()

    def update_text_position(self):
        """Обновить позицию текста."""
        rect = self.rect()
        text_rect = self.text_item.boundingRect()
        center_x = rect.center().x() - text_rect.width() / 2
        center_y = rect.center().y() - text_rect.height() / 2
        self.text_item.setPos(center_x, center_y)

    def hoverEnterEvent(self, event):
        """Наведение мыши."""
        self.setPen(QPen(self.pen().color(), 3))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Уход мыши."""
        self.setPen(QPen(self.pen().color(), 2))
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Двойной клик - редактирование сегмента."""
        if self.timeline_scene.main_window:
            # Найти индекс маркера
            try:
                idx = self.timeline_scene.controller.markers.index(self.marker)
                self.timeline_scene.main_window.open_segment_editor(idx)
            except ValueError:
                pass
        super().mouseDoubleClickEvent(event)


class PlayheadGraphicsItem(QGraphicsLineItem):
    """Индикатор текущей позиции воспроизведения."""

    def __init__(self):
        super().__init__()
        self.setPen(QPen(QColor('#FFFF00'), 3))  # Жёлтый playhead
        self.setZValue(100)  # Поверх всего


class TimelineGraphicsScene(QGraphicsScene):
    """QGraphicsScene для таймлайна с масштабированием."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.main_window = None  # Set by main window

        # Параметры отображения
        self.track_height = 50
        self.header_height = 30
        self.pixels_per_frame = 0.5  # Начальный масштаб

        # Элементы
        self.playhead = PlayheadGraphicsItem()
        self.addItem(self.playhead)

        # Заголовки дорожек
        self.track_headers = []

        self.update_scene()

    def update_scene(self):
        """Обновить всю сцену."""
        self.clear()
        self.addItem(self.playhead)

        # Получить события
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        events = event_manager.get_all_events()

        # Создать дорожки для каждого типа событий
        for track_idx, event in enumerate(events):
            y_pos = self.header_height + track_idx * self.track_height

            # Заголовок дорожки
            header = self.addRect(0, track_idx * self.track_height,
                                100, self.header_height,
                                QPen(Qt.black), QBrush(QColor(event.color)))
            header_text = self.addText(event.name)
            header_text.setPos(5, track_idx * self.track_height + 5)
            header_text.setDefaultTextColor(Qt.white)

            # Сегменты на этой дорожке
            for marker in self.controller.markers:
                if marker.event_name == event.name:
                    x = marker.start_frame * self.pixels_per_frame
                    width = (marker.end_frame - marker.start_frame) * self.pixels_per_frame
                    height = self.track_height - 5

                    segment = SegmentGraphicsItem(marker, self)
                    segment.setRect(x, y_pos + 2.5, width, height)
                    self.addItem(segment)

        # Обновить playhead
        self.update_playhead(self.controller.get_current_frame_idx())

    def update_playhead(self, frame_idx: int):
        """Обновить позицию playhead."""
        x = frame_idx * self.pixels_per_frame
        scene_height = len(self.controller.markers) * self.track_height + self.header_height
        self.playhead.setLine(x, 0, x, scene_height)

    def frame_to_scene_x(self, frame_idx: int) -> float:
        """Преобразовать индекс кадра в X координату сцены."""
        return frame_idx * self.pixels_per_frame

    def scene_x_to_frame(self, x: float) -> int:
        """Преобразовать X координату сцены в индекс кадра."""
        return int(x / self.pixels_per_frame)


class TimelineGraphicsView(QGraphicsView):
    """QGraphicsView для отображения таймлайна с поддержкой масштабирования."""

    def __init__(self):
        super().__init__()
        self.scene_obj = None
        self.main_window = None  # Set by main window
        self.controller = None

        # Настройки отображения
        self.setRenderHint(self.renderHints() | self.RenderHint.Antialiasing)
        self.setViewportUpdateMode(self.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Масштабирование колесом мыши
        self.setTransformationAnchor(self.ViewportAnchor.AnchorUnderMouse)
        self.scale_factor = 1.0

    def set_controller(self, controller):
        """Установить контроллер."""
        self.controller = controller
        self.scene_obj = TimelineGraphicsScene(controller)
        self.scene_obj.main_window = self.main_window
        self.setScene(self.scene_obj)

    def wheelEvent(self, event):
        """Масштабирование колесом мыши с Ctrl."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_factor = 1.2
            if event.angleDelta().y() > 0:
                # Приближение
                self.scale(zoom_factor, 1.0)
                self.scene_obj.pixels_per_frame *= zoom_factor
                self.scale_factor *= zoom_factor
            else:
                # Отдаление
                self.scale(1.0 / zoom_factor, 1.0)
                self.scene_obj.pixels_per_frame /= zoom_factor
                self.scale_factor /= zoom_factor

            # Обновить сцену
            self.scene_obj.update_scene()
        else:
            # Стандартная прокрутка
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Клик для seek."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            frame_idx = self.scene_obj.scene_x_to_frame(scene_pos.x())

            # Ограничить рамками видео
            total_frames = self.controller.get_total_frames()
            frame_idx = max(0, min(frame_idx, total_frames - 1))

            self.controller.seek_frame(frame_idx)

        super().mousePressEvent(event)
```
