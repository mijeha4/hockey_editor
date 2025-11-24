from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton, QColorDialog,
    QLineEdit, QCheckBox
)
from PySide6.QtGui import QColor
import json
import os
from enum import Enum


class SettingsDialog(QDialog):
    """Окно настроек с вкладками."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.config_file = "config.json"
        self.load_config()
        
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 500, 400)
        self.setup_ui()

    def setup_ui(self):
        """Создать UI с вкладками."""
        layout = QVBoxLayout()
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка 1: Режим расстановки
        tabs.addTab(self._create_recording_mode_tab(), "Recording Mode")
        
        # Вкладка 2: Горячие клавиши
        tabs.addTab(self._create_hotkeys_tab(), "Hotkeys")
        
        # Вкладка 3: Визуализация
        tabs.addTab(self._create_colors_tab(), "Colors")
        
        # Вкладка 4: Автосохранение
        tabs.addTab(self._create_autosave_tab(), "Autosave")
        
        layout.addWidget(tabs)
        
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
        
        widget.addWidget(QLabel("Customize Hotkeys:"))
        
        self.hotkey_edits = {}
        for key, event_type in self.controller.hotkeys.items():
            layout = QHBoxLayout()
            layout.addWidget(QLabel(f"{event_type.name}:"))
            edit = QLineEdit()
            edit.setText(key)
            edit.setMaxLength(1)
            self.hotkey_edits[event_type.name] = edit
            layout.addWidget(edit)
            widget.addLayout(layout)
        
        widget.addStretch()
        return self._wrap_widget(widget)

    def _create_colors_tab(self):
        """Вкладка цветов."""
        widget = QVBoxLayout()
        
        widget.addWidget(QLabel("Event Colors:"))
        
        self.color_buttons = {}
        colors = {
            'ATTACK': '#8b0000',
            'DEFENSE': '#000080',
            'SHIFT': '#006400',
        }
        
        for event_type, color_hex in colors.items():
            layout = QHBoxLayout()
            layout.addWidget(QLabel(event_type + ":"))
            
            btn = QPushButton()
            btn.setStyleSheet(f"background-color: {color_hex}; width: 100px;")
            btn.clicked.connect(lambda checked, e=event_type: self._choose_color(e))
            self.color_buttons[event_type] = (btn, color_hex)
            layout.addWidget(btn)
            widget.addLayout(layout)
        
        widget.addStretch()
        return self._wrap_widget(widget)

    def _create_autosave_tab(self):
        """Вкладка автосохранения."""
        widget = QVBoxLayout()
        
        # Автосохранение
        widget.addWidget(QLabel("Autosave Settings:"))
        
        self.autosave_check = QCheckBox("Enable autosave")
        self.autosave_check.setChecked(True)
        widget.addWidget(self.autosave_check)
        
        # Интервал
        widget.addWidget(QLabel("\nAutosave interval (minutes):"))
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        self.autosave_interval_spin.setValue(5)
        widget.addWidget(self.autosave_interval_spin)
        
        # Информация
        widget.addWidget(QLabel("\nMarkers are automatically saved to 'project.json'"))
        
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
        from hockey_editor.core.video_controller import RecordingMode
        self.controller.set_recording_mode(RecordingMode(mode_str))
        
        # Фиксированная длина
        self.controller.set_fixed_duration(self.fixed_duration_spin.value())
        
        # Pre-roll и Post-roll
        self.controller.set_pre_roll(self.pre_roll_spin.value())
        self.controller.post_roll_sec = self.post_roll_spin.value()
        
        # Сохранить конфиг
        self.save_config()
        
        self.accept()

    def load_config(self):
        """Загрузить конфиг из файла."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Применить настройки из файла
                    if 'recording_mode' in data:
                        pass  # Применять при инициализации контроллера
            except:
                pass

    def save_config(self):
        """Сохранить конфиг в файл."""
        config = {
            'recording_mode': self.controller.recording_mode.value,
            'fixed_duration_sec': self.controller.fixed_duration_sec,
            'pre_roll_sec': self.controller.pre_roll_sec,
            'post_roll_sec': self.controller.post_roll_sec,
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass
