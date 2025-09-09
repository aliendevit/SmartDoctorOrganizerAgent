# appointment_tab.py — Glass-matched Appointments (senior pass)

from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime
import csv
import os

# -------- design tokens (safe fallback) --------
try:
    from UI.design_system import COLORS as DS_COLORS
except Exception:
    DS_COLORS = {
        "text": "#1f2937", "textDim": "#334155", "muted": "#64748b",
        "primary": "#3A8DFF", "info": "#2CBBA6", "success": "#7A77FF",
        "danger": "#EF4444", "warning": "#F59E0B",
        "stroke": "#E5EFFA", "panel": "rgba(255,255,255,0.55)",
        "panelInner": "rgba(255,255,255,0.65)", "inputBg": "rgba(255,255,255,0.88)",
        "stripe": "rgba(240,247,255,0.65)", "selBg": "#3A8DFF", "selFg": "#ffffff",
    }

# -------- data backend (safe fallbacks) --------
try:
    from data.data import load_appointments, append_appointment, delete_appointment, save_appointments
except Exception:
    _STORE = []
    def load_appointments():
        return list(_STORE)
    def append_appointment(ap):
        key = (ap.get("Name",""), ap.get("Appointment Date",""), ap.get("Appointment Time",""))
        idx = next((i for i,a in enumerate(_STORE) if (a.get("Name",""),a.get("Appointment Date",""),a.get("Appointment Time",""))==key), -1)
        if idx >= 0: _STORE[idx] = dict(ap)
        else: _STORE.append(dict(ap))
        return True, list(_STORE)
    def delete_appointment(name, date, time):
        global _STORE
        _STORE = [a for a in _STORE if (a.get("Name",""),a.get("Appointment Date",""),a.get("Appointment Time",""))!=(name,date,time)]
    def save_appointments(rows):
        global _STORE
        _STORE = list(rows or [])

# -------- small utils --------
def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

def _tr(text: str) -> str:
    try:
        from features.translation_helper import tr
        return tr(text)
    except Exception:
        return text

def _qdate_from_str(s: str) -> QtCore.QDate:
    for fmt in ("dd-MM-yyyy", "yyyy-MM-dd"):
        d = QtCore.QDate.fromString((s or "").strip(), fmt)
        if d.isValid():
            return d
    return QtCore.QDate()

def _now_ddmmyyyy():
    return QtCore.QDate.currentDate().toString("dd-MM-yyyy")

def _boolish(val) -> bool:
    t = str(val).strip().lower()
    return t in ("true", "1", "yes", "on")

# -------- delegates --------
class StatusChipDelegate(QtWidgets.QStyledItemDelegate):
    """Paints status as a rounded chip (keeps selection highlight underneath)."""
    COLORS = {
        "Scheduled": ("#0b5394", "rgba(11,83,148,0.14)"),   # deep blue fg, soft bg
        "Completed": ("#166534", "rgba(22,101,52,0.14)"),
        "Canceled":  ("#b91c1c", "rgba(185,28,28,0.14)"),
        "No Show":   ("#92400e", "rgba(146,64,14,0.14)"),
    }
    def paint(self, painter, option, index):
        status = (index.data() or "").strip()
        if not status:
            return super().paint(painter, option, index)

        # Selection underlay to keep platform highlight behavior
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.save()
            painter.fillRect(option.rect, option.palette.highlight())
            painter.restore()

        fg, bg = self.COLORS.get(status, (DS_COLORS["textDim"], "rgba(0,0,0,0.08)"))
        painter.save()
        r = option.rect.adjusted(6, 6, -6, -6)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(r), 10, 10)
        painter.fillPath(path, QtGui.QColor(bg))
        pen = QtGui.QPen(QtGui.QColor(fg)); pen.setWidth(1)
        painter.setPen(pen); painter.drawPath(path)
        painter.setPen(QtGui.QColor(fg))
        f = option.font; f.setBold(True); painter.setFont(f)
        painter.drawText(r, QtCore.Qt.AlignCenter, status)
        painter.restore()

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QtCore.QSize(max(s.width(), 96), max(s.height(), 30))

