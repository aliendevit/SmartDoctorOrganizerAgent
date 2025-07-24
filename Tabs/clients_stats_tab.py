# client_stats_tab.py  — Glass-matched Client Analytics tab
from __future__ import annotations
import csv
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

from PyQt5 import QtWidgets, QtCore, QtGui

# ---------- i18n ----------
def _tr(s: str) -> str:
    try:
        from features.translation_helper import tr
        return tr(s)
    except Exception:
        return s

# ---------- data layer (safe) ----------
try:
    from data.data import load_all_clients, load_appointments
except Exception:
    def load_all_clients() -> List[Dict]: return []
    def load_appointments() -> List[Dict]: return []

# ---------- design tokens (from global theme, with safe fallback) ----------
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

# ---------- optional matplotlib ----------
_HAS_MPL = False
try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    _HAS_MPL = True
except Exception:
    pass

def _apply_mpl_glass_theme():
    if not _HAS_MPL:
        return
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.facecolor": (1, 1, 1, 0),
        "savefig.facecolor": (1, 1, 1, 0),
        "axes.facecolor": (1, 1, 1, 0),
        "axes.edgecolor": DS_COLORS["textDim"],
        "axes.labelcolor": DS_COLORS["textDim"],
        "xtick.color": DS_COLORS["textDim"],
        "ytick.color": DS_COLORS["textDim"],
        "grid.color": DS_COLORS["stroke"],
        "grid.linestyle": "-",
        "grid.alpha": 0.85,
        "axes.grid": True,
        "text.color": "#111827",
        "legend.frameon": False,
    })

# ---------- clinical config ----------
_RED_FLAG_TERMS = {
    "severe chest pain","shortness of breath","vision loss","worst headache",
    "stroke","facial droop","weakness one side","uncontrolled bleeding",
    "anaphylaxis","airway compromise","loss of consciousness"
}

# ---------- helpers ----------
def _to_date(d: str) -> Optional[datetime.date]:
    if not d:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(d.strip(), fmt).date()
        except Exception:
            pass
    return None

def _to_float(x) -> float:
    try:
        if x is None: return 0.0
        s = str(x).replace(",", "").strip()
        return float(s) if s else 0.0
    except Exception:
        return 0.0

def _has_red_flags(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in _RED_FLAG_TERMS)

def _desktop_path() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop")

def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

# ---------- Styled mini table ----------
class _MiniTable(QtWidgets.QTableWidget):
    def __init__(self, cols, headers, parent=None):
        super().__init__(0, cols, parent)
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)

    def populate(self, rows: List[Tuple]):
        self.setSortingEnabled(False)
        self.setRowCount(0)
        for r, row in enumerate(rows or []):
            self.insertRow(r)
            for c, val in enumerate(row):
                it = QtWidgets.QTableWidgetItem("" if val is None else str(val))
                if isinstance(val, (int, float)):
                    it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.setItem(r, c, it)
        self.setSortingEnabled(True)
        self.resizeColumnsToContents()

# ---------- KPI Card ----------
class KPIBox(QtWidgets.QFrame):
    """
    Glassy KPI tile. Uses properties so QSS (below) paints accents consistently:
      - setProperty('kpiCard', True)
      - setProperty('accent', 'primary'|'teal'|'purple'|'danger'|'warning')
    """
    def __init__(self, title: str, value: str, hint: str = "", accent="primary", parent=None):
        super().__init__(parent)
        self.setProperty("kpiCard", True)
        self.setProperty("accent", {
            "info": "teal", "success": "purple",  # backwards-compat accents
            "warning": "warning", "danger": "danger", "violet": "purple"
        }.get(accent, accent))

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 14); v.setSpacing(6)

        self.title = QtWidgets.QLabel(title);  self.title.setObjectName("KpiTitle")
        self.value = QtWidgets.QLabel(value);  self.value.setObjectName("KpiValue")
        self.hint  = QtWidgets.QLabel(hint);   self.hint.setObjectName("KpiCaption")

        self.value.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        v.addWidget(self.title); v.addWidget(self.value, 1); v.addWidget(self.hint)

    def set(self, value: str, hint: Optional[str] = None):
        self.value.setText(value)
        if hint is not None: self.hint.setText(hint or "")

# ---------- Cohorts container ----------
@dataclass
class _Cohorts:
    upcoming: List[Tuple[str,str,str]]
    overdue:  List[Tuple[str,int,str]]
    balances: List[Tuple[str,float,float]]
    flags:    List[Tuple[str,str]]
    symptoms: List[Tuple[str,int]]

