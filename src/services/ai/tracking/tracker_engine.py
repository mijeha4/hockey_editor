"""
Tracker Engine — движки трекинга объектов.

Поддерживает несколько алгоритмов OpenCV:
- CSRT: Точный, но медленнее (по умолчанию)
- KCF: Быстрый, менее точный
- MOSSE: Самый быстрый, минимальная точность
- MedianFlow: Хорош для предсказуемого движения

Все работают без GPU и без нейросетей.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np


class TrackerType(Enum):
    """Доступные алгоритмы трекинга."""
    CSRT = auto()         # Channel and Spatial Reliability Tracker
    KCF = auto()          # Kernelized Correlation Filters
    MOSSE = auto()        # Minimum Output Sum of Squared Error
    MEDIAN_FLOW = auto()  # MedianFlow tracker


@dataclass
class TrackedObject:
    """Отслеживаемый объект."""
    track_id: int
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float = 1.0
    label: str = "Игрок"
    color: Tuple[int, int, int] = (124, 58, 237)  # RGB
    is_active: bool = True
    frames_tracked: int = 0
    frames_lost: int = 0
    velocity: Tuple[float, float] = (0.0, 0.0)  # пикс/кадр
    trajectory: List[Tuple[int, int]] = field(default_factory=list)
    max_trajectory_length: int = 120  # ~4 секунды при 30fps

    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)

    def update_trajectory(self):
        cx, cy = self.center
        self.trajectory.append((cx, cy))
        if len(self.trajectory) > self.max_trajectory_length:
            self.trajectory = self.trajectory[-self.max_trajectory_length:]

    def update_velocity(self):
        if len(self.trajectory) >= 2:
            p1 = self.trajectory[-2]
            p2 = self.trajectory[-1]
            self.velocity = (float(p2[0] - p1[0]), float(p2[1] - p1[1]))


class SingleTracker:
    """Обёртка над одним OpenCV трекером."""

    def __init__(self, tracker_type: TrackerType = TrackerType.CSRT):
        self._type = tracker_type
        self._tracker: Optional[cv2.Tracker] = None
        self._initialized = False

    def _create_tracker(self) -> cv2.Tracker:
        """Создать экземпляр трекера OpenCV."""
        if self._type == TrackerType.CSRT:
            return cv2.TrackerCSRT_create()
        elif self._type == TrackerType.KCF:
            return cv2.TrackerKCF_create()
        elif self._type == TrackerType.MOSSE:
            return cv2.legacy.TrackerMOSSE_create()
        elif self._type == TrackerType.MEDIAN_FLOW:
            return cv2.legacy.TrackerMedianFlow_create()
        else:
            return cv2.TrackerCSRT_create()

    def init(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
        """Инициализировать трекер на кадре с bounding box.

        Args:
            frame: BGR кадр
            bbox: (x, y, width, height)

        Returns:
            True если инициализация успешна
        """
        self._tracker = self._create_tracker()
        x, y, w, h = bbox

        # Убедиться что bbox валиден
        frame_h, frame_w = frame.shape[:2]
        x = max(0, min(x, frame_w - 1))
        y = max(0, min(y, frame_h - 1))
        w = max(10, min(w, frame_w - x))
        h = max(10, min(h, frame_h - y))

        try:
            success = self._tracker.init(frame, (x, y, w, h))
            self._initialized = success
            return success
        except Exception:
            self._initialized = False
            return False

    def update(self, frame: np.ndarray) -> Tuple[bool, Tuple[int, int, int, int]]:
        """Обновить позицию на следующем кадре.

        Returns:
            (success, (x, y, w, h))
        """
        if not self._initialized or self._tracker is None:
            return False, (0, 0, 0, 0)

        try:
            success, box = self._tracker.update(frame)
            if success:
                x, y, w, h = [int(v) for v in box]
                return True, (x, y, w, h)
            return False, (0, 0, 0, 0)
        except Exception:
            return False, (0, 0, 0, 0)

    def is_initialized(self) -> bool:
        return self._initialized

    def reset(self):
        self._tracker = None
        self._initialized = False


class MultiTracker:
    """Управление несколькими трекерами одновременно."""

    def __init__(self, tracker_type: TrackerType = TrackerType.CSRT):
        self._tracker_type = tracker_type
        self._trackers: Dict[int, SingleTracker] = {}
        self._objects: Dict[int, TrackedObject] = {}
        self._next_id = 1
        self._max_lost_frames = 30  # После скольких потерянных кадров удалить

    @property
    def tracked_objects(self) -> Dict[int, TrackedObject]:
        return self._objects

    @property
    def active_count(self) -> int:
        return sum(1 for obj in self._objects.values() if obj.is_active)

    def add_object(self, frame: np.ndarray,
                   bbox: Tuple[int, int, int, int],
                   label: str = "Игрок",
                   color: Tuple[int, int, int] = (124, 58, 237)) -> Optional[int]:
        """Добавить новый объект для трекинга.

        Returns:
            track_id или None при ошибке
        """
        tracker = SingleTracker(self._tracker_type)
        success = tracker.init(frame, bbox)

        if not success:
            return None

        track_id = self._next_id
        self._next_id += 1

        self._trackers[track_id] = tracker
        self._objects[track_id] = TrackedObject(
            track_id=track_id,
            bbox=bbox,
            label=label,
            color=color,
            is_active=True,
            frames_tracked=1,
        )
        self._objects[track_id].update_trajectory()

        return track_id

    def update(self, frame: np.ndarray) -> Dict[int, TrackedObject]:
        """Обновить все трекеры на новом кадре.

        Returns:
            Словарь активных объектов
        """
        to_remove = []

        for track_id, tracker in self._trackers.items():
            obj = self._objects[track_id]

            if not obj.is_active:
                continue

            success, bbox = tracker.update(frame)

            if success:
                obj.bbox = bbox
                obj.frames_tracked += 1
                obj.frames_lost = 0
                obj.confidence = min(1.0, obj.confidence + 0.05)
                obj.update_trajectory()
                obj.update_velocity()
            else:
                obj.frames_lost += 1
                obj.confidence = max(0.0, obj.confidence - 0.15)

                if obj.frames_lost > self._max_lost_frames:
                    obj.is_active = False
                    to_remove.append(track_id)

        # Удалить давно потерянные
        for tid in to_remove:
            pass  # Оставляем в списке но неактивными

        return {tid: obj for tid, obj in self._objects.items() if obj.is_active}

    def remove_object(self, track_id: int):
        """Удалить объект из трекинга."""
        if track_id in self._trackers:
            self._trackers[track_id].reset()
            del self._trackers[track_id]
        if track_id in self._objects:
            self._objects[track_id].is_active = False

    def reinit_object(self, track_id: int, frame: np.ndarray,
                      bbox: Tuple[int, int, int, int]) -> bool:
        """Переинициализировать трекер (после потери или ручной коррекции)."""
        if track_id not in self._objects:
            return False

        tracker = SingleTracker(self._tracker_type)
        success = tracker.init(frame, bbox)

        if success:
            self._trackers[track_id] = tracker
            obj = self._objects[track_id]
            obj.bbox = bbox
            obj.is_active = True
            obj.frames_lost = 0
            obj.confidence = 1.0
            obj.trajectory.clear()
            obj.update_trajectory()
            return True

        return False

    def clear_all(self):
        """Удалить все трекеры."""
        for tracker in self._trackers.values():
            tracker.reset()
        self._trackers.clear()
        self._objects.clear()
        self._next_id = 1

    def set_tracker_type(self, tracker_type: TrackerType):
        """Изменить тип трекера (для новых объектов)."""
        self._tracker_type = tracker_type