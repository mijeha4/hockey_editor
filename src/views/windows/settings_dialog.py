"""
Settings Dialog - диалог настроек приложения.

Обеспечивает пользовательский интерфейс для настройки параметров приложения
с интеграцией с SettingsController.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton,
    QCheckBox, QWidget, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt

from controllers.settings_controller import SettingsController
from controllers.custom_event_controller import CustomEventController
from views.dialogs.custom_event_dialog import CustomEventManagerDialog


class SettingsDialog(QDialog):
    """Диалог настроек приложения с вкладками."""

    def __init__(self, settings_controller: SettingsController,
                 custom_event_controller: CustomEventController,
                 parent=None):
        super().__init__(parent)
        self.settings_controller = settings_controller
        self.custom_event_controller = custom_event_controller

        self.setWindowTitle("Настройки")
        self.setGeometry(200, 200, 500, 400)
        self.setModal(True)

        self.setup_ui()

        # Загрузить текущие настройки
        self.load_settings()

    def setup_ui(self):
        """Создать UI с вкладками."""
        layout = QVBoxLayout()

        # Вкладки
        tabs = QTabWidget()

        # Вкладка 1: Режим расстановки
        tabs.addTab(self._create_recording_mode_tab(), "Режим записи")

        # Вкладка 2: Горячие клавиши
        tabs.addTab(self._create_hotkeys_tab(), "Горячие клавиши")

        # Вкладка 3: Автосохранение
        tabs.addTab(self._create_autosave_tab(), "Автосохранение")

        layout.addWidget(tabs)

        # Кнопка управления пользовательскими событиями
        events_btn = QPushButton("📝 Управление событиями")
        events_btn.clicked.connect(self._manage_events)
        layout.addWidget(events_btn)

        # Кнопки
        button_layout = QHBoxLayout()

        save_btn = QPushButton("💾 Сохранить")
        save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_recording_mode_tab(self):
        """Вкладка режима расстановки отрезков."""
        widget = QVBoxLayout()

        # Режим расстановки
        widget.addWidget(QLabel("Режим записи:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Динамический (2 нажатия)", "Фиксированная длина (1 нажатие)"])
        widget.addWidget(self.mode_combo)

        # Фиксированная длина
        widget.addWidget(QLabel("\nФиксированная длительность (секунды):"))
        self.fixed_duration_spin = QSpinBox()
        self.fixed_duration_spin.setRange(1, 120)
        self.fixed_duration_spin.setSingleStep(5)
        widget.addWidget(self.fixed_duration_spin)

        # Pre-roll
        widget.addWidget(QLabel("\nПредварительный откат (секунды):"))
        self.pre_roll_spin = QDoubleSpinBox()
        self.pre_roll_spin.setRange(0.0, 10.0)
        self.pre_roll_spin.setSingleStep(0.5)
        widget.addWidget(self.pre_roll_spin)

        # Post-roll
        widget.addWidget(QLabel("\nДобавление в конец (секунды):"))
        self.post_roll_spin = QDoubleSpinBox()
        self.post_roll_spin.setRange(0.0, 10.0)
        self.post_roll_spin.setSingleStep(0.5)
        widget.addWidget(self.post_roll_spin)

        widget.addStretch()
        return self._wrap_widget(widget)

    def _create_hotkeys_tab(self):
        """Вкладка горячих клавиш."""
        widget = QVBoxLayout()

        widget.addWidget(QLabel("Настройки горячих клавиш:"))
        widget.addWidget(QLabel("Горячие клавиши управляются в диалоге 'Управление событиями'."))
        widget.addWidget(QLabel("Используйте кнопку 'Управление событиями' ниже для настройки событий и их сочетаний клавиш."))

        # Статусная информация
        info_text = """
Система горячих клавиш:
• Настраиваемые сочетания клавиш для пользовательских событий
• Работает глобально даже при фокусе на таймлайне или других элементах
• Пробел - Воспроизведение/Пауза видео
• Ctrl+E - Экспорт, Ctrl+S - Сохранить проект
"""
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        widget.addWidget(info_label)

        widget.addStretch()
        return self._wrap_widget(widget)

    def _create_autosave_tab(self):
        """Вкладка автосохранения."""
        widget = QVBoxLayout()

        # Автосохранение
        widget.addWidget(QLabel("Настройки автосохранения:"))

        self.autosave_check = QCheckBox("Включить автосохранение")
        widget.addWidget(self.autosave_check)

        # Интервал
        widget.addWidget(QLabel("\nИнтервал автосохранения (минуты):"))
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        widget.addWidget(self.autosave_interval_spin)

        # Информация
        widget.addWidget(QLabel("\nМаркеры автоматически сохраняются в 'project.json'"))

        widget.addStretch()
        return self._wrap_widget(widget)

    def _wrap_widget(self, layout):
        """Обёртка для вкладки."""
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def load_settings(self):
        """Загрузить настройки в UI."""
        # Режим расстановки
        mode = self.settings_controller.get_recording_mode()
        mode_idx = 0 if mode == "dynamic" else 1
        self.mode_combo.setCurrentIndex(mode_idx)

        # Фиксированная длина
        self.fixed_duration_spin.setValue(self.settings_controller.get_fixed_duration())

        # Pre-roll и Post-roll
        self.pre_roll_spin.setValue(self.settings_controller.get_pre_roll())
        self.post_roll_spin.setValue(self.settings_controller.get_post_roll())

        # Автосохранение
        self.autosave_check.setChecked(self.settings_controller.get_autosave_enabled())
        self.autosave_interval_spin.setValue(self.settings_controller.get_autosave_interval())

    def save_and_close(self):
        """Сохранить настройки и закрыть."""
        try:
            # Режим расстановки
            mode = "dynamic" if self.mode_combo.currentIndex() == 0 else "fixed_length"
            self.settings_controller.set_recording_mode(mode)

            # Фиксированная длина
            self.settings_controller.set_fixed_duration(self.fixed_duration_spin.value())

            # Pre-roll и Post-roll
            self.settings_controller.set_pre_roll(self.pre_roll_spin.value())
            self.settings_controller.set_post_roll(self.post_roll_spin.value())

            # Автосохранение
            self.settings_controller.set_autosave_enabled(self.autosave_check.isChecked())
            self.settings_controller.set_autosave_interval(self.autosave_interval_spin.value())

            # Сохранить настройки
            if self.settings_controller.save_settings():
                QMessageBox.information(self, "Настройки сохранены",
                                       "Настройки успешно сохранены.\n\n"
                                       "Перезапустите приложение для применения некоторых изменений.")
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить настройки.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при сохранении настроек:\n{str(e)}")

    def _manage_events(self):
        """Открыть диалог управления событиями."""
        dialog = CustomEventManagerDialog(self)
        dialog.exec()
