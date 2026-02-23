from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QProgressBar, QMessageBox, QFileDialog, QGroupBox,
    QScrollArea, QWidget, QTabWidget
)
from typing import List, Dict, Optional


class ExportWorker(QThread):
    """Worker thread для экспорта видео без блокировки UI."""

    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, video_path: str, markers: List[Dict], output_path: str,
                 fps: float, codec: str, quality: int, resolution: str = "source",
                 include_audio: bool = True, merge_segments: bool = False):
        super().__init__()
        self.video_path = video_path
        self.markers = markers
        self.output_path = output_path
        self.fps = fps
        self.codec = codec
        self.quality = quality
        self.resolution = resolution
        self.include_audio = include_audio
        self.merge_segments = merge_segments
        self.is_cancelled = False

    def run(self):
        try:
            self.progress.emit(0)
            from services.export.video_exporter import VideoExporter

            for idx, marker in enumerate(self.markers):
                if self.is_cancelled:
                    self.finished.emit(False, "Export cancelled")
                    return
                progress = int((idx + 1) / len(self.markers) * 100)
                self.progress.emit(progress)

            success = VideoExporter.export_segments(
                video_path=self.video_path,
                markers=self.markers,
                fps=self.fps,
                output_path=self.output_path,
                codec=self.codec,
                quality=self.quality,
                resolution=self.resolution,
                include_audio=self.include_audio,
                merge_segments=self.merge_segments
            )

            self.progress.emit(100)
            if success:
                if self.merge_segments:
                    message = f"Export completed: {self.output_path}"
                else:
                    message = f"Export completed: {len(self.markers)} separate files"
                self.finished.emit(True, message)
            else:
                self.finished.emit(False, "Export failed")

        except Exception as e:
            self.finished.emit(False, f"Export failed: {str(e)}")

    def cancel(self):
        self.is_cancelled = True


