import sys
from PyQt5 import QtWidgets, QtCore
from data.data import insert_client  # assuming insert_client is defined in data.py

class AddClientTab(QtWidgets.QWidget):
    def tr(self, text):
        # Use our custom translation helper.
        from translation_helper import tr
        return tr(text)
    """
    Provides a simple, grouped form for adding a new client.
    Fields are organized into Personal Info, Appointment Details,
    and Payment Information sections.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_styles()



    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- Personal Information Group ---
        self.personal_group = QtWidgets.QGroupBox(self.tr("Personal Information"))
        personal_layout = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.age_edit = QtWidgets.QLineEdit()
        self.symptoms_edit = QtWidgets.QLineEdit()  # comma-separated
        self.notes_edit = QtWidgets.QTextEdit()
        personal_layout.addRow(self.tr("Name") + ":", self.name_edit)
        personal_layout.addRow(self.tr("Age") + ":", self.age_edit)
        personal_layout.addRow(self.tr("Symptoms") + ":", self.symptoms_edit)
        personal_layout.addRow(self.tr("Notes") + ":", self.notes_edit)
        self.personal_group.setLayout(personal_layout)
        main_layout.addWidget(self.personal_group)

        # --- Appointment Details Group ---
        self.appointment_group = QtWidgets.QGroupBox(self.tr("Appointment Details"))
        appointment_layout = QtWidgets.QFormLayout()
        self.general_date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.general_date_edit.setDisplayFormat("dd-MM-yyyy")
        self.appointment_date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.appointment_date_edit.setDisplayFormat("dd-MM-yyyy")
        self.appointment_time_edit = QtWidgets.QTimeEdit(QtCore.QTime.currentTime())
        self.appointment_time_edit.setDisplayFormat("hh:mm AP")
        self.follow_up_date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addDays(7))
        self.follow_up_date_edit.setDisplayFormat("dd-MM-yyyy")
        self.summary_edit = QtWidgets.QTextEdit()
        appointment_layout.addRow(self.tr("General Date") + ":", self.general_date_edit)
        appointment_layout.addRow(self.tr("Appt Date") + ":", self.appointment_date_edit)
        appointment_layout.addRow(self.tr("Appt Time") + ":", self.appointment_time_edit)
        appointment_layout.addRow(self.tr("Follow-Up Date") + ":", self.follow_up_date_edit)
        appointment_layout.addRow(self.tr("Summary") + ":", self.summary_edit)
        self.appointment_group.setLayout(appointment_layout)
        main_layout.addWidget(self.appointment_group)

        # --- Payment Information Group ---
        self.payment_group = QtWidgets.QGroupBox(self.tr("Payment Information"))
        payment_layout = QtWidgets.QFormLayout()
        self.total_paid_edit = QtWidgets.QLineEdit()
        self.owed_edit = QtWidgets.QLineEdit()
        self.total_amount_edit = QtWidgets.QLineEdit()
        payment_layout.addRow(self.tr("Total Paid") + ":", self.total_paid_edit)
        payment_layout.addRow(self.tr("Owed") + ":", self.owed_edit)
        payment_layout.addRow(self.tr("Total Amount") + ":", self.total_amount_edit)
        self.payment_group.setLayout(payment_layout)
        main_layout.addWidget(self.payment_group)

        # --- Submit Button ---
        self.add_button = QtWidgets.QPushButton(self.tr("Add Client"))
        self.add_button.setFixedHeight(40)
        self.add_button.clicked.connect(self.add_client)
        main_layout.addWidget(self.add_button)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def add_client(self):
        name = self.name_edit.text().strip()
        age_text = self.age_edit.text().strip()
        total_paid_text = self.total_paid_edit.text().strip()
        owed_text = self.owed_edit.text().strip()
        total_amount_text = self.total_amount_edit.text().strip()
        symptoms_text = self.symptoms_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()
        summary = self.summary_edit.toPlainText().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, self.tr("Input Error"), self.tr("Name is required."))
            return

        age = int(age_text) if age_text.isdigit() else None
        total_paid = float(total_paid_text) if self._is_number(total_paid_text) else 0
        owed = float(owed_text) if self._is_number(owed_text) else 0
        total_amount = float(total_amount_text) if self._is_number(total_amount_text) else 0
        symptoms = [s.strip() for s in symptoms_text.split(",") if s.strip()]

        general_date = self.general_date_edit.date().toString("dd-MM-yyyy")
        appointment_date = self.appointment_date_edit.date().toString("dd-MM-yyyy")
        appointment_time = self.appointment_time_edit.time().toString("hh:mm AP")
        follow_up_date = self.follow_up_date_edit.date().toString("dd-MM-yyyy")

        client_data = {
            "Name": name,
            "Age": age,
            "Total Paid": total_paid,
            "Owed": owed,
            "Total Amount": total_amount,
            "Symptoms": symptoms,
            "Notes": notes,
            "Date": general_date,
            "Appointment Date": appointment_date,
            "Appointment Time": appointment_time,
            "Follow-Up Date": follow_up_date,
            "Summary": summary
        }

        try:
            insert_client(client_data)
            QtWidgets.QMessageBox.information(self, self.tr("Success"),
                                              self.tr("Client '{0}' added successfully.").format(name))
            self.clear_fields()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, self.tr("Error"),
                                           self.tr("Error adding client: ") + str(e))

    def _is_number(self, text):
        try:
            float(text)
            return True
        except ValueError:
            return False

    def clear_fields(self):
        self.name_edit.clear()
        self.age_edit.clear()
        self.total_paid_edit.clear()
        self.owed_edit.clear()
        self.total_amount_edit.clear()
        self.symptoms_edit.clear()
        self.notes_edit.clear()
        self.general_date_edit.setDate(QtCore.QDate.currentDate())
        self.appointment_date_edit.setDate(QtCore.QDate.currentDate())
        self.appointment_time_edit.setTime(QtCore.QTime.currentTime())
        self.follow_up_date_edit.setDate(QtCore.QDate.currentDate().addDays(7))
        self.summary_edit.clear()

    def apply_styles(self):
        style = """
        QWidget {
            background-color: #f0f0f0;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #003366;
        }
        QGroupBox {
            border: 2px solid #008080;
            border-radius: 8px;
            margin-top: 10px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            background-color: #008080;
            color: white;
            border-radius: 4px;
        }
        QLineEdit, QTextEdit {
            background-color: #ffffff;
            border: 1px solid #E1E4E8;
            border-radius: 8px;
            padding: 8px;
        }
        QPushButton {
            background-color: #008080;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 18px;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #006666;
        }
        """
        self.setStyleSheet(style)

    def retranslateUi(self):
        self.personal_group.setTitle(self.tr("Personal Information"))
        self.appointment_group.setTitle(self.tr("Appointment Details"))
        self.payment_group.setTitle(self.tr("Payment Information"))
        self.add_button.setText(self.tr("Add Client"))

# -------------------- LoadEditClientTab --------------------
class LoadEditClientTab(QtWidgets.QWidget):
    """
    Provides a straightforward table view and search field for loading and editing clients.
    Displays essential details: Name, Age, Total Paid, Owed, and Total Amount.
    Double-clicking a row or searching by name opens an edit dialog.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_styles()

    def tr(self, text):
        from translation_helper import tr
        return tr(text)

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # --- Search Area ---
        search_layout = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit(self)
        self.search_input.setPlaceholderText(self.tr("Enter client name..."))
        self.search_button = QtWidgets.QPushButton(self.tr("Load Client"))
        self.search_button.clicked.connect(self.load_client)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # --- Clients Table ---
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Age"), self.tr("Total Paid"), self.tr("Owed"), self.tr("Total Amount")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.edit_client)
        main_layout.addWidget(self.table)

        # --- Refresh Button ---
        refresh_button = QtWidgets.QPushButton(self.tr("Refresh"))
        refresh_button.clicked.connect(self.load_clients)
        main_layout.addWidget(refresh_button)
        main_layout.addStretch()

        self.setLayout(main_layout)
        self.load_clients()

    def load_clients(self):
        from data.data import load_all_clients
        self.clients = load_all_clients()
        self.table.setRowCount(0)
        for row, client in enumerate(self.clients):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(client.get("Name", "")))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(client.get("Age", ""))))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(client.get("Total Paid", 0))))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(client.get("Owed", 0))))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(client.get("Total Amount", 0))))

    def load_client(self):
        search_text = self.search_input.text().strip().lower()
        if not search_text:
            QtWidgets.QMessageBox.information(self, self.tr("Input Required"), self.tr("Please enter a client name."))
            return
        found = None
        for client in self.clients:
            if client.get("Name", "").lower() == search_text:
                found = client
                break
        if found:
            self.open_edit_dialog(found)
        else:
            QtWidgets.QMessageBox.information(self, self.tr("Not Found"),
                                              self.tr("No client found with name '{0}'").format(search_text))

    def edit_client(self, index):
        row = index.row()
        client = self.clients[row]
        self.open_edit_dialog(client)

    def open_edit_dialog(self, client):
        from widgets.clientWidget import ClientAccountPage
        dialog = ClientAccountPage(client, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            from data.data import update_account_in_db
            updated_data = dialog.get_updated_data()
            update_account_in_db(client.get("Name", ""), updated_data)
            self.load_clients()

    def apply_styles(self):
        style = """
        QWidget {
            background-color: #f0f0f0;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #003366;
        }
        QTableWidget {
            background-color: #ffffff;
            border: 1px solid #E1E4E8;
            border-radius: 8px;
        }
        QHeaderView::section {
            background-color: #008080;
            padding: 10px;
            border: none;
            color: white;
            font-size: 16px;
        }
        QPushButton {
            background-color: #008080;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 8px 14px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #006666;
        }
        """
        self.setStyleSheet(style)

    def retranslateUi(self):
        self.search_input.setPlaceholderText(self.tr("Enter client name..."))
        self.search_button.setText(self.tr("Load Client"))
        self.table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Age"), self.tr("Total Paid"), self.tr("Owed"), self.tr("Total Amount")
        ])

