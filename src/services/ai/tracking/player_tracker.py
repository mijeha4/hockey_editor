"""
Player Tracker — высокоуровневый сервис трекинга игроков.

Координирует:
- Выделение игрока мышью (ROI selection)
- Запуск трекинга
- Авто-реинициализацию при потере
- Детекцию игроков для помощи в выделении
"""

from __future__ import annotations

from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import cv2
import numpy as np

from PySide6.QtCore import QObject, Signal

from services.ai.tracking.tracker_engine import (
    MultiTracker, TrackedObject, TrackerType
)


@dataclass
class PlayerInfo:
    """Информация об отслеживаемом игроке."""
    track_id: int
    label: str
    team: str = ""
    number: str = ""
    color: Tuple[int, int, int] = (124, 58, 237)


class PlayerTracker(QObject):
    """Сервис трекинга игроков на видео.

    Использование:
    1. Пользователь выделяет игрока мышью на видео (ROI)
    2. PlayerTracker инициализирует трекер
    3. При каждом новом кадре вызывается update()
    4. Возвращает позиции всех отслеживаемых игроков
    """

    # Сигналы
    tracking_started = Signal(int)          # track_id
    tracking_lost = Signal(int)             # track_id
    tracking_updated = Signal(dict)         # {track_id: TrackedObject}
    player_selected = Signal(int, object)   # track_id, TrackedObject

    def __init__(self, parent=None):
        super().__init__(parent)

        self._multi_tracker = MultiTracker(TrackerType.CSRT)
        self._players: Dict[int, PlayerInfo] = {}
        self._enabled = False
        self._last_frame: Optional[np.ndarray] = None
        self._frame_count = 0

        # Настройки
        self._show_trajectory = True
        self._show_bbox = True
        self._show_label = True
        self._auto_reinit = True

        # Палитра цветов для разных игроков
        self._color_palette = [
            (124, 58, 237),   # Фиолетовый
            (6, 182, 212),    # Бирюзовый
            (239, 68, 68),    # Красный
            (16, 185, 129),   # Зелёный
            (245, 158, 11),   # Оранжевый
            (236, 72, 153),   # Розовый
            (59, 130, 246),   # Синий
            (168, 85, 247),   # Пурпурный
        ]
        self._color_index = 0

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def active_players(self) -> Dict[int, TrackedObject]:
        return self._multi_tracker.tracked_objects

    @property
    def active_count(self) -> int:
        return self._multi_tracker.active_count

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self.clear_all()

    def set_tracker_type(self, tracker_type: str):
        """Установить алгоритм трекинга."""
        type_map = {
            "CSRT": TrackerType.CSRT,
            "KCF": TrackerType.KCF,
            "MOSSE": TrackerType.MOSSE,
            "MedianFlow": TrackerType.MEDIAN_FLOW,
        }
        tt = type_map.get(tracker_type, TrackerType.CSRT)
        self._multi_tracker.set_tracker_type(tt)

    def set_show_trajectory(self, show: bool):
        self._show_trajectory = show

    def set_show_bbox(self, show: bool):
        self._show_bbox = show

    def set_show_label(self, show: bool):
        self._show_label = show

    def add_player(self, frame: np.ndarray,
                   bbox: Tuple[int, int, int, int],
                   label: str = "",
                   team: str = "") -> Optional[int]:
        """Добавить игрока для отслеживания.

        Args:
            frame: Текущий BGR кадр
            bbox: (x, y, width, height) выделенная область
            label: Метка (имя, номер)
            team: Команда

        Returns:
            track_id или None
        """
        color = self._next_color()

        if not label:
            label = f"Игрок {self._multi_tracker._next_id}"

        track_id = self._multi_tracker.add_object(frame, bbox, label, color)

        if track_id is not None:
            self._players[track_id] = PlayerInfo(
                track_id=track_id,
                label=label,
                team=team,
                color=color,
            )
            self._enabled = True
            self.tracking_started.emit(track_id)

        return track_id

    def update(self, frame: np.ndarray) -> Dict[int, TrackedObject]:
        """Обновить трекинг на новом кадре.

        Вызывается для каждого кадра при воспроизведении.

        Args:
            frame: Текущий BGR кадр

        Returns:
            Словарь активных объектов
        """
        if not self._enabled or self._multi_tracker.active_count == 0:
            return {}

        self._last_frame = frame
        self._frame_count += 1

        # Обновить все трекеры
        active = self._multi_tracker.update(frame)

        # Проверить потерянные объекты
        for track_id, obj in self._multi_tracker.tracked_objects.items():
            if not obj.is_active and track_id in self._players:
                self.tracking_lost.emit(track_id)

        self.tracking_updated.emit(active)
        return active

    def remove_player(self, track_id: int):
        """Удалить игрока из трекинга."""
        self._multi_tracker.remove_object(track_id)
        if track_id in self._players:
            del self._players[track_id]

    def reinit_player(self, track_id: int, frame: np.ndarray,
                      bbox: Tuple[int, int, int, int]) -> bool:
        """Переинициализировать трекер после потери."""
        return self._multi_tracker.reinit_object(track_id, frame, bbox)

    def clear_all(self):
        """Удалить всех отслеживаемых игроков."""
        self._multi_tracker.clear_all()
        self._players.clear()
        self._color_index = 0

    def get_player_info(self, track_id: int) -> Optional[PlayerInfo]:
        return self._players.get(track_id)

    def on_seek(self, frame: np.ndarray):
        """Вызвать при перемотке — нужна переинициализация.

        При перемотке трекеры теряют контекст. Пробуем
        реинициализировать по последним известным позициям.
        """
        if not self._enabled:
            return

        for track_id, obj in list(self._multi_tracker.tracked_objects.items()):
            if obj.is_active:
                # Попытаться реинициализировать в той же позиции
                self._multi_tracker.reinit_object(track_id, frame, obj.bbox)

    # ──────────────────────────────────────────────────────────────
    # Rendering
    # ──────────────────────────────────────────────────────────────

    def render_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Отрисовать оверлей трекинга на кадре.

        Args:
            frame: BGR кадр (будет модифицирован)

        Returns:
            Кадр с нарисованными элементами трекинга
        """
        if not self._enabled:
            return frame

        overlay = frame.copy()

        for track_id, obj in self._multi_tracker.tracked_objects.items():
            if not obj.is_active:
                continue

            x, y, w, h = obj.bbox
            r, g, b = obj.color

            # ── Trajectory (хвост) ──
            if self._show_trajectory and len(obj.trajectory) > 1:
                points = obj.trajectory
                for i in range(1, len(points)):
                    # Постепенное затухание
                    alpha = i / len(points)
                    thickness = max(1, int(3 * alpha))
                    color = (
                        int(b * alpha),
                        int(g * alpha),
                        int(r * alpha),
                    )
                    cv2.line(overlay, points[i - 1], points[i],
                             color, thickness, cv2.LINE_AA)

            # ── Bounding box ──
            if self._show_bbox:
                # Полупрозрачная заливка
                sub_img = overlay[max(0, y):y + h, max(0, x):x + w]
                if sub_img.size > 0:
                    tint = np.full_like(sub_img, (b, g, r), dtype=np.uint8)
                    cv2.addWeighted(tint, 0.15, sub_img, 0.85, 0, sub_img)

                # Рамка
                cv2.rectangle(overlay, (x, y), (x + w, y + h),
                              (b, g, r), 2, cv2.LINE_AA)

                # Уголки (стильные)
                corner_len = min(20, w // 4, h // 4)
                corner_thickness = 3
                # Top-left
                cv2.line(overlay, (x, y), (x + corner_len, y),
                         (b, g, r), corner_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x, y), (x, y + corner_len),
                         (b, g, r), corner_thickness, cv2.LINE_AA)
                # Top-right
                cv2.line(overlay, (x + w, y), (x + w - corner_len, y),
                         (b, g, r), corner_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x + w, y), (x + w, y + corner_len),
                         (b, g, r), corner_thickness, cv2.LINE_AA)
                # Bottom-left
                cv2.line(overlay, (x, y + h), (x + corner_len, y + h),
                         (b, g, r), corner_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x, y + h), (x, y + h - corner_len),
                         (b, g, r), corner_thickness, cv2.LINE_AA)
                # Bottom-right
                cv2.line(overlay, (x + w, y + h), (x + w - corner_len, y + h),
                         (b, g, r), corner_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x + w, y + h), (x + w, y + h - corner_len),
                         (b, g, r), corner_thickness, cv2.LINE_AA)

            # ── Label ──
            if self._show_label:
                info = self._players.get(track_id)
                label_text = info.label if info else f"#{track_id}"

                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness = 1
                (text_w, text_h), baseline = cv2.getTextSize(
                    label_text, font, font_scale, thickness
                )

                # Фон метки
                label_x = x
                label_y = max(0, y - text_h - 10)
                pad = 4

                cv2.rectangle(
                    overlay,
                    (label_x, label_y),
                    (label_x + text_w + pad * 2, label_y + text_h + pad * 2),
                    (b, g, r), -1, cv2.LINE_AA
                )

                # Текст
                cv2.putText(
                    overlay, label_text,
                    (label_x + pad, label_y + text_h + pad),
                    font, font_scale, (255, 255, 255),
                    thickness, cv2.LINE_AA
                )

            # ── Confidence indicator ──
            if obj.confidence < 0.7:
                # Показать что трекер теряет объект
                warning_text = f"{int(obj.confidence * 100)}%"
                cv2.putText(
                    overlay, warning_text,
                    (x + w + 5, y + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (0, 165, 255), 1, cv2.LINE_AA
                )

        return overlay

    def _next_color(self) -> Tuple[int, int, int]:
        color = self._color_palette[self._color_index % len(self._color_palette)]
        self._color_index += 1
        return color