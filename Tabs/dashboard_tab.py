# dashboard_tab.py — Glass-matched Practice Dashboard (full file)

import csv
import json
import os
from typing import List, Dict

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QDate, QStandardPaths

# ---- Global design tokens (safe fallback) -----------------------------------
try:
    from UI.design_system import COLORS as DS_COLORS
except Exception:
    DS_COLORS = {
        "text": "#1f2937", "textDim": "#334155", "muted": "#64748b",
        "primary": "#3A8DFF", "info": "#2CBBA6", "success": "#7A77FF",
        "stroke": "#E5EFFA", "panel": "rgba(255,255,255,0.55)",
        "panelInner": "rgba(255,255,255,0.65)", "inputBg": "rgba(255,255,255,0.88)",
        "stripe": "rgba(240,247,255,0.65)", "selBg": "#3A8DFF", "selFg": "#ffffff",
    }

# ---- Settings (optional) -----------------------------------------------------
try:
    from core import app_settings as AS
except Exception:
    AS = None

_CSYM = {"USD":"$", "EUR":"€", "GBP":"£", "JPY":"¥", "AUD":"$", "CAD":"$", "INR":"₹"}
def _sym(code: str) -> str:
    return _CSYM.get((code or "").upper(), code or "$")

# ---- Robust data access ------------------------------------------------------
def _load_all_clients_safe() -> List[Dict]:
    try:
        from data.data import load_all_clients
        return load_all_clients() or []
    except Exception:
        return []

# ---- Archive path (portable) -------------------------------------------------
def _archive_file_path() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.path.expanduser("~")
    folder = os.path.join(base, "MedicalDocAI", "archives")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "monthly_receipts_archive.json")

ARCHIVE_FILE = _archive_file_path()

# ---- Small helpers -----------------------------------------------------------
def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

def _tr(text: str) -> str:
    try:
        from features.translation_helper import tr as _t
        return _t(text)
    except Exception:
        return text

def _to_float(v) -> float:
    try:
        if v is None: return 0.0
        s = str(v).strip().replace(",", "")
        return float(s) if s else 0.0
    except Exception:
        return 0.0

# -----------------------------------------------------------------------------


class DashboardTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_clients_cache: List[Dict] = []
        self._outstanding_cache: List[Dict] = []
        self._session_settings = QtCore.QSettings("YourOrg", "MedicalDocAI Demo v1.9.3")

        # currency from settings (optional)
        self._currency = "USD"
        if AS:
            try:
                cfg = AS.read_all()
                self._currency = str(cfg.get("bill/currency", "USD"))
            except Exception:
                pass

        self._build_ui()
        self._load_persisted_period()
        self.load_archive()
        self.refresh_data()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== Header (title + presets + days spin + refresh) =====
        header_card = QtWidgets.QFrame(); header_card.setProperty("modernCard", True)
        h = QtWidgets.QHBoxLayout(header_card)
        h.setContentsMargins(12, 12, 12, 12); h.setSpacing(10)

        self.title = QtWidgets.QLabel(_tr("Practice Dashboard"))
        self.title.setStyleSheet("font: 700 20px 'Segoe UI';")
        h.addWidget(self.title)
        h.addStretch(1)

        # presets – ghost style with subtle check state (i18n-proof via ids)
        self.btn_7d   = QtWidgets.QPushButton(_tr("7d"))
        self.btn_30d  = QtWidgets.QPushButton(_tr("30d"))
        self.btn_90d  = QtWidgets.QPushButton(_tr("90d"))
        self.btn_365d = QtWidgets.QPushButton(_tr("365d"))
        for b in (self.btn_7d, self.btn_30d, self.btn_90d, self.btn_365d):
            b.setProperty("accent", "slate")
            b.setCheckable(True)
            h.addWidget(b)
        _polish(self.btn_7d, self.btn_30d, self.btn_90d, self.btn_365d)

        self._preset_group = QtWidgets.QButtonGroup(self)
        self._preset_group.addButton(self.btn_7d,    7)
        self._preset_group.addButton(self.btn_30d,  30)
        self._preset_group.addButton(self.btn_90d,  90)
        self._preset_group.addButton(self.btn_365d,365)
        self._preset_group.buttonClicked[int].connect(self._apply_preset_days)

        self.period_label = QtWidgets.QLabel(_tr("Days:"))
        self.inventory_days_spinbox = QtWidgets.QSpinBox()
        self.inventory_days_spinbox.setRange(1, 365)
        self.inventory_days_spinbox.setValue(30)
        self.inventory_days_spinbox.valueChanged.connect(self._on_days_changed)

        self.btn_refresh_all = QtWidgets.QPushButton(_tr("Refresh All"))
        self.btn_refresh_all.setProperty("accent", "violet")
        self.btn_refresh_all.clicked.connect(self.refresh_data)
        _polish(self.btn_refresh_all)

        h.addWidget(self.period_label)
        h.addWidget(self.inventory_days_spinbox)
        h.addWidget(self.btn_refresh_all)
        root.addWidget(header_card)

        # ===== Splitter: Left (KPIs & Summary) | Right (Tables) =====
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(split, 1)

        # ----- LEFT COLUMN -----
        left = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(left); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(12)

        # KPI tiles grid (2x2)
        kpi_card = QtWidgets.QFrame(); kpi_card.setProperty("modernCard", True)
        kg = QtWidgets.QGridLayout(kpi_card)
        kg.setContentsMargins(12, 12, 12, 12); kg.setHorizontalSpacing(10); kg.setVerticalSpacing(10)

        def _make_kpi(title_text: str, accent: str):
            box = QtWidgets.QFrame()
            box.setProperty("kpiCard", True)
            box.setProperty("accent", accent)
            vb = QtWidgets.QVBoxLayout(box); vb.setContentsMargins(10, 10, 10, 10); vb.setSpacing(6)
            value = QtWidgets.QLabel("—"); value.setObjectName("KpiValue")
            value.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            title = QtWidgets.QLabel(title_text); title.setObjectName("KpiCaption")
            title.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            vb.addWidget(value); vb.addWidget(title)
            return box, value

        self.kpi_total_clients_card,     self.kpi_total_clients_value     = _make_kpi(_tr("Total Clients"),     "primary")
        self.kpi_total_revenue_card,     self.kpi_total_revenue_value     = _make_kpi(_tr("Total Revenue"),     "teal")
        self.kpi_total_outstanding_card, self.kpi_total_outstanding_value = _make_kpi(_tr("Total Outstanding"), "warning")
        self.kpi_unpaid_clients_card,    self.kpi_unpaid_clients_value    = _make_kpi(_tr("Unpaid Clients"),    "danger")

        kg.addWidget(self.kpi_total_clients_card,     0, 0)
        kg.addWidget(self.kpi_total_revenue_card,     0, 1)
        kg.addWidget(self.kpi_total_outstanding_card, 1, 0)
        kg.addWidget(self.kpi_unpaid_clients_card,    1, 1)
        l.addWidget(kpi_card)

        # Inventory / Period summary
        inv_card = QtWidgets.QFrame(); inv_card.setProperty("modernCard", True)
        ily = QtWidgets.QVBoxLayout(inv_card); ily.setContentsMargins(12, 12, 12, 12); ily.setSpacing(8)

        self.inventory_title = QtWidgets.QLabel(_tr("Inventory Summary"))
        self.inventory_title.setStyleSheet("font-weight: 700;")
        ily.addWidget(self.inventory_title)

        self.current_inventory_label = QtWidgets.QLabel(_tr("Loading inventory summary..."))
        self.current_inventory_label.setStyleSheet("font-weight: 600;")
        ily.addWidget(self.current_inventory_label)

        il_actions = QtWidgets.QHBoxLayout(); il_actions.setSpacing(8)

        self.show_unpaid_btn = QtWidgets.QPushButton(_tr("Show Unpaid Clients"))
        self.show_unpaid_btn.setProperty("variant", "danger")
        self.show_unpaid_btn.clicked.connect(self.show_unpaid_clients)

        self.archive_button = QtWidgets.QPushButton(_tr("Archive Inventory"))
        self.archive_button.setProperty("variant", "warning")
        self.archive_button.clicked.connect(self.archive_current_period)

        il_actions.addWidget(self.show_unpaid_btn)
        il_actions.addStretch(1)
        il_actions.addWidget(self.archive_button)
        _polish(self.show_unpaid_btn, self.archive_button)

        ily.addLayout(il_actions)
        l.addWidget(inv_card)
        l.addStretch(1)
        split.addWidget(left)

        # ----- RIGHT COLUMN -----
        right = QtWidgets.QWidget()
        r = QtWidgets.QVBoxLayout(right); r.setContentsMargins(0, 0, 0, 0); r.setSpacing(12)

        # Outstanding card with search/filter + table
        out_card = QtWidgets.QFrame(); out_card.setProperty("modernCard", True)
        og = QtWidgets.QVBoxLayout(out_card); og.setContentsMargins(12, 12, 12, 12); og.setSpacing(8)

        out_top = QtWidgets.QHBoxLayout(); out_top.setSpacing(8)
        out_title = QtWidgets.QLabel(_tr("Outstanding Payments"))
        out_title.setStyleSheet("font-weight: 700;")
        out_top.addWidget(out_title); out_top.addStretch(1)

        self.search_line = QtWidgets.QLineEdit(); self.search_line.setPlaceholderText(_tr("Search by name…"))
        self.search_line.textChanged.connect(self._apply_outstanding_filters)
        out_top.addWidget(self.search_line)

        self.min_out_spin = QtWidgets.QDoubleSpinBox()
        self.min_out_spin.setRange(0.0, 10_000_000.0); self.min_out_spin.setDecimals(2)
        self.min_out_spin.setPrefix(_tr("Min: "))
        self.min_out_spin.valueChanged.connect(self._apply_outstanding_filters)
        out_top.addWidget(self.min_out_spin)

        self.refresh_outstanding_btn = QtWidgets.QPushButton(_tr("Refresh"))
        self.refresh_outstanding_btn.setProperty("accent", "violet")
        self.refresh_outstanding_btn.clicked.connect(self.refresh_data)
        _polish(self.refresh_outstanding_btn)
        out_top.addWidget(self.refresh_outstanding_btn)
        og.addLayout(out_top)

        # quick summary line
        self.outstanding_label = QtWidgets.QLabel(_tr("Loading outstanding payments..."))
        self.outstanding_label.setStyleSheet("font-weight: 600;")
        og.addWidget(self.outstanding_label)

        self.outstanding_table = QtWidgets.QTableWidget()
        self.outstanding_table.setColumnCount(4)
        sym = _sym(self._currency)
        self.outstanding_table.setHorizontalHeaderLabels([
            _tr("Name"),
            f"{_tr('Total Amount')} ({sym})",
            f"{_tr('Total Paid')} ({sym})",
            f"{_tr('Outstanding')} ({sym})"
        ])
        self.outstanding_table.horizontalHeader().setStretchLastSection(True)
        self.outstanding_table.verticalHeader().setVisible(False)
        self.outstanding_table.setAlternatingRowColors(True)
        self.outstanding_table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.outstanding_table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.outstanding_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.outstanding_table.customContextMenuRequested.connect(self._menu_outstanding)
        self.outstanding_table.setSortingEnabled(True)
        og.addWidget(self.outstanding_table, 2)
        r.addWidget(out_card, 2)

        # Archive card (history)
        arch_card = QtWidgets.QFrame(); arch_card.setProperty("modernCard", True)
        ag = QtWidgets.QVBoxLayout(arch_card); ag.setContentsMargins(12, 12, 12, 12); ag.setSpacing(8)

        arch_top = QtWidgets.QHBoxLayout(); arch_top.setSpacing(8)
        arch_title = QtWidgets.QLabel(_tr("Archived Inventory"))
        arch_title.setStyleSheet("font-weight: 700;")
        arch_top.addWidget(arch_title); arch_top.addStretch(1)

        self.btn_open_archive = QtWidgets.QPushButton(_tr("Open Archive Folder"))
        self.btn_open_archive.setProperty("accent", "sky")
        self.btn_open_archive.clicked.connect(self._open_archive_folder)
        _polish(self.btn_open_archive)
        arch_top.addWidget(self.btn_open_archive)

        ag.addLayout(arch_top)

        self.archive_table = QtWidgets.QTableWidget()
        self.archive_table.setColumnCount(4)
        self.archive_table.setHorizontalHeaderLabels([
            _tr("Period"), _tr("Total Receipts"), _tr("Total Outstanding"), _tr("Unpaid Clients")
        ])
        self.archive_table.horizontalHeader().setStretchLastSection(True)
        self.archive_table.verticalHeader().setVisible(False)
        self.archive_table.setAlternatingRowColors(True)
        self.archive_table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.archive_table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.archive_table.setSortingEnabled(True)
        ag.addWidget(self.archive_table, 1)

        r.addWidget(arch_card, 1)
        split.addWidget(right)

        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)

        # ---- Apply glass-matched QSS for THIS TAB ----
        self.setStyleSheet(self._tab_qss())

        # ---- Shortcuts ----
        QtWidgets.QShortcut(QtGui.QKeySequence("F5"),              self, activated=self.refresh_data)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+E"),          self, activated=self._export_outstanding_csv)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+C"),          self, activated=self._copy_selected_row)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+F"),          self, activated=self.search_line.setFocus)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+E"),    self, activated=self._export_outstanding_csv)

        # ---- Persist column widths ----
        self.outstanding_table.horizontalHeader().sectionResized.connect(
            lambda *_: self._save_table_widths(self.outstanding_table, "dash/out_cols")
        )
        self.archive_table.horizontalHeader().sectionResized.connect(
            lambda *_: self._save_table_widths(self.archive_table, "dash/arc_cols")
        )
        QtCore.QTimer.singleShot(0, lambda: self._restore_table_widths(self.outstanding_table, "dash/out_cols"))
        QtCore.QTimer.singleShot(0, lambda: self._restore_table_widths(self.archive_table, "dash/arc_cols"))

    # ---------------- Tab QSS ----------------
    def _tab_qss(self) -> str:
        p = DS_COLORS
        return f"""
        QWidget {{ color: {p['text']}; font-family:'Segoe UI', Arial; font-size:14px; }}

        /* Cards */
        QFrame[modernCard="true"] {{
            background: {p['panel']};
            border: 1px solid rgba(255,255,255,0.45);
            border-radius: 12px;
        }}

        /* KPI tiles (accented left border) */
        QFrame[kpiCard="true"] {{
            background: {p['panelInner']};
            border: 1px solid {p['stroke']};
            border-radius: 12px;
            padding: 10px;
        }}
        QFrame[kpiCard="true"][accent="primary"] {{ border-left: 6px solid {p['primary']}; }}
        QFrame[kpiCard="true"][accent="teal"]    {{ border-left: 6px solid {p['info']};    }}
        QFrame[kpiCard="true"][accent="purple"]  {{ border-left: 6px solid {p['success']}; }}
        QFrame[kpiCard="true"][accent="danger"]  {{ border-left: 6px solid #ff6b6b;       }}
        QFrame[kpiCard="true"][accent="warning"] {{ border-left: 6px solid #f59e0b;       }}

        QLabel#KpiValue   {{ color:#0f172a; font:700 22px 'Segoe UI'; }}
        QLabel#KpiCaption {{ color:{p['muted']}; font:600 12px 'Segoe UI'; }}

        /* Inputs */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background: {p['inputBg']};
            color:#0f172a;
            border:1px solid #D6E4F5;
            border-radius:8px;
            padding:6px 10px;
            selection-background-color:{p['selBg']};
            selection-color:{p['selFg']};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {p['primary']};
            box-shadow: 0 0 0 2px rgba(58,141,255,0.18);
        }}

        /* Buttons */
        QPushButton {{
            border-radius:10px; padding:8px 14px; font-weight:600;
            border:1px solid transparent; background:{p['primary']}; color:white;
        }}
        QPushButton:hover {{ filter:brightness(1.05); }}
        QPushButton:pressed {{ filter:brightness(0.95); }}

        /* ghost-ish accent for presets */
        QPushButton[accent="slate"] {{
            background: rgba(255,255,255,0.85); color:#0F172A; border:1px solid #D6E4F5;
        }}
        QPushButton[accent="slate"]:hover {{ background: rgba(255,255,255,0.95); }}
        QPushButton[accent="slate"]:checked {{
            border:1px solid {p['primary']};
            box-shadow:0 0 0 2px rgba(58,141,255,0.18);
        }}

        QPushButton[accent="violet"] {{ background:{p['success']}; color:white; }}
        QPushButton[accent="sky"]    {{ background:{p['primary']}; color:white; }}

        QPushButton[variant="danger"]  {{ background:#ef4444; color:white; }}
        QPushButton[variant="warning"] {{ background:#f59e0b; color:white; }}

        /* Tables */
        QHeaderView::section {{
            background: rgba(255,255,255,0.85);
            color:#334155;
            padding:8px 10px;
            border:0; border-bottom:1px solid {p['stroke']};
            font-weight:600;
        }}
        QTableWidget, QTableView {{
            background:{p['panelInner']};
            color:#0f172a;
            border:1px solid {p['stroke']};
            border-radius:10px;
            gridline-color:#E8EEF7;
            selection-background-color:{p['selBg']};
            selection-color:{p['selFg']};
        }}
        QTableView::item:!selected:alternate {{ background:{p['stripe']}; }}

        /* Scrollbars */
        QScrollBar:vertical {{ background:transparent; width:10px; margin:4px; }}
        QScrollBar::handle:vertical {{ background:rgba(58,141,255,0.55); min-height:28px; border-radius:6px; }}
        QScrollBar:horizontal {{ background:transparent; height:10px; margin:4px; }}
        QScrollBar::handle:horizontal {{ background:rgba(58,141,255,0.55); min-width:28px; border-radius:6px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}
        """

    # ---------------- Data / Logic ----------------
    def _on_days_changed(self, val: int):
        # update preset check state to match standard presets, or none for custom
        btn = self._preset_group.button(val)
        self._preset_group.blockSignals(True)
        for b in (self.btn_7d, self.btn_30d, self.btn_90d, self.btn_365d):
            b.setChecked(False)
        if btn:
            btn.setChecked(True)
        self._preset_group.blockSignals(False)

        self._persist_period(val)
        self.refresh_data()

    def _apply_preset_days(self, days: int):
        self.inventory_days_spinbox.blockSignals(True)
        self.inventory_days_spinbox.setValue(days)
        self.inventory_days_spinbox.blockSignals(False)
        self._persist_period(days)
        self.refresh_data()

    def _persist_period(self, days: int):
        self._session_settings.setValue("dashboard/days", int(days))

    def _load_persisted_period(self):
        val = self._session_settings.value("dashboard/days")
        try:
            days = int(val) if val is not None else 30
        except Exception:
            days = 30
        self.inventory_days_spinbox.setValue(days)
        btn = self._preset_group.button(days)
        if btn:
            btn.setChecked(True)
        else:
            for b in (self.btn_7d, self.btn_30d, self.btn_90d, self.btn_365d):
                b.setChecked(False)

    def refresh_data(self):
        clients = _load_all_clients_safe()
        self._all_clients_cache = list(clients)

        # Outstanding (overall)
        outstanding_clients = []
        for client in clients:
            total_amount = _to_float(client.get("Total Amount", 0))
            total_paid   = _to_float(client.get("Total Paid", 0))
            if total_paid < total_amount:
                outstanding_clients.append({
                    "Name": client.get("Name", "") or _tr("Unknown"),
                    "Total Amount": total_amount,
                    "Total Paid": total_paid,
                    "Outstanding": max(0.0, total_amount - total_paid)
                })
        self._outstanding_cache = outstanding_clients
        self._apply_outstanding_filters()

        # Period summary
        days = int(self.inventory_days_spinbox.value())
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        total_paid_period = 0.0
        total_outstanding_period = 0.0
        num_unpaid_period = 0

        for client in clients:
            date_obj = QDate.fromString(client.get("Date", ""), "dd-MM-yyyy")
            if date_obj.isValid() and start_date <= date_obj <= end_date:
                tp = _to_float(client.get("Total Paid", 0))
                ta = _to_float(client.get("Total Amount", 0))
                total_paid_period += tp
                if tp < ta:
                    total_outstanding_period += (ta - tp)
                    num_unpaid_period += 1

        period_label = f"{start_date.toString('dd-MM-yyyy')} {_tr('to')} {end_date.toString('dd-MM-yyyy')}"
        self.current_inventory_label.setText(
            f"{period_label} — {_tr('Total Receipts:')} {total_paid_period:,.2f} | "
            f"{_tr('Outstanding:')} {total_outstanding_period:,.2f} | "
            f"{_tr('Unpaid Clients:')} {num_unpaid_period}"
        )

        # Overall KPIs
        total_clients = len(clients)
        total_revenue = 0.0
        total_outstanding_all = 0.0
        total_unpaid = 0

        for client in clients:
            tp = _to_float(client.get("Total Paid", 0))
            ta = _to_float(client.get("Total Amount", 0))
            total_revenue += tp
            if tp < ta:
                total_outstanding_all += (ta - tp)
                total_unpaid += 1

        self._update_kpis(total_clients, total_revenue, total_outstanding_all, total_unpaid)

    def _update_kpis(self, total_clients: int, total_revenue: float, total_outstanding: float, unpaid_clients: int):
        self.kpi_total_clients_value.setText(f"{total_clients:,}")
        self.kpi_total_revenue_value.setText(f"{total_revenue:,.2f}")
        self.kpi_total_outstanding_value.setText(f"{total_outstanding:,.2f}")
        self.kpi_unpaid_clients_value.setText(f"{unpaid_clients:,}")

    def _apply_outstanding_filters(self):
        query = (self.search_line.text() or "").strip().lower()
        min_out = float(self.min_out_spin.value())
        data, total_out = [], 0.0
        for item in self._outstanding_cache:
            if query and query not in (item["Name"] or "").lower(): continue
            if item["Outstanding"] < min_out: continue
            data.append(item); total_out += item["Outstanding"]
        self.outstanding_label.setText(
            f"{_tr('Patients with outstanding payments:')} {len(data)} | "
            f"{_tr('Total Outstanding:')} {total_out:,.2f}"
        )
        self._populate_outstanding_table(data)

    def _populate_outstanding_table(self, data: List[Dict]):
        self.archive_table.clearSelection()
        self.outstanding_table.setRowCount(0)
        for row, item in enumerate(sorted(data, key=lambda x: x["Outstanding"], reverse=True)):
            self.outstanding_table.insertRow(row)
            it_name = QtWidgets.QTableWidgetItem(item["Name"])
            it_name.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            def _num_item(val: float):
                it = QtWidgets.QTableWidgetItem(f"{val:,.2f}")
                it.setData(QtCore.Qt.UserRole, float(val))
                it.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                return it
            self.outstanding_table.setItem(row, 0, it_name)
            self.outstanding_table.setItem(row, 1, _num_item(item["Total Amount"]))
            self.outstanding_table.setItem(row, 2, _num_item(item["Total Paid"]))
            self.outstanding_table.setItem(row, 3, _num_item(item["Outstanding"]))
        self.outstanding_table.sortItems(3, QtCore.Qt.DescendingOrder)

    # ---------------- Actions ----------------
    def show_unpaid_clients(self):
        days = int(self.inventory_days_spinbox.value())
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        unpaid_names = []
        clients = self._all_clients_cache or _load_all_clients_safe()
        for client in clients:
            date_obj = QDate.fromString(client.get("Date", ""), "dd-MM-yyyy")
            if date_obj.isValid() and start_date <= date_obj <= end_date:
                tp = _to_float(client.get("Total Paid", 0))
                ta = _to_float(client.get("Total Amount", 0))
                if tp < ta:
                    unpaid_names.append(client.get("Name", _tr("Unknown")))
        if unpaid_names:
            QtWidgets.QMessageBox.information(
                self, _tr("Unpaid Clients"),
                _tr("Clients with outstanding payments:\n") + "\n".join(unpaid_names)
            )
        else:
            QtWidgets.QMessageBox.information(
                self, _tr("Unpaid Clients"),
                _tr("All clients have fully paid in the selected period.")
            )

    def archive_current_period(self):
        days = int(self.inventory_days_spinbox.value())
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        period_label = f"{start_date.toString('dd-MM-yyyy')} {_tr('to')} {end_date.toString('dd-MM-yyyy')}"
        clients = self._all_clients_cache or _load_all_clients_safe()
        total_paid_period = 0.0
        total_outstanding_period = 0.0
        num_unpaid_period = 0
        for client in clients:
            date_obj = QDate.fromString(client.get("Date", ""), "dd-MM-yyyy")
            if date_obj.isValid() and start_date <= date_obj <= end_date:
                tp = _to_float(client.get("Total Paid", 0))
                ta = _to_float(client.get("Total Amount", 0))
                total_paid_period += tp
                if tp < ta:
                    total_outstanding_period += (ta - tp)
                    num_unpaid_period += 1
        period_summary = {
            "period": period_label,
            "total_receipts": total_paid_period,
            "total_outstanding": total_outstanding_period,
            "unpaid_clients": num_unpaid_period
        }
        archive = []
        if os.path.exists(ARCHIVE_FILE):
            try:
                with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                    archive = json.load(f)
            except Exception:
                archive = []
        updated = False
        for entry in archive:
            if entry.get("period") == period_label:
                entry.update(period_summary); updated = True; break
        if not updated: archive.append(period_summary)
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(archive, f, indent=4, ensure_ascii=False)
        self.load_archive()
        QtWidgets.QMessageBox.information(self, _tr("Archive"),
                                          _tr("Summary for ") + period_label + _tr(" archived successfully."))

    def load_archive(self):
        archive = []
        if os.path.exists(ARCHIVE_FILE):
            try:
                with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                    archive = json.load(f)
            except Exception:
                archive = []
        self.archive_table.setRowCount(0)
        for row, entry in enumerate(archive):
            self.archive_table.insertRow(row)
            period = entry.get("period", "")
            receipts = _to_float(entry.get("total_receipts", 0))
            outstanding = _to_float(entry.get("total_outstanding", 0))
            unpaid = int(entry.get("unpaid_clients", 0) or 0)
            it_period = QtWidgets.QTableWidgetItem(period)
            it_period.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            def _num(val: float):
                it = QtWidgets.QTableWidgetItem(f"{val:,.2f}")
                it.setData(QtCore.Qt.UserRole, float(val))
                it.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                return it
            it_unpaid = QtWidgets.QTableWidgetItem(str(unpaid))
            it_unpaid.setData(QtCore.Qt.UserRole, int(unpaid))
            it_unpaid.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
            self.archive_table.setItem(row, 0, it_period)
            self.archive_table.setItem(row, 1, _num(receipts))
            self.archive_table.setItem(row, 2, _num(outstanding))
            self.archive_table.setItem(row, 3, it_unpaid)
        self.archive_table.sortItems(0, QtCore.Qt.DescendingOrder)

    def _open_archive_folder(self):
        folder = os.path.dirname(ARCHIVE_FILE)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))

    # ---------------- Table context menu / utilities ----------------
    def _menu_outstanding(self, pos: QtCore.QPoint):
        idx = self.outstanding_table.indexAt(pos)
        menu = QtWidgets.QMenu(self)
        act_export = menu.addAction(_tr("Export to CSV…"))
        act_copy   = menu.addAction(_tr("Copy selected row"))
        menu.addSeparator()
        act_refresh = menu.addAction(_tr("Refresh"))
        act = menu.exec_(self.outstanding_table.viewport().mapToGlobal(pos))
        if act == act_export:
            self._export_outstanding_csv()
        elif act == act_copy:
            self._copy_selected_row()
        elif act == act_refresh:
            self.refresh_data()

    def _selected_outstanding_row_values(self) -> List[str]:
        sm = self.outstanding_table.selectionModel()
        if not sm or not sm.hasSelection():
            return []
        r = sm.selectedRows()[0].row()
        vals = []
        for c in range(self.outstanding_table.columnCount()):
            it = self.outstanding_table.item(r, c)
            vals.append("" if it is None else it.text())
        return vals

    def _copy_selected_row(self):
        vals = self._selected_outstanding_row_values()
        if not vals:
            QtWidgets.QMessageBox.information(self, _tr("Copy"), _tr("Select a row first."))
            return
        QtWidgets.QApplication.clipboard().setText("\t".join(vals))
        self.outstanding_label.setText(_tr("Copied selected row to clipboard."))

    def _export_outstanding_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, _tr("Export CSV"), "outstanding.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                headers = [self.outstanding_table.horizontalHeaderItem(i).text()
                           for i in range(self.outstanding_table.columnCount())]
                w.writerow(headers)
                for r in range(self.outstanding_table.rowCount()):
                    row_vals = []
                    for c in range(self.outstanding_table.columnCount()):
                        it = self.outstanding_table.item(r, c)
                        row_vals.append("" if it is None else it.text())
                    w.writerow(row_vals)
            QtWidgets.QMessageBox.information(self, _tr("Export"), _tr("Exported to: ") + path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Export"), _tr("Error: ") + str(e))

    # ---------------- Column width persistence ----------------
    def _save_table_widths(self, table: QtWidgets.QTableWidget, key: str):
        s = self._settings()
        s.setValue(key, [table.columnWidth(c) for c in range(table.columnCount())])

    def _restore_table_widths(self, table: QtWidgets.QTableWidget, key: str):
        s = self._settings()
        widths = s.value(key)
        if isinstance(widths, list) and len(widths) == table.columnCount():
            for c, w in enumerate(widths):
                try: table.setColumnWidth(c, int(w))
                except Exception: pass

    def _settings(self):
        return QtCore.QSettings("YourOrg", "MedicalDocAI Demo v1.9.3")

    # ---------------- i18n refresh ----------------
    def retranslateUi(self):
        self.title.setText(_tr("Practice Dashboard"))
        for b, label in [(self.btn_7d, "7d"), (self.btn_30d, "30d"), (self.btn_90d, "90d"), (self.btn_365d, "365d")]:
            b.setText(_tr(label))
        self.period_label.setText(_tr("Days:"))
        self.btn_refresh_all.setText(_tr("Refresh All"))

        self.inventory_title.setText(_tr("Inventory Summary"))
        self.current_inventory_label.setText(_tr("Loading inventory summary..."))
        self.show_unpaid_btn.setText(_tr("Show Unpaid Clients"))
        self.archive_button.setText(_tr("Archive Inventory"))

        self.outstanding_label.setText(_tr("Loading outstanding payments..."))
        sym = _sym(self._currency)
        self.outstanding_table.setHorizontalHeaderLabels([
            _tr("Name"),
            f"{_tr('Total Amount')} ({sym})",
            f"{_tr('Total Paid')} ({sym})",
            f"{_tr('Outstanding')} ({sym})"
        ])
        self.refresh_outstanding_btn.setText(_tr("Refresh"))

        self.btn_open_archive.setText(_tr("Open Archive Folder"))
        self.archive_table.setHorizontalHeaderLabels([
            _tr("Period"), _tr("Total Receipts"), _tr("Total Outstanding"), _tr("Unpaid Clients")
        ])


# ---- standalone run ----
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        from UI.design_system import apply_global_theme, apply_window_backdrop
        apply_global_theme(app, base_point_size=11)
    except Exception:
        pass
    w = DashboardTab()
    w.resize(1100, 760)
    w.show()
    try:
        from UI.design_system import apply_window_backdrop
        apply_window_backdrop(w, prefer_mica=True)
    except Exception:
        pass
    sys.exit(app.exec_())