# -------------------- ClientManagementTab --------------------
class ClientManagementTab(QtWidgets.QWidget):
    """
    Main widget that includes two tabs:
      - "Add New Client" (for manual entry with grouped sections)
      - "Load/Edit Client" (for simple search and edit, showing only essential details)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_styles()

    def tr(self, text):
        from translation_helper import tr
        return tr(text)

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget(self)
        # Import the individual tabs from client_management_tab module.
        from client_management_tab import AddClientTab as ACTab, LoadEditClientTab as LETab
        self.add_client_tab = ACTab(self)
        self.load_edit_client_tab = LETab(self)
        self.tabs.addTab(self.add_client_tab, self.tr("Add New Client"))
        self.tabs.addTab(self.load_edit_client_tab, self.tr("Load/Edit Client"))
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def retranslateUi(self):
        self.tabs.setTabText(0, self.tr("Add New Client"))
        self.tabs.setTabText(1, self.tr("Load/Edit Client"))

    def apply_styles(self):
        style = """
        QWidget {
            background-color: #f0f0f0;
        }
        QTabWidget::pane {
            border: 1px solid #E1E4E8;
            border-radius: 8px;
            margin-top: -1px;
        }
        QTabBar::tab {
            background: #ffffff;
            padding: 10px 20px;
            margin: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border: 1px solid #E1E4E8;
        }
        QTabBar::tab:selected {
            background: #008080;
            color: white;
        }
        """
        self.setStyleSheet(style)

# -------------------- Testing Client Management Tab Independently --------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = ClientManagementTab()
    widget.show()
    sys.exit(app.exec_())