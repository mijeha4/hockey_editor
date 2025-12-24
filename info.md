## Спецификация миграции логики событий

На основе анализа файлов `video_controller.py`, `event_creation_controller.py` и `marker.py` составлена спецификация логики создания событий, которую необходимо перенести в новую архитектуру.

### 1. Режимы записи (Recording Modes)

Поддерживаются два режима:

__DYNAMIC__ ("dynamic"):

- Два последовательных нажатия одной и той же горячей клавиши определяют начало и конец события
- Первое нажатие начинает запись, второе завершает
- Между нажатиями состояние `is_recording = True`

__FIXED_LENGTH__ ("fixed_length"):

- Одно нажатие клавиши создает событие фиксированной длительности
- Длительность задается в секундах (`fixed_duration_sec`)

Оба режима используют настройки из `SettingsManager` и сохраняются между сессиями.

### 2. Тайминг (Timing)

__Расчет start_frame и end_frame:__

Для __DYNAMIC__ режима:

```javascript
pre_roll_frames = max(0, int(pre_roll_sec * fps))
start_frame = max(0, recording_start_frame - pre_roll_frames)
end_frame = current_frame  # кадр второго нажатия
```

Для __FIXED_LENGTH__ режима:

```javascript
fixed_frames = int(fixed_duration_sec * fps)
pre_roll_frames = max(0, int(pre_roll_sec * fps))
start_frame = max(0, current_frame - pre_roll_frames)
end_frame = min(total_frames - 1, current_frame + fixed_frames - pre_roll_frames)
```

__Pre-roll и Post-roll:__

- `pre_roll_sec`: время в секундах для отката назад от точки нажатия
- `post_roll_sec`: настраивается, но в текущей логике не используется для расчета границ
- Значения хранятся в настройках и конвертируются в кадры по формуле: `frames = int(seconds * fps)`

### 3. Обработка клавиш

__Механизм обработки:__

- Горячие клавиши делегируются от `VideoController` к `EventCreationController.on_hotkey_pressed()`
- Для каждой клавиши ищется соответствующее событие через `CustomEventManager.get_event_by_hotkey()`
- Если событие найдено, вызывается соответствующий обработчик режима

__Debounce:__

- Явного механизма предотвращения повторных нажатий не реализовано
- В DYNAMIC режиме повторное нажатие той же клавиши завершает запись

### 4. Данные Marker

При создании заполняются поля:

- `start_frame`: рассчитанный начальный кадр
- `end_frame`: рассчитанный конечный кадр
- `event_name`: имя события из `CustomEventManager` (например "Attack", "Defense")
- `note`: пустая строка по умолчанию

### Архитектурные замечания для миграции

__В timeline_controller.py__ перенести:

- Логику обработки горячих клавиш
- Расчеты тайминга (start_frame, end_frame)
- Управление состояниями записи (is_recording, recording_start_frame)

__В main_controller.py__ перенести:

- Интеграцию с CustomEventManager
- Управление настройками (pre_roll, post_roll, fixed_duration)
- Создание и добавление Marker объектов

__Ключевые зависимости:__

- Доступ к текущему кадру видео
- FPS видео для конвертации секунд в кадры
- CustomEventManager для маппинга клавиш на события
- SettingsManager для персистентности настроек

## Отчет по миграции настроек

На основе анализа файлов `custom_event_manager.py`, `custom_event_type.py` и `settings_manager.py` составлен отчет по системе настроек старого проекта.

### 1. Типы событий

__Источник данных:__

- Список событий загружается из QSettings через `CustomEventManager.load_custom_events()`
- Дефолтные события определены в коде как `DEFAULT_EVENTS` (13 предустановленных событий)
- Пользовательские события сохраняются в настройках и дополняют дефолтные

__Дефолтные события:__

- Goal, Shot on Goal, Missed Shot, Blocked Shot
- Zone Entry, Zone Exit, Dump In
- Turnover, Takeaway, Faceoff Win, Faceoff Loss
- Defensive Block, Penalty

### 2. Структура события

Каждый тип события (`CustomEventType`) имеет атрибуты:

- `name`: str - уникальное имя события
- `color`: str - hex-код цвета (например "#FF0000")
- `shortcut`: str - клавиша быстрого доступа (например "G", "H")
- `description`: str - описание события

