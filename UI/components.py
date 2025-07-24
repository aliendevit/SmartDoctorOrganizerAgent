# ui/components.py
from __future__ import annotations
from PyQt5 import QtWidgets, QtGui, QtCore
from .design_system import DS, add_elevation, use

class Card(QtWidgets.QFrame):
    """
    Standard card with optional title/subtitle and right-aligned actions.
    Set title roles using 'role' property for theme selectors.
    """
    def __init__(self, parent=None, title:str=None, subtitle:str=None, actions=None, elevated:bool=False, theme_mode:str="dark"):
        super().__init__(parent)
        self.setProperty("card", True)
        if elevated and use(theme_mode).name == "light":
            add_elevation(self, blur=24, y=2, alpha=70)

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(DS.PAD, DS.PAD, DS.PAD, DS.PAD)
        v.setSpacing(8)

        if title:
            row = QtWidgets.QHBoxLayout(); row.setSpacing(8)
            t = QtWidgets.QLabel(title); t.setProperty("role", "h1")
            row_left = QtWidgets.QVBoxLayout(); row_left.setSpacing(0)
            row_left.addWidget(t)
            if subtitle:
                s = QtWidgets.QLabel(subtitle); s.setProperty("role", "muted")
                row_left.addWidget(s)
            row.addLayout(row_left); row.addStretch(1)
            if actions:
                for a in actions:
                    row.addWidget(a, 0, QtCore.Qt.AlignRight)
            v.addLayout(row)

class StatTile(QtWidgets.QFrame):
    """
    KPI tile with accent stripe and optional hint.
    """
    def __init__(self, label, value="—", hint="", accent="info", parent=None):
        super().__init__(parent)
        self.setProperty("card", True)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(4)

        self._lbl = QtWidgets.QLabel(label);  self._lbl.setStyleSheet(f"color:{use('dark').z_MID}; font-weight:600;")
        self._val = QtWidgets.QLabel(value);  self._val.setStyleSheet(f"color:{use('dark').TEXT}; font:700 22pt '{DS.FONT}';")
        self._hint= QtWidgets.QLabel(hint);   self._hint.setStyleSheet(f"color:{use('dark').TEXT_DIM};")

        lay.addWidget(self._lbl); lay.addWidget(self._val); lay.addWidget(self._hint)
        self.set_accent(accent)

    def set_accent(self, accent: str):
        accents = {
            "success": use('dark').OK, "warning": use('dark').WARN,
            "danger":  use('dark').ERR,"info":    use('dark').PRI,
            "violet":  use('dark').VIOLET
        }
        c = accents.get(accent, use('dark').PRI)
        # left border + a very subtle top gradient for depth on light mode
        self.setStyleSheet(self.styleSheet() + f"""
            QFrame[card="true"] {{ border-left:4px solid {c}; }}
        """)

    def set_value(self, text, hint=None):
        self._val.setText(text)
        if hint is not None: self._hint.setText(hint)

class Section(QtWidgets.QGroupBox):
    """
    DPI-safe section container (title never clips).
    """
    def __init__(self, title, *widgets):
        super().__init__(title)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(10, 18, 10, 10)
        v.setSpacing(8)
        for w in widgets: v.addWidget(w)