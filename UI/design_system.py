# ui/design_system.py
# Clinic-ready Qt theme with readable tabs, dark zebra rows, and sensible defaults.
# Supports "dark", "light", and "high_contrast" modes.

from PyQt5 import QtWidgets, QtGui, QtCore

class DS:
    # Base typography & spacing
    FONT   = "Segoe UI"
    RADIUS = 12
    GAP    = 10
    PAD    = 12

    # ---- Dark palette (default) ----
    name     = "dark"
    BG       = "#0f172a"  # cards/surfaces
    BG_SOFT  = "#0b1020"  # inputs/tables
    FRAME    = "#1f2937"
    TEXT     = "#e5e7eb"
    TEXT_MID = "#cbd5e1"
    TEXT_DIM = "#94a3b8"
    PRI      = "#0ea5e9"
    OK       = "#16a34a"
    WARN     = "#f59e0b"
    ERR      = "#ef4444"
    VIOLET   = "#8b5cf6"

class DS_Light(DS):
    name     = "light"
    BG       = "#ffffff"
    BG_SOFT  = "#f8fafc"
    FRAME    = "#e5e7eb"
    TEXT     = "#0f172a"
    TEXT_MID = "#334155"
    TEXT_DIM = "#64748b"
    PRI      = "#2563eb"
    OK       = "#16a34a"
    WARN     = "#d97706"
    ERR      = "#dc2626"
    VIOLET   = "#7c3aed"

class DS_HC(DS):
    name     = "high_contrast"
    BG       = "#000000"
    BG_SOFT  = "#0a0a0a"
    FRAME    = "#2a2a2a"
    TEXT     = "#ffffff"
    TEXT_MID = "#e7e7e7"
    TEXT_DIM = "#bdbdbd"
    PRI      = "#00b7ff"
    OK       = "#00ff7f"
    WARN     = "#ffd000"
    ERR      = "#ff4d4f"
    VIOLET   = "#9d5cff"

def use(mode: str):
    m = (mode or "dark").lower()
    if m.startswith("light"): return DS_Light()
    if m.startswith("high"):  return DS_HC()
    return DS()

