# UI/design_system.py
from __future__ import annotations
from PyQt5 import QtCore, QtGui, QtWidgets
import sys, platform

# ---------- Design Tokens ----------
COLORS = {
    "text":        "#1f2937",  # slate-800
    "textDim":     "#334155",  # slate-600
    "muted":       "#64748b",  # slate-500
    "primary":     "#3A8DFF",  # doctor calm blue
    "info":        "#2CBBA6",  # teal
    "success":     "#7A77FF",  # soft purple
    "stroke":      "#E5EFFA",  # pale blue stroke
    "panel":       "rgba(255,255,255,0.55)",
    "panelInner":  "rgba(255,255,255,0.65)",
    "inputBg":     "rgba(255,255,255,0.88)",
    "stripe":      "rgba(240,247,255,0.65)",
    "selBg":       "#3A8DFF",
    "selFg":       "#ffffff",
}

GLOBAL_QSS = f"""
/* -------- Base -------- */
* {{
  font-family: 'Segoe UI', Arial;
  font-size: 14px;
  color: {COLORS["text"]};
}}
QLabel {{ color: #111827; }}

/* -------- Cards / Panels -------- */
QFrame[modernCard="true"],
QGroupBox[modernCard="true"],
QWidget[modernCard="true"] {{
  background: {COLORS["panel"]};
  border: 1px solid rgba(255,255,255,0.45);
  border-radius: 12px;
}}

/* CollapsibleSection inner surface (if used) */
QWidget > QWidget#SectionContent {{
  background: {COLORS["panelInner"]};
  border: 1px solid {COLORS["stroke"]};
  border-radius: 10px;
}}
QToolButton {{
  font: 700 14px 'Segoe UI';
  color: #0F172A;
  background: transparent;
  border: 0;
}}

/* -------- Inputs -------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QDateEdit, QTimeEdit, QComboBox {{
  background: {COLORS["inputBg"]};
  color: #0f172a;
  border: 1px solid #D6E4F5;
  border-radius: 8px;
  padding: 6px 10px;
  selection-background-color: {COLORS["selBg"]};
  selection-color: {COLORS["selFg"]};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus {{
  border: 1px solid {COLORS["primary"]};
  box-shadow: 0 0 0 2px rgba(58,141,255,0.18);
}}

QComboBox::drop-down {{
    border: none; width: 24px;
}}
QComboBox::down-arrow {{
    width: 10px; height: 10px;
}}

/* -------- Buttons -------- */
QPushButton {{
  border-radius: 10px;
  padding: 8px 14px;
  font-weight: 600;
  border: 1px solid transparent;
  background: {COLORS["primary"]};
  color: white;
}}
QPushButton:hover {{ filter: brightness(1.05); }}
QPushButton:pressed {{ filter: brightness(0.95); }}

QPushButton[variant="ghost"] {{
  background: rgba(255,255,255,0.85);
  color: #0F172A;
  border: 1px solid #D6E4F5;
}}
QPushButton[variant="ghost"]:hover {{ background: rgba(255,255,255,0.95); }}

QPushButton[variant="info"]    {{ background: {COLORS["info"]};    color: white; }}
QPushButton[variant="success"] {{ background: {COLORS["success"]}; color: white; }}

/* -------- Tables -------- */
QHeaderView::section {{
  background: rgba(255,255,255,0.85);
  color: #334155;
  padding: 8px 10px;
  border: 0; border-bottom: 1px solid {COLORS["stroke"]};
  font-weight: 600;
}}
QTableWidget, QTableView {{
  background: {COLORS["panelInner"]};
  color: #0f172a;
  border: 1px solid {COLORS["stroke"]};
  border-radius: 10px;
  gridline-color: #E8EEF7;
  selection-background-color: {COLORS["selBg"]};
  selection-color: {COLORS["selFg"]};
}}
QTableView::item:!selected:alternate {{
  background: {COLORS["stripe"]};
}}

/* -------- Status / Tooltips -------- */
QToolTip {{
  background-color: rgba(255,255,255,0.98);
  color: #0f172a;
  border: 1px solid {COLORS["stroke"]};
  border-radius: 8px;
  padding: 6px 8px;
}}

/* -------- Scrollbars -------- */
QScrollBar:vertical {{
  background: transparent; width: 10px; margin: 4px;
}}
QScrollBar::handle:vertical {{
  background: rgba(58,141,255,0.55); min-height: 28px; border-radius: 6px;
}}
QScrollBar:horizontal {{
  background: transparent; height: 10px; margin: 4px;
}}
QScrollBar::handle:horizontal {{
  background: rgba(58,141,255,0.55); min-width: 28px; border-radius: 6px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
"""

# ---------- Global Apply ----------
def apply_global_theme(app: QtWidgets.QApplication, base_point_size: int = 11) -> None:
    """Apply palette + QSS globally."""
    app.setStyle("fusion")
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(COLORS["text"]))
    pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(COLORS["text"]))
    pal.setColor(QtGui.QPalette.Text, QtGui.QColor(COLORS["text"]))
    pal.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor("#ffffff"))
    pal.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor("#0f172a"))
    app.setPalette(pal)

    f = app.font()
    f.setPointSize(base_point_size)
    app.setFont(f)

    app.setStyleSheet(GLOBAL_QSS)

# ---------- Windows Mica/Acrylic (optional) ----------
def _is_windows() -> bool:
    return platform.system().lower() == "windows"

if _is_windows():
    import ctypes
    from ctypes import wintypes

    class ACCENT_POLICY(ctypes.Structure):
        _fields_ = [("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_uint32),
                    ("AnimationId", ctypes.c_int)]
    class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
        _fields_ = [("Attribute", ctypes.c_int),
                    ("Data", ctypes.c_void_p),
                    ("SizeOfData", ctypes.c_size_t)]
    WCA_ACCENT_POLICY = 19
    ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMSBT_MAINWINDOW = 2

    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi

    def _argb(a, r, g, b) -> int:
        return ((a & 0xFF) << 24) | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)

    def _enable_acrylic(hwnd: int, opacity=0xCC, tint=(58,141,255)):
        accent = ACCENT_POLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 0
        accent.GradientColor = _argb(opacity, *tint)
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)
        user32.SetWindowCompositionAttribute(int(hwnd), ctypes.byref(data))

    def _enable_mica(hwnd: int, dark=None):
        if dark is not None:
            pv = ctypes.c_int(1 if dark else 0)
            dwmapi.DwmSetWindowAttribute(int(hwnd), DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(pv), ctypes.sizeof(pv))
        mica = ctypes.c_int(DWMSBT_MAINWINDOW)
        dwmapi.DwmSetWindowAttribute(int(hwnd), DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(mica), ctypes.sizeof(mica))

def apply_window_backdrop(window: QtWidgets.QWidget, *, prefer_mica=True):
    """Enable blur (Mica/Acrylic) on Windows; no-op elsewhere. Call after .show()."""
    if not _is_windows(): return
    try:
        hwnd = int(window.winId())
        if prefer_mica and sys.getwindowsversion().build >= 22000:
            _enable_mica(hwnd)
        else:
            _enable_acrylic(hwnd)
    except Exception as e:
        print("Backdrop enable failed:", e)