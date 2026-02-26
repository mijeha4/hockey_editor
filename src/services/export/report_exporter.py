"""
Report Exporter — экспорт данных о сегментах в CSV и PDF.

CSV: Простая таблица с колонками ID, Тип, Начало, Конец, Длительность, Заметка.
PDF: Отчёт с заголовком, таблицей сегментов, статистикой по типам.

Зависимости:
- CSV: только стандартная библиотека Python (csv, io)
- PDF: опционально reportlab. Если не установлен — fallback на HTML файл.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from models.domain.marker import Marker


class ReportExporter:
    """Сервис экспорта отчётов о сегментах."""

    # ──────────────────────────────────────────────────────────────────────
    # CSV Export
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def export_csv(
        markers: List[Marker],
        fps: float,
        output_path: str,
        project_name: str = "",
        video_path: str = "",
        encoding: str = "utf-8-sig",
        name_mapping: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Экспортировать сегменты в CSV файл."""
        try:
            fps = fps if fps > 0 else 30.0
            if name_mapping is None:
                name_mapping = {}
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            with open(output_path, "w", newline="", encoding=encoding) as f:
                writer = csv.writer(f, delimiter=";")

                # Заголовок с метаданными
                writer.writerow(["# Проект", project_name or "Без названия"])
                writer.writerow(["# Видео", video_path or "Н/Д"])
                writer.writerow(["# FPS", f"{fps:.2f}"])
                writer.writerow(["# Дата экспорта", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(["# Всего сегментов", str(len(markers))])
                writer.writerow([])

                # Заголовки колонок
                writer.writerow([
                    "№", "Тип события", "Начало (ММ:СС)",
                    "Конец (ММ:СС)", "Длительность (сек)",
                    "Начало (кадр)", "Конец (кадр)",
                    "Длительность (кадры)", "Заметка"
                ])

                # Данные
                sorted_markers = sorted(markers, key=lambda m: m.start_frame)
                for i, marker in enumerate(sorted_markers, 1):
                    start_sec = marker.start_frame / fps
                    end_sec = marker.end_frame / fps
                    duration_sec = (marker.end_frame - marker.start_frame) / fps
                    duration_frames = marker.end_frame - marker.start_frame

                    display_name = name_mapping.get(marker.event_name, marker.event_name)

                    writer.writerow([
                        i,
                        display_name,
                        ReportExporter._format_time(start_sec),
                        ReportExporter._format_time(end_sec),
                        f"{duration_sec:.2f}",
                        marker.start_frame,
                        marker.end_frame,
                        duration_frames,
                        marker.note or "",
                    ])

                # Статистика
                writer.writerow([])
                writer.writerow(["# === СТАТИСТИКА ==="])

                stats = ReportExporter._compute_stats(markers, fps)
                writer.writerow(["# Тип события", "Количество", "Общее время (сек)", "Среднее время (сек)"])
                for event_name, count, total_dur, avg_dur in stats:
                    display_name = name_mapping.get(event_name, event_name)
                    writer.writerow([
                        f"# {display_name}",
                        count,
                        f"{total_dur:.2f}",
                        f"{avg_dur:.2f}",
                    ])

            return True

        except Exception as e:
            print(f"Ошибка экспорта CSV: {e}")
            return False

    # ──────────────────────────────────────────────────────────────────────
    # PDF Export
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def export_pdf(
        markers: List[Marker],
        fps: float,
        output_path: str,
        project_name: str = "",
        video_path: str = "",
        name_mapping: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Экспортировать отчёт в PDF или HTML."""
        if name_mapping is None:
            name_mapping = {}
        try:
            return ReportExporter._export_pdf_reportlab(
                markers, fps, output_path, project_name, video_path, name_mapping
            )
        except ImportError:
            html_path = output_path
            if html_path.lower().endswith(".pdf"):
                html_path = html_path[:-4] + ".html"
            elif not html_path.lower().endswith(".html"):
                html_path += ".html"
            return ReportExporter._export_html_report(
                markers, fps, html_path, project_name, video_path, name_mapping
            )
        except Exception as e:
            print(f"Ошибка экспорта PDF: {e}")
            html_path = output_path
            if html_path.lower().endswith(".pdf"):
                html_path = html_path[:-4] + ".html"
            elif not html_path.lower().endswith(".html"):
                html_path += ".html"
            return ReportExporter._export_html_report(
                markers, fps, html_path, project_name, video_path, name_mapping
            )

    @staticmethod
    def _find_unicode_font() -> Optional[str]:
        """Найти шрифт с поддержкой Unicode/кириллицы в системе."""
        font_candidates = [
            # Windows
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/verdana.ttf",
            "C:/Windows/Fonts/times.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]

        for path in font_candidates:
            if os.path.exists(path):
                return path

        return None

    @staticmethod
    def _find_unicode_font_bold() -> Optional[str]:
        """Найти жирный вариант Unicode шрифта."""
        bold_candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/tahomabd.ttf",
            "C:/Windows/Fonts/verdanab.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]

        for path in bold_candidates:
            if os.path.exists(path):
                return path

        return None

    @staticmethod
    def _export_pdf_reportlab(
        markers: List[Marker],
        fps: float,
        output_path: str,
        project_name: str,
        video_path: str,
        name_mapping: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Экспорт PDF через reportlab с поддержкой Unicode."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        fps = fps if fps > 0 else 30.0
        if name_mapping is None:
            name_mapping = {}
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # === Регистрация Unicode шрифта ===
        font_regular = "Helvetica"
        font_bold = "Helvetica-Bold"
        use_unicode_font = False

        ttf_path = ReportExporter._find_unicode_font()
        ttf_bold_path = ReportExporter._find_unicode_font_bold()

        if ttf_path:
            try:
                pdfmetrics.registerFont(TTFont("UnicodeFont", ttf_path))
                font_regular = "UnicodeFont"
                use_unicode_font = True

                if ttf_bold_path:
                    pdfmetrics.registerFont(TTFont("UnicodeFontBold", ttf_bold_path))
                    font_bold = "UnicodeFontBold"
                else:
                    font_bold = "UnicodeFont"

                print(f"PDF: Используется Unicode шрифт: {ttf_path}")
            except Exception as e:
                print(f"PDF: Не удалось зарегистрировать Unicode шрифт: {e}")
                font_regular = "Helvetica"
                font_bold = "Helvetica-Bold"

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontName=font_bold,
            fontSize=18,
            spaceAfter=10,
        )
        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=5,
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontName=font_bold,
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
        )

        elements = []

        # === Заголовок ===
        elements.append(Paragraph(
            f"Отчёт: {project_name or 'Без названия'}",
            title_style
        ))
        elements.append(Paragraph(
            f"Видео: {os.path.basename(video_path) if video_path else 'Н/Д'}",
            subtitle_style
        ))
        elements.append(Paragraph(
            f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"FPS: {fps:.1f} | Сегментов: {len(markers)}",
            subtitle_style
        ))
        elements.append(Spacer(1, 10))

        # === Таблица сегментов ===
        elements.append(Paragraph("Сегменты", section_style))

        sorted_markers = sorted(markers, key=lambda m: m.start_frame)

        table_data = [["№", "Тип события", "Начало", "Конец", "Длит.", "Заметка"]]
        for i, marker in enumerate(sorted_markers, 1):
            start_sec = marker.start_frame / fps
            end_sec = marker.end_frame / fps
            dur_sec = (marker.end_frame - marker.start_frame) / fps

            note_text = (marker.note or "")[:50]
            if len(marker.note or "") > 50:
                note_text += "..."

            table_data.append([
                str(i),
                name_mapping.get(marker.event_name, marker.event_name),
                ReportExporter._format_time(start_sec),
                ReportExporter._format_time(end_sec),
                f"{dur_sec:.1f}с",
                note_text,
            ])

        col_widths = [25, 110, 50, 50, 42, 193]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table_style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a4d7a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTNAME", (0, 1), (-1, -1), font_regular),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (4, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white, colors.HexColor("#f0f0f0")
            ]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        table.setStyle(TableStyle(table_style_commands))
        elements.append(table)
        elements.append(Spacer(1, 15))

        # === Статистика ===
        elements.append(Paragraph("Статистика по типам событий", section_style))

        stats = ReportExporter._compute_stats(markers, fps)
        stats_data = [["Тип события", "Количество", "Общее время", "Среднее время"]]
        for event_name, count, total_dur, avg_dur in stats:
            stats_data.append([
                name_mapping.get(event_name, event_name),
                str(count),
                f"{total_dur:.1f}с",
                f"{avg_dur:.1f}с",
            ])

        # Итого
        total_count = len(markers)
        total_time = sum(
            (m.end_frame - m.start_frame) / fps for m in markers
        )
        stats_data.append([
            "ИТОГО",
            str(total_count),
            f"{total_time:.1f}с",
            f"{total_time / max(1, total_count):.1f}с",
        ])

        stats_table = Table(stats_data, colWidths=[150, 80, 90, 90], repeatRows=1)

        stats_style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 1), (-1, -1), font_regular),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [
                colors.white, colors.HexColor("#f5f5f5")
            ]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e0e0e0")),
            ("FONTNAME", (0, -1), (-1, -1), font_bold),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        stats_table.setStyle(TableStyle(stats_style_commands))
        elements.append(stats_table)

        # === Footer ===
        elements.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=8,
            textColor=colors.HexColor("#aaaaaa"),
        )
        elements.append(Paragraph(
            "Hockey Editor Pro — автоматически сгенерированный отчёт",
            footer_style
        ))

        doc.build(elements)
        return True

    @staticmethod
    def _export_html_report(
        markers: List[Marker],
        fps: float,
        output_path: str,
        project_name: str,
        video_path: str,
        name_mapping: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Fallback: HTML отчёт если reportlab не установлен."""
        fps = fps if fps > 0 else 30.0
        if name_mapping is None:
            name_mapping = {}
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        sorted_markers = sorted(markers, key=lambda m: m.start_frame)
        stats = ReportExporter._compute_stats(markers, fps)

        rows_html = ""
        for i, marker in enumerate(sorted_markers, 1):
            start_sec = marker.start_frame / fps
            end_sec = marker.end_frame / fps
            dur_sec = (marker.end_frame - marker.start_frame) / fps
            note = (marker.note or "").replace("<", "&lt;").replace(">", "&gt;")
            bg = "#ffffff" if i % 2 == 1 else "#f5f5f5"
            rows_html += f"""
            <tr style="background:{bg}">
                <td style="text-align:center">{i}</td>
                <td>{name_mapping.get(marker.event_name, marker.event_name)}</td>
                <td style="text-align:center">{ReportExporter._format_time(start_sec)}</td>
                <td style="text-align:center">{ReportExporter._format_time(end_sec)}</td>
                <td style="text-align:center">{dur_sec:.1f}с</td>
                <td>{note}</td>
            </tr>"""

        stats_html = ""
        for event_name, count, total_dur, avg_dur in stats:
            stats_html += f"""
            <tr>
                <td>{name_mapping.get(event_name, event_name)}</td>
                <td style="text-align:center">{count}</td>
                <td style="text-align:center">{total_dur:.1f}с</td>
                <td style="text-align:center">{avg_dur:.1f}с</td>
            </tr>"""

        total_count = len(markers)
        total_time = sum((m.end_frame - m.start_frame) / fps for m in markers)

        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Отчёт — {project_name or 'Без названия'}</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; color: #333; }}
    h1 {{ color: #1a4d7a; margin-bottom: 5px; }}
    .meta {{ color: #888; font-size: 13px; margin-bottom: 20px; }}
    h2 {{ color: #333; border-bottom: 2px solid #1a4d7a; padding-bottom: 5px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 25px; }}
    th {{ background: #1a4d7a; color: white; padding: 8px 12px; text-align: left; }}
    td {{ padding: 6px 12px; border-bottom: 1px solid #ddd; }}
    .total {{ background: #e0e0e0; font-weight: bold; }}
    @media print {{ body {{ margin: 10mm; }} }}
</style>
</head><body>
<h1>Отчёт: {project_name or 'Без названия'}</h1>
<div class="meta">
    Видео: {os.path.basename(video_path) if video_path else 'Н/Д'}<br>
    Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')} |
    FPS: {fps:.1f} | Сегментов: {len(markers)}
</div>

<h2>Сегменты</h2>
<table>
<tr><th>№</th><th>Тип события</th><th>Начало</th><th>Конец</th><th>Длит.</th><th>Заметка</th></tr>
{rows_html}
</table>

<h2>Статистика по типам событий</h2>
<table>
<tr><th>Тип события</th><th>Количество</th><th>Общее время</th><th>Среднее время</th></tr>
{stats_html}
<tr class="total">
    <td>ИТОГО</td>
    <td style="text-align:center">{total_count}</td>
    <td style="text-align:center">{total_time:.1f}с</td>
    <td style="text-align:center">{total_time / max(1, total_count):.1f}с</td>
</tr>
</table>

<p style="color:#aaa; font-size:11px; margin-top:30px;">
    Hockey Editor Pro — автоматически сгенерированный отчёт
</p>
</body></html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return True

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_stats(
        markers: List[Marker], fps: float
    ) -> List[Tuple[str, int, float, float]]:
        """Вычислить статистику по типам событий.

        Returns:
            List of (event_name, count, total_duration_sec, avg_duration_sec)
        """
        if fps <= 0:
            fps = 30.0

        event_data: Dict[str, List[float]] = {}
        for marker in markers:
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
    def _format_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_time_full(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"