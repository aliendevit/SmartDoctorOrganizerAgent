from PyQt5 import QtWidgets, QtCore, QtGui
from data.database import load_all_clients  # Ensure your database module is available

class AppointmentTab(QtWidgets.QWidget):
    def __init__(self, tray_icon=None, parent=None):
        super().__init__(parent)
        self.tray_icon = tray_icon
        self.appointments = load_all_clients()  # Load stored appointments
        self.setup_ui()
        self.update_table()

    def tr(self, text):
        from translation_helper import tr
        return tr(text)

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header label
        self.header_label = QtWidgets.QLabel(self.tr("Scheduled Appointments"))
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        self.header_label.setFont(QtGui.QFont("Arial", 24, QtGui.QFont.Bold))
        layout.addWidget(self.header_label)

        # Refresh button with teal styling.
        self.refresh_button = QtWidgets.QPushButton(self.tr("Refresh Appointments"))
        self.refresh_button.setFont(QtGui.QFont("Arial", 14))
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #008080;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #006666;
            }
        """)
        self.refresh_button.clicked.connect(self.update_table)
        layout.addWidget(self.refresh_button)

        # Table for appointments.
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([self.tr("Client Name"), self.tr("Appointment Date"), self.tr("Appointment Time")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #E1E4E8;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
                border: 1px solid #E1E4E8;
            }
            QHeaderView::section {
                background-color: #008080;
                color: white;
                padding: 10px;
                border: none;
                font-family: Arial, sans-serif;
                font-size: 16px;
            }
            QScrollBar:vertical {
                background: #99C2E0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #008080;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #006666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.table, stretch=1)

        layout.addStretch()
        self.setLayout(layout)
        self.apply_styles()

    def apply_styles(self):
        # Overall style for the AppointmentTab.
        style = """
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial, sans-serif;
                font-size: 14px;
                color: #003366;
            }
        """
        self.setStyleSheet(style)

    def retranslateUi(self):
        # Update all user-visible texts
        self.header_label.setText(self.tr("Scheduled Appointments"))
        self.refresh_button.setText(self.tr("Refresh Appointments"))
        self.table.setHorizontalHeaderLabels([self.tr("Client Name"), self.tr("Appointment Date"), self.tr("Appointment Time")])

    def add_appointment(self, data):
        appointment_date = data.get("Appointment Date", "Not Specified")
        if appointment_date == "Not Specified":
            print("No valid appointment date; appointment not added.")
            return
        appointment_time = data.get("Appointment Time", "Not Specified")
        appointment = {
            "Name": data.get("Name", "Unknown"),
            "Appointment Date": appointment_date,
            "Appointment Time": appointment_time
        }
        self.appointments.append(appointment)
        self.update_table()

    def update_table(self):
        self.table.setRowCount(0)
        for i, appt in enumerate(self.appointments):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(appt["Name"]))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(appt["Appointment Date"]))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(appt["Appointment Time"]))

    def highlight_client(self, client_name):
        # Scroll to and highlight the row for the given client name.
        client_name = client_name.strip().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().strip().lower() == client_name:
                for col in range(self.table.columnCount()):
                    self.table.item(row, col).setBackground(QtGui.QColor("yellow"))
                self.table.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    appointment_tab = AppointmentTab()
    appointment_tab.show()
    sys.exit(app.exec_())
