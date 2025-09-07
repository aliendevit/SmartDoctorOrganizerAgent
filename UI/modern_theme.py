# UI/modern_theme.py
# Glassy (frosted) theme for a clinical app UI + optional tab font scaling.
# Works with PyQt5 (and falls back to PySide2 if needed).

from typing import Optional

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QPalette, QFont
    from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QGraphicsBlurEffect, QTabWidget
    QT_LIB = "PyQt5"
except ImportError:  # Fallback if the project uses PySide2
    from PySide2.QtCore import Qt
    from PySide2.QtGui import QColor, QPalette, QFont
    from PySide2.QtWidgets import QApplication, QWidget, QFrame, QGraphicsBlurEffect, QTabWidget
    QT_LIB = "PySide2"

import sys
import platform
from typing import Optional
# -----------------------------
# Doctor-friendly palette
# -----------------------------
COLORS = {
    "primary": "#3A8DFF",      # calm medical blue
    "secondary": "#2CBBA6",    # teal / healing
    "accent": "#7A77FF",       # soft purple
    "danger": "#FF6B6B",       # coral red (friendly)
    "bg": "#F5F7FB",           # very light blue-gray
    "text": "#2E2E2E",         # strong readable text
    "subtext": "#6C757D",      # muted labels
    "stroke": "#E7ECF3",       # dividers / outlines
    "white": "#FFFFFF",
    "black": "#000000",
}


def _qcolor(hex_str: str, a: Optional[int] = None) -> QColor:
    """Create QColor from hex, with optional alpha (0-255)."""
    c = QColor(hex_str)
    if a is not None:
        c.setAlpha(a)
    return c


# -----------------------------
# App palette (affects native widgets)
# -----------------------------
def apply_palette(app: QApplication) -> None:
    pal = app.palette()  # start from current

    pal.setColor(QPalette.Window, _qcolor(COLORS["bg"]))                # main window background
    pal.setColor(QPalette.Base, _qcolor(COLORS["white"]))               # text fields, tables base
    pal.setColor(QPalette.AlternateBase, _qcolor(COLORS["bg"]))         # alternating rows
    pal.setColor(QPalette.Text, _qcolor(COLORS["text"]))                # primary text
    pal.setColor(QPalette.WindowText, _qcolor(COLORS["text"]))          # titles
    pal.setColor(QPalette.Button, _qcolor(COLORS["white"]))             # button base (under QSS)
    pal.setColor(QPalette.ButtonText, _qcolor(COLORS["text"]))          # button text
    pal.setColor(QPalette.ToolTipBase, _qcolor(COLORS["white"]))
    pal.setColor(QPalette.ToolTipText, _qcolor(COLORS["text"]))
    pal.setColor(QPalette.Highlight, _qcolor(COLORS["primary"]))        # selection highlight
    pal.setColor(QPalette.HighlightedText, _qcolor(COLORS["white"]))    # selected text

    app.setPalette(pal)


