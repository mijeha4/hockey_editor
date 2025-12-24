from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QPushButton, QDialogButtonBox, QColorDialog, QLineEdit,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.config.app_settings import AppSettings, EventType, RecordingMode
except ImportError:
    # Для случаев, когда запускаем из src/
    from ...models.config.app_settings import AppSettings, EventType, RecordingMode


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""

    # Сигнал при сохранении настроек
    settings_saved = Signal(AppSettings)

    def __init__(self, current_settings: AppSettings, parent=None):
        super().__init__(parent)

        self.current_settings = current_settings
        self.modified_settings = AppSettings(
            default_events=current_settings.default_events.copy(),
            recording_mode=current_settings.recording_mode,
            pre_roll_sec=current_settings.pre_roll_sec,
            fixed_duration_sec=current_settings.fixed_duration_sec,
            post_roll_sec=current_settings.post_roll_sec,
            playback_speed=current_settings.playback_speed,
            language=current_settings.language
        )

        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(600, 500)

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QVBoxLayout(self)

        # Вкладки
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Вкладка General
        self._create_general_tab()

        # Вкладка Events
        self._create_events_tab()

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_general_tab(self):
        """Создать вкладку General."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Режим записи
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Recording Mode:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Dynamic", RecordingMode.DYNAMIC)
        self.mode_combo.addItem("Fixed Length", RecordingMode.FIXED_LENGTH)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Pre-roll
        pre_roll_layout = QHBoxLayout()
        pre_roll_layout.addWidget(QLabel("Pre-roll (seconds):"))

        self.pre_roll_spin = QSpinBox()
        self.pre_roll_spin.setRange(0, 60)
        self.pre_roll_spin.setValue(3)
        pre_roll_layout.addWidget(self.pre_roll_spin)
        pre_roll_layout.addStretch()
        layout.addLayout(pre_roll_layout)

        # Post-roll
        post_roll_layout = QHBoxLayout()
        post_roll_layout.addWidget(QLabel("Post-roll (seconds):"))

        self.post_roll_spin = QSpinBox()
        self.post_roll_spin.setRange(0, 60)
        self.post_roll_spin.setValue(0)
        post_roll_layout.addWidget(self.post_roll_spin)
        post_roll_layout.addStretch()
        layout.addLayout(post_roll_layout)

        # Fixed duration
        fixed_duration_layout = QHBoxLayout()
        fixed_duration_layout.addWidget(QLabel("Fixed Duration (seconds):"))

        self.fixed_duration_spin = QSpinBox()
        self.fixed_duration_spin.setRange(1, 300)
        self.fixed_duration_spin.setValue(10)
        fixed_duration_layout.addWidget(self.fixed_duration_spin)
        fixed_duration_layout.addStretch()
        layout.addLayout(fixed_duration_layout)

        layout.addStretch()
        self.tab_widget.addTab(tab, "General")

    def _create_events_tab(self):
        """Создать вкладку Events."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Таблица событий
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(3)
        self.events_table.setHorizontalHeaderLabels(["Name", "Color", "Hotkey"])

        # Настройка заголовков
        header = self.events_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Color
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Hotkey

        self.events_table.setColumnWidth(1, 60)  # Color button width
        self.events_table.setColumnWidth(2, 60)  # Hotkey width

        layout.addWidget(self.events_table)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Event")
        self.add_button.clicked.connect(self._on_add_event)
        buttons_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Event")
        self.remove_button.clicked.connect(self._on_remove_event)
        buttons_layout.addWidget(self.remove_button)

        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self._on_reset_events)
        buttons_layout.addWidget(self.reset_button)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self.tab_widget.addTab(tab, "Events")

    def _load_current_settings(self):
        """Загрузить текущие настройки в UI."""
        # General settings
        if self.current_settings.recording_mode == "dynamic":
            self.mode_combo.setCurrentIndex(0)
        else:
            self.mode_combo.setCurrentIndex(1)

        self.pre_roll_spin.setValue(int(self.current_settings.pre_roll_sec))
        self.post_roll_spin.setValue(int(self.current_settings.post_roll_sec))
        self.fixed_duration_spin.setValue(self.current_settings.fixed_duration_sec)

        # Events
        self._load_events_table()

    def _load_events_table(self):
        """Загрузить события в таблицу."""
        events = self.modified_settings.default_events
        self.events_table.setRowCount(len(events))

        for row, event in enumerate(events):
            # Name
            name_item = QTableWidgetItem(event.name)
            self.events_table.setItem(row, 0, name_item)

            # Color button
            color_button = QPushButton()
            color_button.setStyleSheet(f"background-color: {event.color}; border: 1px solid #555;")
            color_button.setFixedSize(40, 20)
            color_button.clicked.connect(lambda checked, r=row: self._on_color_button_clicked(r))
            self.events_table.setCellWidget(row, 1, color_button)

            # Hotkey
            hotkey_item = QTableWidgetItem(event.shortcut)
            self.events_table.setItem(row, 2, hotkey_item)

    def _on_color_button_clicked(self, row: int):
        """Обработка клика на кнопку цвета."""
        current_color = QColor(self.modified_settings.default_events[row].color)
        color = QColorDialog.getColor(current_color, self, "Choose Color")

        if color.isValid():
            # Обновить настройки
            self.modified_settings.default_events[row].color = color.name()

            # Обновить кнопку
            button = self.events_table.cellWidget(row, 1)
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")

    def _on_add_event(self):
        """Добавить новое событие."""
        # Простая реализация - можно улучшить
        new_event = EventType(name="New Event", color="#FF0000", shortcut="N")
        self.modified_settings.default_events.append(new_event)
        self._load_events_table()

    def _on_remove_event(self):
        """Удалить выбранное событие."""
        current_row = self.events_table.currentRow()
        if current_row >= 0:
            # Не удалять первые 13 стандартных событий
            if current_row >= 13:
                del self.modified_settings.default_events[current_row]
                self._load_events_table()
            else:
                QMessageBox.warning(self, "Warning", "Cannot remove default events!")

    def _on_reset_events(self):
        """Сбросить события к умолчанию."""
        self.modified_settings.default_events = AppSettings().default_events
        self._load_events_table()

    def _on_save(self):
        """Обработка сохранения."""
        # Собрать данные из UI
        self.modified_settings.recording_mode = self.mode_combo.currentData().value
        self.modified_settings.pre_roll_sec = float(self.pre_roll_spin.value())
        self.modified_settings.post_roll_sec = float(self.post_roll_spin.value())
        self.modified_settings.fixed_duration_sec = self.fixed_duration_spin.value()

        # Собрать события из таблицы
        for row in range(self.events_table.rowCount()):
            name_item = self.events_table.item(row, 0)
            hotkey_item = self.events_table.item(row, 2)

            if name_item and row < len(self.modified_settings.default_events):
                self.modified_settings.default_events[row].name = name_item.text()
                if hotkey_item:
                    self.modified_settings.default_events[row].shortcut = hotkey_item.text()

        # Испустить сигнал
        self.settings_saved.emit(self.modified_settings)
        self.accept()
