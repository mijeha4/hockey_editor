"""
Settings Dialog — диалог настроек приложения.
Включает вкладку «Экспорт» с пресетами и настройками по умолчанию.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton,
    QCheckBox, QWidget, QMessageBox, QGroupBox,
    QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt

from controllers.settings_controller import SettingsController
from controllers.custom_event_controller import CustomEventController
from views.dialogs.custom_event_dialog import CustomEventManagerDialog
from models.config.app_settings import AppSettings


# ── Пресеты экспорта ──────────────────────────────────────────────────────

EXPORT_PRESETS = {
    "custom": {
        "label": "Свои настройки",
    },
    "full_quality": {
        "label": "Полное качество",
        "codec": "libx264",
        "quality_crf": 18,
        "resolution": "source",
        "include_audio": True,
    },
    "medium": {
        "label": "Среднее качество (1080p)",
        "codec": "libx264",
        "quality_crf": 23,
        "resolution": "1080p",
        "include_audio": True,
    },
    "social_media": {
        "label": "Для соцсетей (720p)",
        "codec": "libx264",
        "quality_crf": 28,
        "resolution": "720p",
        "include_audio": True,
    },
    "fast_copy": {
        "label": "Быстрый (без перекодирования)",
        "codec": "copy",
        "quality_crf": 23,
        "resolution": "source",
        "include_audio": True,
    },
    "compact": {
        "label": "Компактный (480p)",
        "codec": "libx264",
        "quality_crf": 30,
        "resolution": "480p",
        "include_audio": True,
    },
}


class SettingsDialog(QDialog):
    """Диалог настроек приложения с вкладками."""

    def __init__(self, settings_controller: SettingsController,
                 custom_event_controller: CustomEventController,
                 parent=None):
        super().__init__(parent)
        self.settings_controller = settings_controller
        self.custom_event_controller = custom_event_controller

        self._preset_applying = False

        self.setWindowTitle("Настройки")
        self.setGeometry(200, 200, 580, 580)
        self.setModal(True)

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(self._create_recording_mode_tab(), "Режим записи")
        tabs.addTab(self._create_export_tab(), "Экспорт")
        tabs.addTab(self._create_hotkeys_tab(), "Горячие клавиши")
        tabs.addTab(self._create_autosave_tab(), "Автосохранение")

        layout.addWidget(tabs)

        events_btn = QPushButton("📝 Управление событиями")
        events_btn.clicked.connect(self._manage_events)
        layout.addWidget(events_btn)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Сохранить")
        save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    # ──────────────────────────────────────────────────────────────────────
    # Tab: Recording mode
    # ──────────────────────────────────────────────────────────────────────

    def _create_recording_mode_tab(self):
        widget = QVBoxLayout()

        widget.addWidget(QLabel("Режим записи:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Динамический (2 нажатия)", "Фиксированная длина (1 нажатие)"])
        widget.addWidget(self.mode_combo)

        widget.addWidget(QLabel("\nФиксированная длительность (секунды):"))
        self.fixed_duration_spin = QSpinBox()
        self.fixed_duration_spin.setRange(1, 120)
        self.fixed_duration_spin.setSingleStep(5)
        widget.addWidget(self.fixed_duration_spin)

        widget.addWidget(QLabel("\nПредварительный откат (секунды):"))
        self.pre_roll_spin = QDoubleSpinBox()
        self.pre_roll_spin.setRange(0.0, 10.0)
        self.pre_roll_spin.setSingleStep(0.5)
        widget.addWidget(self.pre_roll_spin)

        widget.addWidget(QLabel("\nДобавление в конец (секунды):"))
        self.post_roll_spin = QDoubleSpinBox()
        self.post_roll_spin.setRange(0.0, 10.0)
        self.post_roll_spin.setSingleStep(0.5)
        widget.addWidget(self.post_roll_spin)

        widget.addStretch()
        return self._wrap_widget(widget)

    # ──────────────────────────────────────────────────────────────────────
    # Tab: Export (с пресетами)
    # ──────────────────────────────────────────────────────────────────────

    def _create_export_tab(self):
        layout = QVBoxLayout()

        # ── Пресет ──
        preset_group = QGroupBox("Пресет")
        pg = QHBoxLayout()
        pg.addWidget(QLabel("Пресет:"))
        self.export_preset_combo = QComboBox()
        for key, data in EXPORT_PRESETS.items():
            self.export_preset_combo.addItem(data["label"], key)
        self.export_preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        pg.addWidget(self.export_preset_combo, 1)
        preset_group.setLayout(pg)
        layout.addWidget(preset_group)

        # ── Видео ──
        video_group = QGroupBox("Параметры видео")
        vg = QVBoxLayout()

        # Папка
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Папка:"))
        self.export_dir_edit = QLineEdit()
        self.export_dir_edit.setPlaceholderText("Не задана (спрашивать каждый раз)")
        dir_layout.addWidget(self.export_dir_edit)
        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(36)
        browse_btn.clicked.connect(self._browse_export_dir)
        dir_layout.addWidget(browse_btn)
        vg.addLayout(dir_layout)

        # Кодек
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Кодек:"))
        self.export_codec_combo = QComboBox()
        self.export_codec_combo.addItems(["libx264", "libx265", "mpeg4", "copy"])
        self.export_codec_combo.currentIndexChanged.connect(self._on_export_field_changed)
        codec_layout.addWidget(self.export_codec_combo)
        codec_layout.addStretch()
        vg.addLayout(codec_layout)

        # Качество
        q_layout = QHBoxLayout()
        q_layout.addWidget(QLabel("Качество:"))
        self.export_quality_combo = QComboBox()
        self.export_quality_combo.addItems([
            "Высокое (CRF 18)", "Среднее (CRF 23)",
            "Низкое (CRF 28)", "Своё"
        ])
        self.export_quality_combo.currentIndexChanged.connect(self._on_export_quality_changed)
        q_layout.addWidget(self.export_quality_combo)

        self.export_quality_spin = QSpinBox()
        self.export_quality_spin.setRange(0, 51)
        self.export_quality_spin.setValue(23)
        self.export_quality_spin.setSuffix(" CRF")
        self.export_quality_spin.setVisible(False)
        self.export_quality_spin.valueChanged.connect(self._on_export_field_changed)
        q_layout.addWidget(self.export_quality_spin)
        q_layout.addStretch()
        vg.addLayout(q_layout)

        # Разрешение
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Разрешение:"))
        self.export_resolution_combo = QComboBox()
        self.export_resolution_combo.addItems(["source", "2160p", "1080p", "720p", "480p", "360p"])
        self.export_resolution_combo.currentIndexChanged.connect(self._on_export_field_changed)
        res_layout.addWidget(self.export_resolution_combo)
        res_layout.addStretch()
        vg.addLayout(res_layout)

        # Чекбоксы
        opts = QHBoxLayout()
        self.export_audio_check = QCheckBox("Включить аудио")
        self.export_audio_check.setChecked(True)
        opts.addWidget(self.export_audio_check)
        self.export_merge_check = QCheckBox("Объединить в один файл")
        self.export_merge_check.setChecked(True)
        opts.addWidget(self.export_merge_check)
        opts.addStretch()
        vg.addLayout(opts)

        # Авто-открытие папки
        self.export_auto_open_check = QCheckBox("Открывать папку после экспорта")
        self.export_auto_open_check.setChecked(True)
        vg.addWidget(self.export_auto_open_check)

        video_group.setLayout(vg)
        layout.addWidget(video_group)

        # ── Параметры клипов ──
        clip_group = QGroupBox("Параметры клипов")
        cg = QVBoxLayout()

        pad_layout = QHBoxLayout()
        pad_layout.addWidget(QLabel("Отступ до:"))
        self.export_pad_before = QDoubleSpinBox()
        self.export_pad_before.setRange(0.0, 60.0)
        self.export_pad_before.setSingleStep(0.5)
        self.export_pad_before.setSuffix(" сек")
        pad_layout.addWidget(self.export_pad_before)

        pad_layout.addWidget(QLabel("  Отступ после:"))
        self.export_pad_after = QDoubleSpinBox()
        self.export_pad_after.setRange(0.0, 60.0)
        self.export_pad_after.setSingleStep(0.5)
        self.export_pad_after.setSuffix(" сек")
        pad_layout.addWidget(self.export_pad_after)
        pad_layout.addStretch()
        cg.addLayout(pad_layout)

        tmpl_layout = QHBoxLayout()
        tmpl_layout.addWidget(QLabel("Шаблон имени:"))
        self.export_template_edit = QLineEdit()
        self.export_template_edit.setPlaceholderText("{event}_{index}_{time}")
        self.export_template_edit.textChanged.connect(self._update_template_preview)
        tmpl_layout.addWidget(self.export_template_edit)
        cg.addLayout(tmpl_layout)

        self.export_template_preview = QLabel("")
        self.export_template_preview.setStyleSheet("color: #88cc88; font-size: 11px;")
        cg.addWidget(self.export_template_preview)

        hint = QLabel("Переменные: {event} {index} {time} {duration} {project}")
        hint.setStyleSheet("color: #888888; font-size: 10px;")
        cg.addWidget(hint)

        clip_group.setLayout(cg)
        layout.addWidget(clip_group)

        layout.addStretch()
        return self._wrap_widget(layout)

    # ── Пресеты ──

    def _on_preset_selected(self, index: int):
        key = self.export_preset_combo.currentData()
        if not key or key == "custom":
            return

        preset = EXPORT_PRESETS.get(key)
        if not preset:
            return

        self._preset_applying = True
        try:
            codec = preset.get("codec")
            if codec:
                idx = self.export_codec_combo.findText(codec)
                if idx >= 0:
                    self.export_codec_combo.setCurrentIndex(idx)

            crf = preset.get("quality_crf")
            if crf is not None:
                self.export_quality_spin.setValue(int(crf))
                if crf == 18:
                    self.export_quality_combo.setCurrentIndex(0)
                elif crf == 23:
                    self.export_quality_combo.setCurrentIndex(1)
                elif crf == 28:
                    self.export_quality_combo.setCurrentIndex(2)
                else:
                    self.export_quality_combo.setCurrentIndex(3)
                    self.export_quality_spin.setVisible(True)

            res = preset.get("resolution")
            if res:
                idx = self.export_resolution_combo.findText(res)
                if idx >= 0:
                    self.export_resolution_combo.setCurrentIndex(idx)

            if "include_audio" in preset:
                self.export_audio_check.setChecked(preset["include_audio"])

        finally:
            self._preset_applying = False

    def _on_export_field_changed(self):
        if self._preset_applying:
            return
        self.export_preset_combo.blockSignals(True)
        self.export_preset_combo.setCurrentIndex(0)
        self.export_preset_combo.blockSignals(False)

    def _on_export_quality_changed(self):
        text = self.export_quality_combo.currentText()
        if "Своё" in text:
            self.export_quality_spin.setVisible(True)
        else:
            self.export_quality_spin.setVisible(False)
            if "Высокое" in text:
                self.export_quality_spin.setValue(18)
            elif "Среднее" in text:
                self.export_quality_spin.setValue(23)
            elif "Низкое" in text:
                self.export_quality_spin.setValue(28)

        self._on_export_field_changed()

    def _browse_export_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Папка для экспорта")
        if path:
            self.export_dir_edit.setText(path)

    def _update_template_preview(self):
        template = self.export_template_edit.text().strip()
        if not template:
            self.export_template_preview.setText("")
            return
        try:
            preview = template.format_map({
                "event": "Goal",
                "index": "001",
                "time": "02-15",
                "duration": "12",
                "project": "MyProject",
            })
            self.export_template_preview.setText(f"Пример: {preview}.mp4")
            self.export_template_preview.setStyleSheet("color: #88cc88; font-size: 11px;")
        except (KeyError, ValueError, IndexError):
            self.export_template_preview.setText("⚠ Неверный шаблон")
            self.export_template_preview.setStyleSheet("color: #cc8888; font-size: 11px;")

    # ──────────────────────────────────────────────────────────────────────
    # Tab: Hotkeys
    # ──────────────────────────────────────────────────────────────────────

    def _create_hotkeys_tab(self):
        widget = QVBoxLayout()

        widget.addWidget(QLabel("Настройки горячих клавиш:"))
        widget.addWidget(QLabel(
            "Горячие клавиши управляются в диалоге 'Управление событиями'."
        ))

        info_text = (
            "\nСистема горячих клавиш:\n"
            "• Настраиваемые сочетания клавиш для пользовательских событий\n"
            "• Работает глобально даже при фокусе на таймлайне\n"
            "• Пробел — Воспроизведение/Пауза видео\n"
            "• Ctrl+E — Экспорт, Ctrl+S — Сохранить проект"
        )
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        widget.addWidget(info_label)

        widget.addStretch()
        return self._wrap_widget(widget)

    # ──────────────────────────────────────────────────────────────────────
    # Tab: Autosave
    # ──────────────────────────────────────────────────────────────────────

    def _create_autosave_tab(self):
        widget = QVBoxLayout()

        widget.addWidget(QLabel("Настройки автосохранения:"))
        self.autosave_check = QCheckBox("Включить автосохранение")
        widget.addWidget(self.autosave_check)

        widget.addWidget(QLabel("\nИнтервал автосохранения (минуты):"))
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        widget.addWidget(self.autosave_interval_spin)

        widget.addWidget(QLabel("\nМаркеры автоматически сохраняются в 'project.json'"))

        widget.addStretch()
        return self._wrap_widget(widget)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _wrap_widget(self, layout):
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    # ──────────────────────────────────────────────────────────────────────
    # Load / Save
    # ──────────────────────────────────────────────────────────────────────

    def load_settings(self):
        sc = self.settings_controller

        # Recording mode
        mode = sc.get_recording_mode()
        self.mode_combo.setCurrentIndex(0 if mode == "dynamic" else 1)
        self.fixed_duration_spin.setValue(sc.get_fixed_duration())
        self.pre_roll_spin.setValue(sc.get_pre_roll())
        self.post_roll_spin.setValue(sc.get_post_roll())

        # Autosave
        self.autosave_check.setChecked(sc.get_autosave_enabled())
        self.autosave_interval_spin.setValue(sc.get_autosave_interval())

        # ── Export ──
        self._preset_applying = True
        try:
            self.export_dir_edit.setText(sc.get_export_default_dir())

            codec = sc.get_export_codec()
            idx = self.export_codec_combo.findText(codec)
            if idx >= 0:
                self.export_codec_combo.setCurrentIndex(idx)

            crf = sc.get_export_quality_crf()
            self.export_quality_spin.setValue(crf)
            if crf == 18:
                self.export_quality_combo.setCurrentIndex(0)
            elif crf == 23:
                self.export_quality_combo.setCurrentIndex(1)
            elif crf == 28:
                self.export_quality_combo.setCurrentIndex(2)
            else:
                self.export_quality_combo.setCurrentIndex(3)
                self.export_quality_spin.setVisible(True)

            res = sc.get_export_resolution()
            idx = self.export_resolution_combo.findText(res)
            if idx >= 0:
                self.export_resolution_combo.setCurrentIndex(idx)

            self.export_audio_check.setChecked(sc.get_export_include_audio())
            self.export_merge_check.setChecked(sc.get_export_merge_segments())
            self.export_auto_open_check.setChecked(sc.get_export_auto_open())
            self.export_template_edit.setText(sc.get_export_file_template())
            self.export_pad_before.setValue(sc.get_export_padding_before())
            self.export_pad_after.setValue(sc.get_export_padding_after())

            self._detect_current_preset()

        finally:
            self._preset_applying = False

        self._update_template_preview()

    def _detect_current_preset(self):
        """Определить какой пресет соответствует текущим настройкам."""
        current_codec = self.export_codec_combo.currentText()
        current_crf = self.export_quality_spin.value()
        current_res = self.export_resolution_combo.currentText()

        for i in range(self.export_preset_combo.count()):
            key = self.export_preset_combo.itemData(i)
            if key == "custom":
                continue
            preset = EXPORT_PRESETS.get(key, {})
            if (preset.get("codec") == current_codec and
                preset.get("quality_crf") == current_crf and
                preset.get("resolution") == current_res):
                self.export_preset_combo.setCurrentIndex(i)
                return

        self.export_preset_combo.setCurrentIndex(0)

    def save_and_close(self):
        try:
            sc = self.settings_controller

            # Recording mode
            mode = "dynamic" if self.mode_combo.currentIndex() == 0 else "fixed_length"
            sc.set_recording_mode(mode)
            sc.set_fixed_duration(self.fixed_duration_spin.value())
            sc.set_pre_roll(self.pre_roll_spin.value())
            sc.set_post_roll(self.post_roll_spin.value())

            # Autosave
            sc.set_autosave_enabled(self.autosave_check.isChecked())
            sc.set_autosave_interval(self.autosave_interval_spin.value())

            # ── Export ──
            sc.set_export_default_dir(self.export_dir_edit.text().strip())
            sc.set_export_codec(self.export_codec_combo.currentText())
            sc.set_export_quality_crf(self.export_quality_spin.value())
            sc.set_export_resolution(self.export_resolution_combo.currentText())
            sc.set_export_include_audio(self.export_audio_check.isChecked())
            sc.set_export_merge_segments(self.export_merge_check.isChecked())
            sc.set_export_auto_open(self.export_auto_open_check.isChecked())
            sc.set_export_file_template(
                self.export_template_edit.text().strip() or "{event}_{index}_{time}"
            )
            sc.set_export_padding_before(self.export_pad_before.value())
            sc.set_export_padding_after(self.export_pad_after.value())

            if sc.save_settings():
                QMessageBox.information(
                    self, "Настройки сохранены",
                    "Настройки успешно сохранены."
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить настройки.")

        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Произошла ошибка при сохранении настроек:\n{str(e)}"
            )

    def _manage_events(self):
        dialog = CustomEventManagerDialog(self)
        dialog.exec()