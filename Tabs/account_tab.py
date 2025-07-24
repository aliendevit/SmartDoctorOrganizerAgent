# Tabs/account_tab.py
from __future__ import annotations

import csv
import io
import traceback
from typing import Any, Dict, List

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QLineEdit, QStyledItemDelegate

# ---- Photo drop-zone widget (ensure widgets/photo_field.py exists) ----
from widgets.photo_field import PhotoField

# ---------------- data layer (safe fallbacks) ----------------
try:
    from data.data import load_all_clients, update_account_in_db, insert_client
except Exception:
    def load_all_clients() -> List[Dict]: return []
    def update_account_in_db(name: str, payload: Dict) -> bool: return False
    def insert_client(payload: Dict) -> bool: return False

# --------------- optional profile dialog (graceful if missing) -----------
try:
    from widgets.clientWidget import ClientAccountPage
except Exception:
    ClientAccountPage = None

# ---------------- translation ----------------------
def _tr(text: str) -> str:
    try:
        from features.translation_helper import tr
        return tr(text)
    except Exception:
        return text

# ---------------- helpers --------------------------
def _to_float(val: Any) -> float:
    try:
        s = "" if val is None else str(val)
        s = s.replace(",", "").strip()
        return float(s) if s else 0.0
    except Exception:
        return 0.0

def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

class NumberDelegate(QStyledItemDelegate):
    """Validated numeric editing + consistent 2-dp rendering for currency columns."""
    def __init__(self, parent=None, decimals=2, bottom=0.0, top=1e12):
        super().__init__(parent)
        self.decimals, self.bottom, self.top = decimals, bottom, top

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        v = QDoubleValidator(self.bottom, self.top, self.decimals, editor)
        v.setNotation(QDoubleValidator.StandardNotation)
        editor.setValidator(v)
        editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(str(_to_float(index.data())))

    def setModelData(self, editor, model, index):
        val = _to_float(editor.text())
        model.setData(index, f"{val:.2f}")               # display
        model.setData(index, val, QtCore.Qt.UserRole)    # numeric sort

# ---------------- collapsible section ----------------
class CollapsibleSection(QtWidgets.QWidget):
    """A simple collapsible section with a title and optional subtitle."""
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self._content = QtWidgets.QWidget(self)
        self._content.setObjectName("SectionContent")
        self._content.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._grid = QtWidgets.QGridLayout(self._content)
        self._grid.setContentsMargins(12, 8, 12, 8)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(10)

        # Header
        self._btn = QtWidgets.QToolButton(self)
        self._btn.setText("▾")
        self._btn.setCheckable(True)
        self._btn.setChecked(True)
        self._btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._btn.toggled.connect(self._on_toggle)

        self._title = QtWidgets.QLabel(title)
        self._title.setStyleSheet("font: 600 14pt 'Segoe UI';")
        self._sub = QtWidgets.QLabel(subtitle)
        self._sub.setStyleSheet("color:#94a3b8;")

        head = QtWidgets.QHBoxLayout()
        head.setContentsMargins(8, 8, 8, 4)
        head.setSpacing(8)
        head.addWidget(self._btn, 0, QtCore.Qt.AlignLeft)
        v = QtWidgets.QVBoxLayout()
        v.setSpacing(0)
        v.addWidget(self._title)
        if subtitle:
            v.addWidget(self._sub)
        head.addLayout(v)
        head.addStretch(1)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)
        outer.addLayout(head)
        outer.addWidget(self._content)

        # card hint
        self.setProperty("modernCard", True)
        self.setStyleSheet("""
        QWidget > QWidget#SectionContent {
            border:1px solid #E5EFFA; border-radius:10px; background: rgba(255,255,255,0.65);
        }
        QToolButton { font: 700 14px 'Segoe UI'; color:#0F172A; background:transparent; border:0; }
        """)
        self._label_w = 140

    def add_row(self, row: int, label: str, widget: QtWidgets.QWidget):
        lab = QtWidgets.QLabel(label)
        lab.setMinimumWidth(self._label_w)
        lab.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lab.setStyleSheet("color:#334155;")   # slate-600
        self._grid.addWidget(lab, row, 0)
        self._grid.addWidget(widget, row, 1)

    def add_full_row(self, row: int, widget: QtWidgets.QWidget):
        self._grid.addWidget(widget, row, 0, 1, 2)

    def _on_toggle(self, open_: bool):
        self._btn.setText("▾" if open_ else "▸")
        self._content.setVisible(open_)
        self._content.adjustSize()
        self.adjustSize()

