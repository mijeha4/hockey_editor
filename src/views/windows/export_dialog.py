from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QProgressBar, QMessageBox, QFileDialog, QGroupBox,
    QScrollArea, QWidget
)
from typing import List, Dict


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
        self.segment_checkboxes = []

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

        # Качество / CRF
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality (CRF):"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setMinimum(0)
        self.quality_spin.setMaximum(51)
        self.quality_spin.setValue(23)
        self.quality_spin.setSuffix(" CRF")
        self.quality_spin.setToolTip("CRF value (0=best quality, 51=worst)")
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()
        video_layout.addLayout(quality_layout)

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
            start_time = self._format_time(start_frame / 30.0)  # Предполагаем 30 FPS для отображения
            end_time = self._format_time(end_frame / 30.0)

            text = f"{segment_id+1}. {event_name} ({start_time}–{end_time}) [{duration_sec:.1f}s]"
            checkbox = QCheckBox(text)
            checkbox.setChecked(True)

            self.segment_checkboxes.append((segment_id, checkbox))
            self.segments_layout.addWidget(checkbox)

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

    def _on_export_clicked(self):
        """Начать экспорт."""
        if not self.output_path:
            QMessageBox.warning(self, "No Output Path", "Please select output path")
            return

        selected_ids = self.get_selected_segment_ids()
        if not selected_ids:
            QMessageBox.warning(self, "No Segments", "Please select at least one segment to export")
            return

        # Отправить сигнал Controller
        params = self.get_export_params()
        self.export_requested.emit(params)