class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    """Inline editor/painter for 'Remind' column."""
    def createEditor(self, parent, option, index):
        return QtWidgets.QCheckBox(parent)
    def setEditorData(self, editor, index):
        editor.setChecked(_boolish(index.data()))
    def setModelData(self, editor, model, index):
        model.setData(index, "True" if editor.isChecked() else "False")
    def paint(self, painter, option, index):
        checked = _boolish(index.data())
        cb = QtWidgets.QStyleOptionButton()
        cb.state |= QtWidgets.QStyle.State_Enabled
        cb.state |= (QtWidgets.QStyle.State_On if checked else QtWidgets.QStyle.State_Off)
        cb.rect = QtWidgets.QApplication.style().subElementRect(
            QtWidgets.QStyle.SE_CheckBoxIndicator, cb, None)
        cb.rect.moveCenter(option.rect.center())
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_CheckBox, cb, painter)

# -------- dialog --------
class AppointmentDialog(QtWidgets.QDialog):
    """Add/Edit appointment dialog with past-time confirmation."""
    def __init__(self, parent=None, data: dict=None):
        super().__init__(parent)
        self.setWindowTitle(_tr("Appointment"))
        self.setModal(True)
        self._data = dict(data or {})
        self._build()
        self._apply_style()

    def _build(self):
        f = QtWidgets.QFormLayout(self); f.setContentsMargins(12, 12, 12, 12); f.setSpacing(8)

        self.e_name = QtWidgets.QLineEdit(self._data.get("Name",""))
        self.e_date = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.e_date.setCalendarPopup(True); self.e_date.setDisplayFormat("dd-MM-yyyy")
        d = _qdate_from_str(self._data.get("Appointment Date",""))
        if d.isValid(): self.e_date.setDate(d)

        self.e_time = QtWidgets.QTimeEdit(QtCore.QTime.currentTime())
        self.e_time.setDisplayFormat("hh:mm AP")
        t_str = (self._data.get("Appointment Time","") or "").strip()
        if t_str:
            for fmt in ("%I:%M %p", "%H:%M"):
                try:
                    dt = datetime.strptime(t_str, fmt)
                    self.e_time.setTime(QtCore.QTime(dt.hour, dt.minute)); break
                except Exception: pass

        self.e_status = QtWidgets.QComboBox(); self.e_status.addItems(["Scheduled","Completed","Canceled","No Show"])
        cur = (self._data.get("Status") or "Scheduled"); i = self.e_status.findText(cur)
        if i >= 0: self.e_status.setCurrentIndex(i)

        self.e_notes = QtWidgets.QTextEdit(); self.e_notes.setFixedHeight(80)
        self.e_notes.setPlainText(self._data.get("Notes",""))
        self.e_remind = QtWidgets.QCheckBox(_tr("Remind me"))
        self.e_remind.setChecked(bool(self._data.get("Remind", False)))

        f.addRow(_tr("Name"), self.e_name)
        f.addRow(_tr("Date"), self.e_date)
        f.addRow(_tr("Time"), self.e_time)
        f.addRow(_tr("Status"), self.e_status)
        f.addRow(_tr("Notes"), self.e_notes)
        f.addRow("", self.e_remind)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        f.addRow(btns)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)

    def _apply_style(self):
        p = DS_COLORS
        self.setStyleSheet(f"""
        QDialog {{
            background:{p['panel']};
            border:1px solid rgba(255,255,255,0.45);
            border-radius:12px;
        }}
        QLabel {{ color:{p['text']}; }}
        QLineEdit, QComboBox, QTextEdit, QDateEdit, QTimeEdit {{
            background:{p['inputBg']}; color:#0f172a;
            border:1px solid {p['stroke']}; border-radius:8px; padding:6px 10px;
            selection-background-color:{p['selBg']}; selection-color:{p['selFg']};
        }}
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus {{
            border:1px solid {p['primary']};
        }}
        """)

    def _accept(self):
        if not self.e_name.text().strip():
            QtWidgets.QMessageBox.warning(self, _tr("Input"), _tr("Name is required.")); return
        dt_combined = QtCore.QDateTime(self.e_date.date(), self.e_time.time())
        if dt_combined < QtCore.QDateTime.currentDateTime():
            if QtWidgets.QMessageBox.question(self, _tr("Past Time"),
                    _tr("This appointment is in the past. Create/update anyway?")) != QtWidgets.QMessageBox.Yes:
                return
        self.accept()

    def data(self) -> dict:
        return {
            "Name": self.e_name.text().strip() or "Unknown",
            "Appointment Date": self.e_date.date().toString("dd-MM-yyyy"),
            "Appointment Time": self.e_time.time().toString("hh:mm AP"),
            "Status": self.e_status.currentText(),
            "Notes": self.e_notes.toPlainText().strip(),
            "Remind": self.e_remind.isChecked(),
        }

