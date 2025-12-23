#!/usr/bin/env python3
"""
Тест новой реализации QListView + QStyledItemDelegate для отображения карточек событий.
Проверяет, что компоненты создаются корректно и работают базовые функции.
"""

import sys
import os
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

def test_qlistview_components():
    """Тест создания QListView компонентов."""

    # Создаем QApplication если его нет
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    try:
        # Импортируем компоненты
        from hockey_editor.ui.event_list_model import MarkersListModel
        from hockey_editor.ui.event_card_delegate import EventCardDelegate
        from hockey_editor.models.marker import Marker

        print("✓ Импорт компонентов прошел успешно")

        # Создаем модель
        model = MarkersListModel()
        print("✓ MarkersListModel создан")

        # Создаем делегат
        delegate = EventCardDelegate()
        print("✓ EventCardDelegate создан")

        # Создаем тестовые маркеры
        markers = [
            Marker(start_frame=0, end_frame=100, event_name="Attack", note="Test attack"),
            Marker(start_frame=200, end_frame=300, event_name="Defense", note="Test defense"),
            Marker(start_frame=400, end_frame=500, event_name="Shift", note="")
        ]

        # Устанавливаем маркеры в модель
        model.set_fps(30.0)
        model.set_markers(markers)

        # Проверяем количество элементов
        assert model.rowCount() == 3, f"Ожидалось 3 элемента, получено {model.rowCount()}"
        print("✓ Модель содержит правильное количество элементов")

        # Проверяем данные
        for i in range(3):
            original_idx, marker = model.get_marker_at(i)
            assert marker is not None, f"Маркер {i} не найден"
            assert original_idx == i, f"Неправильный индекс: ожидалось {i}, получено {original_idx}"
        print("✓ Данные модели корректны")

        # Проверяем фильтры
        model.set_markers(markers)  # Без фильтров - все 3
        assert model.rowCount() == 3

        # Фильтр по заметкам
        model._filter_has_notes = True
        model.set_markers(markers)  # Только с заметками - 2 элемента
        assert model.rowCount() == 2, f"Ожидалось 2 элемента с заметками, получено {model.rowCount()}"
        print("✓ Фильтры работают корректно")

        # Проверяем делегат
        delegate.set_fps(30.0)
        assert delegate._fps == 30.0, "FPS не установлен в делегате"
        print("✓ Делегат настроен корректно")

        # Проверяем размер элемента
        from PySide6.QtWidgets import QStyleOptionViewItem
        from PySide6.QtCore import QModelIndex

        option = QStyleOptionViewItem()
        index = model.index(0, 0)
        size = delegate.sizeHint(option, index)

        assert size.width() == 300, f"Ширина должна быть 300, получено {size.width()}"
        assert size.height() == 80, f"Высота должна быть 80, получено {size.height()}"
        print("✓ Размер элементов корректный")

        # Проверяем поиск по индексу маркера
        row = model.find_row_by_marker_idx(1)  # Второй маркер
        assert row == 1, f"Ожидалась строка 1, получено {row}"
        print("✓ Поиск по индексу маркера работает")

        return True

    except Exception as e:
        print(f"✗ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if app:
            app.quit()

def test_preview_window_integration():
    """Тест интеграции с PreviewWindow."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    try:
        from hockey_editor.core.video_controller import VideoController
        from hockey_editor.ui.preview_window import PreviewWindow
        from hockey_editor.models.marker import Marker

        # Создаем mock контроллера
        mock_controller = Mock(spec=VideoController)
        mock_controller.markers = [
            Marker(start_frame=0, end_frame=100, event_name="Attack", note="Test"),
            Marker(start_frame=200, end_frame=300, event_name="Defense", note="")
        ]
        mock_controller.get_fps.return_value = 30.0
        mock_controller.get_playback_speed.return_value = 1.0

        # Создаем PreviewWindow
        window = PreviewWindow(mock_controller)
        print("✓ PreviewWindow создан с новой реализацией")

        # Проверяем, что QListView используется вместо QListWidget
        assert hasattr(window, 'markers_list'), "markers_list не найден"
        assert hasattr(window.markers_list, 'setModel'), "Это не QListView"
        print("✓ QListView используется вместо QListWidget")

        # Проверяем наличие модели и делегата
        assert hasattr(window, 'markers_model'), "Модель не найдена"
        assert hasattr(window, 'markers_delegate'), "Делегат не найден"
        print("✓ Модель и делегат инициализированы")

        # Проверяем, что модель подключена
        assert window.markers_list.model() == window.markers_model, "Модель не подключена к QListView"
        print("✓ Модель подключена к QListView")

        # Проверяем, что делегат подключен
        assert window.markers_list.itemDelegate() == window.markers_delegate, "Делегат не подключен к QListView"
        print("✓ Делегат подключен к QListView")

        window.close()
        return True

    except Exception as e:
        print(f"✗ Ошибка в интеграционном тесте: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if app:
            app.quit()

if __name__ == "__main__":
    print("Тестирование QListView + QStyledItemDelegate реализации...")
    print("=" * 70)

    success1 = test_qlistview_components()
    print()
    success2 = test_preview_window_integration()

    print()
    print("=" * 70)
    if success1 and success2:
        print("✓ Все тесты пройдены! QListView + QStyledItemDelegate реализация работает корректно.")
        print()
        print("Новая реализация включает:")
        print("• MarkersListModel - модель данных с фильтрацией")
        print("• EventCardDelegate - делегат для рисования карточек")
        print("• QListView вместо QListWidget для лучшей производительности")
        print("• QPainter для кастомного рисования карточек")
        print("• Обработка кликов на кнопках через editorEvent")
        print("• Поддержка выделения активной карточки")
        print()
        print("Теперь карточки событий отображаются более эффективно и стильно!")
        sys.exit(0)
    else:
        print("✗ Некоторые тесты не пройдены.")
        sys.exit(1)
