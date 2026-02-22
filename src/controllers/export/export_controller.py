from __future__ import annotations

from typing import List, Dict, Optional, Any

from PySide6.QtCore import QThread, Signal, QObject

from models.domain.marker import Marker
from models.domain.project import Project
from services.export.video_exporter import VideoExporter
from views.windows.export_dialog import ExportDialog


class ExportWorker(QThread):
    """Worker thread для экспорта видео без блокировки UI."""

    progress = Signal(int)          # 0-100
    finished = Signal(bool, str)    # success, message
    cancelled = Signal()            # emitted when cancelled (optional)

    def __init__(self, video_path: str, markers: List[Marker], fps: float, params: Dict[str, Any]):
        super().__init__()
        self.video_path = video_path
        self.markers = markers
        self.fps = fps
        self.params = params
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation."""
        self._cancelled = True

    def _cancel_check(self) -> bool:
        """Return True if export should stop."""
        return self._cancelled

    def run(self) -> None:
        try:
            self.progress.emit(0)

            if self._cancel_check():
                self.cancelled.emit()
                self.finished.emit(False, "Export cancelled")
                return

            # If your VideoExporter supports progress/cancel callbacks — use them.
            # Otherwise cancel won't interrupt the exporter, but at least prevents start.
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
                # Optional extensions (need support in VideoExporter):
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
            # Backward compatibility: VideoExporter may not accept extra args
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
    """Контроллер управления экспортом видео."""

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
        # Create a fresh dialog each time
        self.view = ExportDialog()
        self.view.export_requested.connect(self._on_export_requested)

        # Optional: if your dialog has cancel button signal
        if hasattr(self.view, "cancel_requested"):
            self.view.cancel_requested.connect(self._on_cancel_requested)

        segments_data = self._prepare_segments_data()
        self.view.set_segments(segments_data)

        self.view.set_video_path(self.video_path)
        self.view.set_fps(self.fps)

        self.view.exec()

    def _prepare_segments_data(self) -> List[Dict[str, Any]]:
        """Подготовить данные сегментов для View.

        IMPORTANT: use stable marker.id instead of enumerate index.
        """
        segments_data: List[Dict[str, Any]] = []
        fps = self.fps if self.fps > 0 else 0.0

        for marker in self.project.markers:
            duration_sec = ((marker.end_frame - marker.start_frame) / fps) if fps > 0 else 0.0
            segments_data.append({
                "id": marker.id,                    # stable id
                "event_name": marker.event_name,
                "start_frame": marker.start_frame,
                "end_frame": marker.end_frame,
                "duration_sec": duration_sec,
            })

        return segments_data

    # ──────────────────────────────────────────────────────────────────────────
    # Export
    # ──────────────────────────────────────────────────────────────────────────

    def _on_export_requested(self, params: Dict[str, Any]) -> None:
        """Обработка запроса на экспорт."""
        if not self.view:
            return

        if self.export_worker is not None:
            # already exporting
            return

        selected_ids = params.get("selected_segment_ids", [])
        if not selected_ids:
            return

        # Map id -> marker
        marker_by_id = {m.id: m for m in self.project.markers}
        selected_markers: List[Marker] = []
        for mid in selected_ids:
            m = marker_by_id.get(mid)
            if m is not None:
                selected_markers.append(m)

        if not selected_markers:
            return

        # Disable controls
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
        """User pressed cancel in dialog (if supported)."""
        if self.export_worker is not None:
            self.export_worker.cancel()

    def _on_progress_update(self, value: int) -> None:
        if self.view:
            self.view.set_progress(value, f"Exporting... {value}%")

    def _on_export_cancelled(self) -> None:
        # Optional hook; final UI is set in finished anyway
        pass

    def _on_export_finished(self, success: bool, message: str) -> None:
        """Экспорт завершен."""
        if self.view:
            self.view.set_controls_enabled(True)
            self.view.show_export_result(success, message)

        # Clean worker safely
        if self.export_worker is not None:
            try:
                self.export_worker.progress.disconnect(self._on_progress_update)
                self.export_worker.finished.disconnect(self._on_export_finished)
            except Exception:
                pass

            self.export_worker = None