# ---------- Analytics Tab ----------
class ClientStatsTab(QtWidgets.QWidget):
    """
    • KPIs: patients, active +/-7d, overdue follow-ups, outstanding, avg A/R
    • Cohorts: upcoming (14d), overdue, highest balances, clinical flags
    • Filters: name contains, only balance>0
    • Optional charts (matplotlib if present)
    • CSV export of current cohorts (Desktop)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clients: List[Dict] = []
        self.appts:   List[Dict] = []
        self._build_ui()
        self.refresh_data()

    # ---------- UI ----------
    def _build_ui(self):
        _apply_mpl_glass_theme()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(10)

        # Header
        head = QtWidgets.QFrame(); head.setProperty("modernCard", True)
        h = QtWidgets.QHBoxLayout(head); h.setContentsMargins(12, 12, 12, 12); h.setSpacing(10)
        ttl = QtWidgets.QLabel(_tr("Patient Analytics")); ttl.setStyleSheet("font: 700 20pt 'Segoe UI';")
        sub = QtWidgets.QLabel(_tr("Operational KPIs and cohorts to guide your day"))
        sub.setStyleSheet(f"color:{DS_COLORS['muted']}; font-size:11pt;")
        left = QtWidgets.QVBoxLayout(); left.addWidget(ttl); left.addWidget(sub)
        h.addLayout(left)

        h.addStretch(1)
        self.filter_name = QtWidgets.QLineEdit(); self.filter_name.setPlaceholderText(_tr("Filter by patient name…"))
        self.filter_name.textChanged.connect(self._apply_filters)
        self.chk_balance = QtWidgets.QCheckBox(_tr("Only with balance > 0"))
        self.chk_balance.stateChanged.connect(self._apply_filters)
        h.addWidget(self.filter_name); h.addWidget(self.chk_balance)

        self.refresh_btn = QtWidgets.QPushButton(_tr("Refresh")); self.refresh_btn.setProperty("variant","info")
        self.refresh_btn.clicked.connect(self.refresh_data)
        h.addWidget(self.refresh_btn)
        _polish(self.refresh_btn)
        root.addWidget(head)

        # KPIs (use properties for accents)
        kpi_row = QtWidgets.QHBoxLayout()
        self.k_total   = KPIBox(_tr("Total Patients"), "—", "", accent="primary")
        self.k_active  = KPIBox(_tr("Active (±7d)"), "—", _tr("appt in last/next 7 days"), accent="teal")
        self.k_overdue = KPIBox(_tr("Overdue Follow-ups"), "—", accent="warning")
        self.k_balance = KPIBox(_tr("Outstanding Balance"), "—", accent="danger")
        self.k_ar      = KPIBox(_tr("Avg. A/R per Patient"), "—", accent="purple")
        for k in (self.k_total, self.k_active, self.k_overdue, self.k_balance, self.k_ar):
            kpi_row.addWidget(k)
        root.addLayout(kpi_row)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal); split.setChildrenCollapsible(False)
        split.setSizes([640, 560]); root.addWidget(split, 1)

        # DPI-safe GroupBox style (glassy)
        self._groupbox_css = self._make_groupbox_css()

        # LEFT column
        left = QtWidgets.QFrame(); left.setProperty("modernCard", True)
        lv = QtWidgets.QVBoxLayout(left); lv.setContentsMargins(12, 12, 12, 12); lv.setSpacing(10)

        self.tbl_due = _MiniTable(3, [_tr("Name"), _tr("Follow-Up Date"), _tr("Owed")])
        box1 = self._group(_tr("Upcoming (next 14 days)")); b1v = QtWidgets.QVBoxLayout(box1)
        b1v.setContentsMargins(16, 24, 16, 12); b1v.addWidget(self.tbl_due)

        self.tbl_over = _MiniTable(3, [_tr("Name"), _tr("Days Overdue"), _tr("Owed")])
        box2 = self._group(_tr("Overdue Follow-ups")); b2v = QtWidgets.QVBoxLayout(box2)
        b2v.setContentsMargins(10, 18, 10, 10); b2v.addWidget(self.tbl_over)

        self.tbl_bal = _MiniTable(3, [_tr("Name"), _tr("Owed"), _tr("Total Amt")])
        self.tbl_bal.doubleClicked.connect(self._focus_name_from_balances)
        box3 = self._group(_tr("Highest Balances")); b3v = QtWidgets.QVBoxLayout(box3)
        b3v.setContentsMargins(10, 18, 10, 10); b3v.addWidget(self.tbl_bal)

        self.tbl_flags = _MiniTable(2, [_tr("Name"), _tr("Reason")])
        box4 = self._group(_tr("Clinical Risk Flags")); b4v = QtWidgets.QVBoxLayout(box4)
        b4v.setContentsMargins(10, 18, 10, 10); b4v.addWidget(self.tbl_flags)

        # Export row
        export_row = QtWidgets.QHBoxLayout()
        self.btn_export = QtWidgets.QPushButton(_tr("Export Cohorts (CSV)")); self.btn_export.setProperty("variant","ghost")
        self.btn_export.clicked.connect(self._export_csv)
        export_row.addStretch(1); export_row.addWidget(self.btn_export)
        _polish(self.btn_export)

        for w in (box1, box2, box3, box4):
            lv.addWidget(w)
        lv.addLayout(export_row)
        split.addWidget(left)

        # RIGHT column
        right = QtWidgets.QFrame(); right.setProperty("modernCard", True)
        rv = QtWidgets.QVBoxLayout(right); rv.setContentsMargins(12, 12, 12, 12); rv.setSpacing(10)

        self.tbl_symptoms = _MiniTable(2, [_tr("Symptom"), _tr("Count")])
        sym_box = self._group(_tr("Top Symptoms")); sv = QtWidgets.QVBoxLayout(sym_box)
        sv.setContentsMargins(10, 18, 10, 10); sv.addWidget(self.tbl_symptoms)
        rv.addWidget(sym_box)

        if _HAS_MPL:
            charts = self._group(_tr("Trends")); cv = QtWidgets.QVBoxLayout(charts)
            cv.setContentsMargins(10, 18, 10, 10)
            self.fig = Figure(figsize=(5, 3), tight_layout=True)
            self.canvas = FigureCanvas(self.fig)
            # transparent canvas styling
            try:
                self.canvas.setStyleSheet("background: transparent;")
                self.fig.patch.set_alpha(0.0)
            except Exception:
                pass
            cv.addWidget(self.canvas)
            rv.addWidget(charts)
        else:
            note = QtWidgets.QLabel(_tr("Install matplotlib to see trend charts."))
            note.setStyleSheet(f"color:{DS_COLORS['muted']};")
            rv.addWidget(note)

        split.addWidget(right)

        self.status = QtWidgets.QLabel(""); root.addWidget(self.status)

        # Apply glass-matched QSS for THIS TAB ONLY
        self.setStyleSheet(self._tab_qss())

    # ---------- QSS builders ----------
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

        /* KPI tiles */
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

        QLabel#KpiTitle   {{ color:#0f172a; font:600 11pt "Segoe UI"; }}
        QLabel#KpiValue   {{ color:#0f172a; font:700 24pt "Segoe UI"; }}
        QLabel#KpiCaption {{ color:{p['muted']};    font:10pt "Segoe UI"; }}

        /* Group headers and tables */
        QHeaderView::section {{
            background: rgba(255,255,255,0.85);
            color: #334155;
            padding: 8px 10px;
            border: 0; border-bottom: 1px solid {p['stroke']};
            font-weight: 600;
        }}
        QTableWidget, QTableView {{
            background: {p['panelInner']};
            color: #0f172a;
            border: 1px solid {p['stroke']};
            border-radius: 10px;
            gridline-color: #E8EEF7;
            selection-background-color: {p['selBg']};
            selection-color: {p['selFg']};
        }}
        QTableView::item:!selected:alternate {{ background: {p['stripe']}; }}

        /* Inputs & buttons in header */
        QLineEdit {{
            background: {p['inputBg']}; color:#0f172a; border:1px solid #D6E4F5;
            border-radius:8px; padding:6px 10px;
            selection-background-color:{p['selBg']}; selection-color:white;
        }}
        QLineEdit:focus {{
            border:1px solid {p['primary']};
            box-shadow:0 0 0 2px rgba(58,141,255,0.18);
        }}
        QCheckBox {{ color:#0f172a; }}

        QPushButton {{
            border-radius: 10px; padding: 8px 14px; font-weight: 600; border: 1px solid transparent;
            background: {p['primary']}; color: white;
        }}
        QPushButton:hover {{ filter: brightness(1.05); }}
        QPushButton:pressed {{ filter: brightness(0.95); }}

        QPushButton[variant="ghost"] {{
            background: rgba(255,255,255,0.85); color: #0F172A; border: 1px solid #D6E4F5;
        }}
        QPushButton[variant="ghost"]:hover {{ background: rgba(255,255,255,0.95); }}

        QPushButton[variant="info"]    {{ background: {p['info']};    color:white; }}
        QPushButton[variant="success"] {{ background: {p['success']}; color:white; }}

        /* Scrollbars */
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
        QScrollBar::handle:vertical {{ background: rgba(58,141,255,0.55); min-height: 28px; border-radius: 6px; }}
        QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 4px; }}
        QScrollBar::handle:horizontal {{ background: rgba(58,141,255,0.55); min-width: 28px; border-radius: 6px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        """

    def _make_groupbox_css(self) -> str:
        # Glassy group boxes with DPI-safe title area
        fm = QtGui.QFontMetrics(self.font())
        title_h = fm.height()
        margin_top = title_h + 12
        p = DS_COLORS
        return f"""
        QGroupBox {{
            color:#0f172a; border:1px solid {p['stroke']}; border-radius:10px;
            margin-top:{margin_top}px; background:{p['panelInner']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; subcontrol-position: top left;
            left:16px; top:2px; padding:0 10px;
            color:#0f172a; background:{p['panelInner']}; font-weight:600;
        }}
        """

    def _group(self, title: str) -> QtWidgets.QGroupBox:
        gb = QtWidgets.QGroupBox(title); gb.setStyleSheet(self._groupbox_css); return gb

    # ---------- data / filters ----------
    def refresh_data(self):
        self.clients = load_all_clients() or []
        self.appts   = load_appointments() or []
        self._recompute()
        self._apply_filters()

    def _recompute(self):
        today = datetime.today().date()
        outstanding_sum = 0.0
        ar_values: List[float] = []
        upcoming: List[Tuple[str,str,str]] = []
        overdue:  List[Tuple[str,int,str]] = []
        balances: List[Tuple[str,float,float]] = []
        flags:    List[Tuple[str,str]] = []
        symptoms: Dict[str,int] = {}

        # active ±7d from appointments
        active_names = set()
        week = timedelta(days=7)
        for a in self.appts:
            nm = (a.get("Name") or "").strip()
            d  = _to_date(a.get("Appointment Date") or a.get("Date"))
            if not nm or not d: continue
            if abs(d - today) <= week:
                active_names.add(nm)

        for c in self.clients:
            name = (c.get("Name") or "").strip() or "Unknown"
            owed = max(0.0, _to_float(c.get("Owed")))
            tot  = max(0.0, _to_float(c.get("Total Amount")))
            outstanding_sum += owed
            ar_values.append(owed)
            balances.append((name, round(owed, 2), round(tot, 2)))

            fu = _to_date(c.get("Follow-Up Date"))
            if fu:
                if fu >= today and (fu - today).days <= 14:
                    upcoming.append((name, fu.strftime("%d-%m-%Y"), f"{owed:.2f}"))
                elif fu < today:
                    overdue.append((name, (today - fu).days, f"{owed:.2f}"))

            for s in (c.get("Symptoms") or []):
                s2 = (s or "").strip().lower()
                if s2: symptoms[s2] = symptoms.get(s2, 0) + 1

            if _has_red_flags(c.get("Notes", "")):
                flags.append((name, _tr("Red-flag in notes")))

        upcoming.sort(key=lambda r: _to_date(r[1]) or today)
        overdue.sort(key=lambda r: r[1], reverse=True)
        balances.sort(key=lambda r: r[1], reverse=True)
        flags.sort(key=lambda r: r[0])

        total_patients = len(self.clients)
        active_7d = len(active_names)
        avg_ar = (sum(ar_values)/len(ar_values)) if ar_values else 0.0

        # KPIs
        self.k_total.set(str(total_patients))
        self.k_active.set(str(active_7d), _tr("appt in last/next 7 days"))
        self.k_overdue.set(str(len(overdue)))
        self.k_balance.set(f"{outstanding_sum:,.2f}")
        self.k_ar.set(f"{avg_ar:,.2f}")

        # stash cohorts
        self._cohorts = _Cohorts(
            upcoming=upcoming, overdue=overdue,
            balances=balances, flags=flags,
            symptoms=sorted(symptoms.items(), key=lambda kv: kv[1], reverse=True)
        )

        # charts
        if _HAS_MPL:
            self._draw_charts()

        self.status.setText(_tr("Updated: {0} patients, {1} appointments").format(len(self.clients), len(self.appts)))

    def _apply_filters(self):
        name_q = (self.filter_name.text() or "").strip().lower()
        only_bal = self.chk_balance.isChecked()

        def keep_name(nm: str) -> bool:
            if not name_q: return True
            return name_q in (nm or "").lower()

        up = [(n,d,o) for (n,d,o) in self._cohorts.upcoming if keep_name(n) and (not only_bal or _to_float(o) > 0)]
        ov = [(n,dd,o) for (n,dd,o) in self._cohorts.overdue  if keep_name(n) and (not only_bal or _to_float(o) > 0)]
        hb = [(n,o,t) for (n,o,t) in self._cohorts.balances  if keep_name(n) and (not only_bal or o > 0.0)]
        fl = [(n,r)   for (n,r)   in self._cohorts.flags     if keep_name(n)]

        self.tbl_due.populate(up[:100])
        self.tbl_over.populate(ov[:100])
        self.tbl_bal.populate(hb[:100])
        self.tbl_flags.populate(fl[:100])
        self.tbl_symptoms.populate(self._cohorts.symptoms[:30])

    # ---------- charts ----------
    def _draw_charts(self):
        self.fig.clear()
        ax1 = self.fig.add_subplot(1, 2, 1)
        ax2 = self.fig.add_subplot(1, 2, 2)

        # owed distribution
        vals = [_to_float(c.get("Owed")) for c in self.clients]
        if vals:
            bins = min(20, max(5, int(math.sqrt(len(vals)))))
            ax1.hist(vals, bins=bins)
        ax1.set_title(_tr("Owed Distribution"))
        ax1.set_xlabel(_tr("Amount")); ax1.set_ylabel(_tr("Patients"))

        # appts per week (last 8w)
        today = datetime.today().date()
        start = today - timedelta(days=7*8)
        week_buckets: Dict[str,int] = {}
        for a in self.appts:
            d = _to_date(a.get("Appointment Date") or a.get("Date"))
            if not d or d < start: continue
            y, w, _ = d.isocalendar()
            key = f"{y}-W{w:02d}"
            week_buckets[key] = week_buckets.get(key, 0) + 1
        xs = sorted(week_buckets.keys())
        ys = [week_buckets[k] for k in xs]
        ax2.plot(range(len(xs)), ys, marker="o")
        ax2.set_xticks(range(len(xs))); ax2.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
        ax2.set_title(_tr("Appointments per Week")); ax2.set_ylabel(_tr("Count"))

        self.canvas.draw()

    # ---------- UX niceties ----------
    def _focus_name_from_balances(self, idx: QtCore.QModelIndex):
        if not idx.isValid(): return
        row = idx.row()
        nm = (self.tbl_bal.item(row, 0) or QtWidgets.QTableWidgetItem("")).text().strip()
        if nm:
            self.filter_name.setText(nm)

    def _export_csv(self):
        base = os.path.join(_desktop_path(), "cohorts_export.csv")
        try:
            with open(base, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["UPCOMING (next 14d)"]); w.writerow(["Name","Follow-Up Date","Owed"])
                for r in range(self.tbl_due.rowCount()):
                    w.writerow([self.tbl_due.item(r,0).text(), self.tbl_due.item(r,1).text(), self.tbl_due.item(r,2).text()])
                w.writerow([])
                w.writerow(["OVERDUE"]); w.writerow(["Name","Days Overdue","Owed"])
                for r in range(self.tbl_over.rowCount()):
                    w.writerow([self.tbl_over.item(r,0).text(), self.tbl_over.item(r,1).text(), self.tbl_over.item(r,2).text()])
                w.writerow([])
                w.writerow(["HIGHEST BALANCES"]); w.writerow(["Name","Owed","Total Amount"])
                for r in range(self.tbl_bal.rowCount()):
                    w.writerow([self.tbl_bal.item(r,0).text(), self.tbl_bal.item(r,1).text(), self.tbl_bal.item(r,2).text()])
                w.writerow([])
                w.writerow(["CLINICAL FLAGS"]); w.writerow(["Name","Reason"])
                for r in range(self.tbl_flags.rowCount()):
                    w.writerow([self.tbl_flags.item(r,0).text(), self.tbl_flags.item(r,1).text()])
            QtWidgets.QMessageBox.information(self, _tr("Export"), _tr("Saved to Desktop:\n") + base)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Export"), _tr("Failed to write CSV:\n") + str(e))

    # ---------- i18n ----------
    def retranslateUi(self):
        # rebuild with translated strings
        self._build_ui()
        self.refresh_data()

# ---- standalone run ----
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        # If you have the global theme, apply it
        from UI.design_system import apply_global_theme, apply_window_backdrop
        apply_global_theme(app, base_point_size=11)
    except Exception:
        pass
    w = ClientStatsTab()
    w.resize(1200, 760)
    w.show()
    try:
        from UI.design_system import apply_window_backdrop
        apply_window_backdrop(w, prefer_mica=True)
    except Exception:
        pass
    sys.exit(app.exec_())