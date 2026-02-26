#!/usr/bin/env python3
"""
Генератор ассетов: иконка приложения (.png + .ico).
Запускать: python scripts/generate_assets.py
"""

import os
import sys
import struct

# Добавить src в путь для импорта PySide6
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush,
    QLinearGradient, QRadialGradient, QPainterPath, QImage
)
from PySide6.QtCore import Qt, QRect, QRectF, QPointF


def draw_icon(size: int) -> QImage:
    """Нарисовать иконку Hockey Editor заданного размера."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    s = size  # alias
    margin = int(s * 0.06)
    inner = s - margin * 2

    # ── Фон: скруглённый квадрат с градиентом ──
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0.0, QColor("#0d47a1"))   # тёмно-синий
    grad.setColorAt(0.5, QColor("#1565c0"))   # синий
    grad.setColorAt(1.0, QColor("#0d47a1"))   # тёмно-синий

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad))
    radius = int(s * 0.18)
    p.drawRoundedRect(margin, margin, inner, inner, radius, radius)

    # ── Шайба (эллипс внизу) ──
    puck_w = int(s * 0.50)
    puck_h = int(s * 0.15)
    puck_x = (s - puck_w) // 2
    puck_y = int(s * 0.62)

    puck_grad = QRadialGradient(s / 2, puck_y + puck_h / 2, puck_w * 0.6)
    puck_grad.setColorAt(0.0, QColor("#333333"))
    puck_grad.setColorAt(1.0, QColor("#111111"))

    p.setBrush(QBrush(puck_grad))
    p.setPen(QPen(QColor("#555555"), max(1, int(s * 0.01))))
    p.drawEllipse(puck_x, puck_y, puck_w, puck_h)

    # ── Клюшка (L-образная форма) ──
    stick_pen = QPen(QColor("#ffffff"), max(2, int(s * 0.045)))
    stick_pen.setCapStyle(Qt.RoundCap)
    stick_pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(stick_pen)
    p.setBrush(Qt.NoBrush)

    path = QPainterPath()
    # Ручка клюшки (наклонная линия сверху вниз)
    handle_top = QPointF(s * 0.65, s * 0.15)
    handle_bottom = QPointF(s * 0.38, s * 0.60)
    path.moveTo(handle_top)
    path.lineTo(handle_bottom)
    # Крюк (горизонтальная часть)
    blade_end = QPointF(s * 0.22, s * 0.63)
    path.quadTo(QPointF(s * 0.30, s * 0.65), blade_end)
    p.drawPath(path)

    # ── Кнопка Play (треугольник) ──
    play_cx = int(s * 0.62)
    play_cy = int(s * 0.42)
    play_size = int(s * 0.18)

    play_path = QPainterPath()
    play_path.moveTo(play_cx - play_size * 0.4, play_cy - play_size * 0.5)
    play_path.lineTo(play_cx + play_size * 0.5, play_cy)
    play_path.lineTo(play_cx - play_size * 0.4, play_cy + play_size * 0.5)
    play_path.closeSubpath()

    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#4fc3f7"))
    p.drawPath(play_path)

    # ── Блик (лёгкое свечение сверху) ──
    highlight = QLinearGradient(0, margin, 0, margin + inner * 0.4)
    highlight.setColorAt(0.0, QColor(255, 255, 255, 40))
    highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(QBrush(highlight))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(margin, margin, inner, int(inner * 0.4), radius, radius)

    p.end()
    return img


def image_to_png_bytes(img: QImage) -> bytes:
    """Конвертировать QImage в PNG bytes."""
    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def create_ico(png_images: list, output_path: str) -> None:
    """Создать .ico файл из списка (size, png_bytes).

    ICO формат: заголовок + директория + PNG данные.
    """
    count = len(png_images)

    # Header: reserved(2) + type(2) + count(2) = 6 bytes
    header = struct.pack('<HHH', 0, 1, count)

    # Вычислить смещения данных
    dir_size = 16 * count
    data_offset = 6 + dir_size

    directory = b''
    all_data = b''
    current_offset = data_offset

    for size, png_data in png_images:
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        data_len = len(png_data)

        # Directory entry: w(1) h(1) colors(1) reserved(1) planes(2) bpp(2) size(4) offset(4)
        entry = struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, data_len, current_offset)
        directory += entry
        all_data += png_data
        current_offset += data_len

    with open(output_path, 'wb') as f:
        f.write(header + directory + all_data)


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    # Директории
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_dir = os.path.join(project_root, 'assets', 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    # Генерация PNG для разных размеров
    sizes = [16, 24, 32, 48, 64, 128, 256]
    png_list = []

    for size in sizes:
        img = draw_icon(size)
        png_data = image_to_png_bytes(img)
        png_list.append((size, png_data))

        png_path = os.path.join(icons_dir, f'app_icon_{size}.png')
        img.save(png_path)
        print(f"  ✓ {png_path}")

    # Основной PNG (256px)
    main_img = draw_icon(256)
    main_png_path = os.path.join(icons_dir, 'app_icon.png')
    main_img.save(main_png_path)
    print(f"  ✓ {main_png_path}")

    # ICO файл
    ico_path = os.path.join(icons_dir, 'app_icon.ico')
    create_ico(png_list, ico_path)
    print(f"  ✓ {ico_path}")

    print(f"\nГотово! Файлы в {icons_dir}")


if __name__ == '__main__':
    main()