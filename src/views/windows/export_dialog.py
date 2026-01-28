from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QProgressBar, QMessageBox, QFileDialog, QGroupBox,
    QScrollArea, QWidget
)
from typing import List, Dict, Optional


class ExportWorker(QThread):
    """Worker thread для экспорта видео без блокировки UI."""

    progress = Signal(int)  # 0-100
    finished = Signal(bool, str)  # (success, message)

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
        """Запустить экспорт в отдельном потоке."""
        try:
            self.progress.emit(0)

            # Импортировать VideoExporter здесь, чтобы избежать циклических импортов
            from services.export.video_exporter import VideoExporter

            # Экспортировать сегменты
            for idx, marker in enumerate(self.markers):
                if self.is_cancelled:
                    self.finished.emit(False, "Export cancelled")
                    return

                progress = int((idx + 1) / len(self.markers) * 100)
                self.progress.emit(progress)

            # Финализировать экспорт
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
        """Отменить экспорт."""
        self.is_cancelled = True


class ExportDialog(QDialog):
    """Диалог экспорта видео сегментов - чистый View."""

    # Сигналы для Controller
    export_requested = Signal(dict)  # параметры экспорта
    browse_output_requested = Signal(bool)  # merge_segments

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Export Segments")
        self.setGeometry(200, 200, 700, 650)

        self.output_path = None
        self.video_path = None  # Добавлено: путь к видео файлу
        self.fps = 30.0  # Добавлено: FPS видео
        self.segment_checkboxes = []
        self.export_worker = None

        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # ===== ВЫБОР ОТРЕЗКОВ =====
        group = QGroupBox("Segments to Export")
        group_layout = QVBoxLayout()

        # Кнопки управления выбором
        select_btn_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all_segments)
        select_btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self._deselect_all_segments)
        select_btn_layout.addWidget(self.deselect_all_btn)

        select_btn_layout.addStretch()
        group_layout.addLayout(select_btn_layout)

        # Список отрезков с checkbox
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(150)

        scroll_widget = QWidget()
        self.segments_layout = QVBoxLayout()
        scroll_widget.setLayout(self.segments_layout)
        scroll_area.setWidget(scroll_widget)

        group_layout.addWidget(scroll_area)
        group.setLayout(group_layout)
        layout.addWidget(group)

        # ===== ОПЦИИ ВИДЕО =====
        video_group = QGroupBox("Video Options")
        video_layout = QVBoxLayout()

        # Кодек
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Codec:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["libx264", "libx265", "mpeg4", "copy"])
        self.codec_combo.setToolTip("Video codec (libx264 recommended)")
        codec_layout.addWidget(self.codec_combo)
        codec_layout.addStretch()
        video_layout.addLayout(codec_layout)

        # Разрешение
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "source",
            "2160p",
            "1080p",
            "720p",
            "480p",
            "360p"
        ])
        self.resolution_combo.setCurrentIndex(0)  # source by default
        self.resolution_combo.setToolTip("Output video resolution")
        resolution_layout.addWidget(self.resolution_combo)
        resolution_layout.addStretch()
        video_layout.addLayout(resolution_layout)

        # Качество / CRF с пресетами
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "High (CRF 18)",
            "Medium (CRF 23)",
            "Low (CRF 28)",
            "Custom"
        ])
        self.quality_combo.setCurrentIndex(1)  # Medium by default
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        self.quality_combo.setToolTip("Video quality (lower CRF = better quality)")
        quality_layout.addWidget(self.quality_combo)

        self.quality_spin = QSpinBox()
        self.quality_spin.setMinimum(0)
        self.quality_spin.setMaximum(51)
        self.quality_spin.setValue(23)
        self.quality_spin.setSuffix(" CRF")
        self.quality_spin.setToolTip("CRF value (0=best, 51=worst)")
        self.quality_spin.setVisible(False)
        quality_layout.addWidget(self.quality_spin)

        quality_layout.addStretch()
        video_layout.addLayout(quality_layout)

        # Формат
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4 (.mp4)", "MOV (.mov)", "MKV (.mkv)", "WebM (.webm)"])
        self.format_combo.setToolTip("Output file format")
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        video_layout.addLayout(format_layout)

        # Дополнительные опции
        options_layout = QHBoxLayout()

        self.audio_check = QCheckBox("Include Audio")
        self.audio_check.setChecked(True)
        self.audio_check.setToolTip("Include audio from source video")
        options_layout.addWidget(self.audio_check)

        self.merge_check = QCheckBox("Merge Segments")
        self.merge_check.setChecked(True)
        self.merge_check.setToolTip("Merge all segments into one video file")
        self.merge_check.stateChanged.connect(self._on_merge_segments_changed)
        options_layout.addWidget(self.merge_check)

        options_layout.addStretch()
        video_layout.addLayout(options_layout)

        video_group.setLayout(video_layout)
        layout.addWidget(video_group)

        # ===== ПРОГРЕСС =====
        progress_group = QGroupBox("Export Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to export")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # ===== КНОПКИ =====
        btn_layout = QHBoxLayout()

        self.browse_btn = QPushButton("📁 Browse Output")
        self.browse_btn.setToolTip("Select output file path")
        self.browse_btn.clicked.connect(self._on_browse_output)
        btn_layout.addWidget(self.browse_btn)

        btn_layout.addStretch()

        self.export_btn = QPushButton("▶ Export")
        self.export_btn.setToolTip("Start export process")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5016;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d6b1f;
            }
        """)
        self.export_btn.clicked.connect(self._on_export_clicked)
        btn_layout.addWidget(self.export_btn)

        self.cancel_btn = QPushButton("✕ Cancel")
        self.cancel_btn.setToolTip("Cancel and close dialog")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Инициализировать подсказку кнопки
        self._on_merge_segments_changed()

    def set_segments(self, segments_data: List[Dict]):
        """
        Установить список сегментов для выбора.

        segments_data: [{'id': int, 'event_name': str, 'start_frame': int,
                        'end_frame': int, 'duration_sec': float}, ...]
        """
        # Очистить старые checkbox
        for cb in self.segment_checkboxes:
            cb.setParent(None)
        self.segment_checkboxes.clear()

        # Создать checkbox для каждого сегмента
        for segment in segments_data:
            segment_id = segment['id']
            event_name = segment['event_name']
            start_frame = segment['start_frame']
            end_frame = segment['end_frame']
            duration_sec = segment['duration_sec']

            # Форматировать время
            start_time = self._format_time(start_frame / self.fps)  # Используем реальный FPS
            end_time = self._format_time(end_frame / self.fps)

            text = f"{segment_id+1}. {event_name} ({start_time}–{end_time}) [{duration_sec:.1f}s]"
            checkbox = QCheckBox(text)
            checkbox.setChecked(True)

            self.segment_checkboxes.append((segment_id, checkbox))
            self.segments_layout.addWidget(checkbox)

    def set_video_path(self, video_path: str):
        """Установить путь к видео файлу."""
        self.video_path = video_path

    def set_fps(self, fps: float):
        """Установить FPS видео."""
        self.fps = fps

    def get_selected_segment_ids(self) -> List[int]:
        """Получить ID выбранных сегментов."""
        selected_ids = []
        for segment_id, checkbox in self.segment_checkboxes:
            if checkbox.isChecked():
                selected_ids.append(segment_id)
        return selected_ids

    def get_export_params(self) -> Dict:
        """Получить параметры экспорта."""
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
        """Установить прогресс экспорта."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def show_export_result(self, success: bool, message: str):
        """Показать результат экспорта."""
        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", message)
            self.progress_bar.setValue(0)

    def set_controls_enabled(self, enabled: bool):
        """Включить/отключить элементы управления."""
        self.export_btn.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.codec_combo.setEnabled(enabled)
        self.quality_spin.setEnabled(enabled)
        self.resolution_combo.setEnabled(enabled)
        self.audio_check.setEnabled(enabled)
        self.merge_check.setEnabled(enabled)

    def _select_all_segments(self):
        """Выбрать все сегменты."""
        for _, checkbox in self.segment_checkboxes:
            checkbox.setChecked(True)

    def _deselect_all_segments(self):
        """Снять выбор со всех сегментов."""
        for _, checkbox in self.segment_checkboxes:
            checkbox.setChecked(False)

    def _format_time(self, seconds: float) -> str:
        """Форматировать время в MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _on_merge_segments_changed(self):
        """Обработка изменения Merge Segments."""
        merge_segments = self.merge_check.isChecked()
        if merge_segments:
            self.browse_btn.setToolTip("Select output file path")
        else:
            self.browse_btn.setToolTip("Select output directory for separate files")

    def _on_browse_output(self):
        """Выбрать путь сохранения."""
        merge_segments = self.merge_check.isChecked()

        if merge_segments:
            # Выбор файла для объединенного видео
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Export As", "",
                "Video Files (*.mp4);;All Files (*)"
            )
        else:
            # Выбор папки для отдельных файлов
            path = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", ""
            )

        if path:
            self.output_path = path
            if merge_segments:
                self.progress_label.setText(f"Output: {path}")
            else:
                self.progress_label.setText(f"Output directory: {path}")

    def _on_quality_changed(self):
        """Обработка изменения качества."""
        quality_text = self.quality_combo.currentText()

        if "Custom" in quality_text:
            self.quality_spin.setVisible(True)
        else:
            self.quality_spin.setVisible(False)

            if "High" in quality_text:
                self.quality_spin.setValue(18)
            elif "Medium" in quality_text:
                self.quality_spin.setValue(23)
            elif "Low" in quality_text:
                self.quality_spin.setValue(28)

    def _on_export_clicked(self):
        """Начать экспорт."""
        # Проверить выбор сегментов
        selected_segment_ids = self.get_selected_segment_ids()
        if not selected_segment_ids:
            QMessageBox.warning(self, "No Segments", "Please select at least one segment to export")
            return

        if not self.output_path:
            if self.merge_check.isChecked():
                QMessageBox.warning(self, "No Output Path", "Please select output file")
            else:
                QMessageBox.warning(self, "No Output Directory", "Please select output directory")
            return

        # Отключить элементы управления
        self.set_controls_enabled(False)

        # Получить параметры экспорта
        codec = self.codec_combo.currentText()
        crf_value = self.quality_spin.value()
        resolution = self.resolution_combo.currentText()
        include_audio = self.audio_check.isChecked()
        merge_segments = self.merge_check.isChecked()

        # Отправить сигнал с параметрами (реальные маркеры получит controller)
        params = {
            'codec': codec,
            'quality': crf_value,
            'resolution': resolution,
            'include_audio': include_audio,
            'merge_segments': merge_segments,
            'output_path': self.output_path,
            'selected_segment_ids': selected_segment_ids
        }

        self.export_requested.emit(params)

    def _on_progress_update(self, value: int):
        """Обновить прогресс."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"Exporting... {value}%")

    def _on_export_finished(self, success: bool, message: str):
        """Экспорт завершился."""
        # Re-enable controls
        self.set_controls_enabled(True)

        if success:
            QMessageBox.information(self, "Success", message)
            self.progress_label.setText("Export completed!")
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", message)
            self.progress_label.setText("Export failed")
            self.progress_bar.setValue(0)

    def closeEvent(self, event):
        """Handle dialog close - cancel any running export."""
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.cancel()
            self.export_worker.wait()
        super().closeEvent(event)