Дополнительно поддерживается локализация названий и описаний для дефолтных событий.

### 3. Глобальные настройки

__Сохраненные параметры:__

- __Режимы записи:__ recording_mode, fixed_duration_sec, pre_roll_sec, post_roll_sec
- __UI:__ window_x/y/width/height, language
- __Воспроизведение:__ playback_speed
- __Автосохранение:__ autosave_enabled, autosave_interval_minutes
- __Проекты:__ recent_projects (список последних 10 проектов)
- __События:__ custom_events (список пользовательских событий)

__Устаревшие поля:__

- `hotkeys` - заменено на shortcuts внутри custom_events
- `track_colors` - заменено на colors внутри custom_events

### Рекомендации для `src/models/config/app_settings.py`

__Текущий статус:__ ✅ Все необходимые поля уже присутствуют

__Дополнительные поля для рассмотрения:__

```python
# Дефолтные события (можно реализовать в сервисе настроек)
default_events: List[Dict] = field(default_factory=lambda: [
    {'name': 'Goal', 'color': '#FF0000', 'shortcut': 'G', 'description': 'Goal scored'},
    # ... остальные дефолтные события
])

# Локализация (если нужна поддержка мультиязычности)
localization_enabled: bool = True
```

__Архитектурные замечания:__

- __CustomEventManager__ должен быть перенесен в новый сервис для управления событиями
- __SettingsManager__ (QSettings) должен быть заменен на файловое хранилище (JSON/TOML)
- Локализация названий событий должна быть реализована через отдельный сервис
- Валидация уникальности shortcuts должна быть сохранена

__Миграционная стратегия:__

1. Создать `EventTypeService` для управления типами событий
2. Реализовать `SettingsService` с файловым хранилищем
3. Перенести дефолтные события в сервис
4. Обеспечить обратную совместимость при загрузке старых проектов

## Анализ управления воспроизведением

На основе анализа `video_controller.py` и `player_controls.py`, а также результатов поиска по коду, составлена спецификация функционала воспроизведения.

### 1. Скорости воспроизведения

__Поддерживаемые скорости:__

- Доступные значения: 0.25x, 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x, 3.0x, 4.0x
- Регулировка через combo box в PlayerControls
- Кнопки ⏪/⏩ для пошагового изменения скорости
- Скорость сохраняется в настройках (`playback_speed`)
- Влияет на `frame_time_ms = int(1000 / (fps * playback_speed))`

### 2. Навигация

__Перемотка по времени:__

- __Стрелки Left/Right__: перемотка на ±5 секунд
- __Shift + стрелки__: не реализована в основной навигации

__Покадровая перемотка:__

- __Left/Right стрелки__: ±1 кадр (в instance_edit_window)
- __Клавиши J/L__: ±1 кадр (в instance_edit_window)
- __Shift + Left/Right__: ±10 кадров (в instance_edit_window)

__Специальные окна:__

- В `preview_window.py`: Left/Right стрелки перематывают на ±1 секунду (fps кадров)

### 3. Особенности

__Тайминг воспроизведения:__

- Используется QTimer с интервалом `frame_time_ms`
- Синхронизация с FPS видео: `frame_time_ms = int(1000 / (fps * playback_speed))`
- При достижении конца видео автоматически останавливается

__Состояние воспроизведения:__

- `playing` флаг управляет запуском/остановкой таймера
- `toggle_play_pause()` переключает состояние
- `stop()` останавливает и перематывает в начало

__Отсутствующие особенности:__

- Нет "умной" паузы или синхронизации звука
- Нет переменной скорости (только фиксированные значения)
- Нет плавной перемотки (только дискретные шаги)

### Архитектурные замечания для миграции

__В playback_controller.py перенести:__

- Логику управления скоростью воспроизведения
- Расчет frame_time_ms на основе FPS и скорости
- Управление QTimer для воспроизведения
- Методы play/pause/stop/seek

__Клавиши навигации:__

- Left/Right: ±5 секунд (главное окно)
- J/L: ±1 кадр (редактирование)
- Shift+Left/Right: ±10 кадров (редактирование)

__Интеграция:__

- С playback_controller должны интегрироваться timeline_controller (для синхронизации) и main_controller (для обработки клавиш)
- Скорость должна сохраняться через settings service
