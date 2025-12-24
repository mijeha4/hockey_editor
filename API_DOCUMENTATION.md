# Документация API Hockey Editor

## Обзор

Данная документация описывает внутреннюю архитектуру приложения Hockey Editor, включая контроллеры, сервисы и модели данных. Документация предназначена для понимания бизнес-логики и разработки интерфейса приложения.

## Архитектура

Приложение построено по принципу MVC (Model-View-Controller) с дополнительным слоем сервисов:

- **Models** - модели данных и конфигурации
- **Services** - бизнес-логика и инфраструктурные сервисы
- **Controllers** - контроллеры, управляющие взаимодействием между UI и бизнес-логикой
- **Views** - пользовательский интерфейс (не описан в данной документации)

## Модели данных (Models)

### Domain Models

#### Marker
Модель маркера события в видео.

**Атрибуты:**
- `start_frame: int` - начальный кадр события
- `end_frame: int` - конечный кадр события
- `event_name: str` - имя события (например, "Attack", "Defense", "MyCustomEvent")
- `note: str` - дополнительная заметка (по умолчанию пустая строка)

**Методы:**
- `to_dict() -> Dict[str, Any]` - сериализация в словарь
- `from_dict(data: Dict[str, Any]) -> Marker` - десериализация из словаря

#### Project
Модель проекта Hockey Editor.

**Атрибуты:**
- `name: str` - имя проекта
- `video_path: str` - путь к видеофайлу
- `fps: float` - частота кадров видео (по умолчанию 30.0)
- `markers: List[Marker]` - список маркеров событий
- `created_at: str` - дата создания (ISO формат)
- `modified_at: str` - дата последнего изменения (ISO формат)
- `version: str` - версия проекта (по умолчанию "1.0")

**Методы:**
- `to_dict() -> Dict[str, Any]` - сериализация в словарь
- `from_dict(data: Dict[str, Any]) -> Project` - десериализация из словаря

#### EventType
Модель типа события с локализацией.

**Атрибуты:**
- `name: str` - имя события
- `color: str` - цвет в hex формате (например, "#FF0000")
- `shortcut: str` - горячая клавиша
- `description: str` - описание события

**Методы:**
- `to_dict() -> Dict[str, Any]` - сериализация в словарь
- `from_dict(data: Dict[str, Any]) -> EventType` - десериализация из словаря
- `get_localized_name() -> str` - получение локализованного имени
- `get_localized_description() -> str` - получение локализованного описания

### Configuration Models

#### AppSettings
Модель настроек приложения.

**Атрибуты:**
- `default_events: List[EventType]` - список стандартных событий (13 типов)
- `hotkeys: Dict[str, str]` - горячие клавиши для режимов
- `recording_mode: str` - режим записи ("dynamic" или "fixed_length")
- `fixed_duration_sec: int` - фиксированная длительность в секундах
- `pre_roll_sec: float` - время до события
- `post_roll_sec: float` - время после события
- `track_colors: Dict[str, str]` - цвета дорожек
- `window_x, window_y, window_width, window_height: int` - позиция и размер окна
- `autosave_enabled: bool` - включено ли автосохранение
- `autosave_interval_minutes: int` - интервал автосохранения
- `recent_projects: List[str]` - список последних проектов
- `custom_events: List[Dict]` - пользовательские события
- `language: str` - язык интерфейса
- `playback_speed: float` - скорость воспроизведения

**Методы:**
- `to_dict() -> Dict` - сериализация в словарь
- `from_dict(data: Dict) -> AppSettings` - десериализация из словаря

## Сервисы (Services)

### History Services

#### Command (Interface)
Абстрактный базовый класс для команд в системе undo/redo.

**Атрибуты:**
- `description: str` - описание команды

**Методы:**
- `execute()` - выполнить команду (абстрактный)
- `undo()` - отменить команду (абстрактный)

#### HistoryManager
Менеджер истории команд для реализации undo/redo.

**Атрибуты:**
- `undo_stack: List[Command]` - стек команд для отмены
- `redo_stack: List[Command]` - стек команд для повтора
- `max_history: int` - максимальный размер истории

**Методы:**
- `execute_command(command: Command)` - выполнить команду и добавить в историю
- `undo()` - отменить последнюю команду
- `redo()` - повторить отменённую команду
- `can_undo() -> bool` - проверить возможность отмены
- `can_redo() -> bool` - проверить возможность повтора
- `clear_history()` - очистить всю историю

### Serialization Services

#### ProjectIO
Сервис для сохранения и загрузки проектов.

**Методы:**
- `save_project(project: Project, filepath: str) -> bool` - сохранить проект в JSON файл
- `load_project(filepath: str) -> Optional[Project]` - загрузить проект из JSON файла

### Export Services

#### VideoExporter
Сервис для экспорта видео сегментов.

**Основные методы:**
- `export_segments(video_path: str, markers: List[Marker], fps: float, output_path: str, codec: str = "libx264", quality: int = 23, resolution: Optional[str] = None, include_audio: bool = True, merge_segments: bool = True) -> bool`

**Параметры экспорта:**
- `video_path` - путь к исходному видео
- `markers` - список маркеров для экспорта
- `fps` - частота кадров
- `output_path` - путь для сохранения
- `codec` - кодек видео ("libx264", "copy", etc.)
- `quality` - качество (CRF 0-51)
- `resolution` - разрешение ("source", "2160p", "1080p", "720p", etc.)
- `include_audio` - включать ли аудио
- `merge_segments` - объединять ли сегменты

