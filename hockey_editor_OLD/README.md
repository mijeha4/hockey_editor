# Hockey Editor - инструмент анализа видео хоккейных матчей

Покадровый анализ хоккейных матчей с поддержкой 13 типов игровых событий и возможностью создания собственных категорий.

## Основной функционал

- **Видеоплеер**: Управление воспроизведением и перемоткой
  ```python
  controller.load_video("game.mp4")
  controller.play()  # или pause(), seek_frame(100)
  ```

- **Маркеры событий**: Создание и управление сегментами с горячими клавишами
  ```python
  controller.on_hotkey_pressed("G")  # Гол
  controller.on_hotkey_pressed("Z")  # Вход в зону
  ```

- **Интерактивный таймлайн**: Визуализация событий с цветными дорожками
  ```python
  # Каждый тип события имеет свою цветную дорожку
  timeline_scene.rebuild()  # Перестроение таймлайна
  ```

- **Предпросмотр сегментов**: Просмотр и фильтрация отмеченных отрезков
  ```python
  preview_window = PreviewWindow(controller, main_window)
  preview_window.show()
  ```

- **Экспорт**: Сохранение сегментов в видео форматы
  ```python
  exporter.export_segments(controller.markers, "output.mp4")
  ```

- **Система проектов**: Сохранение и загрузка анализа
  ```python
  controller.save_project("analysis.hep")
  controller.load_project("saved.hep")
  ```

- **Undo/Redo**: Отмена и повтор операций
  ```python
  controller.undo()
  controller.redo()
  ```

- **Настраиваемые события**: Создание собственных типов событий
  ```python
  event_manager.add_event(CustomEventType("Custom", "#FF0000", "C"))
  ```

## Стек технологий

Python, PySide6, OpenCV, NumPy, Pillow, OpenPyXL, Pandas, ReportLab, MoviePy

## Установка и запуск

```bash
# Клонирование репозитория
git clone https://github.com/mijeha4/hockey_editor.git
cd hockey_editor

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python main.py
```

## Примеры использования

### Основной workflow

1. **Загрузка видео**: Перетащите файл или используйте Ctrl+O
2. **Анализ матча**: Нажимайте горячие клавиши во время просмотра:
   - **G** - Гол
   - **H** - Бросок в створ
   - **M** - Бросок мимо
   - **B** - Заблокированный бросок
   - **Z** - Вход в зону
   - **X** - Выход из зоны
   - **D** - Вброс
   - **T** - Потеря
   - **A** - Перехват
   - **F** - Вбрасывание выиграно
   - **L** - Вбрасывание проиграно
   - **K** - Блокшот в обороне
   - **P** - Удаление

3. **Просмотр таймлайна**: Каждый тип события отображается на своей цветной дорожке
4. **Экспорт сегментов**: Выберите нужные отрезки и сохраните в видео файл

### Настройка событий

В настройках можно добавить собственные типы событий с уникальными горячими клавишами и цветами.
