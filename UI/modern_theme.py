# modern_theme.py
from PyQt5 import QtCore, QtGui, QtWidgets

class ModernTheme:
    LIGHT = "light"
    DARK = "dark"

    @staticmethod
    def _palette(mode):
        p = QtGui.QPalette()
        if mode == ModernTheme.DARK:
            # Base colors
            bg   = QtGui.QColor("#0f172a")  # slate-900
            card = QtGui.QColor("#111827")  # near-slate
            base = QtGui.QColor("#111827")
            text = QtGui.QColor("#e5e7eb")  # gray-200
            sub  = QtGui.QColor("#9ca3af")  # gray-400
            acc  = QtGui.QColor("#4f46e5")  # indigo-600
            hl   = QtGui.QColor("#22c55e")  # green-500

            # Assign to palette
            p.setColor(QtGui.QPalette.Window, bg)
            p.setColor(QtGui.QPalette.Base, base)
            p.setColor(QtGui.QPalette.AlternateBase, card)
            p.setColor(QtGui.QPalette.WindowText, text)
            p.setColor(QtGui.QPalette.Text, text)
            p.setColor(QtGui.QPalette.Button, card)
            p.setColor(QtGui.QPalette.ButtonText, text)
            p.setColor(QtGui.QPalette.ToolTipBase, card)
            p.setColor(QtGui.QPalette.ToolTipText, text)
            p.setColor(QtGui.QPalette.Highlight, acc)
            p.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
            p.setColor(QtGui.QPalette.Link, acc)
            p.setColor(QtGui.QPalette.PlaceholderText, sub)
            p.setColor(QtGui.QPalette.BrightText, hl)
        else:
            # Light
            bg   = QtGui.QColor("#f8fafc")  # slate-50
            card = QtGui.QColor("#ffffff")
            base = QtGui.QColor("#ffffff")
            text = QtGui.QColor("#0f172a")  # slate-900
            sub  = QtGui.QColor("#64748b")  # slate-500
            acc  = QtGui.QColor("#4f46e5")  # indigo-600
            hl   = QtGui.QColor("#16a34a")  # green-600

            p.setColor(QtGui.QPalette.Window, bg)
            p.setColor(QtGui.QPalette.Base, base)
            p.setColor(QtGui.QPalette.AlternateBase, card)
            p.setColor(QtGui.QPalette.WindowText, text)
            p.setColor(QtGui.QPalette.Text, text)
            p.setColor(QtGui.QPalette.Button, card)
            p.setColor(QtGui.QPalette.ButtonText, text)
            p.setColor(QtGui.QPalette.ToolTipBase, card)
            p.setColor(QtGui.QPalette.ToolTipText, text)
            p.setColor(QtGui.QPalette.Highlight, acc)
            p.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
            p.setColor(QtGui.QPalette.Link, acc)
            p.setColor(QtGui.QPalette.PlaceholderText, sub)
            p.setColor(QtGui.QPalette.BrightText, hl)
        return p

    @staticmethod
    def _stylesheet(mode):
        is_dark = (mode == ModernTheme.DARK)
        border  = "#1f2937" if is_dark else "#e5e7eb"
        card    = "#111827" if is_dark else "#ffffff"
        hover   = "#374151" if is_dark else "#f3f4f6"
        text    = "#e5e7eb" if is_dark else "#0f172a"
        sub     = "#9ca3af" if is_dark else "#64748b"

        # default indigo accent
        acc      = "#4f46e5"  # indigo-600
        acc_hov  = "#4338ca"  # indigo-700
        acc_prs  = "#3730a3"  # indigo-800

        # accent palettes
        emerald  = ("#10b981", "#059669", "#047857")
        sky      = ("#0ea5e9", "#0284c7", "#0369a1")
        rose     = ("#f43f5e", "#e11d48", "#be123c")
        amber    = ("#f59e0b", "#d97706", "#b45309")
        violet   = ("#8b5cf6", "#7c3aed", "#6d28d9")
        slate    = ("#64748b", "#475569", "#334155")

        success  = ("#16a34a", "#15803d", "#166534")
        warning  = ("#f59e0b", "#d97706", "#b45309")
        info     = ("#0ea5e9", "#0284c7", "#0369a1")
        danger   = ("#ef4444", "#dc2626", "#b91c1c")

        return f"""
        * {{
            outline: 0;
        }}
        QMainWindow, QWidget {{
            background: transparent;
            color: {text};
            font-size: 11pt;
        }}

        /* Cards / group boxes */
        QFrame[modernCard="true"], QGroupBox {{
            background: {card};
            border: 1px solid {border};
            border-radius: 14px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 6px 8px 0 8px;
            color: {sub};
            font-weight: 600;
        }}

        /* ===== Buttons: default (primary / indigo) ===== */
        QPushButton {{
            background: {acc};
            color: #ffffff;
            border-radius: 10px;
            padding: 8px 14px;
            border: none;
        }}
        /* keep text visible in all states */
        QPushButton:enabled              {{ color: #ffffff; }}
        QPushButton:hover                {{ background: {acc_hov};  color: #ffffff; }}
        QPushButton:pressed              {{ background: {acc_prs};  color: #ffffff; }}
        QPushButton:disabled             {{ background: {border};   color: {sub}; }}

        /* Ghost (outlined) — explicit colors on all states */
        QPushButton[variant="ghost"],
        QPushButton[variant="ghost"]:hover,
        QPushButton[variant="ghost"]:pressed {{
            background: transparent;
            color: {text};
            border: 1px solid {border};
            font-weight: 600;
        }}
        QPushButton[variant="ghost"]:hover   {{ background: {hover}; }}
        QPushButton[variant="ghost"]:disabled{{ color: {sub}; border-color: {border}; }}

        /* Danger / Success / Warning / Info (solid) */
        QPushButton[variant="danger"],
        QPushButton[variant="danger"]:hover,
        QPushButton[variant="danger"]:pressed {{ color: #ffffff; }}
        QPushButton[variant="danger"]         {{ background: {danger[0]}; }}
        QPushButton[variant="danger"]:hover   {{ background: {danger[1]}; }}
        QPushButton[variant="danger"]:pressed {{ background: {danger[2]}; }}

        QPushButton[variant="success"],
        QPushButton[variant="success"]:hover,
        QPushButton[variant="success"]:pressed {{ color: #ffffff; }}
        QPushButton[variant="success"]         {{ background: {success[0]}; }}
        QPushButton[variant="success"]:hover   {{ background: {success[1]}; }}
        QPushButton[variant="success"]:pressed {{ background: {success[2]}; }}

        QPushButton[variant="warning"]        {{ background: {warning[0]}; color: #111827; }}
        QPushButton[variant="warning"]:hover  {{ background: {warning[1]}; color: #111827; }}
        QPushButton[variant="warning"]:pressed{{ background: {warning[2]}; color: #ffffff; }}

        QPushButton[variant="info"],
        QPushButton[variant="info"]:hover,
        QPushButton[variant="info"]:pressed    {{ color: #ffffff; }}
        QPushButton[variant="info"]            {{ background: {info[0]}; }}
        QPushButton[variant="info"]:hover      {{ background: {info[1]}; }}
        QPushButton[variant="info"]:pressed    {{ background: {info[2]}; }}

        /* ===== Solid accents (per-button) — keep text readable ===== */
        QPushButton[accent="emerald"],
        QPushButton[accent="emerald"]:hover,
        QPushButton[accent="emerald"]:pressed {{ color: #ffffff; }}
        QPushButton[accent="emerald"]         {{ background: {emerald[0]}; }}
        QPushButton[accent="emerald"]:hover   {{ background: {emerald[1]}; }}
        QPushButton[accent="emerald"]:pressed {{ background: {emerald[2]}; }}

        QPushButton[accent="sky"],
        QPushButton[accent="sky"]:hover,
        QPushButton[accent="sky"]:pressed     {{ color: #ffffff; }}
        QPushButton[accent="sky"]             {{ background: {sky[0]}; }}
        QPushButton[accent="sky"]:hover       {{ background: {sky[1]}; }}
        QPushButton[accent="sky"]:pressed     {{ background: {sky[2]}; }}

        QPushButton[accent="rose"],
        QPushButton[accent="rose"]:hover,
        QPushButton[accent="rose"]:pressed    {{ color: #ffffff; }}
        QPushButton[accent="rose"]            {{ background: {rose[0]}; }}
        QPushButton[accent="rose"]:hover      {{ background: {rose[1]}; }}
        QPushButton[accent="rose"]:pressed    {{ background: {rose[2]}; }}

        QPushButton[accent="amber"]           {{ background: {amber[0]}; color: #111827; }}
        QPushButton[accent="amber"]:hover     {{ background: {amber[1]}; color: #111827; }}
        QPushButton[accent="amber"]:pressed   {{ background: {amber[2]}; color: #ffffff; }}

        QPushButton[accent="violet"],
        QPushButton[accent="violet"]:hover,
        QPushButton[accent="violet"]:pressed  {{ color: #ffffff; }}
        QPushButton[accent="violet"]          {{ background: {violet[0]}; }}
        QPushButton[accent="violet"]:hover    {{ background: {violet[1]}; }}
        QPushButton[accent="violet"]:pressed  {{ background: {violet[2]}; }}

        QPushButton[accent="slate"],
        QPushButton[accent="slate"]:hover,
        QPushButton[accent="slate"]:pressed   {{ color: #ffffff; }}
        QPushButton[accent="slate"]           {{ background: {slate[0]}; }}
        QPushButton[accent="slate"]:hover     {{ background: {slate[1]}; }}
        QPushButton[accent="slate"]:pressed   {{ background: {slate[2]}; }}

        /* ===== Outlined (ghost) + accent ===== */
        QPushButton[variant="ghost"][accent="emerald"],
        QPushButton[variant="ghost"][accent="emerald"]:hover,
        QPushButton[variant="ghost"][accent="emerald"]:pressed {{
            color: {emerald[0]}; border: 1px solid {emerald[0]};
        }}
        QPushButton[variant="ghost"][accent="emerald"]:hover {{
            background: rgba(16,185,129,0.12);
        }}

        QPushButton[variant="ghost"][accent="sky"],
        QPushButton[variant="ghost"][accent="sky"]:hover,
        QPushButton[variant="ghost"][accent="sky"]:pressed {{
            color: {sky[0]}; border: 1px solid {sky[0]};
        }}
        QPushButton[variant="ghost"][accent="sky"]:hover {{
            background: rgba(14,165,233,0.14);
        }}

        QPushButton[variant="ghost"][accent="rose"],
        QPushButton[variant="ghost"][accent="rose"]:hover,
        QPushButton[variant="ghost"][accent="rose"]:pressed {{
            color: {rose[0]}; border: 1px solid {rose[0]};
        }}
        QPushButton[variant="ghost"][accent="rose"]:hover {{
            background: rgba(244,63,94,0.14);
        }}

        QPushButton[variant="ghost"][accent="amber"],
        QPushButton[variant="ghost"][accent="amber"]:hover,
        QPushButton[variant="ghost"][accent="amber"]:pressed {{
            color: {amber[0]}; border: 1px solid {amber[0]};
        }}
        QPushButton[variant="ghost"][accent="amber"]:hover {{
            background: rgba(245,158,11,0.18);
        }}

        QPushButton[variant="ghost"][accent="violet"],
        QPushButton[variant="ghost"][accent="violet"]:hover,
        QPushButton[variant="ghost"][accent="violet"]:pressed {{
            color: {violet[0]}; border: 1px solid {violet[0]};
        }}
        QPushButton[variant="ghost"][accent="violet"]:hover {{
            background: rgba(139,92,246,0.14);
        }}

        QPushButton[variant="ghost"][accent="slate"],
        QPushButton[variant="ghost"][accent="slate"]:hover,
        QPushButton[variant="ghost"][accent="slate"]:pressed {{
            color: {slate[0]}; border: 1px solid {slate[0]};
        }}
        QPushButton[variant="ghost"][accent="slate"]:hover {{
            background: rgba(100,116,139,0.14);
        }}

        /* Inputs */
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
            background: {card};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 8px 10px;
            selection-background-color: {acc};
            selection-color: #ffffff;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
            border: 1px solid {acc};
        }}

        /* Table */
        QTableView, QTableWidget {{
            background: {card};
            border: 1px solid {border};
            border-radius: 12px;
            gridline-color: {border};
            selection-background-color: {acc};
            selection-color: #ffffff;
        }}
        QHeaderView::section {{
            background: {hover};
            color: {text};
            border: none;
            padding: 10px 8px;
            font-weight: 600;
        }}
        QTableView::item:hover, QTableWidget::item:hover {{ background: {hover}; }}

        /* Tabs */
        QTabWidget::pane {{ border: none; }}
        QTabBar::tab {{
            background: transparent;
            color: {sub};
            border: none;
            padding: 10px 16px;
            margin: 2px 6px;
            border-radius: 10px;
            text-align: left;
            min-width: 160px;
        }}
        QTabBar::tab:selected {{ color: {text}; background: {hover}; font-weight: 600; }}
        QTabBar::tab:hover   {{ background: {hover}; color: {text}; }}

        /* Toolbar / Menus */
        QToolBar {{
            background: {card};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 6px;
        }}
        QMenu {{
            background: {card};
            border: 1px solid {border};
            border-radius: 10px;
        }}
        QMenu::item {{ padding: 8px 12px; }}
        QMenu::item:selected {{ background: {hover}; }}

        /* Scrollbars */
        QScrollBar:vertical, QScrollBar:horizontal {{
            background: transparent;
            border: none;
            margin: 4px;
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {hover};
            border-radius: 8px;
            min-height: 24px;
            min-width: 24px;
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
        """

    @staticmethod
    def apply(app: QtWidgets.QApplication, mode="dark", base_point_size=11, rtl=False):
        # HiDPI
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        app.setStyle("Fusion")

        # Font
        font = QtGui.QFont()
        for fam in ("Segoe UI", "Inter", "Noto Sans", "Arial"):
            font.setFamily(fam)
            break
        font.setPointSize(base_point_size)
        app.setFont(font)

        # Palette + stylesheet
        app.setPalette(ModernTheme._palette(mode))
        app.setStyleSheet(ModernTheme._stylesheet(mode))

        # Layout direction
        app.setLayoutDirection(QtCore.Qt.RightToLeft if rtl else QtCore.Qt.LeftToRight)

        # Remember current mode on the app
        app.setProperty("ModernThemeMode", mode)

    @staticmethod
    def toggle(app):
        # Prefer stored property; fallback to palette inspection
        current = app.property("ModernThemeMode")
        if current not in (ModernTheme.LIGHT, ModernTheme.DARK):
            win_color = app.palette().color(QtGui.QPalette.Window).name().lower()
            current = ModernTheme.DARK if win_color in ("#0f172a", "#111827") else ModernTheme.LIGHT
        next_mode = ModernTheme.LIGHT if current == ModernTheme.DARK else ModernTheme.DARK
        ModernTheme.apply(app, mode=next_mode, base_point_size=app.font().pointSize())
