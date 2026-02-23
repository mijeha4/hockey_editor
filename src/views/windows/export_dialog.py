"""
Export Dialog — экспорт видео, CSV, PDF с фильтрацией событий.
Настройки видео (кодек, качество, разрешение и т.д.) берутся из Settings.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QProgressBar, QMessageBox, QFileDialog, QGroupBox,
    QScrollArea, QWidget, QTabWidget, QLineEdit
)
from typing import List, Dict, Optional
import os


class ExportDialog(QDialog):
    """Диалог экспорта — выбор сегментов + запуск экспорта.

    Все настройки видео (кодек, качество, разрешение, padding, аудио, merge)
    загружаются из AppSettings и НЕ редактируются здесь.
    """

    export_requested = Signal(dict)
    csv_export_requested = Signal(str)
    pdf_export_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Экспорт")
        self.setGeometry(200, 200, 700, 620)

        self.output_path: Optional[str] = None
        self.video_path: Optional[str] = None
        self.fps: float = 30.0

        # Директория по умолчанию для диалогов
        self._default_dir: str = ""

        # Настройки видео из Settings (заполняются через set_export_defaults)
        self._export_settings: Dict = {
            "codec": "libx264",
            "quality_crf": 23,
            "resolution": "source",
            "include_audio": True,
            "merge_segments": True,
            "padding_before": 0.0,
            "padding_after": 0.0,
            "file_template": "{event}_{index}_{time}",
        }

        self._segment_items: List[Dict] = []
        self._all_event_types: List[str] = []

        self._setup_ui()

    # ══════════════════════════════════════════════════════════════════════
    #  UI
    # ══════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # ── Сегменты с фильтрацией ──
        layout.addWidget(self._create_segments_group())

        # ── Вкладки ──
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_video_tab(), "🎬 Видео")
        self.tabs.addTab(self._create_csv_tab(), "📊 CSV")
        self.tabs.addTab(self._create_pdf_tab(), "📄 Отчёт PDF")
        layout.addWidget(self.tabs)

        # ── Прогресс ──
        layout.addWidget(self._create_progress_group())

        # ── Закрыть ──
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

        self.setLayout(layout)

    # ──────────────────────────────────────────────────────────────────────
    # Segments group
    # ──────────────────────────────────────────────────────────────────────

    def _create_segments_group(self) -> QGroupBox:
        group = QGroupBox("Сегменты для экспорта")
        root = QVBoxLayout()

        # Строка фильтров
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Тип:"))
        self.event_type_filter = QComboBox()
        self.event_type_filter.setMinimumWidth(160)
        self.event_type_filter.addItem("Все типы")
        self.event_type_filter.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.event_type_filter)

        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по названию…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search_edit)

        root.addLayout(filter_row)

        # Кнопки выбора + счётчик
        btn_row = QHBoxLayout()

        self.select_all_btn = QPushButton("Выбрать видимые")
        self.select_all_btn.clicked.connect(self._select_visible)
        btn_row.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Снять видимые")
        self.deselect_all_btn.clicked.connect(self._deselect_visible)
        btn_row.addWidget(self.deselect_all_btn)

        btn_row.addStretch()

        self.counter_label = QLabel("0 из 0")
        self.counter_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        btn_row.addWidget(self.counter_label)

        root.addLayout(btn_row)

        # Скролл с чекбоксами
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)

        scroll_widget = QWidget()
        self._checkboxes_layout = QVBoxLayout()
        self._checkboxes_layout.setContentsMargins(4, 4, 4, 4)
        self._checkboxes_layout.setSpacing(2)
        scroll_widget.setLayout(self._checkboxes_layout)
        scroll.setWidget(scroll_widget)

        root.addWidget(scroll)
        group.setLayout(root)
        return group

    # ──────────────────────────────────────────────────────────────────────
    # Video tab — только путь и кнопка экспорта
    # ──────────────────────────────────────────────────────────────────────

    def _create_video_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ── Информация о текущих настройках (read-only) ──
        self.settings_info_label = QLabel("")
        self.settings_info_label.setWordWrap(True)
        self.settings_info_label.setStyleSheet(
            "color: #aaaaaa; font-size: 11px; padding: 8px; "
            "background-color: #2a2a2a; border-radius: 4px;"
        )
        layout.addWidget(self.settings_info_label)

        hint = QLabel("Изменить параметры: Настройки → вкладка «Экспорт»")
        hint.setStyleSheet("color: #666666; font-size: 10px; font-style: italic;")
        layout.addWidget(hint)

        layout.addSpacing(12)

        # ── Путь вывода ──
        path_row = QHBoxLayout()
        self.output_path_label = QLabel("Путь не выбран")
        self.output_path_label.setStyleSheet("color: #999999; font-size: 11px;")
        self.output_path_label.setWordWrap(True)
        path_row.addWidget(self.output_path_label, 1)

        self.video_browse_btn = QPushButton("📁 Выбрать путь")
        self.video_browse_btn.clicked.connect(self._on_browse_video_output)
        path_row.addWidget(self.video_browse_btn)
        layout.addLayout(path_row)

        layout.addStretch()

        # ── Кнопка экспорта ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.export_btn = QPushButton("▶ Экспортировать видео")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5016; color: white;
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d6b1f; }
        """)
        self.export_btn.clicked.connect(self._on_export_video_clicked)
        btn_row.addWidget(self.export_btn)
        layout.addLayout(btn_row)

        return tab

    # ──────────────────────────────────────────────────────────────────────
    # CSV tab
    # ──────────────────────────────────────────────────────────────────────

    def _create_csv_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel(
            "Экспорт таблицы сегментов в CSV формате.\n"
            "Содержит: номер, тип события, время начала/конца,\n"
            "длительность, номера кадров, заметки.\n\n"
            "Файл открывается в Excel, Google Sheets и др."
        )
        info.setStyleSheet("color: #aaaaaa; padding: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        csv_btn = QPushButton("📊 Экспортировать CSV")
        csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a5276; color: white;
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2471a3; }
        """)
        csv_btn.clicked.connect(self._on_export_csv_clicked)
        btn_row.addWidget(csv_btn)
        layout.addLayout(btn_row)
        return tab

    # ──────────────────────────────────────────────────────────────────────
    # PDF tab
    # ──────────────────────────────────────────────────────────────────────

    def _create_pdf_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel(
            "Экспорт отчёта со списком сегментов и статистикой.\n\n"
            "Содержит:\n"
            "• Таблицу всех сегментов с временными метками\n"
            "• Статистику по типам событий\n"
            "• Общее количество и длительность\n\n"
            "Если библиотека reportlab установлена — PDF.\n"
            "Если нет — HTML (открывается в браузере)."
        )
        info.setStyleSheet("color: #aaaaaa; padding: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        pdf_btn = QPushButton("📄 Экспортировать отчёт")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #7d3c98; color: white;
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #9b59b6; }
        """)
        pdf_btn.clicked.connect(self._on_export_pdf_clicked)
        btn_row.addWidget(pdf_btn)
        layout.addLayout(btn_row)
        return tab

    # ──────────────────────────────────────────────────────────────────────
    # Progress group
    # ──────────────────────────────────────────────────────────────────────

    def _create_progress_group(self) -> QGroupBox:
        group = QGroupBox("Прогресс")
        layout = QVBoxLayout()

        self.progress_label = QLabel("Готов к экспорту")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        group.setLayout(layout)
        return group

    # ══════════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════════════════════

    def set_segments(self, segments_data: List[Dict]):
        """Заполнить список сегментов с чекбоксами."""
        for item in self._segment_items:
            item["checkbox"].setParent(None)
        self._segment_items.clear()

        event_types: set = set()

        for seg in segments_data:
            event_types.add(seg["event_name"])

            start_time = self._format_time(seg["start_frame"] / self.fps)
            end_time = self._format_time(seg["end_frame"] / self.fps)
            text = f"{seg['event_name']}  ({start_time} – {end_time})  [{seg['duration_sec']:.1f}с]"

            cb = QCheckBox(text)
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_counter)

            self._segment_items.append({
                "id": seg["id"],
                "event_name": seg["event_name"],
                "start_frame": seg["start_frame"],
                "end_frame": seg["end_frame"],
                "duration_sec": seg["duration_sec"],
                "checkbox": cb,
            })
            self._checkboxes_layout.addWidget(cb)

        # Обновить фильтр по типу
        self._all_event_types = sorted(event_types)
        self.event_type_filter.blockSignals(True)
        self.event_type_filter.clear()
        self.event_type_filter.addItem(f"Все типы ({len(segments_data)})")
        for et in self._all_event_types:
            cnt = sum(1 for s in segments_data if s["event_name"] == et)
            self.event_type_filter.addItem(f"{et} ({cnt})")
        self.event_type_filter.blockSignals(False)

        self._update_counter()

    set_filtered_segments = set_segments

    def set_export_defaults(self, defaults: Dict):
        """Сохранить настройки экспорта из Settings и обновить info-label."""
        if not defaults:
            return

        # Сохраняем ВСЕ настройки
        for key in (
            "codec", "quality_crf", "resolution", "include_audio",
            "merge_segments", "padding_before", "padding_after", "file_template"
        ):
            if key in defaults:
                self._export_settings[key] = defaults[key]

        # Директория для диалогов
        default_dir = defaults.get("default_dir", "")
        if default_dir and os.path.isdir(default_dir):
            self._default_dir = default_dir

        # Обновить информационный label
        self._update_settings_info()
        self._update_path_label()

    def set_video_path(self, video_path: str):
        self.video_path = video_path

    def set_fps(self, fps: float):
        self.fps = fps if fps > 0 else 30.0

    def get_selected_segment_ids(self) -> List[int]:
        return [item["id"] for item in self._segment_items if item["checkbox"].isChecked()]

    def get_export_params(self) -> Dict:
        """Собрать параметры экспорта: настройки из Settings + путь + выбранные сегменты."""
        s = self._export_settings
        return {
            "codec": s["codec"],
            "quality": s["quality_crf"],
            "resolution": s["resolution"],
            "include_audio": s["include_audio"],
            "merge_segments": s["merge_segments"],
            "padding_before": s["padding_before"],
            "padding_after": s["padding_after"],
            "file_template": s.get("file_template"),
            "output_path": self.output_path,
            "selected_segment_ids": self.get_selected_segment_ids(),
        }

    def set_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def show_export_result(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, "Успех", message)
        else:
            QMessageBox.critical(self, "Ошибка", message)
            self.progress_bar.setValue(0)

    def set_controls_enabled(self, enabled: bool):
        self.export_btn.setEnabled(enabled)
        self.video_browse_btn.setEnabled(enabled)
        self.tabs.setEnabled(enabled)

    # ══════════════════════════════════════════════════════════════════════
    #  FILTERING
    # ══════════════════════════════════════════════════════════════════════

    def _apply_filter(self):
        search = self.search_edit.text().lower().strip()

        type_idx = self.event_type_filter.currentIndex()
        selected_type: Optional[str] = None
        if type_idx > 0 and (type_idx - 1) < len(self._all_event_types):
            selected_type = self._all_event_types[type_idx - 1]

        for item in self._segment_items:
            visible = True
            if selected_type and item["event_name"] != selected_type:
                visible = False
            if search and search not in item["checkbox"].text().lower():
                visible = False
            item["checkbox"].setVisible(visible)

        self._update_counter()

    def _select_visible(self):
        for item in self._segment_items:
            if item["checkbox"].isVisible():
                item["checkbox"].setChecked(True)

    def _deselect_visible(self):
        for item in self._segment_items:
            if item["checkbox"].isVisible():
                item["checkbox"].setChecked(False)

    def _update_counter(self):
        total = len(self._segment_items)
        visible = sum(1 for i in self._segment_items if i["checkbox"].isVisible())
        selected = sum(
            1 for i in self._segment_items
            if i["checkbox"].isChecked() and i["checkbox"].isVisible()
        )
        all_selected = sum(1 for i in self._segment_items if i["checkbox"].isChecked())

        if visible < total:
            txt = f"Выбрано: {selected} из {visible} видимых (всего отмечено: {all_selected}/{total})"
        else:
            txt = f"Выбрано: {all_selected} из {total}"

        self.counter_label.setText(txt)

    # ══════════════════════════════════════════════════════════════════════
    #  SETTINGS INFO (read-only display)
    # ══════════════════════════════════════════════════════════════════════

    def _update_settings_info(self):
        """Показать текущие настройки экспорта в виде текста."""
        s = self._export_settings

        codec = s.get("codec", "libx264")
        crf = s.get("quality_crf", 23)
        resolution = s.get("resolution", "source")
        audio = "да" if s.get("include_audio", True) else "нет"
        merge = "один файл" if s.get("merge_segments", True) else "отдельные файлы"
        pad_before = s.get("padding_before", 0.0)
        pad_after = s.get("padding_after", 0.0)
        template = s.get("file_template", "")

        # Название качества
        if crf <= 18:
            quality_name = f"Высокое (CRF {crf})"
        elif crf <= 23:
            quality_name = f"Среднее (CRF {crf})"
        elif crf <= 28:
            quality_name = f"Низкое (CRF {crf})"
        else:
            quality_name = f"CRF {crf}"

        lines = [
            f"Кодек: {codec}  •  Качество: {quality_name}  •  Разрешение: {resolution}",
            f"Аудио: {audio}  •  Режим: {merge}",
        ]

        if pad_before > 0 or pad_after > 0:
            lines.append(f"Отступы: {pad_before:.1f}с до / {pad_after:.1f}с после")

        if template and not s.get("merge_segments", True):
            lines.append(f"Шаблон имени: {template}")

        self.settings_info_label.setText("\n".join(lines))

    # ══════════════════════════════════════════════════════════════════════
    #  PATH HANDLING
    # ══════════════════════════════════════════════════════════════════════

    def _is_merge_mode(self) -> bool:
        return self._export_settings.get("merge_segments", True)

    def _get_browse_start_dir(self) -> str:
        if self.output_path:
            existing_dir = os.path.dirname(self.output_path)
            if os.path.isdir(self.output_path):
                existing_dir = self.output_path
            if existing_dir and os.path.isdir(existing_dir):
                return existing_dir

        if self._default_dir and os.path.isdir(self._default_dir):
            return self._default_dir

        if self.video_path:
            video_dir = os.path.dirname(self.video_path)
            if os.path.isdir(video_dir):
                return video_dir

        return os.getcwd()

    def _on_browse_video_output(self):
        start_dir = self._get_browse_start_dir()

        if self._is_merge_mode():
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить видео",
                os.path.join(start_dir, "export.mp4"),
                "Video Files (*.mp4);;All Files (*)"
            )
            if path:
                if not os.path.splitext(path)[1]:
                    path += ".mp4"
                self.output_path = path
        else:
            path = QFileDialog.getExistingDirectory(
                self, "Папка для файлов", start_dir
            )
            if path:
                self.output_path = path

        self._update_path_label()

    def _update_path_label(self):
        if self.output_path:
            display = self.output_path
            if len(display) > 60:
                display = "…" + display[-57:]

            if self._is_merge_mode():
                self.output_path_label.setText(f"📄 Файл: {display}")
                self.output_path_label.setStyleSheet("color: #88cc88; font-size: 11px;")
            else:
                self.output_path_label.setText(f"📁 Папка: {display}")
                self.output_path_label.setStyleSheet("color: #88aacc; font-size: 11px;")
        else:
            if self._is_merge_mode():
                self.output_path_label.setText("Путь не выбран (нужен файл .mp4)")
            else:
                self.output_path_label.setText("Путь не выбран (нужна папка)")
            self.output_path_label.setStyleSheet("color: #999999; font-size: 11px;")

    def _validate_output_path(self) -> Optional[str]:
        if not self.output_path:
            return "Укажите путь для сохранения."

        if self._is_merge_mode():
            _base, ext = os.path.splitext(self.output_path)
            if not ext:
                return (
                    f"Путь «{self.output_path}» не содержит расширения файла.\n\n"
                    f"В режиме «Один файл» нужно указать файл,\n"
                    f"например: export.mp4"
                )
            if os.path.isdir(self.output_path):
                return (
                    f"Путь «{self.output_path}» — это папка, а не файл.\n\n"
                    f"Нажмите «Выбрать путь» и укажите файл .mp4"
                )
            parent = os.path.dirname(self.output_path)
            if parent and not os.path.isdir(parent):
                return f"Директория не существует: {parent}"
        else:
            if not os.path.isdir(self.output_path):
                parent = os.path.dirname(self.output_path)
                if parent and os.path.isdir(parent):
                    self.output_path = parent
                    self._update_path_label()
                else:
                    return f"Папка не существует: {self.output_path}"

        return None

    # ══════════════════════════════════════════════════════════════════════
    #  HANDLERS
    # ══════════════════════════════════════════════════════════════════════

    def _on_export_video_clicked(self):
        selected = self.get_selected_segment_ids()
        if not selected:
            QMessageBox.warning(self, "Нет сегментов", "Выберите хотя бы один сегмент.")
            return

        error = self._validate_output_path()
        if error:
            QMessageBox.warning(self, "Неверный путь", error)
            return

        self.export_requested.emit(self.get_export_params())

    def _on_export_csv_clicked(self):
        if not self.get_selected_segment_ids():
            QMessageBox.warning(self, "Нет сегментов", "Выберите хотя бы один сегмент.")
            return

        start_dir = self._get_browse_start_dir()
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить CSV",
            os.path.join(start_dir, "segments.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self.csv_export_requested.emit(path)

    def _on_export_pdf_clicked(self):
        if not self.get_selected_segment_ids():
            QMessageBox.warning(self, "Нет сегментов", "Выберите хотя бы один сегмент.")
            return

        start_dir = self._get_browse_start_dir()
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт",
            os.path.join(start_dir, "report.pdf"),
            "PDF Files (*.pdf);;HTML Files (*.html);;All Files (*)"
        )
        if path:
            self.pdf_export_requested.emit(path)

    # ══════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _format_time(seconds: float) -> str:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def closeEvent(self, event):
        super().closeEvent(event)