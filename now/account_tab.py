import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from data.data import load_all_clients, update_account_in_db
from widgets.clientWidget import ClientAccountPage  # Dialog that shows detailed account info


class AccountsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.appointments = load_all_clients()  # Load stored client accounts
        self.updating_table = False  # Flag to block cellChanged signals during table update
        self.setup_ui()
        self.apply_styles()
        self.update_table()
        # Connect cellChanged signal to our calculation function.
        self.table.cellChanged.connect(self.on_cell_changed)

    # Override tr() so that our custom translation helper is used.
    def tr(self, text):
        from translation_helper import tr
        return tr(text)

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Header label for the tab.
        self.header = QtWidgets.QLabel(self.tr("Client Accounts"))
        self.header.setAlignment(QtCore.Qt.AlignCenter)
        self.header.setFont(QtGui.QFont("Segoe UI", 20, QtGui.QFont.Bold))
        layout.addWidget(self.header)

        # Table for displaying client accounts.
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.tr("Name"),
            self.tr("Age"),
            self.tr("Total Paid"),
            self.tr("Owed"),
            self.tr("Total Amount")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QTableWidget.AllEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.open_account_detail)
        layout.addWidget(self.table)

        # Save All Changes button.
        self.save_all_btn = QtWidgets.QPushButton(self.tr("Save All Changes"))
        self.save_all_btn.setFont(QtGui.QFont("Segoe UI", 14))
        self.save_all_btn.clicked.connect(self.save_all_changes)
        layout.addWidget(self.save_all_btn)

        layout.addStretch()
        self.setLayout(layout)

    def update_table(self):
        self.updating_table = True  # Block signals while populating
        self.appointments = load_all_clients()
        self.table.setRowCount(0)
        for i, account in enumerate(self.appointments):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(account.get("Name", "")))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(account.get("Age", ""))))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(account.get("Total Paid", "0"))))
            try:
                total_paid = float(account.get("Total Paid", 0))
                total_amount = float(account.get("Total Amount", 0))
                owed = total_amount - total_paid
            except ValueError:
                owed = account.get("Owed", "0")
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(owed)))
            self.table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(account.get("Total Amount", "0"))))
        self.updating_table = False

    def on_cell_changed(self, row, column):
        if self.updating_table:
            return
        # Only recalc if Total Paid (col 2) or Total Amount (col 4) was modified.
        if column not in (2, 4):
            return
        try:
            total_paid = float(self.table.item(row, 2).text())
            total_amount = float(self.table.item(row, 4).text())
            owed = total_amount - total_paid
        except (ValueError, AttributeError):
            owed = ""
        # Block signals to avoid recursion.
        self.table.blockSignals(True)
        self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(owed)))
        self.table.blockSignals(False)
        # Optionally update the underlying data.
        client_name = self.table.item(row, 0).text().strip()
        for account in self.appointments:
            if account.get("Name", "").strip().lower() == client_name.lower():
                account["Total Paid"] = total_paid
                account["Total Amount"] = total_amount
                account["Owed"] = owed
                break

    def open_account_detail(self, index):
        row = index.row()
        client_name = self.table.item(row, 0).text().strip()
        account_data = None
        for acc in self.appointments:
            if acc.get("Name", "").strip().lower() == client_name.lower():
                account_data = acc
                break
        if account_data:
            dialog = ClientAccountPage(account_data, parent=self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                updated_data = dialog.get_updated_data()
                update_account_in_db(client_name, updated_data)
                self.update_table()
                self.highlight_client(client_name)

    def highlight_client(self, client_name):
        client_name = client_name.strip().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().strip().lower() == client_name:
                for col in range(self.table.columnCount()):
                    self.table.item(row, col).setBackground(QtGui.QColor("yellow"))
                self.table.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

    def save_all_changes(self):
        # Iterate through all rows, collect data, and update the database.
        for row in range(self.table.rowCount()):
            client_name = self.table.item(row, 0).text().strip()
            updated_data = {
                "Name": client_name,
                "Age": self.table.item(row, 1).text().strip(),
                "Total Paid": self.table.item(row, 2).text().strip(),
                "Owed": self.table.item(row, 3).text().strip(),
                "Total Amount": self.table.item(row, 4).text().strip()
            }
            update_account_in_db(client_name, updated_data)
        QtWidgets.QMessageBox.information(self, self.tr("Save All"),
                                          self.tr("All changes have been saved to the database."))
        self.update_table()

    def retranslateUi(self):
        self.header.setText(self.tr("Client Accounts"))
        self.table.setHorizontalHeaderLabels([
            self.tr("Name"),
            self.tr("Age"),
            self.tr("Total Paid"),
            self.tr("Owed"),
            self.tr("Total Amount")
        ])
        self.save_all_btn.setText(self.tr("Save All Changes"))

    def apply_styles(self):
        style = """
        QWidget {
            background-color: #f0f0f0;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #003366;
        }
        QLabel {
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
        """
        self.setStyleSheet(style)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = AccountsTab()
    window.show()
    sys.exit(app.exec_())
