"""
Export Dialog — экспорт видео, CSV, PDF с фильтрацией событий.
Настройки видео берутся из Settings, здесь только выбор сегментов и пути.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QProgressBar, QMessageBox, QFileDialog, QGroupBox,
    QScrollArea, QWidget, QTabWidget, QLineEdit
)
from PySide6.QtCore import QUrl
from typing import List, Dict, Optional
import os


class ExportDialog(QDialog):
    """Диалог экспорта — выбор сегментов + запуск.

    Настройки видео загружаются из AppSettings и НЕ редактируются здесь.
    """

    export_requested = Signal(dict)
    cancel_requested = Signal()
    csv_export_requested = Signal(str)
    pdf_export_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Экспорт")
        self.setGeometry(200, 200, 700, 650)

        self.output_path: Optional[str] = None
        self.video_path: Optional[str] = None
        self.fps: float = 30.0

        self._default_dir: str = ""
        self._auto_open: bool = True
        self._last_export_path: Optional[str] = None

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
        self._event_display_names: Dict[str, str] = {}

        self._setup_ui()

    # ══════════════════════════════════════════════════════════════════════
    #  UI
    # ══════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        layout.addWidget(self._create_segments_group())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_video_tab(), "🎬 Видео")
        self.tabs.addTab(self._create_csv_tab(), "📊 CSV")
        self.tabs.addTab(self._create_pdf_tab(), "📄 Отчёт PDF")
        layout.addWidget(self.tabs)

        layout.addWidget(self._create_progress_group())

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
    # Video tab
    # ──────────────────────────────────────────────────────────────────────

    def _create_video_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Информация о настройках (read-only)
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

        # Путь
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

        # Кнопка экспорта
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
    # Progress group — с кнопкой отмены и «Открыть папку»
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

        # Кнопки под прогрессом
        btn_row = QHBoxLayout()

        # Кнопка отмены
        self.cancel_btn = QPushButton("✕ Отменить экспорт")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b0000; color: white;
                padding: 6px 14px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #a52a2a; }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.cancel_btn.setVisible(False)
        btn_row.addWidget(self.cancel_btn)

        btn_row.addStretch()

        # Кнопка «Открыть папку»
        self.open_folder_btn = QPushButton("📂 Открыть папку")
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a5276; color: white;
                padding: 6px 14px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #2471a3; }
        """)
        self.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        self.open_folder_btn.setVisible(False)
        btn_row.addWidget(self.open_folder_btn)

        layout.addLayout(btn_row)
        group.setLayout(layout)
        return group

    # ══════════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════════════════════

    def set_segments(self, segments_data: List[Dict]):
        for item in self._segment_items:
            item["checkbox"].setParent(None)
        self._segment_items.clear()

        event_types_map: Dict[str, str] = {}  # event_name → display_name

        for seg in segments_data:
            event_name = seg["event_name"]
            display_name = seg.get("display_name", event_name)
            event_types_map[event_name] = display_name

            start_time = self._format_time(seg["start_frame"] / self.fps)
            end_time = self._format_time(seg["end_frame"] / self.fps)
            text = f"{display_name}  ({start_time} – {end_time})  [{seg['duration_sec']:.1f}с]"

            cb = QCheckBox(text)
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_counter)

            self._segment_items.append({
                "id": seg["id"],
                "event_name": event_name,
                "display_name": display_name,
                "start_frame": seg["start_frame"],
                "end_frame": seg["end_frame"],
                "duration_sec": seg["duration_sec"],
                "checkbox": cb,
            })
            self._checkboxes_layout.addWidget(cb)

        self._all_event_types = sorted(event_types_map.keys())
        self._event_display_names = event_types_map

        self.event_type_filter.blockSignals(True)
        self.event_type_filter.clear()
        self.event_type_filter.addItem(f"Все типы ({len(segments_data)})")
        for et in self._all_event_types:
            cnt = sum(1 for s in segments_data if s["event_name"] == et)
            display = event_types_map.get(et, et)
            self.event_type_filter.addItem(f"{display} ({cnt})")
        self.event_type_filter.blockSignals(False)

        self._update_counter()

    set_filtered_segments = set_segments

    def set_export_defaults(self, defaults: Dict):
        if not defaults:
            return

        for key in (
            "codec", "quality_crf", "resolution", "include_audio",
            "merge_segments", "padding_before", "padding_after", "file_template"
        ):
            if key in defaults:
                self._export_settings[key] = defaults[key]

        default_dir = defaults.get("default_dir", "")
        if default_dir and os.path.isdir(default_dir):
            self._default_dir = default_dir

        self._auto_open = defaults.get("auto_open", True)

        self._update_settings_info()
        self._update_path_label()

    def set_video_path(self, video_path: str):
        self.video_path = video_path

    def set_fps(self, fps: float):
        self.fps = fps if fps > 0 else 30.0

    def get_selected_segment_ids(self) -> List[int]:
        return [item["id"] for item in self._segment_items if item["checkbox"].isChecked()]

    def get_export_params(self) -> Dict:
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
        """Показать результат + кнопку «Открыть папку»."""
        self.cancel_btn.setVisible(False)

        if success:
            self.progress_label.setText(f"✅ {message}")
            self.progress_label.setStyleSheet("color: #88cc88; font-weight: bold;")

            if self.output_path:
                self.open_folder_btn.setVisible(True)
                self._last_export_path = self.output_path

                if self._auto_open:
                    self._open_export_folder()
        else:
            self.progress_label.setText(f"❌ {message}")
            self.progress_label.setStyleSheet("color: #cc8888; font-weight: bold;")
            self.progress_bar.setValue(0)

    def set_controls_enabled(self, enabled: bool):
        self.export_btn.setEnabled(enabled)
        self.video_browse_btn.setEnabled(enabled)
        self.tabs.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled)
        self.deselect_all_btn.setEnabled(enabled)
        self.event_type_filter.setEnabled(enabled)
        self.search_edit.setEnabled(enabled)

        # Показать/скрыть кнопку отмены
        self.cancel_btn.setVisible(not enabled)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("✕ Отменить экспорт")

        if enabled:
            self.progress_label.setStyleSheet("")

    # ══════════════════════════════════════════════════════════════════════
    #  SETTINGS INFO
    # ══════════════════════════════════════════════════════════════════════

    def _update_settings_info(self):
        s = self._export_settings

        codec = s.get("codec", "libx264")
        crf = s.get("quality_crf", 23)
        resolution = s.get("resolution", "source")
        audio = "да" if s.get("include_audio", True) else "нет"
        merge = "один файл" if s.get("merge_segments", True) else "отдельные файлы"
        pad_before = s.get("padding_before", 0.0)
        pad_after = s.get("padding_after", 0.0)

        if crf <= 18:
            q_name = f"Высокое (CRF {crf})"
        elif crf <= 23:
            q_name = f"Среднее (CRF {crf})"
        elif crf <= 28:
            q_name = f"Низкое (CRF {crf})"
        else:
            q_name = f"CRF {crf}"

        lines = [
            f"Кодек: {codec}  •  Качество: {q_name}  •  Разрешение: {resolution}",
            f"Аудио: {audio}  •  Режим: {merge}",
        ]
        if pad_before > 0 or pad_after > 0:
            lines.append(f"Отступы: {pad_before:.1f}с до / {pad_after:.1f}с после")

        self.settings_info_label.setText("\n".join(lines))

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
            txt = f"Выбрано: {selected} из {visible} видимых (всего: {all_selected}/{total})"
        else:
            txt = f"Выбрано: {all_selected} из {total}"
        self.counter_label.setText(txt)

    # ══════════════════════════════════════════════════════════════════════
    #  PATH
    # ══════════════════════════════════════════════════════════════════════

    def _is_merge_mode(self) -> bool:
        return self._export_settings.get("merge_segments", True)

    def _get_browse_start_dir(self) -> str:
        if self.output_path:
            d = os.path.dirname(self.output_path)
            if os.path.isdir(self.output_path):
                d = self.output_path
            if d and os.path.isdir(d):
                return d
        if self._default_dir and os.path.isdir(self._default_dir):
            return self._default_dir
        if self.video_path:
            d = os.path.dirname(self.video_path)
            if os.path.isdir(d):
                return d
        return os.getcwd()

    def _on_browse_video_output(self):
        start_dir = self._get_browse_start_dir()

        if self._is_merge_mode():
            path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить видео",
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
                return "Путь не содержит расширения.\nУкажите файл, например: export.mp4"
            if os.path.isdir(self.output_path):
                return "Указана папка, а не файл.\nНажмите «Выбрать путь» и укажите файл .mp4"
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
    #  OPEN FOLDER
    # ══════════════════════════════════════════════════════════════════════

    def _open_export_folder(self):
        path = self._last_export_path or self.output_path
        if not path:
            return

        if os.path.isfile(path):
            folder = os.path.dirname(path)
        elif os.path.isdir(path):
            folder = path
        else:
            folder = os.path.dirname(path)

        if folder and os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _on_open_folder_clicked(self):
        self._open_export_folder()

    # ══════════════════════════════════════════════════════════════════════
    #  HANDLERS
    # ══════════════════════════════════════════════════════════════════════

    def _on_cancel_clicked(self):
        self.cancel_requested.emit()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Отменяем…")

    def _on_export_video_clicked(self):
        selected = self.get_selected_segment_ids()
        if not selected:
            QMessageBox.warning(self, "Нет сегментов", "Выберите хотя бы один сегмент.")
            return

        error = self._validate_output_path()
        if error:
            QMessageBox.warning(self, "Неверный путь", error)
            return

        # Скрыть от прошлого экспорта
        self.open_folder_btn.setVisible(False)
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

    @staticmethod
    def _format_time(seconds: float) -> str:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def closeEvent(self, event):
        super().closeEvent(event)