**Внутренние методы:**
- `_export_with_copy()` - быстрый экспорт без перекодирования
- `_export_with_moviepy()` - экспорт с перекодированием
- `_concatenate_segments()` - объединение сегментов
- `_export_separate_files()` - экспорт в отдельные файлы

## Контроллеры (Controllers)

### Main Controller

#### MainController
Главный контроллер приложения, управляющий основным потоком работы.

**Атрибуты:**
- Ссылки на все основные компоненты приложения

**Методы:**
- `__init__()` - инициализация контроллера
- `_setup_connections()` - настройка сигналов и слотов
- `run()` - запуск приложения
- `load_video(path: str) -> bool` - загрузка видео
- `add_marker(start_frame: int, end_frame: int, event_name: str)` - добавление маркера
- `_on_key_pressed(key: str)` - обработка нажатия клавиш
- `_on_open_video()` - открытие видео файла
- `_on_save_project()` - сохранение проекта
- `_on_load_project()` - загрузка проекта
- `_on_new_project()` - создание нового проекта
- `_on_open_settings()` - открытие настроек
- `_on_export()` - экспорт видео
- `_on_settings_saved(new_settings: AppSettings)` - применение новых настроек

### Playback Controller

#### PlaybackController (QObject)
Контроллер управления воспроизведением видео.

**Атрибуты:**
- `video_service` - сервис работы с видео
- `current_frame` - текущий кадр
- `is_playing` - статус воспроизведения

**Методы:**
- `__init__(video_service, ...)` - инициализация
- `load_video(video_path: str) -> bool` - загрузка видео
- `play()` - начать воспроизведение
- `pause()` - приостановить воспроизведение
- `seek_to_frame(frame_idx: int)` - перейти к кадру
- `_on_playback_tick()` - обработка тика воспроизведения
- `_display_current_frame()` - отображение текущего кадра
- `_numpy_to_pixmap(frame: np.ndarray) -> QPixmap` - конвертация кадра

### Project Controller

#### ProjectController
Контроллер управления проектами.

**Атрибуты:**
- `project_io: ProjectIO` - сервис ввода-вывода проектов

**Методы:**
- `__init__(project_io: ProjectIO)` - инициализация
- `new_project(name: str = "Untitled") -> Project` - создание нового проекта
- `save_project(filepath: str) -> bool` - сохранение проекта
- `load_project(filepath: str) -> Project` - загрузка проекта
- `get_current_project() -> Project` - получение текущего проекта

### Timeline Controller

#### TimelineController
Контроллер управления таймлайном и маркерами.

**Атрибуты:**
- `project: Project` - текущий проект
- `history_manager: HistoryManager` - менеджер истории
- `settings: AppSettings` - настройки приложения

**Методы:**
- `__init__(project, history_manager, settings, ...)` - инициализация
- `handle_hotkey(hotkey: str, current_frame: int, fps: float) -> None` - обработка горячих клавиш
- `_find_event_by_hotkey(hotkey: str) -> str` - поиск события по горячей клавише
- `_handle_dynamic_mode(event_name: str, current_frame: int, fps: float)` - обработка динамического режима
- `_handle_fixed_length_mode(event_name: str, current_frame: int, fps: float)` - обработка режима фиксированной длины
- `add_marker(start_frame: int, end_frame: int, event_name: str, note: str = "")` - добавление маркера
- `_on_marker_clicked(marker_id: int)` - клик по маркеру
- `_on_segment_selected(segment_id: int)` - выбор сегмента
- `refresh_view()` - обновление представления
- `init_tracks(total_frames: int)` - инициализация дорожек

#### AddMarkerCommand (Command)
Команда добавления маркера.

**Атрибуты:**
- `project: Project` - проект
- `marker: Marker` - маркер для добавления

**Методы:**
- `execute()` - выполнить добавление
- `undo()` - отменить добавление

## Режимы работы

### Режимы расстановки маркеров

#### Dynamic Mode (Динамический)
- Два нажатия клавиши = начало и конец события
- Позволяет создавать события произвольной длины

#### Fixed Length Mode (Фиксированная длина)
- Одно нажатие = событие фиксированной длины
- Длина задаётся в настройках (`fixed_duration_sec`)
- Поддерживает pre-roll и post-roll

### Типы событий

Стандартные события (13 типов):
1. **Goal** - Гол
2. **Shot on Goal** - Бросок в створ
3. **Missed Shot** - Бросок мимо
4. **Blocked Shot** - Заблокированный бросок
5. **Zone Entry** - Вход в зону
6. **Zone Exit** - Выход из зоны
7. **Dump In** - Вброс
8. **Turnover** - Потеря
9. **Takeaway** - Перехват
10. **Faceoff Win** - Вбрасывание: Победа
11. **Faceoff Loss** - Вбрасывание: Поражение
12. **Defensive Block** - Блокшот в обороне
13. **Penalty** - Удаление

## Система команд (Undo/Redo)

- Все изменения состояния проекта выполняются через команды
- Поддерживается история операций с возможностью отмены/повтора
- Максимальный размер истории настраивается (по умолчанию 50)

## Сериализация

- Проекты сохраняются в JSON формате
- Поддерживается версионирование проектов
- Метаданные включают время создания и изменения

## Экспорт видео

- Поддержка различных кодеков (H.264, H.265, копирование без изменений)
- Настраиваемое качество и разрешение
- Возможность объединения сегментов или экспорта по отдельности
- Поддержка аудио
- Быстрый режим экспорта без перекодирования
