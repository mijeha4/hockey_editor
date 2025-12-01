from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton, QColorDialog,
    QLineEdit, QCheckBox, QWidget, QMessageBox
)
from PySide6.QtGui import QColor
from enum import Enum
from ..utils.settings_manager import get_settings_manager
from ..utils.localization_manager import get_localization_manager
from .custom_event_dialog import CustomEventManagerDialog


class SettingsDialog(QDialog):
    """Окно настроек с вкладками."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.settings_manager = get_settings_manager()
        self.localization = get_localization_manager()

        self.setWindowTitle(self.localization.tr("dialog_title_settings"))
        self.setGeometry(200, 200, 500, 400)
        self.setup_ui()
        self.retranslate_ui()

        # Подключить сигнал изменения языка
        self.localization.language_changed.connect(self.retranslate_ui)

    def setup_ui(self):
        """Создать UI с вкладками."""
        layout = QVBoxLayout()
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка 1: Режим расстановки
        tabs.addTab(self._create_recording_mode_tab(), "Recording Mode")
        
        # Вкладка 2: Горячие клавиши
        tabs.addTab(self._create_hotkeys_tab(), "Hotkeys")
        
        # Вкладка 3: Автосохранение
        tabs.addTab(self._create_autosave_tab(), "Autosave")

        # Вкладка 4 : Язык
        tabs.addTab(self._create_language_tab(), "Language")

        layout.addWidget(tabs)

        # Кнопка управления пользовательскими событиями
        events_btn = QPushButton("📝 Manage Events")
        events_btn.clicked.connect(self._manage_events)
        layout.addWidget(events_btn)

        # Кнопки
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def _create_recording_mode_tab(self):
        """Вкладка режима расстановки отрезков."""
        widget = QVBoxLayout()
        
        # Режим расстановки
        widget.addWidget(QLabel("Recording Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Dynamic (2 taps)", "Fixed Length (1 tap)"])
        mode_idx = 0 if self.controller.recording_mode.value == "dynamic" else 1
        self.mode_combo.setCurrentIndex(mode_idx)
        widget.addWidget(self.mode_combo)
        
        # Фиксированная длина
        widget.addWidget(QLabel("\nFixed Duration (seconds):"))
        self.fixed_duration_spin = QSpinBox()
        self.fixed_duration_spin.setRange(1, 120)
        self.fixed_duration_spin.setValue(int(self.controller.fixed_duration_sec))
        self.fixed_duration_spin.setSingleStep(5)
        widget.addWidget(self.fixed_duration_spin)
        
        # Pre-roll
        widget.addWidget(QLabel("\nPre-roll (seconds):"))
        self.pre_roll_spin = QDoubleSpinBox()
        self.pre_roll_spin.setRange(0.0, 10.0)
        self.pre_roll_spin.setValue(self.controller.pre_roll_sec)
        self.pre_roll_spin.setSingleStep(0.5)
        widget.addWidget(self.pre_roll_spin)
        
        # Post-roll
        widget.addWidget(QLabel("\nPost-roll (seconds):"))
        self.post_roll_spin = QDoubleSpinBox()
        self.post_roll_spin.setRange(0.0, 10.0)
        self.post_roll_spin.setValue(self.controller.post_roll_sec)
        self.post_roll_spin.setSingleStep(0.5)
        widget.addWidget(self.post_roll_spin)
        
        widget.addStretch()
        return self._wrap_widget(widget)

    def _create_hotkeys_tab(self):
        """Вкладка горячих клавиш."""
        widget = QVBoxLayout()

        widget.addWidget(QLabel("Hotkeys Settings:"))
        widget.addWidget(QLabel("Hotkeys are managed in the 'Manage Events' dialog."))
        widget.addWidget(QLabel("Use the '📝 Manage Events' button below to customize events and their shortcuts."))

        # Статусная информация
        info_text = """
            Hotkey System:
            • Custom shortcuts for user-defined events
            • Works globally even when timeline or other controls are focused
            • Space bar for Play/Pause video
            • Ctrl+E for Export, Ctrl+S for Save Project
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
        widget.addWidget(QLabel("Autosave Settings:"))
        
        self.autosave_check = QCheckBox("Enable autosave")
        self.autosave_check.setChecked(self.settings_manager.load_autosave_enabled())
        widget.addWidget(self.autosave_check)

        # Интервал
        widget.addWidget(QLabel("\nAutosave interval (minutes):"))
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        self.autosave_interval_spin.setValue(self.settings_manager.load_autosave_interval())
        widget.addWidget(self.autosave_interval_spin)

        # Информация
        widget.addWidget(QLabel("\nMarkers are automatically saved to 'project.json'"))

        widget.addStretch()
        return self._wrap_widget(widget)

    def _create_language_tab(self):
        """Вкладка выбора языка."""
        widget = QVBoxLayout()

        # Выбор языка
        widget.addWidget(QLabel("Language:"))

        self.language_combo = QComboBox()
        available_languages = self.localization.get_available_languages()
        current_language = self.localization.get_current_language()

        for lang_code in available_languages:
            display_name = self.localization.get_language_display_name(lang_code)
            self.language_combo.addItem(display_name, lang_code)

        # Установить текущий выбранный язык
        current_index = 0
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_language:
                current_index = i
                break
        self.language_combo.setCurrentIndex(current_index)

        widget.addWidget(self.language_combo)

        # Информация
        info_text = """
Language Settings:
• Changes take effect immediately for most UI elements
• Some elements may require application restart
• Settings are saved automatically
"""
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        widget.addWidget(info_label)

        widget.addStretch()
        return self._wrap_widget(widget)

    def _wrap_widget(self, layout):
        """Обёртка для вкладки."""
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _choose_color(self, event_type: str):
        """Выбрать цвет."""
        btn, current_color = self.color_buttons[event_type]
        color = QColorDialog.getColor(QColor(current_color), self, f"Choose color for {event_type}")
        if color.isValid():
            hex_color = color.name()
            btn.setStyleSheet(f"background-color: {hex_color}; width: 100px;")
            self.color_buttons[event_type] = (btn, hex_color)

    def save_and_close(self):
        """Сохранить настройки и закрыть."""
        # Режим расстановки
        mode_str = "dynamic" if self.mode_combo.currentIndex() == 0 else "fixed_length"
        from ..core.video_controller import RecordingMode
        self.controller.set_recording_mode(RecordingMode(mode_str))

        # Фиксированная длина
        self.controller.set_fixed_duration(self.fixed_duration_spin.value())

        # Pre-roll и Post-roll
        self.controller.set_pre_roll(self.pre_roll_spin.value())
        self.controller.set_post_roll(self.post_roll_spin.value())

        # Цвета дорожек (сохранить в QSettings)
        colors = {}
        for event_type, (_, color_hex) in self.color_buttons.items():
            colors[event_type] = color_hex
        self.settings_manager.save_track_colors(colors)

        # Автосохранение
        self.settings_manager.save_autosave_enabled(self.autosave_check.isChecked())
        self.settings_manager.save_autosave_interval(self.autosave_interval_spin.value())

        # Язык
        selected_language = self.language_combo.currentData()
        if selected_language != self.localization.get_current_language():
            self.localization.set_language(selected_language)

        # Применить изменения - перезагрузить настройки
        self.settings_manager.sync()

        QMessageBox.information(self, "Settings Saved",
                               "Settings have been saved successfully.\n\n"
                               "Restart the application for some changes to take full effect.")

        self.accept()

    def retranslate_ui(self):
        """Перевести интерфейс диалога настроек."""
        self.setWindowTitle(self.localization.tr("dialog_title_settings"))

        # Перевести вкладки
        if hasattr(self, 'layout') and self.layout():
            tabs = None
            for i in range(self.layout().count()):
                item = self.layout().itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QTabWidget):
                    tabs = item.widget()
                    break

            if tabs:
                tabs.setTabText(0, self.localization.tr("tab_recording_mode"))
                tabs.setTabText(1, self.localization.tr("tab_hotkeys"))
                tabs.setTabText(3, self.localization.tr("tab_autosave"))
                tabs.setTabText(4, self.localization.tr("tab_language"))

        # Перевести кнопки
        for btn in self.findChildren(QPushButton):
            if "💾 Save" in btn.text() or btn.text() == self.localization.tr("btn_save", "Save"):
                btn.setText(f"💾 {self.localization.tr('btn_save')}")
            elif "✕ Cancel" in btn.text() or btn.text() == self.localization.tr("btn_cancel", "Cancel"):
                btn.setText(f"✕ {self.localization.tr('btn_cancel')}")
            elif "📝 Manage Events" in btn.text():
                # Эта кнопка пока остается без перевода, так как нет ключа в локализации
                pass

        # Перевести метки и элементы в вкладках
        self._retranslate_tabs()

    def _retranslate_tabs(self):
        """Перевести содержимое вкладок."""
        # Найти все метки в диалоге и перевести их
        for label in self.findChildren(QLabel):
            text = label.text()
            if "Recording Mode:" in text or text == self.localization.tr("lbl_recording_mode", "Recording Mode:"):
                label.setText(self.localization.tr("lbl_recording_mode"))
            elif "Fixed Duration (seconds):" in text or text == self.localization.tr("lbl_fixed_duration", "Fixed Duration (seconds):"):
                label.setText(self.localization.tr("lbl_fixed_duration"))
            elif "Pre-roll (seconds):" in text or text == self.localization.tr("lbl_pre_roll", "Pre-roll (seconds):"):
                label.setText(self.localization.tr("lbl_pre_roll"))
            elif "Post-roll (seconds):" in text or text == self.localization.tr("lbl_post_roll", "Post-roll (seconds):"):
                label.setText(self.localization.tr("lbl_post_roll"))
            elif "Hotkeys Settings:" in text or text == self.localization.tr("lbl_hotkeys", "Hotkeys Settings:"):
                label.setText(self.localization.tr("lbl_hotkeys"))
            elif "Autosave Settings:" in text or text == self.localization.tr("lbl_autosave", "Autosave Settings:"):
                label.setText(self.localization.tr("lbl_autosave"))
            elif "Language:" in text or text == self.localization.tr("lbl_language", "Language:"):
                label.setText(self.localization.tr("lbl_language"))

        # Обновить комбо-боксы
        if hasattr(self, 'mode_combo'):
            current_idx = self.mode_combo.currentIndex()
            self.mode_combo.clear()
            self.mode_combo.addItem(self.localization.tr("combo_dynamic"), "dynamic")
            self.mode_combo.addItem(self.localization.tr("combo_fixed"), "fixed_length")
            self.mode_combo.setCurrentIndex(current_idx)

        # Обновить чекбокс автосохранения
        for checkbox in self.findChildren(QCheckBox):
            if "Enable autosave" in checkbox.text():
                # Пока оставим без перевода, так как нет ключа
                pass

    def _manage_events(self):
        """Открыть диалог управления событиями."""
        dialog = CustomEventManagerDialog(self)
        dialog.exec()