# -------- main tab --------
class AppointmentTab(QtWidgets.QWidget):
    C_NAME, C_DATE, C_TIME, C_STATUS, C_NOTES, C_REMIND = range(6)

    def __init__(self, parent=None, tray_icon: QtWidgets.QSystemTrayIcon=None):
        super().__init__(parent)
        self._tray = tray_icon
        self._rows = []
        self._filtered = []
        self._build()
        self._load_from_store()
        self._apply_filters()
        self._restore_column_widths()

    # ---- public hooks for main ----
    def set_tray_icon(self, tray_icon: QtWidgets.QSystemTrayIcon):
        self._tray = tray_icon

    def add_appointment(self, data: dict):
        appt = self._normalize(data)
        changed, stored_list = append_appointment(appt)
        self._rows = list(stored_list)
        self._apply_filters()
        if changed:
            self._notify(_tr("Appointment"),
                         _tr(f"Saved for {appt['Name']} on {appt['Appointment Date']} {appt['Appointment Time']}"))

    def highlight_client(self, client_name: str):
        name_l = (client_name or "").strip().lower()
        for r in range(self.table.rowCount()):
            it = self.table.item(r, self.C_NAME)
            if it and it.text().strip().lower() == name_l:
                self.table.clearSelection(); self.table.selectRow(r)
                self.table.scrollToItem(it, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

    # ---- build UI ----
    def _build(self):
        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16); root.setSpacing(12)

        # Header / controls
        bar = QtWidgets.QFrame(); bar.setProperty("modernCard", True)
        bh = QtWidgets.QHBoxLayout(bar); bh.setContentsMargins(12, 12, 12, 12); bh.setSpacing(8)

        title = QtWidgets.QLabel(_tr("Appointments")); title.setStyleSheet("font: 700 18pt 'Segoe UI';")
        bh.addWidget(title); bh.addSpacing(8)

        self.search = QtWidgets.QLineEdit(); self.search.setPlaceholderText(_tr("Search by name or note…"))
        self.search.setClearButtonEnabled(True); self.search.textChanged.connect(self._apply_filters)

        self.status_filter = QtWidgets.QComboBox()
        self.status_filter.addItems([_tr("All Status"), "Scheduled","Completed","Canceled","No Show"])
        self.status_filter.currentIndexChanged.connect(self._apply_filters)

        self.scope = QtWidgets.QComboBox()
        self.scope.addItems([_tr("All Dates"), _tr("Today"), _tr("Next 7 Days"), _tr("Past 7 Days")])
        self.scope.currentIndexChanged.connect(self._apply_filters)

        self.btn_refresh = QtWidgets.QPushButton(_tr("Refresh")); self.btn_refresh.setProperty("variant","ghost")
        self.btn_refresh.clicked.connect(self._reload)

        self.btn_export = QtWidgets.QPushButton(_tr("Export CSV")); self.btn_export.setProperty("variant","ghost")
        self.btn_export.clicked.connect(self._export_csv)

        self.btn_add = QtWidgets.QPushButton(_tr("Add…")); self.btn_add.setProperty("variant","success")
        self.btn_add.clicked.connect(self._add_dialog)

        for b in (self.btn_refresh, self.btn_export, self.btn_add):
            _polish(b)

        bh.addStretch(1)
        bh.addWidget(self.search)
        bh.addWidget(self.status_filter)
        bh.addWidget(self.scope)
        bh.addWidget(self.btn_refresh)
        bh.addWidget(self.btn_export)
        bh.addWidget(self.btn_add)
        root.addWidget(bar)

        # Table
        card = QtWidgets.QFrame(); card.setProperty("modernCard", True)
        v = QtWidgets.QVBoxLayout(card); v.setContentsMargins(12,12,12,12); v.setSpacing(8)

        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            _tr("Name"), _tr("Appointment Date"), _tr("Appointment Time"),
            _tr("Status"), _tr("Notes"), _tr("Remind")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.SelectedClicked)  # allow checkbox toggle
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_table)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._edit_selected)

        self.table.setItemDelegateForColumn(self.C_STATUS, StatusChipDelegate(self.table))
        self.table.setItemDelegateForColumn(self.C_REMIND, CheckBoxDelegate(self.table))

        # Persist column widths when user resizes
        self.table.horizontalHeader().sectionResized.connect(self._save_column_widths)

        v.addWidget(self.table)

        # Footer actions
        foot = QtWidgets.QHBoxLayout(); foot.setSpacing(8)
        self.btn_mark_done = QtWidgets.QPushButton(_tr("Mark Completed")); self.btn_mark_done.setProperty("variant","info")
        self.btn_mark_done.clicked.connect(lambda: self._bulk_status("Completed"))

        self.btn_cancel = QtWidgets.QPushButton(_tr("Mark Canceled")); self.btn_cancel.setProperty("variant","danger")
        self.btn_cancel.clicked.connect(lambda: self._bulk_status("Canceled"))

        self.btn_delete = QtWidgets.QPushButton(_tr("Delete Selected")); self.btn_delete.setProperty("variant","danger")
        self.btn_delete.clicked.connect(self._delete_selected)

        self.btn_save = QtWidgets.QPushButton(_tr("Save")); self.btn_save.setProperty("variant","success")
        self.btn_save.clicked.connect(self._save_all)

        foot.addWidget(self.btn_mark_done)
        foot.addWidget(self.btn_cancel)
        foot.addStretch(1)
        foot.addWidget(self.btn_delete)
        foot.addWidget(self.btn_save)
        for b in (self.btn_mark_done, self.btn_cancel, self.btn_delete, self.btn_save):
            _polish(b)

        v.addLayout(foot)
        root.addWidget(card)
        root.addStretch(1)

        # Apply glass QSS
        self.setStyleSheet(self._tab_qss())

        # Keyboard shortcuts (clinician quality-of-life)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+N"), self, activated=self._add_dialog)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self._save_all)
        QtWidgets.QShortcut(QtGui.QKeySequence("Delete"), self, activated=self._delete_selected)

    def _tab_qss(self) -> str:
        p = DS_COLORS
        return f"""
        QWidget {{ color:{p['text']}; font-family:'Segoe UI', Arial; font-size:14px; }}

        /* Cards */
        QFrame[modernCard="true"] {{
            background:{p['panel']};
            border:1px solid rgba(255,255,255,0.45);
            border-radius:12px;
        }}

        /* Inputs / selects */
        QLineEdit, QComboBox {{
            background:{p['inputBg']}; color:#0f172a;
            border:1px solid {p['stroke']}; border-radius:8px; padding:6px 10px;
            selection-background-color:{p['selBg']}; selection-color:{p['selFg']};
        }}
        QLineEdit:focus, QComboBox:focus {{
            border:1px solid {p['primary']};
            box-shadow:0 0 0 2px rgba(58,141,255,0.18);
        }}

        /* Buttons */
        QPushButton {{
            border-radius:10px; padding:8px 14px; font-weight:600;
            border:1px solid transparent; background:{p['primary']}; color:white;
        }}
        QPushButton:hover {{ filter:brightness(1.05); }}
        QPushButton:pressed {{ filter:brightness(0.95); }}
        QPushButton[variant="ghost"] {{
            background: rgba(255,255,255,0.85); color:#0F172A; border:1px solid {p['stroke']};
        }}
        QPushButton[variant="ghost"]:hover {{ background: rgba(255,255,255,0.95); }}
        QPushButton[variant="success"] {{ background:{p['success']}; color:white; }}
        QPushButton[variant="info"]    {{ background:{p['info']}; color:white; }}
        QPushButton[variant="danger"]  {{ background:{p['danger']}; color:white; }}

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

    # ---- data flow ----
    def _normalize(self, ap: dict) -> dict:
        out = dict(ap or {})
        out["Name"] = (out.get("Name") or "").strip() or "Unknown"
        d = (out.get("Appointment Date") or "").strip() or _now_ddmmyyyy()
        t = (out.get("Appointment Time") or "").strip() or "12:00 PM"
        out["Appointment Date"] = d
        out["Appointment Time"] = t
        out["Status"] = (out.get("Status") or "Scheduled").strip() or "Scheduled"
        out["Notes"] = out.get("Notes") or ""
        out["Remind"] = bool(out.get("Remind", False))
        if "created_at" not in out:
            out["created_at"] = datetime.now().isoformat(timespec="seconds")
        return out

    def _reload(self):
        self._load_from_store()
        self._apply_filters()

    def _load_from_store(self):
        try:
            self._rows = load_appointments() or []
        except Exception:
            self._rows = []

    def _apply_filters(self):
        q = (self.search.text() or "").strip().lower()
        status_sel = self.status_filter.currentText()
        scope = self.scope.currentText()

        today = QtCore.QDate.currentDate()
        start = QtCore.QDate(1900,1,1); end = QtCore.QDate(2999,12,31)
        if scope == _tr("Today"):
            start = end = today
        elif scope == _tr("Next 7 Days"):
            start = today; end = today.addDays(7)
        elif scope == _tr("Past 7 Days"):
            start = today.addDays(-7); end = today

        def _in_scope(date_str):
            d = _qdate_from_str(date_str)
            return d.isValid() and d >= start and d <= end

        rows = []
        for ap in self._rows:
            if q:
                hay = f"{ap.get('Name','')} {ap.get('Notes','')}".lower()
                if q not in hay:
                    continue
            if status_sel != _tr("All Status"):
                if (ap.get("Status") or "Scheduled") != status_sel:
                    continue
            if scope != _tr("All Dates") and not _in_scope(ap.get("Appointment Date","")):
                continue
            rows.append(ap)

        def _key(ap):
            d = _qdate_from_str(ap.get("Appointment Date",""))
            t = (ap.get("Appointment Time","") or "00:00")
            try:
                tm = datetime.strptime(t, "%I:%M %p").time()
            except Exception:
                try: tm = datetime.strptime(t, "%H:%M").time()
                except Exception: tm = datetime.strptime("00:00","%H:%M").time()
            return (d.isValid() and d.toPyDate() or datetime.max.date(), tm, ap.get("Name",""))

        rows.sort(key=_key)
        self._filtered = rows
        self._rebuild_table()

    def _rebuild_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for r, ap in enumerate(self._filtered):
            self.table.insertRow(r)
            def _it(val, center=False, editable=False):
                it = QtWidgets.QTableWidgetItem("" if val is None else str(val))
                it.setTextAlignment(QtCore.Qt.AlignCenter if center else QtCore.Qt.AlignVCenter|QtCore.Qt.AlignLeft)
                if editable:
                    it.setFlags(it.flags() | QtCore.Qt.ItemIsEditable)
                else:
                    it.setFlags(it.flags() & ~QtCore.Qt.ItemIsEditable)
                return it

            self.table.setItem(r, self.C_NAME,   _it(ap.get("Name","")))
            self.table.setItem(r, self.C_DATE,   _it(ap.get("Appointment Date",""), center=True))
            self.table.setItem(r, self.C_TIME,   _it(ap.get("Appointment Time",""), center=True))
            self.table.setItem(r, self.C_STATUS, _it(ap.get("Status",""), center=True))
            self.table.setItem(r, self.C_NOTES,  _it(ap.get("Notes","")))
            self.table.setItem(r, self.C_REMIND, _it("True" if bool(ap.get("Remind", False)) else "False", center=True, editable=True))
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def _save_all(self):
        updated = {}
        for r in range(self.table.rowCount()):
            name = (self.table.item(r, self.C_NAME)  or QtWidgets.QTableWidgetItem("")).text().strip()
            date = (self.table.item(r, self.C_DATE)  or QtWidgets.QTableWidgetItem("")).text().strip()
            time = (self.table.item(r, self.C_TIME)  or QtWidgets.QTableWidgetItem("")).text().strip()
            remi_item = self.table.item(r, self.C_REMIND)
            remi = False if remi_item is None else _boolish(remi_item.text())
            updated[(name, date, time)] = remi

        for ap in self._rows:
            key = (ap.get("Name","").strip(), ap.get("Appointment Date","").strip(), ap.get("Appointment Time","").strip())
            if key in updated:
                ap["Remind"] = updated[key]
        try:
            save_appointments(self._rows)
            QtWidgets.QMessageBox.information(self, _tr("Save"), _tr("Appointments saved."))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Save"), _tr("Error saving: ") + str(e))

    # ---- context menu / bulk ops ----
    def _menu_table(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid(): return
        menu = QtWidgets.QMenu(self)
        act_edit = menu.addAction(_tr("Edit…"))
        act_done = menu.addAction(_tr("Mark Completed"))
        act_cancel = menu.addAction(_tr("Mark Canceled"))
        menu.addSeparator()
        act_del = menu.addAction(_tr("Delete"))
        act = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if act == act_edit: self._edit_selected()
        elif act == act_done: self._bulk_status("Completed")
        elif act == act_cancel: self._bulk_status("Canceled")
        elif act == act_del: self._delete_selected()

    def _sel_row_key(self):
        idxs = self.table.selectionModel().selectedRows()
        if not idxs: return None
        r = idxs[0].row()
        return (r,
                (self.table.item(r, self.C_NAME) or QtWidgets.QTableWidgetItem("")).text(),
                (self.table.item(r, self.C_DATE) or QtWidgets.QTableWidgetItem("")).text(),
                (self.table.item(r, self.C_TIME) or QtWidgets.QTableWidgetItem("")).text())

    def _edit_selected(self):
        sel = self._sel_row_key()
        if not sel:
            QtWidgets.QMessageBox.information(self, _tr("Edit"), _tr("Select a row first.")); return
        r, name, date, time = sel
        ap = next((a for a in self._rows
                   if (a.get("Name","")==name and a.get("Appointment Date","")==date and a.get("Appointment Time","")==time)), None)
        if not ap:
            QtWidgets.QMessageBox.warning(self, _tr("Edit"), _tr("Could not find selected appointment.")); return
        dlg = AppointmentDialog(self, ap)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            new_ap = dlg.data()
            delete_appointment(name, date, time)
            append_appointment(new_ap)
            self._reload()
            self._notify(_tr("Appointment"),
                         _tr(f"Updated for {new_ap['Name']} on {new_ap['Appointment Date']} {new_ap['Appointment Time']}"))

    def _bulk_status(self, new_status: str):
        sel = self._sel_row_key()
        if not sel:
            QtWidgets.QMessageBox.information(self, _tr("Status"), _tr("Select a row first.")); return
        _, name, date, time = sel
        ap = next((a for a in self._rows
                   if a.get("Name","")==name and a.get("Appointment Date","")==date and a.get("Appointment Time","")==time), None)
        if not ap: return
        ap["Status"] = new_status
        try:
            save_appointments(self._rows)
            self._apply_filters()
            self._notify(_tr("Appointment"), _tr(f"Marked {new_status} for {name}."))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Status"), _tr("Error: ") + str(e))

    def _delete_selected(self):
        sel = self._sel_row_key()
        if not sel:
            QtWidgets.QMessageBox.information(self, _tr("Delete"), _tr("Select a row first.")); return
        _, name, date, time = sel
        if QtWidgets.QMessageBox.question(self, _tr("Delete"),
            _tr(f"Delete appointment for {name} on {date} {time}?")) == QtWidgets.QMessageBox.Yes:
            delete_appointment(name, date, time)
            self._reload()
            self._notify(_tr("Appointment"), _tr("Deleted."))

    def _add_dialog(self):
        dlg = AppointmentDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.add_appointment(dlg.data())

    # ---- export & notifications ----
    def _export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, _tr("Export CSV"), "appointments.csv", "CSV (*.csv)")
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Name","Appointment Date","Appointment Time","Status","Notes","Remind","Created At"])
                for ap in self._filtered:
                    w.writerow([
                        ap.get("Name",""),
                        ap.get("Appointment Date",""),
                        ap.get("Appointment Time",""),
                        ap.get("Status",""),
                        ap.get("Notes","").replace("\n"," ").strip(),
                        "True" if ap.get("Remind", False) else "False",
                        ap.get("created_at",""),
                    ])
            self._notify(_tr("Export"), _tr("CSV exported."))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Export"), _tr("Error: ") + str(e))

    def _notify(self, title: str, msg: str):
        try:
            if self._tray:
                self._tray.showMessage(title, msg, QtWidgets.QSystemTrayIcon.Information, 3000)
        except Exception:
            pass

    # ---- column width persistence ----
    def _settings(self):
        return QtCore.QSettings("YourOrg", "MedicalDocAI Demo v1.9.3")

    def _save_column_widths(self):
        s = self._settings()
        widths = [self.table.columnWidth(c) for c in range(self.table.columnCount())]
        s.setValue("appointments/col_widths", widths)

    def _restore_column_widths(self):
        s = self._settings()
        widths = s.value("appointments/col_widths")
        if isinstance(widths, list) and widths and len(widths) == self.table.columnCount():
            for c, w in enumerate(widths):
                try:
                    self.table.setColumnWidth(c, int(w))
                except Exception:
                    pass

# ---- standalone run ----
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        from UI.design_system import apply_global_theme, apply_window_backdrop
        apply_global_theme(app, base_point_size=11)
    except Exception:
        app.setStyle("Fusion")
    w = AppointmentTab()
    w.resize(1100, 720)
    w.show()
    try:
        from UI.design_system import apply_window_backdrop
        apply_window_backdrop(w, prefer_mica=True)
    except Exception:
        pass
    sys.exit(app.exec_())