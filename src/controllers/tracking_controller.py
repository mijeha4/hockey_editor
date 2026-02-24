"""
Tracking Controller — связывает трекинг с UI и видеоплеером.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, QRect

if TYPE_CHECKING:
    from controllers.main_controller import MainController
    from views.widgets.tracking_overlay import TrackingOverlay
    from views.widgets.tracking_panel import TrackingPanel


class TrackingController(QObject):
    """Контроллер трекинга игроков.

    Связывает:
    - PlayerTracker (сервис) — алгоритмы трекинга
    - TrackingOverlay (виджет) — выделение мышью и визуализация
    - TrackingPanel (виджет) — управление трекерами
    - PlaybackController — получение кадров
    """

    notification = Signal(str, str)  # message, type

    def __init__(self, main_controller: 'MainController', parent=None):
        super().__init__(parent)
        self._main = main_controller
        self._overlay: Optional[TrackingOverlay] = None
        self._panel: Optional[TrackingPanel] = None
        self._tracker = None  # Lazy init
        self._selecting = False

    def _get_tracker(self):
        """Lazy-инициализация трекера."""
        if self._tracker is None:
            from services.ai.tracking.player_tracker import PlayerTracker
            self._tracker = PlayerTracker()
            self._tracker.tracking_started.connect(self._on_tracking_started)
            self._tracker.tracking_lost.connect(self._on_tracking_lost)
            self._tracker.tracking_updated.connect(self._on_tracking_updated)
        return self._tracker

    # ──────────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────────

    def set_overlay(self, overlay: 'TrackingOverlay'):
        """Привязать overlay-виджет."""
        self._overlay = overlay
        overlay.player_selected.connect(self._on_player_selected)
        overlay.selection_cancelled.connect(self._on_selection_cancelled)

    def set_panel(self, panel: 'TrackingPanel'):
        """Привязать панель управления."""
        self._panel = panel
        panel.select_player_requested.connect(self._on_select_requested)
        panel.clear_all_requested.connect(self._on_clear_all)
        panel.tracker_type_changed.connect(self._on_tracker_type_changed)
        panel.show_trajectory_changed.connect(self._on_show_trajectory_changed)
        panel.show_labels_changed.connect(self._on_show_labels_changed)
        panel.remove_player_requested.connect(self._on_remove_player)
        panel.reinit_player_requested.connect(self._on_reinit_player)

    def connect_to_playback(self):
        """Подключиться к сигналам воспроизведения для обновления трекинга."""
        try:
            pc = self._main.playback_controller
            if hasattr(pc, 'frame_ready'):
                pc.frame_ready.connect(self._on_frame_ready)
            if hasattr(pc, 'seek_completed'):
                pc.seek_completed.connect(self._on_seek)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # Frame processing
    # ──────────────────────────────────────────────────────────────

    def process_frame(self, frame):
        """Обработать кадр — обновить трекеры и overlay.

        Вызывается из playback pipeline для каждого кадра.

        Args:
            frame: BGR numpy array

        Returns:
            frame с отрисованным трекингом (или оригинал)
        """
        tracker = self._get_tracker()

        if not tracker.is_enabled or tracker.active_count == 0:
            return frame

        # Обновить трекеры
        active_objects = tracker.update(frame)

        # Обновить overlay
        if self._overlay and active_objects:
            overlay_data = {}
            for tid, obj in active_objects.items():
                overlay_data[tid] = {
                    'bbox': obj.bbox,
                    'label': obj.label,
                    'color': obj.color,
                    'confidence': obj.confidence,
                    'trajectory': list(obj.trajectory),
                    'is_active': obj.is_active,
                }
            self._overlay.update_tracked_objects(overlay_data)

        # Обновить карточки в панели
        if self._panel:
            for tid, obj in tracker._multi_tracker.tracked_objects.items():
                self._panel.update_player_card(
                    tid, obj.confidence, obj.is_active
                )

        return frame

    def update_video_geometry(self, video_rect: QRect,
                               video_width: int, video_height: int):
        """Обновить геометрию видео для маппинга координат."""
        if self._overlay:
            self._overlay.set_video_rect(video_rect)
            self._overlay.set_video_size(video_width, video_height)

    # ──────────────────────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────────────────────

    def _on_select_requested(self):
        """Пользователь нажал 'Выделить игрока'."""
        if self._selecting:
            # Отмена
            self._selecting = False
            if self._overlay:
                self._overlay.cancel_selection()
            if self._panel:
                self._panel.set_selecting_mode(False)
        else:
            # Начать выделение
            self._selecting = True

            # Поставить на паузу
            try:
                if self._main.playback_controller.is_playing:
                    self._main.playback_controller.toggle_play_pause()
            except Exception:
                pass

            if self._overlay:
                self._overlay.start_selection()
            if self._panel:
                self._panel.set_selecting_mode(True)

    def _on_player_selected(self, x: int, y: int, w: int, h: int):
        """Пользователь выделил область на видео."""
        self._selecting = False

        if self._panel:
            self._panel.set_selecting_mode(False)

        # Получить текущий кадр
        frame = self._get_current_frame()
        if frame is None:
            self.notification.emit("Не удалось получить кадр", "error")
            return

        # Добавить в трекер
        tracker = self._get_tracker()
        track_id = tracker.add_player(frame, (x, y, w, h))

        if track_id is not None:
            info = tracker.get_player_info(track_id)
            if self._panel and info:
                self._panel.add_player_card(
                    track_id, info.label, info.color
                )

            if self._overlay:
                self._overlay.set_tracking_mode()

            self.notification.emit(
                f"Трекинг запущен: {info.label if info else f'#{track_id}'}",
                "success"
            )
        else:
            self.notification.emit(
                "Не удалось инициализировать трекер",
                "error"
            )

    def _on_selection_cancelled(self):
        self._selecting = False
        if self._panel:
            self._panel.set_selecting_mode(False)

    def _on_tracking_started(self, track_id: int):
        pass

    def _on_tracking_lost(self, track_id: int):
        tracker = self._get_tracker()
        info = tracker.get_player_info(track_id)
        label = info.label if info else f"#{track_id}"
        self.notification.emit(f"Трекинг потерян: {label}", "warning")

    def _on_tracking_updated(self, objects: dict):
        pass

    def _on_clear_all(self):
        tracker = self._get_tracker()
        tracker.clear_all()
        if self._panel:
            self._panel.clear_all_cards()
        if self._overlay:
            self._overlay.clear_tracking()
        self.notification.emit("Все трекеры удалены", "info")

    def _on_remove_player(self, track_id: int):
        tracker = self._get_tracker()
        tracker.remove_player(track_id)
        if self._panel:
            self._panel.remove_player_card(track_id)

    def _on_reinit_player(self, track_id: int):
        frame = self._get_current_frame()
        if frame is None:
            return
        tracker = self._get_tracker()
        obj = tracker.active_players.get(track_id)
        if obj:
            tracker.reinit_player(track_id, frame, obj.bbox)

    def _on_tracker_type_changed(self, type_name: str):
        self._get_tracker().set_tracker_type(type_name)

    def _on_show_trajectory_changed(self, show: bool):
        self._get_tracker().set_show_trajectory(show)
        if self._overlay:
            self._overlay._show_trajectory = show

    def _on_show_labels_changed(self, show: bool):
        self._get_tracker().set_show_label(show)
        if self._overlay:
            self._overlay._show_labels = show

    def _on_frame_ready(self, frame, frame_idx: int):
        """Callback от playback — обработать кадр."""
        self.process_frame(frame)

    def _on_seek(self):
        """При перемотке — переинициализировать трекеры."""
        frame = self._get_current_frame()
        if frame is not None:
            self._get_tracker().on_seek(frame)

    def _get_current_frame(self):
        """Получить текущий кадр из playback controller."""
        try:
            pc = self._main.playback_controller
            if hasattr(pc, 'get_current_frame_bgr'):
                return pc.get_current_frame_bgr()
            elif hasattr(pc, 'video_engine'):
                engine = pc.video_engine
                if hasattr(engine, 'get_frame'):
                    return engine.get_frame(pc.current_frame)
        except Exception:
            pass
        return None