class ExportDialog(QDialog):
    """Диалог экспорта — видео, CSV, PDF."""

    # Сигналы для Controller
    export_requested = Signal(dict)       # параметры видео экспорта
    csv_export_requested = Signal(str)    # output_path для CSV
    pdf_export_requested = Signal(str)    # output_path для PDF

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Экспорт")
        self.setGeometry(200, 200, 720, 700)

        self.output_path = None
        self.video_path = None
        self.fps = 30.0
        self.segment_checkboxes = []
        self.export_worker = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # ===== ВЫБОР ОТРЕЗКОВ (общий для всех вкладок) =====
        segments_group = QGroupBox("Сегменты для экспорта")
        segments_layout = QVBoxLayout()

        select_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Выбрать все")
        self.select_all_btn.clicked.connect(self._select_all_segments)
        select_btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Снять все")
        self.deselect_all_btn.clicked.connect(self._deselect_all_segments)
        select_btn_layout.addWidget(self.deselect_all_btn)

        select_btn_layout.addStretch()
        segments_layout.addLayout(select_btn_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(150)

        scroll_widget = QWidget()
        self.segments_layout = QVBoxLayout()
        scroll_widget.setLayout(self.segments_layout)
        scroll_area.setWidget(scroll_widget)

        segments_layout.addWidget(scroll_area)
        segments_group.setLayout(segments_layout)
        layout.addWidget(segments_group)

        # ===== ВКЛАДКИ: Видео / CSV / PDF =====
        self.tabs = QTabWidget()

        # --- Вкладка: Видео ---
        video_tab = QWidget()
        self._setup_video_tab(video_tab)
        self.tabs.addTab(video_tab, "🎬 Видео")

        # --- Вкладка: CSV ---
        csv_tab = QWidget()
        self._setup_csv_tab(csv_tab)
        self.tabs.addTab(csv_tab, "📊 CSV")

        # --- Вкладка: PDF/HTML ---
        pdf_tab = QWidget()
        self._setup_pdf_tab(pdf_tab)
        self.tabs.addTab(pdf_tab, "📄 Отчёт PDF")

        layout.addWidget(self.tabs)

        # ===== ПРОГРЕСС =====
        progress_group = QGroupBox("Прогресс")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Готов к экспорту")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # ===== КНОПКА ЗАКРЫТИЯ =====
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

        self.setLayout(layout)

    # ──────────────────────────────────────────────────────────────────────
    # Video tab
    # ──────────────────────────────────────────────────────────────────────

    def _setup_video_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)

        # Кодек
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Кодек:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["libx264", "libx265", "mpeg4", "copy"])
        self.codec_combo.setToolTip("Видеокодек (рекомендуется libx264)")
        codec_layout.addWidget(self.codec_combo)
        codec_layout.addStretch()
        layout.addLayout(codec_layout)

        # Разрешение
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Разрешение:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["source", "2160p", "1080p", "720p", "480p", "360p"])
        res_layout.addWidget(self.resolution_combo)
        res_layout.addStretch()
        layout.addLayout(res_layout)

        # Качество
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Качество:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Высокое (CRF 18)", "Среднее (CRF 23)", "Низкое (CRF 28)", "Своё"])
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_combo)

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(0, 51)
        self.quality_spin.setValue(23)
        self.quality_spin.setSuffix(" CRF")
        self.quality_spin.setVisible(False)
        quality_layout.addWidget(self.quality_spin)

        quality_layout.addStretch()
        layout.addLayout(quality_layout)

        # Опции
        opts_layout = QHBoxLayout()
        self.audio_check = QCheckBox("Включить аудио")
        self.audio_check.setChecked(True)
        opts_layout.addWidget(self.audio_check)

        self.merge_check = QCheckBox("Объединить в один файл")
        self.merge_check.setChecked(True)
        opts_layout.addWidget(self.merge_check)

        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.video_browse_btn = QPushButton("📁 Выбрать путь")
        self.video_browse_btn.clicked.connect(self._on_browse_video_output)
        btn_layout.addWidget(self.video_browse_btn)

        btn_layout.addStretch()

        self.export_btn = QPushButton("▶ Экспортировать видео")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5016; color: white;
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3d6b1f; }
        """)
        self.export_btn.clicked.connect(self._on_export_video_clicked)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    # ──────────────────────────────────────────────────────────────────────
    # CSV tab
    # ──────────────────────────────────────────────────────────────────────

    def _setup_csv_tab(self, tab: QWidget) -> None:
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

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        csv_btn = QPushButton("📊 Экспортировать CSV")
        csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a5276; color: white;
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2471a3; }
        """)
        csv_btn.clicked.connect(self._on_export_csv_clicked)
        btn_layout.addWidget(csv_btn)

        layout.addLayout(btn_layout)

    # ──────────────────────────────────────────────────────────────────────
    # PDF tab
    # ──────────────────────────────────────────────────────────────────────

    def _setup_pdf_tab(self, tab: QWidget) -> None:
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

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        pdf_btn = QPushButton("📄 Экспортировать отчёт")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #7d3c98; color: white;
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #9b59b6; }
        """)
        pdf_btn.clicked.connect(self._on_export_pdf_clicked)
        btn_layout.addWidget(pdf_btn)

        layout.addLayout(btn_layout)

    # ──────────────────────────────────────────────────────────────────────
    # Segments list
    # ──────────────────────────────────────────────────────────────────────

    def set_segments(self, segments_data: List[Dict]):
        for cb in self.segment_checkboxes:
            if isinstance(cb, tuple):
                cb[1].setParent(None)
            else:
                cb.setParent(None)
        self.segment_checkboxes.clear()

        for segment in segments_data:
            segment_id = segment['id']
            event_name = segment['event_name']
            start_frame = segment['start_frame']
            end_frame = segment['end_frame']
            duration_sec = segment['duration_sec']

            start_time = self._format_time(start_frame / self.fps)
            end_time = self._format_time(end_frame / self.fps)

            text = f"{event_name} ({start_time}–{end_time}) [{duration_sec:.1f}с]"
            checkbox = QCheckBox(text)
            checkbox.setChecked(True)

            self.segment_checkboxes.append((segment_id, checkbox))
            self.segments_layout.addWidget(checkbox)

    def set_filtered_segments(self, segments_data: List[Dict]):
        self.set_segments(segments_data)

    def set_video_path(self, video_path: str):
        self.video_path = video_path

    def set_fps(self, fps: float):
        self.fps = fps if fps > 0 else 30.0

    def get_selected_segment_ids(self) -> List[int]:
        selected_ids = []
        for segment_id, checkbox in self.segment_checkboxes:
            if checkbox.isChecked():
                selected_ids.append(segment_id)
        return selected_ids

    def get_export_params(self) -> Dict:
        return {
            'codec': self.codec_combo.currentText(),
            'quality': self.quality_spin.value(),
            'resolution': self.resolution_combo.currentText(),
            'include_audio': self.audio_check.isChecked(),
            'merge_segments': self.merge_check.isChecked(),
            'output_path': self.output_path,
            'selected_segment_ids': self.get_selected_segment_ids()
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
        self.codec_combo.setEnabled(enabled)
        self.quality_spin.setEnabled(enabled)
        self.resolution_combo.setEnabled(enabled)
        self.audio_check.setEnabled(enabled)
        self.merge_check.setEnabled(enabled)
        self.tabs.setEnabled(enabled)

    # ──────────────────────────────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────────────────────────────

    def _select_all_segments(self):
        for _, checkbox in self.segment_checkboxes:
            checkbox.setChecked(True)

    def _deselect_all_segments(self):
        for _, checkbox in self.segment_checkboxes:
            checkbox.setChecked(False)

    def _on_quality_changed(self):
        text = self.quality_combo.currentText()
        if "Своё" in text:
            self.quality_spin.setVisible(True)
        else:
            self.quality_spin.setVisible(False)
            if "Высокое" in text:
                self.quality_spin.setValue(18)
            elif "Среднее" in text:
                self.quality_spin.setValue(23)
            elif "Низкое" in text:
                self.quality_spin.setValue(28)

    def _on_browse_video_output(self):
        if self.merge_check.isChecked():
            path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить видео", "", "Video Files (*.mp4);;All Files (*)"
            )
        else:
            path = QFileDialog.getExistingDirectory(self, "Папка для файлов")

        if path:
            self.output_path = path
            self.progress_label.setText(f"Путь: {path}")

    def _on_export_video_clicked(self):
        selected = self.get_selected_segment_ids()
        if not selected:
            QMessageBox.warning(self, "Нет сегментов", "Выберите хотя бы один сегмент")
            return

        if not self.output_path:
            QMessageBox.warning(self, "Нет пути", "Укажите путь для сохранения")
            return

        self.export_requested.emit(self.get_export_params())

    def _on_export_csv_clicked(self):
        selected = self.get_selected_segment_ids()
        if not selected:
            QMessageBox.warning(self, "Нет сегментов", "Выберите хотя бы один сегмент")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить CSV", "segments.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self.csv_export_requested.emit(path)

    def _on_export_pdf_clicked(self):
        selected = self.get_selected_segment_ids()
        if not selected:
            QMessageBox.warning(self, "Нет сегментов", "Выберите хотя бы один сегмент")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", "report.pdf",
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
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.cancel()
            self.export_worker.wait()
        super().closeEvent(event)