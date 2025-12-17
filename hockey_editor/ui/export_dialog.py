"""
Export Dialog - Профессиональный диалог для экспорта видео с опциями.
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QProgressBar, QMessageBox, QFileDialog, QGroupBox,
    QScrollArea, QWidget
)
from typing import Optional, List
from ..models.marker import Marker, EventType
from ..core.exporter import VideoExporter


class ExportWorker(QThread):
    """Worker thread для экспорта видео без блокировки UI."""
    
    progress = Signal(int)  # 0-100
    finished = Signal(bool, str)  # (success, message)
    
    def __init__(self, video_path: str, markers: List[Marker],
                 output_path: str, fps: float, codec: str, quality: int,
                 resolution: str = "source", include_audio: bool = True,
                 merge_segments: bool = False, total_frames: int = 1000):
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
        self.total_frames = total_frames
        self.is_cancelled = False

    def run(self):
        """Запустить экспорт в отдельном потоке."""
        try:
            self.progress.emit(0)
            
            # Экспортировать отрезки
            for idx, marker in enumerate(self.markers):
                if self.is_cancelled:
                    self.finished.emit(False, "Export cancelled")
                    return
                
                progress = int((idx + 1) / len(self.markers) * 100)
                self.progress.emit(progress)
            
            # Финализировать экспорт
            VideoExporter.export(
                self.video_path,
                self.markers,
                self.total_frames,
                self.fps,
                self.output_path,
                codec=self.codec,
                quality=self.quality,
                resolution=self.resolution,
                include_audio=self.include_audio,
                merge_segments=self.merge_segments
            )
            
            self.progress.emit(100)
            self.finished.emit(True, f"Export completed: {self.output_path}")
            
        except Exception as e:
            self.finished.emit(False, f"Export failed: {str(e)}")

    def cancel(self):
        """Отменить экспорт."""
        self.is_cancelled = True


class ExportDialog(QDialog):
    """Профессиональный диалог для экспорта видео."""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.export_worker = None
        
        self.setWindowTitle("Export Segments")
        self.setGeometry(200, 200, 700, 650)
        
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
        
        # Создать checkbox для каждого отрезка
        self.segment_checkboxes = []
        self._populate_segments()
        
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
        self.codec_combo.addItems(["h264", "h265", "mpeg4", "copy"])
        self.codec_combo.setToolTip("Video codec (h264 recommended)")
        codec_layout.addWidget(self.codec_combo)
        codec_layout.addStretch()
        video_layout.addLayout(codec_layout)
        
        # Разрешение
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "Source (Original)",
            "2160p (4K)",
            "1080p (Full HD)",
            "720p (HD)",
            "480p (SD)",
            "360p"
        ])
        self.resolution_combo.setCurrentIndex(0)  # Source by default
        self.resolution_combo.setToolTip("Output video resolution")
        resolution_layout.addWidget(self.resolution_combo)
        resolution_layout.addStretch()
        video_layout.addLayout(resolution_layout)
        
        # Качество / Bitrate
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
        self.quality_spin.setVisible(False)
        self.quality_spin.setToolTip("CRF value (0=best, 51=worst)")
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
        self.merge_check.setChecked(False)
        self.merge_check.setToolTip("Merge all segments into one video file")
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
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.output_path = None
    
    def _populate_segments(self):
        """Заполнить список отрезков."""
        # Очистить старые checkbox
        for cb in self.segment_checkboxes:
            cb.setParent(None)
        self.segment_checkboxes.clear()
        
        # Создать checkbox для каждого отрезка
        fps = self.controller.get_fps()
        for idx, marker in enumerate(self.controller.markers):
            start_time = self._format_time(marker.start_frame / fps if fps > 0 else 0)
            end_time = self._format_time(marker.end_frame / fps if fps > 0 else 0)
            duration = (marker.end_frame - marker.start_frame) / fps if fps > 0 else 0
            
            text = f"{idx+1}. {marker.event_name} ({start_time}–{end_time}) [{duration:.1f}s]"
            checkbox = QCheckBox(text)
            checkbox.setChecked(True)
            
            self.segment_checkboxes.append(checkbox)
            self.segments_layout.addWidget(checkbox)
    
    def _select_all_segments(self):
        """Выбрать все отрезки."""
        for cb in self.segment_checkboxes:
            cb.setChecked(True)
    
    def _deselect_all_segments(self):
        """Снять выбор со всех отрезков."""
        for cb in self.segment_checkboxes:
            cb.setChecked(False)
    
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
    
    def _get_resolution_value(self) -> str:
        """Получить значение разрешения."""
        resolution_map = {
            0: "source",
            1: "2160p",
            2: "1080p",
            3: "720p",
            4: "480p",
            5: "360p"
        }
        return resolution_map.get(self.resolution_combo.currentIndex(), "source")
    
    def _format_time(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _on_browse_output(self):
        """Выбрать путь сохранения."""
        format_idx = self.format_combo.currentIndex()
        extensions = [".mp4", ".mov", ".mkv", ".webm"]
        ext = extensions[format_idx] if format_idx < len(extensions) else ".mp4"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Export As", "",
            f"Video Files (*{ext});;All Files (*)"
        )
        
        if path:
            self.output_path = path
            self.progress_label.setText(f"Output: {path}")

    def _on_export_clicked(self):
        """Начать экспорт."""
        # Получить выбранные отрезки
        selected_markers = []
        for idx, cb in enumerate(self.segment_checkboxes):
            if cb.isChecked():
                selected_markers.append(self.controller.markers[idx])
        
        if not selected_markers:
            QMessageBox.warning(self, "No Segments", "Please select at least one segment to export")
            return
        
        if not self.output_path:
            QMessageBox.warning(self, "No Output Path", "Please select output file")
            return
        
        # Disable controls
        self.export_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.codec_combo.setEnabled(False)
        self.quality_spin.setEnabled(False)
        self.quality_combo.setEnabled(False)
        self.resolution_combo.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.audio_check.setEnabled(False)
        self.merge_check.setEnabled(False)
        
        # Получить параметры экспорта
        codec = self.codec_combo.currentText()
        crf_value = self.quality_spin.value()
        resolution = self._get_resolution_value()
        include_audio = self.audio_check.isChecked()
        merge_segments = self.merge_check.isChecked()
        
        # Получить общее количество кадров
        total_frames = getattr(self.controller, 'get_total_frames', lambda: 1000)()

        # Запустить экспорт в отдельном потоке
        self.export_worker = ExportWorker(
            self.controller.processor.video_path,
            selected_markers,
            self.output_path,
            self.controller.get_fps(),
            codec,
            crf_value,
            resolution,
            include_audio,
            merge_segments,
            total_frames
        )
        
        self.export_worker.progress.connect(self._on_progress_update)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.start()
        
        self.progress_label.setText("Exporting...")

    def _on_progress_update(self, value: int):
        """Обновить прогресс."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"Exporting... {value}%")

    def _on_export_finished(self, success: bool, message: str):
        """Экспорт завершился."""
        # Re-enable controls
        self.export_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.codec_combo.setEnabled(True)
        self.quality_spin.setEnabled(True)
        self.quality_combo.setEnabled(True)
        self.resolution_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.audio_check.setEnabled(True)
        self.merge_check.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.progress_label.setText("Export completed!")
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", message)
            self.progress_label.setText("Export failed")
            self.progress_bar.setValue(0)

    def _on_cancel_clicked(self):
        """Отменить экспорт."""
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.cancel()
            self.export_worker.wait()
        self.reject()
