"""
Styles module for Hockey Editor application.
Provides color constants and application-wide stylesheet.
"""

from typing import Dict


class AppColors:
    """Color constants for the Hockey Editor application."""

    # Base colors
    BACKGROUND = "#2a2a2a"
    ELEMENT_BG = "#333333"
    TEXT = "#ffffff"
    ACCENT = "#1a4d7a"
    BORDER = "#444444"

    # Event colors
    ATTACK = "#FF0000"
    DEFENSE = "#0000FF"
    CHANGE = "#00FF00"

    # Base colors (old — keep for compatibility)
    BACKGROUND = "#2a2a2a"
    ELEMENT_BG = "#333333"
    TEXT = "#ffffff"
    ACCENT = "#1a4d7a"
    BORDER = "#444444"

    # Event colors
    ATTACK = "#FF0000"
    DEFENSE = "#0000FF"
    CHANGE = "#00FF00"

    # ── NEW: Extended palette for modern widgets ──
    BG_PRIMARY = "#2a2a2a"
    BG_SECONDARY = "#1e1e1e"
    BG_SURFACE = "#333333"
    BG_SURFACE_VARIANT = "#3a3a3a"
    BG_ELEVATED = "#404040"
    BG_HOVER = "#4a4a4a"

    ACCENT_LIGHT = "#4488cc"
    ACCENT_DARK = "#0d3a5c"
    ACCENT_SECONDARY = "#06b6d4"
    ACCENT_GLOW = "rgba(26, 77, 122, 0.25)"

    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"
    INFO = "#06b6d4"

    TEXT_SECONDARY = "#aaaaaa"
    TEXT_MUTED = "#888888"
    TEXT_ON_ACCENT = "#ffffff"

    BORDER_HOVER = "#666666"
    BORDER_FOCUS = "#1a4d7a"


def get_application_stylesheet() -> str:
    """Return the global application stylesheet.

    Returns:
        QString containing the complete QSS stylesheet
    """
    return f"""
    /* ===========================================
       Hockey Editor - Application Styles
       =========================================== */

    /* Main application widgets */
    QMainWindow {{
        background-color: {AppColors.BACKGROUND};
        color: {AppColors.TEXT};
    }}

    QWidget {{
        background-color: {AppColors.BACKGROUND};
        color: {AppColors.TEXT};
    }}

    /* Splitter handles - make them visible */
    QSplitter::handle {{
        background-color: {AppColors.BORDER};
        border: 1px solid {AppColors.BORDER};
        width: 2px;
        height: 2px;
    }}

    QSplitter::handle:hover {{
        background-color: {AppColors.ELEMENT_BG};
    }}

    /* Table widgets */
    QTableWidget {{
        background-color: {AppColors.ELEMENT_BG};
        color: {AppColors.TEXT};
        border: 1px solid {AppColors.BORDER};
        gridline-color: {AppColors.BORDER};
        selection-background-color: {AppColors.ACCENT};
        selection-color: {AppColors.TEXT};
    }}

    QTableWidget::item {{
        padding: 4px;
        border-bottom: 1px solid {AppColors.BORDER};
        border-right: 1px solid {AppColors.BORDER};
    }}

    QTableWidget::item:selected {{
        background-color: {AppColors.ACCENT};
        color: {AppColors.TEXT};
    }}

    /* Table headers */
    QHeaderView::section {{
        background-color: {AppColors.ELEMENT_BG};
        color: {AppColors.TEXT};
        padding: 6px;
        border: 1px solid {AppColors.BORDER};
        font-weight: bold;
    }}

    QHeaderView::section:hover {{
        background-color: {AppColors.ACCENT};
    }}

    /* Push buttons - flat design with rounded corners */
    QPushButton {{
        background-color: {AppColors.ELEMENT_BG};
        color: {AppColors.TEXT};
        border: 1px solid {AppColors.BORDER};
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 11pt;
        outline: none;
    }}

    QPushButton:hover {{
        background-color: {AppColors.ACCENT};
        border-color: {AppColors.ACCENT};
    }}

    QPushButton:pressed {{
        background-color: {AppColors.BACKGROUND};
        border-color: {AppColors.BORDER};
    }}

    QPushButton:disabled {{
        background-color: {AppColors.BACKGROUND};
        color: #888888;
        border-color: {AppColors.BORDER};
    }}

    QPushButton:focus {{
        border-color: {AppColors.ACCENT};
    }}
    """
