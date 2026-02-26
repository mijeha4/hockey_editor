"""
Stats Widget - панель статистики по событиям.
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QGridLayout, QSizePolicy
)
from PySide6.QtGui import QColor, QPainter, QFont, QPen, QBrush, QPaintEvent
from PySide6.QtCore import Qt, QRect, QSize

from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager


class StatBar(QWidget):
    """Одна горизонтальная полоска статистики для типа события."""

    def __init__(
        self,
        event_name: str,
        display_name: str,
        count: int,
        total_sec: float,
        avg_sec: float,
        ratio: float,
        color: QColor,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.event_name = event_name
        self.display_name = display_name
        self.count = count
        self.total_sec = total_sec
        self.avg_sec = avg_sec
        self.ratio = ratio
        self.bar_color = color

        self.setFixedHeight(28)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setToolTip(
            f"{display_name}\n"
            f"Количество: {count}\n"
            f"Общее время: {self._format_duration(total_sec)}\n"
            f"Среднее: {self._format_duration(avg_sec)}"
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        label_width = 140
        count_width = 45
        time_width = 60
        bar_start = label_width
        bar_end = w - count_width - time_width - 8

        bar_width = max(0, bar_end - bar_start)
        filled_width = int(bar_width * self.ratio)

        bg_rect = QRect(bar_start, 4, bar_width, h - 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e1e1e"))
        painter.drawRoundedRect(bg_rect, 3, 3)

        if filled_width > 0:
            fill_rect = QRect(bar_start, 4, filled_width, h - 8)
            fill_color = QColor(self.bar_color)
            fill_color.setAlpha(180)
            painter.setBrush(fill_color)
            painter.drawRoundedRect(fill_rect, 3, 3)

        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 9)
        painter.setFont(font)

        name_rect = QRect(4, 0, label_width - 8, h)
        elided = painter.fontMetrics().elidedText(
            self.display_name, Qt.ElideRight, label_width - 12
        )
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, elided)

        count_rect = QRect(bar_end + 4, 0, count_width, h)
        painter.setPen(QColor("#ffcc00"))
        font_bold = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font_bold)
        painter.drawText(count_rect, Qt.AlignCenter, str(self.count))

        time_rect = QRect(bar_end + count_width + 8, 0, time_width, h)
        painter.setPen(QColor("#aaaaaa"))
        font_small = QFont("Consolas", 8)
        painter.setFont(font_small)
        painter.drawText(
            time_rect, Qt.AlignRight | Qt.AlignVCenter,
            self._format_duration(self.total_sec)
        )

        painter.end()

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        if seconds >= 3600:
            h = int(seconds) // 3600
            m = (int(seconds) % 3600) // 60
            s = int(seconds) % 60
            return f"{h}:{m:02d}:{s:02d}"
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"


class StatsWidget(QWidget):
    """Панель статистики по типам событий."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._markers: List[Marker] = []
        self._fps: float = 30.0
        self._event_manager = get_custom_event_manager()

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Легенда (компактная, без заголовка — он уже на вкладке) ──
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 2)

        self._header_label = QLabel("")
        self._header_label.setStyleSheet(
            "color: #ffffff; font-weight: bold; font-size: 11px;"
        )
        header_layout.addWidget(self._header_label)

        header_layout.addStretch()

        legend = QLabel("кол-во | время")
        legend.setStyleSheet("color: #666666; font-size: 9px;")
        header_layout.addWidget(legend)

        layout.addLayout(header_layout)

        # ── Scroll area (без ограничения высоты) ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("""
            QScrollArea { background-color: #2a2a2a; border: none; }
            QScrollBar:vertical {
                background: #2a2a2a; width: 8px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #555555; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self._bars_container = QWidget()
        self._bars_layout = QVBoxLayout(self._bars_container)
        self._bars_layout.setContentsMargins(2, 2, 2, 2)
        self._bars_layout.setSpacing(2)

        self._scroll.setWidget(self._bars_container)
        layout.addWidget(self._scroll, 1)

        # ── Итого ──
        self._total_label = QLabel("")
        self._total_label.setFixedHeight(22)
        self._total_label.setStyleSheet(
            "color: #aaaaaa; font-size: 10px; padding: 2px 6px;"
            "background-color: #1e1e1e; border-top: 1px solid #444444;"
        )
        layout.addWidget(self._total_label)

        self._show_empty_state()

    def set_markers(self, markers: List[Marker]) -> None:
        self._markers = list(markers)
        self._rebuild()

    def set_fps(self, fps: float) -> None:
        self._fps = fps if fps > 0 else 30.0
        self._rebuild()

    def clear(self) -> None:
        self._markers = []
        self._rebuild()

    def _rebuild(self) -> None:
        while self._bars_layout.count():
            child = self._bars_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self._markers:
            self._show_empty_state()
            return

        stats = self._compute_stats()

        if not stats:
            self._show_empty_state()
            return

        max_count = max(s[1] for s in stats) if stats else 1

        for event_name, count, total_sec, avg_sec in stats:
            event = self._event_manager.get_event(event_name)
            display_name = event.get_localized_name() if event else event_name
            color = QColor(event.color) if event else QColor("#888888")
            ratio = count / max_count if max_count > 0 else 0

            bar = StatBar(
                event_name=event_name,
                display_name=display_name,
                count=count,
                total_sec=total_sec,
                avg_sec=avg_sec,
                ratio=ratio,
                color=color,
            )
            self._bars_layout.addWidget(bar)

        self._bars_layout.addStretch()

        total_count = len(self._markers)
        total_time = sum(
            (m.end_frame - m.start_frame) / self._fps for m in self._markers
        )
        avg_time = total_time / total_count if total_count > 0 else 0

        types_count = len(stats)

        self._total_label.setText(
            f"Итого: {total_count} событий | "
            f"{types_count} типов | "
            f"Время: {self._format_duration(total_time)} | "
            f"Среднее: {self._format_duration(avg_time)}"
        )
        self._total_label.setVisible(True)

        self._header_label.setText(f"{total_count} событий, {types_count} типов")

    def _show_empty_state(self) -> None:
        while self._bars_layout.count():
            child = self._bars_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        empty_label = QLabel("Нет событий")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: #666666; padding: 15px; font-size: 11px;")
        self._bars_layout.addWidget(empty_label)
        self._bars_layout.addStretch()

        self._total_label.setText("")
        self._total_label.setVisible(False)

        self._header_label.setText("")

    def _compute_stats(self) -> List[Tuple[str, int, float, float]]:
        fps = self._fps if self._fps > 0 else 30.0

        event_data: Dict[str, List[float]] = {}
        for marker in self._markers:
            dur = (marker.end_frame - marker.start_frame) / fps
            if marker.event_name not in event_data:
                event_data[marker.event_name] = []
            event_data[marker.event_name].append(dur)

        stats = []
        for event_name, durations in event_data.items():
            count = len(durations)
            total = sum(durations)
            avg = total / count if count > 0 else 0
            stats.append((event_name, count, total, avg))

        stats.sort(key=lambda x: x[1], reverse=True)
        return stats

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        if seconds >= 3600:
            h = int(seconds) // 3600
            m = (int(seconds) % 3600) // 60
            s = int(seconds) % 60
            return f"{h}:{m:02d}:{s:02d}"
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"