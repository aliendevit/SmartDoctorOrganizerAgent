# appointment_tab.py
# Persisted appointments tab
# - Accepts optional tray_icon in __init__ (works with your main.py)
# - Loads persisted appointments on startup
# - add_appointment() writes to disk immediately (de-dupes by Name+Date+Time)
# - highlight_client(), set_tray_icon() provided for main.py hooks

from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime
from data.data import load_appointments, append_appointment, delete_appointment, save_appointments

from data.data import (
    load_appointments,
    append_appointment,
    delete_appointment,
    save_appointments,
)

def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

class AppointmentTab(QtWidgets.QWidget):
    def __init__(self, parent=None, tray_icon: QtWidgets.QSystemTrayIcon=None):
        super().__init__(parent)
        self._tray = tray_icon
        self._rows = []  # local cache (list of dicts)
        self._build()
        self._load_from_store()

    # translation passthrough
    def tr(self, text):
        try:
            from translation_helper import tr
            return tr(text)
        except Exception:
            return text

    # ---- UI ----
    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        hdr = QtWidgets.QFrame(); hdr.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(hdr); hly.setContentsMargins(12, 12, 12, 12)
        title = QtWidgets.QLabel(self.tr("Appointments"))
        title.setStyleSheet("font-size: 16pt; font-weight: 700;")
        hly.addWidget(title); hly.addStretch(1)
        self.btn_refresh = QtWidgets.QPushButton(self.tr("Refresh"))
        self.btn_refresh.setProperty("variant", "ghost"); self.btn_refresh.setProperty("accent", "sky")
        self.btn_refresh.clicked.connect(self._load_from_store)
        hly.addWidget(self.btn_refresh); _polish(self.btn_refresh)
        root.addWidget(hdr)

        # Table card
        card = QtWidgets.QFrame(); card.setProperty("modernCard", True)
        v = QtWidgets.QVBoxLayout(card); v.setContentsMargins(12, 12, 12, 12); v.setSpacing(8)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.tr("Name"),
            self.tr("Appointment Date"),
            self.tr("Appointment Time"),
            self.tr("Status"),
            self.tr("Notes"),
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        v.addWidget(self.table)

        # Actions
        aly = QtWidgets.QHBoxLayout(); aly.setSpacing(8)
        self.btn_add = QtWidgets.QPushButton(self.tr("Add…"))
        self.btn_add.setProperty("variant", "success")
        self.btn_add.clicked.connect(self._quick_add_dialog)

        self.btn_delete = QtWidgets.QPushButton(self.tr("Delete Selected"))
        self.btn_delete.setProperty("variant", "danger")
        self.btn_delete.clicked.connect(self._delete_selected)

        aly.addWidget(self.btn_add)
        aly.addStretch(1)
        aly.addWidget(self.btn_delete)
        _polish(self.btn_add, self.btn_delete)

        v.addLayout(aly)
        root.addWidget(card)
        root.addStretch(1)

    # ---- Public API (used by main.py / Extraction) ----
    def set_tray_icon(self, tray_icon: QtWidgets.QSystemTrayIcon):
        self._tray = tray_icon

    def add_appointment(self, data: dict):
        """
        Called by main.py (from Extraction) to add & persist.
        De-dupes by (Name, Date, Time). Normalizes blanks.
        """
        appt = self._normalize(data)

        # Write to storage (de-dupes inside)
        changed, stored_list = append_appointment(appt)

        # Update UI cache from store to stay consistent
        self._rows = list(stored_list)
        self._rebuild_table()

        # Toast
        if changed:
            self._notify(self.tr("Appointment"), self.tr(f"Saved for {appt['Name']} on {appt['Appointment Date']} {appt['Appointment Time']}"))

    def highlight_client(self, client_name: str):
        name_l = (client_name or "").strip().lower()
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it and it.text().strip().lower() == name_l:
                self.table.clearSelection()
                self.table.selectRow(r)
                self.table.scrollToItem(it, QtWidgets.QAbstractItemView.PositionAtCenter)
                # subtle highlight
                for c in range(self.table.columnCount()):
                    ci = self.table.item(r, c)
                    if ci:
                        ci.setBackground(QtGui.QColor("#fff3cd"))
                break

    # ---- Internals ----
    def _normalize(self, data: dict) -> dict:
        appt = dict(data or {})
        appt["Name"] = (appt.get("Name") or "").strip() or "Unknown"
        date = (appt.get("Appointment Date") or "").strip()
        time = (appt.get("Appointment Time") or "").strip()
        if not date or date.lower() == "not specified":
            date = QtCore.QDate.currentDate().toString("dd-MM-yyyy")
        if not time or time.lower() == "not specified":
            time = "12:00 PM"
        appt["Appointment Date"] = date
        appt["Appointment Time"] = time
        appt["Status"] = appt.get("Status") or "Scheduled"
        appt["Notes"] = appt.get("Notes") or ""
        if "created_at" not in appt:
            appt["created_at"] = datetime.now().isoformat(timespec="seconds")
        return appt

    def _rebuild_table(self):
        self.table.setRowCount(0)
        for row, ap in enumerate(self._rows):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(ap.get("Name","")))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(ap.get("Appointment Date","")))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(ap.get("Appointment Time","")))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(ap.get("Status","")))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(ap.get("Notes","")))

    def _notify(self, title: str, msg: str):
        try:
            if self._tray:
                self._tray.showMessage(title, msg, QtWidgets.QSystemTrayIcon.Information, 3000)
        except Exception:
            pass

    def _load_from_store(self):
        try:
            self._rows = load_appointments() or []
        except Exception:
            self._rows = []
        self._rebuild_table()

    def _delete_selected(self):
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            QtWidgets.QMessageBox.information(self, self.tr("Delete"), self.tr("Select a row first."))
            return
        r = idxs[0].row()
        name = self.table.item(r, 0).text()
        date = self.table.item(r, 1).text()
        time = self.table.item(r, 2).text()
        if QtWidgets.QMessageBox.question(
            self, self.tr("Delete"),
            self.tr(f"Delete appointment for {name} on {date} {time}?")
        ) == QtWidgets.QMessageBox.Yes:
            delete_appointment(name, date, time)
            self._load_from_store()

    # Quick manual add (optional)
    def _quick_add_dialog(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(self.tr("Add Appointment"))
        f = QtWidgets.QFormLayout(dlg)

        e_name = QtWidgets.QLineEdit()
        e_date = QtWidgets.QLineEdit(QtCore.QDate.currentDate().toString("dd-MM-yyyy"))
        e_time = QtWidgets.QLineEdit("12:00 PM")
        e_status = QtWidgets.QComboBox(); e_status.addItems(["Scheduled", "Completed", "Canceled"])
        e_notes = QtWidgets.QLineEdit()

        f.addRow(self.tr("Name"), e_name)
        f.addRow(self.tr("Date (dd-MM-yyyy)"), e_date)
        f.addRow(self.tr("Time"), e_time)
        f.addRow(self.tr("Status"), e_status)
        f.addRow(self.tr("Notes"), e_notes)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        f.addRow(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)

        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.add_appointment({
                "Name": e_name.text(),
                "Appointment Date": e_date.text(),
                "Appointment Time": e_time.text(),
                "Status": e_status.currentText(),
                "Notes": e_notes.text(),
            })