def apply_clinic_theme(app: QtWidgets.QApplication, *, mode="dark", base_pt=11, rtl: bool=False, scale: float=1.0):
    """
    Apply a consistent clinic UI theme.
    Fixes:
      • TabBar text visibility (normal/hover/selected/disabled)
      • Table zebra rows on dark themes (AlternateBase)
      • Selection colors and gridlines
    """
    ds = use(mode)
    QtWidgets.QApplication.setLayoutDirection(QtCore.Qt.RightToLeft if rtl else QtCore.Qt.LeftToRight)
    app.setFont(QtGui.QFont(DS.FONT, base_pt))

    # ---- Palette (important for alternatingRowColors & defaults) ----
    pal = app.palette()
    pal.setColor(QtGui.QPalette.Window,       QtGui.QColor(ds.BG))
    pal.setColor(QtGui.QPalette.Base,         QtGui.QColor(ds.BG_SOFT))
    pal.setColor(QtGui.QPalette.AlternateBase,QtGui.QColor("#0e162b" if ds.name!="light" else "#eef2f7"))
    pal.setColor(QtGui.QPalette.Text,         QtGui.QColor(ds.TEXT))
    pal.setColor(QtGui.QPalette.ButtonText,   QtGui.QColor(ds.TEXT))
    pal.setColor(QtGui.QPalette.Highlight,    QtGui.QColor(ds.PRI))
    pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
    pal.setColor(QtGui.QPalette.ToolTipBase,  QtGui.QColor("#111827" if ds.name!="light" else "#ffffff"))
    pal.setColor(QtGui.QPalette.ToolTipText,  QtGui.QColor("#e5e7eb" if ds.name!="light" else "#0f172a"))
    app.setPalette(pal)

    pad = int(DS.PAD * max(0.85, min(1.6, scale)))
    radius = DS.RADIUS
    alt = "#0e162b" if ds.name!="light" else "#eef2f7"
    hdr = "#0b132a" if ds.name!="light" else "#f1f5f9"

    # ---- Global QSS ----
    app.setStyleSheet(f"""
    QWidget {{ color:{ds.TEXT}; font-family:'{DS.FONT}'; background:{ds.BG}; }}

    QToolTip {{
        background: {'#111827' if ds.name!='light' else '#ffffff'};
        color: {'#e5e7eb' if ds.name!='light' else '#111827'};
        border:1px solid {ds.FRAME}; padding:4px 8px; border-radius:6px;
    }}

    /* Surfaces */
    QFrame[card="true"], QFrame[modernCard="true"] {{
        background:{ds.BG}; border:1px solid {ds.FRAME}; border-radius:{radius}px;
    }}

    /* DPI-safe group boxes */
    QGroupBox {{
        color:{ds.TEXT_MID}; border:1px solid {ds.FRAME}; border-radius:{radius - 2}px;
        margin-top:{pad + 8}px; background:{ds.BG};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; subcontrol-position: top left;
        left:{pad - 2}px; top:0px; padding:0 6px; color:{ds.TEXT_MID}; background:{ds.BG}; font-weight:600;
    }}

    /* Headings via role property (role=h1|h2|muted) */
    QLabel[role="h1"] {{ font: 700 {int(base_pt*1.9)}pt '{DS.FONT}'; color:{ds.TEXT}; }}
    QLabel[role="h2"] {{ font: 600 {int(base_pt*1.4)}pt '{DS.FONT}'; color:{ds.TEXT_MID}; }}
    QLabel[role="muted"] {{ color:{ds.TEXT_DIM}; }}

    /* Inputs */
    QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QDateEdit, QTimeEdit, QComboBox {{
        background:{ds.BG_SOFT}; color:{ds.TEXT}; border:1px solid {ds.FRAME}; border-radius:8px; padding:6px 8px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus,
    QDateEdit:focus, QTimeEdit:focus, QComboBox:focus {{
        outline:none; border:1px solid {ds.PRI};
    }}
    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QTextEdit:disabled,
    QDateEdit:disabled, QTimeEdit:disabled, QComboBox:disabled {{
        color:{ds.TEXT_DIM}; background: {'#0a0f1c' if ds.name!='light' else '#f1f5f9'};
    }}

    /* Buttons */
    QPushButton {{
        background:{ds.PRI}; color:white; border:none; border-radius:8px; padding:8px 14px; font-weight:600;
    }}
    QPushButton:hover {{ filter:brightness(1.06); }}
    QPushButton:pressed {{ transform: translateY(1px); }}
    QPushButton:disabled {{ background:{ds.FRAME}; color:{ds.TEXT_DIM}; }}
    QPushButton[variant="ghost"] {{ background:{ds.BG_SOFT}; color:{ds.TEXT_MID}; border:1px solid {ds.FRAME}; }}
    QPushButton[variant="success"] {{ background:{ds.OK}; }}
    QPushButton[variant="warning"] {{ background:{ds.WARN}; }}
    QPushButton[variant="danger"]  {{ background:{ds.ERR}; }}
    QPushButton[variant="info"]    {{ background:{ds.PRI}; }}

    /* Tables (explicit zebra & selection to avoid platform defaults) */
    QTableWidget {{
        background:{ds.BG_SOFT};
        color:{ds.TEXT};
        border:1px solid {ds.FRAME};
        border-radius:8px;
        alternate-background-color:{alt};
        gridline-color:{ds.FRAME};
        selection-background-color:{ds.PRI};
        selection-color:white;
    }}
    QHeaderView::section {{
        background:{hdr};
        color:{ds.TEXT_MID};
        padding:8px; border:none;
    }}
    QTableCornerButton::section {{ background:{ds.BG_SOFT}; border:1px solid {ds.FRAME}; }}

    /* Tabs – readable in all states */
    QTabWidget::pane {{
        border:1px solid {ds.FRAME};
        border-radius:{radius - 2}px;
        top:-1px; background:{ds.BG};
    }}
    QTabBar {{ background: transparent; }}
    QTabBar::tab {{
        background:{ds.BG_SOFT};
        color:{ds.TEXT_MID};
        border:1px solid {ds.FRAME};
        padding:6px 12px;
        margin-right:2px;
        border-top-left-radius:8px; border-top-right-radius:8px;
        min-height: 26px;
    }}
    QTabBar::tab:hover {{
        color:{ds.TEXT};
        background:{'#111827' if ds.name!='light' else '#eef2f7'};
    }}
    QTabBar::tab:selected {{
        background:{ds.BG};
        color:{ds.TEXT};
        border-bottom-color: transparent;
        font-weight:600;
    }}
    QTabBar::tab:disabled {{ color:{ds.TEXT_DIM}; }}

    /* Menus/Checks/Scrollbars */
    QMenu {{ background:{ds.BG}; color:{ds.TEXT}; border:1px solid {ds.FRAME}; border-radius:8px; }}
    QMenu::item:selected {{ background:{ds.BG_SOFT}; }}
    QCheckBox, QRadioButton {{ color:{ds.TEXT}; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width:16px; height:16px; border:1px solid {ds.FRAME}; border-radius:3px; background:{ds.BG_SOFT};
    }}
    QCheckBox::indicator:checked {{ image:none; background:{ds.PRI}; border-color:{ds.PRI}; }}

    QScrollBar:vertical {{ background:transparent; width:10px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{ds.FRAME}; border-radius:5px; min-height:24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}
    """)

def apply_table_palette(table: QtWidgets.QTableWidget, *, dark=True):
    """
    Optional helper if you need to enforce palette on a specific table at runtime.
    Not required if you applied the global theme before creating widgets.
    """
    pal = table.palette()
    pal.setColor(QtGui.QPalette.Base,           QtGui.QColor("#0b1020" if dark else "#ffffff"))
    pal.setColor(QtGui.QPalette.AlternateBase,  QtGui.QColor("#0e162b" if dark else "#eef2f7"))
    pal.setColor(QtGui.QPalette.Text,           QtGui.QColor("#e5e7eb" if dark else "#0f172a"))
    pal.setColor(QtGui.QPalette.Highlight,      QtGui.QColor("#0ea5e9"))
    pal.setColor(QtGui.QPalette.HighlightedText,QtGui.QColor("#ffffff"))
    table.setPalette(pal)