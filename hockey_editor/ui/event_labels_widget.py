"""
Compact event labels widget with multi-row layout and collapsible panel.

Provides a space-efficient way to display event type buttons with tooltips,
multi-row organization, and show/hide functionality.
"""

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QRect, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QFrame, QLabel, QSizePolicy
)
from ..utils.custom_events import get_custom_event_manager
from ..utils.localization_manager import get_localization_manager


class CompactEventButton(QPushButton):
    """Compact button showing first letter of event with tooltip."""

    def __init__(self, event_obj, parent=None):
        super().__init__(parent)
        self.event_obj = event_obj
        self.setFixedSize(42, 42)  # Увеличенный размер для лучшей видимости

        # Первая буква или иконка
        first_letter = event_obj.name[0].upper() if event_obj.name else "?"
        self.setText(first_letter)

        # Установка цвета фона через палитру вместо stylesheet
        from PySide6.QtGui import QPalette
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Button, QColor(event_obj.color))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Tooltip с локализованным названием и горячей клавишей
        localized_name = event_obj.get_localized_name()
        localized_desc = event_obj.get_localized_description()

        tooltip = localized_name
        if event_obj.shortcut:
            tooltip += " (" + event_obj.shortcut.upper() + ")"
        if localized_desc:
            tooltip += "\n" + localized_desc
        self.setToolTip(tooltip)

    def _lighten_color(self, color_hex: str) -> str:
        """Светлая версия цвета для hover."""
        try:
            color = QColor(color_hex)
            color = color.lighter(120)
            return color.name()
        except:
            return color_hex

    def _darken_color(self, color_hex: str, factor: float = 1.2) -> str:
        """Тёмная версия цвета для pressed с настраиваемым фактором."""
        try:
            color = QColor(color_hex)
            color = color.darker(int(100 * factor))
            return color.name()
        except:
            return color_hex


class EventLabelsWidget(QWidget):
    """Widget for displaying event labels in compact multi-row layout."""

    # Сигнал при нажатии на кнопку события
    event_button_clicked = Signal(str)  # event_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.event_manager = get_custom_event_manager()
        self.localization = get_localization_manager()
        self.is_collapsed = False
        self.button_size = 42  # Размер кнопки
        self.button_spacing = 6  # Расстояние между кнопками
        self.max_buttons_per_row = 8  # Начальное значение, будет адаптировано

        self.setup_ui()
        self.connect_signals()
        self.update_event_buttons()

    def setup_ui(self):
        """Создание UI."""
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Заголовок с кнопкой сворачивания
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.toggle_button = QPushButton("▼")
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.toggle_button.setToolTip("Hide/Show event labels")
        self.toggle_button.clicked.connect(self.toggle_panel)
        header_layout.addWidget(self.toggle_button)

        main_layout.addLayout(header_layout)

        # Контейнер для кнопок с прокруткой
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setMaximumHeight(200)  # Увеличенное ограничение высоты
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #888888;
            }
        """)

        # Виджет-контейнер для кнопок
        self.buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(2)

        self.scroll_area.setWidget(self.buttons_container)
        main_layout.addWidget(self.scroll_area)

    def connect_signals(self):
        """Подключение сигналов."""
        self.event_manager.events_changed.connect(self.update_event_buttons)
        self.localization.language_changed.connect(self.retranslate_ui)

    def update_event_buttons(self):
        """Обновление кнопок событий."""
        # Очистка существующих кнопок
        for i in reversed(range(self.buttons_layout.count())):
            layout_item = self.buttons_layout.itemAt(i)
            if layout_item.widget():
                layout_item.widget().setParent(None)
            elif layout_item.layout():
                # Очистка вложенных layout'ов
                sub_layout = layout_item.layout()
                for j in reversed(range(sub_layout.count())):
                    sub_item = sub_layout.itemAt(j)
                    if sub_item.widget():
                        sub_item.widget().setParent(None)
                self.buttons_layout.removeItem(layout_item)

        # Получение всех событий
        events = self.event_manager.get_all_events()

        # Адаптивное определение количества кнопок в ряду на основе ширины виджета
        available_width = self.width() if self.width() > 200 else 400  # Минимальная ширина
        max_buttons = max(5, (available_width - 20) // (self.button_size + self.button_spacing))
        self.max_buttons_per_row = min(max_buttons, 12)  # Ограничение максимума

        # Распределение по рядам
        current_row_layout = None
        buttons_in_current_row = 0

        for event in events:
            # Создание нового ряда при необходимости
            if current_row_layout is None or buttons_in_current_row >= self.max_buttons_per_row:
                current_row_layout = QHBoxLayout()
                current_row_layout.setContentsMargins(0, 0, 0, 0)
                current_row_layout.setSpacing(self.button_spacing)
                self.buttons_layout.addLayout(current_row_layout)
                buttons_in_current_row = 0

            # Создание кнопки
            button = CompactEventButton(event)
            button.clicked.connect(lambda checked, e=event.name: self.event_button_clicked.emit(e))
            current_row_layout.addWidget(button)
            buttons_in_current_row += 1

        # Добавление stretch в последний ряд для выравнивания
        if current_row_layout:
            current_row_layout.addStretch()

        self.update_visibility()

    def toggle_panel(self):
        """Переключение видимости панели."""
        self.is_collapsed = not self.is_collapsed

        # Анимация
        self.animation = QPropertyAnimation(self.scroll_area, b"maximumHeight")
        if self.is_collapsed:
            self.animation.setStartValue(self.scroll_area.maximumHeight())
            self.animation.setEndValue(0)
            self.toggle_button.setText("▶")
            self.toggle_button.setToolTip("Show event labels")
        else:
            self.animation.setStartValue(0)
            self.animation.setEndValue(200)
            self.toggle_button.setText("▼")
            self.toggle_button.setToolTip("Hide event labels")

        self.animation.setDuration(200)
        self.animation.start()

    def update_visibility(self):
        """Обновление видимости в зависимости от состояния сворачивания."""
        if self.is_collapsed:
            self.scroll_area.setMaximumHeight(0)
            self.toggle_button.setText("▶")
        else:
            self.scroll_area.setMaximumHeight(200)
            self.toggle_button.setText("▼")

    def set_max_buttons_per_row(self, max_buttons: int):
        """Установка максимального количества кнопок в ряду."""
        self.max_buttons_per_row = max(max_buttons, 5)
        self.update_event_buttons()

    def get_preferred_height(self) -> int:
        """Получение предпочтительной высоты виджета."""
        if self.is_collapsed:
            return 25  # Только заголовок
        else:
            # Расчёт на основе количества рядов
            events_count = len(self.event_manager.get_all_events())
            rows_count = (events_count + self.max_buttons_per_row - 1) // self.max_buttons_per_row
            row_height = self.button_size + 4  # Высота ряда с учетом spacing
            return 25 + min(rows_count * row_height, 200)  # Заголовок + ряды (с ограничением)

    def retranslate_ui(self):
        """Перевести интерфейс виджета."""
        self.title_label.setText(self.localization.tr("widget_event_labels"))
        self.toggle_button.setToolTip(self.localization.tr("widget_toggle_hide") if self.is_collapsed else self.localization.tr("widget_toggle_show"))
        # Обновить все кнопки событий с новыми переводами
        self.update_event_buttons()

    def resizeEvent(self, event):
        """Обработка изменения размера виджета."""
        super().resizeEvent(event)
        # Перерасчет количества кнопок в ряду при изменении ширины
        self.update_event_buttons()
