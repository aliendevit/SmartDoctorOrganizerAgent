from PyQt5 import QtWidgets, QtCore, QtGui
from data.database import load_all_clients  # Ensure your database module is available

def _polish(*widgets):
    for w in widgets:
        w.style().unpolish(w); w.style().polish(w); w.update()

class AppointmentTab(QtWidgets.QWidget):
    def __init__(self, tray_icon=None, parent=None):
        super().__init__(parent)
        self.tray_icon = tray_icon
        self.appointments = load_all_clients() or []  # Load stored appointments
        self._build()
        self.update_table()

    def tr(self, text):
        try:
            from translation_helper import tr
            return tr(text)
        except Exception:
            return text

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # -------- Header card --------
        header = QtWidgets.QFrame(); header.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(header); hly.setContentsMargins(12, 12, 12, 12)
        self.header_label = QtWidgets.QLabel(self.tr("Scheduled Appointments"))
        self.header_label.setStyleSheet("font-size: 16pt; font-weight: 700;")
        hly.addWidget(self.header_label); hly.addStretch(1)

        self.refresh_button = QtWidgets.QPushButton(self.tr("Refresh Appointments"))
        # self.refresh_button.setProperty("variant", "ghost")
        self.refresh_button.setProperty("accent", "sky")
        self.refresh_button.clicked.connect(self._refresh_from_db)
        hly.addWidget(self.refresh_button); _polish(self.refresh_button)

        root.addWidget(header)

        # -------- Table card --------
        table_card = QtWidgets.QFrame(); table_card.setProperty("modernCard", True)
        tly = QtWidgets.QVBoxLayout(table_card); tly.setContentsMargins(12, 12, 12, 12)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            self.tr("Client Name"), self.tr("Appointment Date"), self.tr("Appointment Time")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        tly.addWidget(self.table)

        root.addWidget(table_card, 1)
        root.addStretch(1)

    def retranslateUi(self):
        self.header_label.setText(self.tr("Scheduled Appointments"))
        self.refresh_button.setText(self.tr("Refresh Appointments"))
        self.table.setHorizontalHeaderLabels([
            self.tr("Client Name"), self.tr("Appointment Date"), self.tr("Appointment Time")
        ])

    # -------- Data ops --------
    def _refresh_from_db(self):
        self.appointments = load_all_clients() or []
        self.update_table()
        # optional tray balloon
        try:
            if self.tray_icon and self.tray_icon.supportsMessages():
                self.tray_icon.showMessage("MediAgent AI", self.tr("Appointments refreshed."), QtWidgets.QSystemTrayIcon.Information, 2500)
        except Exception:
            pass

    def add_appointment(self, data):
        appointment_date = data.get("Appointment Date", "Not Specified")
        if appointment_date == "Not Specified":
            return
        appointment_time = data.get("Appointment Time", "Not Specified")
        self.appointments.append({
            "Name": data.get("Name", "Unknown"),
            "Appointment Date": appointment_date,
            "Appointment Time": appointment_time
        })
        self.update_table()

    def update_table(self):
        self.table.setRowCount(0)
        for i, appt in enumerate(self.appointments):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(appt.get("Name", "")))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(appt.get("Appointment Date", "")))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(appt.get("Appointment Time", "")))
        self.table.sortItems(1, QtCore.Qt.AscendingOrder)

    def highlight_client(self, client_name):
        client_name = client_name.strip().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().strip().lower() == client_name:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it:
                        it.setBackground(QtGui.QBrush(QtGui.QColor("#fff3cd")))  # soft highlight
                self.table.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        from modern_theme import ModernTheme
        ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
    except Exception:
        pass
    appointment_tab = AppointmentTab()
    appointment_tab.resize(900, 600)
    appointment_tab.show()
    sys.exit(app.exec_())