# ---------------- accounts tab ----------------
class AccountsTab(QtWidgets.QWidget):
    clientAdded = QtCore.pyqtSignal(dict)
    clientUpdated = QtCore.pyqtSignal(dict)

    COL_NAME  = 0
    COL_AGE   = 1
    COL_PAID  = 2
    COL_OWED  = 3
    COL_TOTAL = 4
    COL_PHOTO = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clients: List[Dict] = []
        self._building = False
        self._save_debounce = QtCore.QTimer(self)
        self._save_debounce.setSingleShot(True)
        self._save_debounce.setInterval(400)
        self._save_debounce.timeout.connect(self._save_all)

        self._build_ui()
        self._wire_signals()
        self._refresh_from_db()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        hdr = QtWidgets.QFrame(); hdr.setProperty("modernCard", True)
        h = QtWidgets.QHBoxLayout(hdr); h.setContentsMargins(14, 14, 14, 14); h.setSpacing(10)
        title = QtWidgets.QLabel(_tr("Patient Accounts")); title.setStyleSheet("font:700 18pt 'Segoe UI';")
        subtitle = QtWidgets.QLabel(_tr("Add, review, and update billing & profile"))
        subtitle.setStyleSheet("color:#64748b; margin-left:6px;")  # slate-500
        left_hdr = QtWidgets.QVBoxLayout(); left_hdr.addWidget(title); left_hdr.addWidget(subtitle)
        h.addLayout(left_hdr); h.addStretch(1)

        self.search_line = QtWidgets.QLineEdit(); self.search_line.setPlaceholderText(_tr("Search by name or note…")); self.search_line.setClearButtonEnabled(True)
        self.btn_export = QtWidgets.QPushButton(_tr("Export CSV")); self.btn_export.setProperty("variant","ghost")
        self.refresh_btn = QtWidgets.QPushButton(_tr("Refresh")); self.refresh_btn.setProperty("variant", "info")
        h.addWidget(self.search_line, 0)
        h.addWidget(self.btn_export, 0)
        h.addWidget(self.refresh_btn, 0)
        root.addWidget(hdr)

        # Splitter
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        # ===== LEFT: scrollable organized form =====
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        left_wrap = QtWidgets.QWidget()
        left_v = QtWidgets.QVBoxLayout(left_wrap)
        left_v.setContentsMargins(6, 6, 6, 6)
        left_v.setSpacing(12)

        # Demographics
        self.in_name = QtWidgets.QLineEdit(); self.in_name.setPlaceholderText(_tr("Full name"))
        self.in_age  = QtWidgets.QSpinBox(); self.in_age.setRange(0, 120)
        self.photoField = PhotoField(left_wrap, min_size=(320, 180))

        sec_demo = CollapsibleSection(_tr("Demographics"), _tr("Basic patient info & photo"))
        sec_demo.add_row(0, _tr("Name"), self.in_name)
        sec_demo.add_row(1, _tr("Age"), self.in_age)
        sec_demo.add_row(2, _tr("Photo"), self.photoField)
        left_v.addWidget(sec_demo)

        # Clinical
        self.in_symp = QtWidgets.QLineEdit(); self.in_symp.setPlaceholderText(_tr("e.g., toothache, swelling"))
        self.in_notes = QtWidgets.QTextEdit(); self.in_notes.setFixedHeight(110)
        sec_clin = CollapsibleSection(_tr("Clinical"), _tr("Presenting symptoms & notes"))
        sec_clin.add_row(0, _tr("Symptoms (comma-sep.)"), self.in_symp)
        sec_clin.add_row(1, _tr("Notes"), self.in_notes)
        left_v.addWidget(sec_clin)

        # Scheduling
        self.in_date = QtWidgets.QDateEdit(QtCore.QDate.currentDate()); self.in_date.setCalendarPopup(True); self.in_date.setDisplayFormat("dd-MM-yyyy")
        self.in_appt = QtWidgets.QDateEdit(QtCore.QDate.currentDate()); self.in_appt.setCalendarPopup(True); self.in_appt.setDisplayFormat("dd-MM-yyyy")
        self.in_time = QtWidgets.QTimeEdit(QtCore.QTime.currentTime()); self.in_time.setDisplayFormat("hh:mm AP")
        self.in_follow = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addDays(7)); self.in_follow.setCalendarPopup(True); self.in_follow.setDisplayFormat("dd-MM-yyyy")
        self.in_summary = QtWidgets.QTextEdit(); self.in_summary.setFixedHeight(80)
        sec_sched = CollapsibleSection(_tr("Scheduling"), _tr("Dates, times & visit summary"))
        sec_sched.add_row(0, _tr("General Date"), self.in_date)
        sec_sched.add_row(1, _tr("Appt Date"), self.in_appt)
        sec_sched.add_row(2, _tr("Appt Time"), self.in_time)
        sec_sched.add_row(3, _tr("Follow-Up Date"), self.in_follow)
        sec_sched.add_row(4, _tr("Summary"), self.in_summary)
        left_v.addWidget(sec_sched)

        # Billing
        self.in_total = QtWidgets.QDoubleSpinBox(); self.in_total.setRange(0, 1e9); self.in_total.setDecimals(2)
        self.in_paid  = QtWidgets.QDoubleSpinBox(); self.in_paid.setRange(0, 1e9);  self.in_paid.setDecimals(2)
        self.in_owed  = QtWidgets.QDoubleSpinBox(); self.in_owed.setRange(0, 1e9);  self.in_owed.setDecimals(2); self.in_owed.setReadOnly(True)
        sec_bill = CollapsibleSection(_tr("Billing"), _tr("Auto-calculates owed = total − paid"))
        sec_bill.add_row(0, _tr("Total Amount"), self.in_total)
        sec_bill.add_row(1, _tr("Total Paid"), self.in_paid)
        sec_bill.add_row(2, _tr("Owed"), self.in_owed)
        left_v.addWidget(sec_bill)

        # Actions
        row = QtWidgets.QHBoxLayout()
        self.btn_clear = QtWidgets.QPushButton(_tr("Clear")); self.btn_clear.setProperty("variant", "ghost")
        self.btn_add   = QtWidgets.QPushButton(_tr("Add Client")); self.btn_add.setProperty("variant", "success")
        row.addStretch(1); row.addWidget(self.btn_clear); row.addWidget(self.btn_add)
        hint = QtWidgets.QLabel(_tr("Tip: Ctrl+S to save table edits · Enter to add client"))
        hint.setStyleSheet("color:#64748b;")  # slate-500
        sec_actions = CollapsibleSection(_tr("Actions"))
        w = QtWidgets.QWidget(); lw = QtWidgets.QVBoxLayout(w); lw.setContentsMargins(0,0,0,0); lw.setSpacing(8)
        lw.addLayout(row); lw.addWidget(hint)
        sec_actions.add_full_row(0, w)
        left_v.addWidget(sec_actions)

        left_v.addStretch(1)
        scroll.setWidget(left_wrap)

        # ===== RIGHT: Accounts Table =====
        right = QtWidgets.QFrame(); right.setProperty("modernCard", True)
        r = QtWidgets.QVBoxLayout(right); r.setContentsMargins(12, 12, 12, 12); r.setSpacing(8)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            _tr("Name"), _tr("Age"), _tr("Total Paid"), _tr("Owed"), _tr("Total Amount"), _tr("Has Photo")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.SelectedClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self.table.setSortingEnabled(True)
        self.table.setItemDelegateForColumn(self.COL_PAID, NumberDelegate(self))
        self.table.setItemDelegateForColumn(self.COL_TOTAL, NumberDelegate(self))
        top_act = QtWidgets.QHBoxLayout()
        self.open_btn = QtWidgets.QPushButton(_tr("Open Selected")); self.open_btn.setProperty("variant", "info")
        self.save_all_btn = QtWidgets.QPushButton(_tr("Save All Changes (Ctrl+S)")); self.save_all_btn.setProperty("variant", "success")
        top_act.addWidget(self.open_btn); top_act.addStretch(1); top_act.addWidget(self.save_all_btn)
        r.addWidget(self.table, 1)
        r.addLayout(top_act)

        split.addWidget(scroll)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([560, 920])

        # Status line
        self.status = QtWidgets.QLabel("")
        root.addWidget(self.status)

        # Menus & shortcuts
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_menu)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self._save_all)
        QtWidgets.QShortcut(QtGui.QKeySequence("Return"), self, activated=self._add_client_from_form)

        # ✨ apply refined local theme colors
        self._apply_local_theme()

        _polish(self.refresh_btn, self.btn_export, self.btn_add, self.btn_clear, self.open_btn, self.save_all_btn)

    # ---------- local theme ----------
    def _apply_local_theme(self):
        """
        Doctor-friendly colors layered over your global glass theme.
        """
        self.setStyleSheet("""
        /* Base */
        QWidget { font-family: 'Segoe UI', Arial; font-size: 14px; color: #1f2937; }
        QLabel { color: #111827; }

        /* Cards */
        QFrame[modernCard="true"] {
            background: rgba(255,255,255,0.55);
            border: 1px solid rgba(255,255,255,0.45);
            border-radius: 12px;
        }

        /* Sections */
        QWidget > QWidget#SectionContent {
            background: rgba(255,255,255,0.65);
            border: 1px solid #E5EFFA;
            border-radius: 10px;
        }
        QToolButton { font: 700 14px 'Segoe UI'; color: #0F172A; background: transparent; border: 0; }

        /* Inputs */
        QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QDateEdit, QTimeEdit {
            background: rgba(255,255,255,0.88);
            color: #0f172a;
            border: 1px solid #D6E4F5;
            border-radius: 8px; 
            padding: 6px 10px;
            selection-background-color: #3A8DFF;
            selection-color: white;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus {
            border: 1px solid #3A8DFF;
            box-shadow: 0 0 0 2px rgba(58,141,255,0.18);
        }

        /* Buttons */
        QPushButton {
            border-radius: 10px; padding: 8px 14px; font-weight: 600; border: 1px solid transparent;
            background: #3A8DFF; color: white;
        }
        QPushButton:hover { filter: brightness(1.05); }
        QPushButton:pressed { filter: brightness(0.95); }

        QPushButton[variant="ghost"] { background: rgba(255,255,255,0.85); color: #0F172A; border: 1px solid #D6E4F5; }
        QPushButton[variant="ghost"]:hover { background: rgba(255,255,255,0.95); }

        QPushButton[variant="info"] { background: #2CBBA6; color: white; }
        QPushButton[variant="success"] { background: #7A77FF; color: white; }

        /* Table */
        QHeaderView::section {
            background: rgba(255,255,255,0.85);
            color: #334155;
            padding: 8px 10px;
            border: 0; border-bottom: 1px solid #E5EFFA;
            font-weight: 600;
        }
        QTableWidget { 
            background: rgba(255,255,255,0.65);
            color: #0f172a;
            border: 1px solid #E5EFFA; border-radius: 10px;
            gridline-color: #E8EEF7;
            selection-background-color: #3A8DFF; selection-color: white;
        }
        QTableView::item:!selected:alternate { background: rgba(240,247,255,0.65); }

        /* Scrollbars */
        QScrollBar:vertical { background: transparent; width: 10px; margin: 4px; }
        QScrollBar::handle:vertical { background: rgba(58,141,255,0.55); min-height: 28px; border-radius: 6px; }
        QScrollBar:horizontal { background: transparent; height: 10px; margin: 4px; }
        QScrollBar::handle:horizontal { background: rgba(58,141,255,0.55); min-width: 28px; border-radius: 6px; }
        QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

        /* Tooltips */
        QToolTip {
            background-color: rgba(255,255,255,0.98);
            color: #0f172a;
            border: 1px solid #E5EFFA;
            border-radius: 8px;
            padding: 6px 8px;
        }
        """)

    # ---------- signals ----------
    def _wire_signals(self):
        self.refresh_btn.clicked.connect(self._refresh_from_db)
        self.btn_export.clicked.connect(self._export_csv)
        self.btn_add.clicked.connect(self._add_client_from_form)
        self.btn_clear.clicked.connect(self._clear_form)
        self.search_line.textChanged.connect(self._apply_search_filter)
        self.open_btn.clicked.connect(lambda: self.open_account_detail(self.table.currentRow()))
        self.save_all_btn.clicked.connect(self._save_all)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.doubleClicked.connect(self.open_account_detail)
        self.table.itemActivated.connect(lambda it: self.open_account_detail(it.row()))
        self.in_total.valueChanged.connect(self._recalc_owed)
        self.in_paid.valueChanged.connect(self._recalc_owed)

    # ---------- helpers ----------
    def _recalc_owed(self):
        owed = max(0.0, float(self.in_total.value()) - float(self.in_paid.value()))
        self.in_owed.blockSignals(True)
        self.in_owed.setValue(owed)
        self.in_owed.blockSignals(False)

    def _clear_form(self):
        self.in_name.clear(); self.in_age.setValue(0)
        self.photoField.clear_image()
        self.in_symp.clear(); self.in_notes.clear()
        self.in_date.setDate(QtCore.QDate.currentDate())
        self.in_appt.setDate(QtCore.QDate.currentDate())
        self.in_time.setTime(QtCore.QTime.currentTime())
        self.in_follow.setDate(QtCore.QDate.currentDate().addDays(7))
        self.in_summary.clear()
        self.in_total.setValue(0.0); self.in_paid.setValue(0.0); self.in_owed.setValue(0.0)

    # ---------- CRUD ----------
    def _add_client_from_form(self):
        name = self.in_name.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, _tr("Input Error"), _tr("Name is required."))
            return
        if any((c.get("Name") or "").strip().lower() == name.lower() for c in self.clients):
            if QtWidgets.QMessageBox.question(
                self, _tr("Duplicate"),
                _tr("A client with this name already exists. Add anyway?")
            ) != QtWidgets.QMessageBox.Yes:
                return
        payload = {
            "Name": name,
            "Age": int(self.in_age.value()),
            "Image": self.photoField.imagePath() or "",
            "Symptoms": [s.strip() for s in self.in_symp.text().split(",") if s.strip()],
            "Notes": self.in_notes.toPlainText().strip(),
            "Date": self.in_date.date().toString("dd-MM-yyyy"),
            "Appointment Date": self.in_appt.date().toString("dd-MM-yyyy"),
            "Appointment Time": self.in_time.time().toString("hh:mm AP"),
            "Follow-Up Date": self.in_follow.date().toString("dd-MM-yyyy"),
            "Summary": self.in_summary.toPlainText().strip(),
            "Total Amount": float(self.in_total.value()),
            "Total Paid": float(self.in_paid.value()),
            "Owed": float(self.in_owed.value()),
        }
        try:
            insert_client(payload)
            self.status.setText(f"✅ {_tr('Client added')}: {name}")
            self._refresh_from_db()
            self._clear_form()
            self._highlight_client(name)
            self.clientAdded.emit(payload)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Error"), _tr("Error adding client: ") + str(e))

    def _refresh_from_db(self):
        try:
            self.clients = load_all_clients() or []
        except Exception:
            self.clients = []
            traceback.print_exc()
        self._update_table()
        self._apply_search_filter()

    def _update_table(self):
        self._building = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for i, c in enumerate(self.clients):
            self.table.insertRow(i)

            def _it(text, editable=False, right=False, numeric_role=None):
                it = QtWidgets.QTableWidgetItem("" if text is None else str(text))
                flags = it.flags()
                if not editable: flags &= ~QtCore.Qt.ItemIsEditable
                it.setFlags(flags)
                if right: it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                if numeric_role is not None: it.setData(QtCore.Qt.UserRole, numeric_role)
                return it

            total_paid = _to_float(c.get("Total Paid", 0))
            total_amount = _to_float(c.get("Total Amount", 0))
            owed_val = max(0.0, total_amount - total_paid)
            has_photo = "✅" if (c.get("Image") or "").strip() else "—"

            self.table.setItem(i, self.COL_NAME,  _it(c.get("Name", "")))
            self.table.setItem(i, self.COL_AGE,   _it(c.get("Age", "")))
            self.table.setItem(i, self.COL_PAID,  _it(f"{total_paid:.2f}", editable=True, right=True, numeric_role=total_paid))
            self.table.setItem(i, self.COL_OWED,  _it(f"{owed_val:.2f}", right=True, numeric_role=owed_val))
            self.table.setItem(i, self.COL_TOTAL, _it(f"{total_amount:.2f}", editable=True, right=True, numeric_role=total_amount))
            self.table.setItem(i, self.COL_PHOTO, _it(has_photo))

            # Gentle highlight if balance owed
            if owed_val > 0.01:
                bg = QtGui.QColor("#FFF8E1")  # pale cream (readable on light)
                for col in range(self.table.columnCount()):
                    it = self.table.item(i, col)
                    if it: it.setBackground(QtGui.QBrush(bg))

        self.table.blockSignals(False)
        self._building = False
        self.table.resizeColumnsToContents()

    def _on_cell_changed(self, row, column):
        if self._building:
            return
        if column not in (self.COL_PAID, self.COL_TOTAL):
            return
        try:
            total_paid = _to_float(self._txt(row, self.COL_PAID))
            total_amount = _to_float(self._txt(row, self.COL_TOTAL))
            owed = max(0.0, total_amount - total_paid)

            self.table.blockSignals(True)
            self.table.item(row, self.COL_PAID).setData(QtCore.Qt.UserRole, total_paid)
            self.table.item(row, self.COL_TOTAL).setData(QtCore.Qt.UserRole, total_amount)
            self.table.setItem(row, self.COL_OWED, QtWidgets.QTableWidgetItem(f"{owed:.2f}"))
            self.table.item(row, self.COL_OWED).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.table.item(row, self.COL_OWED).setData(QtCore.Qt.UserRole, owed)
            self.table.blockSignals(False)

            name_key = (self._txt(row, self.COL_NAME) or "").strip()
            if name_key:
                self._save_debounce.start()
        except Exception:
            traceback.print_exc()

    def _txt(self, r, c) -> str:
        it = self.table.item(r, c)
        return it.text() if it else ""

    # ---------- search / export ----------
    def _apply_search_filter(self):
        q = (self.search_line.text() or "").strip().lower()
        for r in range(self.table.rowCount()):
            name = (self.table.item(r, self.COL_NAME) or QtWidgets.QTableWidgetItem("")).text().lower()
            show = (q in name) if q else True
            self.table.setRowHidden(r, not show)

    def _export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, _tr("Export CSV"), "accounts.csv", "CSV (*.csv)")
        if not path:
            return
        headers = [_tr("Name"), _tr("Age"), _tr("Total Paid"), _tr("Owed"), _tr("Total Amount"), _tr("Has Photo")]
        try:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(headers)
            for r in range(self.table.rowCount()):
                if self.table.isRowHidden(r):
                    continue
                row = [self._txt(r, c) for c in range(self.table.columnCount())]
                writer.writerow(row)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(buf.getvalue())
            QtWidgets.QMessageBox.information(self, _tr("Export"), _tr("CSV exported successfully."))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Export"), _tr("Failed to export: ") + str(e))

    # ---------- context / profile ----------
    def _on_table_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction(_tr("Open Account"))
        act_copy = menu.addAction(_tr("Copy Row"))
        act = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if act == act_open:
            self.open_account_detail(idx)
        elif act == act_copy:
            self._copy_row(idx.row())

    def _copy_row(self, row: int):
        vals = [self._txt(row, c) for c in range(self.table.columnCount())]
        QtWidgets.QApplication.clipboard().setText("\t".join(vals))
        self.status.setText(_tr("Row copied to clipboard"))

    def open_account_detail(self, index):
        row = index.row() if isinstance(index, QtCore.QModelIndex) else int(index)
        if row < 0 or row >= self.table.rowCount():
            return
        client_name = (self.table.item(row, self.COL_NAME) or QtWidgets.QTableWidgetItem("")).text().strip()
        acc = next((a for a in self.clients if (a.get("Name", "") or "").strip().lower() == client_name.lower()), None)
        if not acc:
            QtWidgets.QMessageBox.warning(self, _tr("Open"), _tr("Could not find this client: ") + client_name)
            return
        if not ClientAccountPage:
            QtWidgets.QMessageBox.information(self, _tr("Open"), _tr("Profile dialog not available in this build."))
            return
        dlg = ClientAccountPage(dict(acc), parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            updated = dlg.get_updated_client()
            update_account_in_db(client_name, updated)
            self._refresh_from_db()
            self._highlight_client(updated.get("Name", client_name))
            self.clientUpdated.emit(updated)

    def _highlight_client(self, name: str):
        key = (name or "").strip().lower()
        for row in range(self.table.rowCount()):
            it0 = self.table.item(row, self.COL_NAME)
            if it0 and it0.text().strip().lower() == key:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it: it.setBackground(QtGui.QBrush(QtGui.QColor("#E0F2FE")))  # light sky tint
                self.table.scrollToItem(it0, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

    # ---------- save ----------
    def _save_all(self):
        n = self.table.rowCount()
        failures = 0
        for r in range(n):
            try:
                name = (self.table.item(r, self.COL_NAME) or QtWidgets.QTableWidgetItem("")).text().strip()
                if not name:
                    continue
                total_paid = _to_float(self._txt(r, self.COL_PAID))
                total_amount = _to_float(self._txt(r, self.COL_TOTAL))
                owed = max(0.0, total_amount - total_paid)
                ok = update_account_in_db(name, {
                    "Name": name,
                    "Total Paid": total_paid,
                    "Total Amount": total_amount,
                    "Owed": owed
                })
                if ok is False:
                    failures += 1
            except Exception:
                failures += 1
                traceback.print_exc()
        if failures:
            QtWidgets.QMessageBox.warning(self, _tr("Save"), _tr("Saved with some errors. Check logs."))
        else:
            QtWidgets.QMessageBox.information(self, _tr("Save"), _tr("All changes saved."))
        self._refresh_from_db()

    # ---------- public hook ----------
    def update_table(self):
        self._refresh_from_db()

    # ---------- i18n ----------
    def retranslateUi(self):
        self.refresh_btn.setText(_tr("Refresh"))
        self.btn_export.setText(_tr("Export CSV"))
        self.search_line.setPlaceholderText(_tr("Search by name or note…"))
        self.table.setHorizontalHeaderLabels([
            _tr("Name"), _tr("Age"), _tr("Total Paid"), _tr("Owed"), _tr("Total Amount"), _tr("Has Photo")
        ])
        self.btn_clear.setText(_tr("Clear"))
        self.btn_add.setText(_tr("Add Client"))


# ---- standalone run ----
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        from UI import modern_theme
        modern_theme.apply_glassy_theme(app)
    except Exception:
        pass
    w = AccountsTab()
    w.resize(1200, 760)
    w.show()
    try:
        from UI import modern_theme as mt
        mt.apply_real_glass(w, use_mica_prefer=True)
    except Exception:
        pass
    sys.exit(app.exec_())