# -----------------------------
# Glassy QSS (stylesheets)
# Notes:
# - Qt doesn't support CSS 'backdrop-filter'. We emulate "frosted" via
#   semi-transparent backgrounds + optional Blur effect on containers.
# - Keep sizes modest for clinical readability.
# -----------------------------
GLASSY_QSS = f"""
/* ------- Global ------- */
QMainWindow, QWidget {{
    background: rgba(255, 255, 255, 0);   /* allow parent/grandparent to show */
    color: {COLORS["text"]};
}}


QFrame#GlassPanel, QWidget#GlassPanel {{
    background: rgba(255, 255, 255, 0.60);    /* glass sheet */
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 16px;
}}

QGroupBox {{
    background: rgba(255, 255, 255, 0.55);
    border: 1px solid {COLORS["stroke"]};
    border-radius: 12px;
    margin-top: 14px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 6px;
    color: {COLORS["subtext"]};
    font-weight: 600;
}}

/* ------- Tabs ------- */
QTabWidget::pane {{
    border: 0px;
    padding: 6px;
    margin-top: 4px;
}}
QTabBar::tab {{
    background: rgba(255, 255, 255, 0.40);
    border: 1px solid rgba(255,255,255,0.35);
    border-radius: 10px;
    padding: 8px 16px;
    margin: 4px;
    color: {COLORS["text"]};
    font-size: 14px;
}}
QTabBar::tab:selected {{
    background: rgba(58, 141, 255, 0.60);     /* primary blue tint */
    color: white;
    font-size: 12px;                           /* smaller when active */
    font-weight: 700;
    border: 1px solid rgba(255,255,255,0.55);
}}
QTabBar::tab:hover:!selected {{
    background: rgba(255, 255, 255, 0.55);
}}

/* ------- Buttons ------- */
QPushButton {{
    background: rgba(44, 187, 166, 0.55);      /* teal glass */
    color: white;
    border-radius: 12px;
    padding: 6px 14px;
    border: 1px solid rgba(255,255,255,0.45);
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: rgba(44, 187, 166, 0.70);
}}
QPushButton:pressed {{
    background: rgba(44, 187, 166, 0.88);
}}

/* ------- Inputs ------- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, QComboBox {{
    background: rgba(255,255,255,0.65);
    border: 1px solid rgba(255,255,255,0.40);
    border-radius: 10px;
    padding: 6px 10px;
    selection-background-color: {COLORS["primary"]};
    selection-color: white;
}}
QComboBox::drop-down {{
    border: 0px;
    padding-right: 6px;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QComboBox:focus {{
    border: 1px solid {COLORS["primary"]};
}}

/* ------- Tables ------- */
QHeaderView::section {{
    background: rgba(255,255,255,0.55);
    border: 0px;
    border-bottom: 1px solid {COLORS["stroke"]};
    padding: 8px 10px;
    font-weight: 600;
    color: {COLORS["subtext"]};
}}
QTableView {{
    background: rgba(255,255,255,0.50);
    border: 1px solid rgba(255,255,255,0.40);
    border-radius: 12px;
    gridline-color: {COLORS["stroke"]};
    selection-background-color: {COLORS["primary"]};
    selection-color: white;
}}
QTableView::item:selected {{
    background: {COLORS["primary"]};
    color: white;
}}

/* ------- Status / Info ------- */
QToolTip {{
    background-color: rgba(255,255,255,0.95);
    color: {COLORS["text"]};
    border: 1px solid {COLORS["stroke"]};
    border-radius: 8px;
    padding: 6px 8px;
}}

/* ------- Scrollbars (minimal) ------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: rgba(122, 119, 255, 0.6);      /* accent */
    min-height: 28px;
    border-radius: 6px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 4px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(122, 119, 255, 0.6);
    min-width: 28px;
    border-radius: 6px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    background: transparent;
    border: none;
    width: 0px;
    height: 0px;
}}
"""


# -----------------------------
# Optional: "Glass panel" helper
# - Give any container this effect by:
#   panel = GlassFrame(); panel.setObjectName("GlassPanel")
#   (and place child widgets inside)
# -----------------------------
class GlassFrame(QFrame):
    def __init__(self, blur_radius: int = 18, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Blur behind the panel contents (visual depth). Keep modest for performance.
        blur = QGraphicsBlurEffect(self)
        blur.setBlurRadius(blur_radius)
        self.setGraphicsEffect(blur)


# -----------------------------
# Optional: active tab font scaling
# - Keeps active tab slightly smaller (requested behavior)
# -----------------------------
def install_tab_font_scaling(tabs: QTabWidget, normal_pt: int = 14, active_pt: int = 12) -> None:
    bar = tabs.tabBar()

    def refresh(idx: int):
        # Qt5/Qt6 lacks per-tab font setter; we rely on QSS (already set) + repaint.
        # Force a repaint to apply size delta smoothly.
        for i in range(bar.count()):
            # Nudge text to trigger layout refresh on some platforms
            bar.setTabText(i, bar.tabText(i))
        bar.update()

    tabs.currentChanged.connect(refresh)
    refresh(tabs.currentIndex())


# -----------------------------
# Entry point to apply theme
# -----------------------------
def apply_glassy_theme(app: QApplication, *, use_palette: bool = True) -> None:
    """
    Apply the glassy clinical theme to the entire app.
    Call early in main.py, before creating main windows.
        from UI import modern_theme
        modern_theme.apply_glassy_theme(app)
    """
    if use_palette:
        apply_palette(app)
    app.setStyleSheet(GLASSY_QSS)


# -----------------------------
# Convenience: apply to a top-level window
# (background gradient + containment panel)
# -----------------------------
def decorate_window_as_glassy(window: QWidget, *, with_panel: bool = False, blur_radius: int = 18) -> None:
    """
    Optional helper to give a subtle clinical gradient and, optionally, a frosted panel.
    """
    # Gentle clinical gradient on root
    window.setStyleSheet(window.styleSheet() + f"""
        {window.metaObject().className()} {{
            background: qlineargradient(
                x1:0 y1:0, x2:0 y2:1,
                stop:0 rgba(245, 247, 251, 1.0),
                stop:1 rgba(232, 239, 249, 1.0)
            );
        }}
    """)
    if with_panel:
        # If you want a single central frosted container, instantiate GlassFrame()
        # in your window code and set layout accordingly.
        panel = GlassFrame(blur_radius=blur_radius, parent=window)
        panel.setObjectName("GlassPanel")
        panel.show()
        # Positioning/layout of this panel is left to the caller (setGeometry or layouts).
