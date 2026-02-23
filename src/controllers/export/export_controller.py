from __future__ import annotations

from typing import List, Dict, Optional, Any

from PySide6.QtCore import QThread, Signal, QObject

from models.domain.marker import Marker
from models.domain.project import Project
from services.export.video_exporter import VideoExporter
from services.export.report_exporter import ReportExporter
from views.windows.export_dialog import ExportDialog


class ExportWorker(QThread):
    """Worker thread для экспорта видео без блокировки UI."""

    progress = Signal(int)          # 0-100
    finished = Signal(bool, str)    # success, message
    cancelled = Signal()

    def __init__(self, video_path: str, markers: List[Marker], fps: float, params: Dict[str, Any]):
        super().__init__()
        self.video_path = video_path
        self.markers = markers
        self.fps = fps
        self.params = params
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _cancel_check(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            self.progress.emit(0)

            if self._cancel_check():
                self.cancelled.emit()
                self.finished.emit(False, "Export cancelled")
                return

            success = VideoExporter.export_segments(
                video_path=self.video_path,
                markers=self.markers,
                fps=self.fps,
                output_path=self.params["output_path"],
                codec=self.params["codec"],
                quality=self.params["quality"],
                resolution=self.params["resolution"],
                include_audio=self.params["include_audio"],
                merge_segments=self.params["merge_segments"],
                progress_callback=getattr(self, "_progress_callback", None),
                cancel_check=self._cancel_check,
            )

            if self._cancel_check():
                self.cancelled.emit()
                self.finished.emit(False, "Export cancelled")
                return

            self.progress.emit(100)

            if success:
                if self.params["merge_segments"]:
                    message = f"Export completed: {self.params['output_path']}"
                else:
                    message = (
                        f"Export completed: {len(self.markers)} separate files in "
                        f"{self.params['output_path']}"
                    )
            else:
                message = "Export failed"

            self.finished.emit(success, message)

        except TypeError:
            try:
                success = VideoExporter.export_segments(
                    video_path=self.video_path,
                    markers=self.markers,
                    fps=self.fps,
                    output_path=self.params["output_path"],
                    codec=self.params["codec"],
                    quality=self.params["quality"],
                    resolution=self.params["resolution"],
                    include_audio=self.params["include_audio"],
                    merge_segments=self.params["merge_segments"],
                )
                self.progress.emit(100)
                self.finished.emit(bool(success), "Export completed" if success else "Export failed")
            except Exception as e:
                self.finished.emit(False, f"Export failed: {e}")

        except Exception as e:
            self.finished.emit(False, f"Export failed: {e}")


class ExportController(QObject):
    """Контроллер управления экспортом видео и отчётов."""

    def __init__(self, project: Project, video_path: str, fps: float):
        super().__init__()
        self.project = project
        self.video_path = video_path
        self.fps = fps

        self.view: Optional[ExportDialog] = None
        self.export_worker: Optional[ExportWorker] = None

    # ──────────────────────────────────────────────────────────────────────────
    # Dialog
    # ──────────────────────────────────────────────────────────────────────────

    def show_dialog(self) -> None:
        """Показать диалог экспорта."""
        self.view = ExportDialog()
        self.view.export_requested.connect(self._on_export_requested)

        if hasattr(self.view, "cancel_requested"):
            self.view.cancel_requested.connect(self._on_cancel_requested)

        # === НОВОЕ: подключение сигналов экспорта отчётов ===
        if hasattr(self.view, "csv_export_requested"):
            self.view.csv_export_requested.connect(self._on_csv_export)
        if hasattr(self.view, "pdf_export_requested"):
            self.view.pdf_export_requested.connect(self._on_pdf_export)

        segments_data = self._prepare_segments_data()
        self.view.set_segments(segments_data)

        self.view.set_video_path(self.video_path)
        self.view.set_fps(self.fps)

        self.view.exec()

    def _prepare_segments_data(self) -> List[Dict[str, Any]]:
        segments_data: List[Dict[str, Any]] = []
        fps = self.fps if self.fps > 0 else 0.0

        for marker in self.project.markers:
            duration_sec = ((marker.end_frame - marker.start_frame) / fps) if fps > 0 else 0.0
            segments_data.append({
                "id": marker.id,
                "event_name": marker.event_name,
                "start_frame": marker.start_frame,
                "end_frame": marker.end_frame,
                "duration_sec": duration_sec,
            })

        return segments_data

    # ──────────────────────────────────────────────────────────────────────────
    # Video Export
    # ──────────────────────────────────────────────────────────────────────────

    def _on_export_requested(self, params: Dict[str, Any]) -> None:
        if not self.view:
            return

        if self.export_worker is not None:
            return

        selected_ids = params.get("selected_segment_ids", [])
        if not selected_ids:
            return

        marker_by_id = {m.id: m for m in self.project.markers}
        selected_markers: List[Marker] = []
        for mid in selected_ids:
            m = marker_by_id.get(mid)
            if m is not None:
                selected_markers.append(m)

        if not selected_markers:
            return

        self.view.set_controls_enabled(False)
        self.view.set_progress(0, "Exporting...")

        self.export_worker = ExportWorker(
            video_path=self.video_path,
            markers=selected_markers,
            fps=self.fps,
            params=params,
        )
        self.export_worker.progress.connect(self._on_progress_update)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.cancelled.connect(self._on_export_cancelled)

        self.export_worker.start()

    def _on_cancel_requested(self) -> None:
        if self.export_worker is not None:
            self.export_worker.cancel()

    def _on_progress_update(self, value: int) -> None:
        if self.view:
            self.view.set_progress(value, f"Exporting... {value}%")

    def _on_export_cancelled(self) -> None:
        pass

    def _on_export_finished(self, success: bool, message: str) -> None:
        if self.view:
            self.view.set_controls_enabled(True)
            self.view.show_export_result(success, message)

        if self.export_worker is not None:
            try:
                self.export_worker.progress.disconnect(self._on_progress_update)
                self.export_worker.finished.disconnect(self._on_export_finished)
            except Exception:
                pass
            self.export_worker = None

    # ──────────────────────────────────────────────────────────────────────────
    # CSV / PDF Export (NEW)
    # ──────────────────────────────────────────────────────────────────────────

    def _on_csv_export(self, output_path: str) -> None:
        """Экспорт данных сегментов в CSV."""
        try:
            markers = self._get_selected_markers_from_view()
            if not markers:
                markers = list(self.project.markers)

            success = ReportExporter.export_csv(
                markers=markers,
                fps=self.fps,
                output_path=output_path,
                project_name=getattr(self.project, "name", ""),
                video_path=self.video_path,
            )

            if self.view:
                if success:
                    self.view.show_export_result(True, f"CSV экспортирован: {output_path}")
                else:
                    self.view.show_export_result(False, "Ошибка экспорта CSV")

        except Exception as e:
            if self.view:
                self.view.show_export_result(False, f"Ошибка CSV: {e}")

    def _on_pdf_export(self, output_path: str) -> None:
        """Экспорт отчёта в PDF (или HTML)."""
        try:
            markers = self._get_selected_markers_from_view()
            if not markers:
                markers = list(self.project.markers)

            success = ReportExporter.export_pdf(
                markers=markers,
                fps=self.fps,
                output_path=output_path,
                project_name=getattr(self.project, "name", ""),
                video_path=self.video_path,
            )

            if self.view:
                if success:
                    self.view.show_export_result(True, f"Отчёт экспортирован: {output_path}")
                else:
                    self.view.show_export_result(False, "Ошибка экспорта отчёта")

        except Exception as e:
            if self.view:
                self.view.show_export_result(False, f"Ошибка отчёта: {e}")

    def _get_selected_markers_from_view(self) -> List[Marker]:
        """Получить выбранные маркеры из диалога."""
        if not self.view:
            return []

        selected_ids = self.view.get_selected_segment_ids()
        if not selected_ids:
            return []

        marker_by_id = {m.id: m for m in self.project.markers}
        return [marker_by_id[mid] for mid in selected_ids if mid in marker_by_id]