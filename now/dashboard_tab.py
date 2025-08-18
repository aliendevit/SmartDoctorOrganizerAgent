import json
import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QDate
from data.data import load_all_clients  # This function is also used by the AccountsTab

ARCHIVE_FILE = "../json/monthly_receipts_archive.json"

class DashboardTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_archive()
        self.refresh_data()

    # Override tr() so that our custom translation helper is used.
    def tr(self, text):
        from translation_helper import tr
        return tr(text)

    def setup_ui(self):
        # Apply a clean, modern style via the stylesheet.
        self.setStyleSheet("""
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
            QLabel {
                font-size: 14px;
                color: #003366;
            }
            QPushButton {
                background-color: #008080;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #006666;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f9f9f9;
                gridline-color: #cccccc;
                border: 1px solid #E1E4E8;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #008080;
                color: white;
                padding: 10px;
                border: none;
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

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)

        # --- Outstanding Payments Section ---
        self.outstanding_group = QtWidgets.QGroupBox(self.tr("Outstanding Payments"))
        o_layout = QtWidgets.QVBoxLayout()
        self.outstanding_label = QtWidgets.QLabel(self.tr("Loading outstanding payments..."))
        o_layout.addWidget(self.outstanding_label)
        self.outstanding_table = QtWidgets.QTableWidget()
        self.outstanding_table.setColumnCount(4)
        self.outstanding_table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Total Amount"), self.tr("Total Paid"), self.tr("Outstanding")
        ])
        self.outstanding_table.horizontalHeader().setStretchLastSection(True)
        self.outstanding_table.setAlternatingRowColors(True)
        o_layout.addWidget(self.outstanding_table)
        self.refresh_outstanding_btn = QtWidgets.QPushButton(self.tr("Refresh Outstanding Payments"))
        self.refresh_outstanding_btn.clicked.connect(self.refresh_data)
        o_layout.addWidget(self.refresh_outstanding_btn)
        self.outstanding_group.setLayout(o_layout)
        layout.addWidget(self.outstanding_group)

        # --- Inventory Summary Section ---
        self.inventory_group = QtWidgets.QGroupBox(self.tr("Inventory Summary"))
        i_layout = QtWidgets.QVBoxLayout()
        # Inventory period selector.
        period_layout = QtWidgets.QHBoxLayout()
        self.period_label = QtWidgets.QLabel(self.tr("Inventory Period (days):"))
        self.inventory_days_spinbox = QtWidgets.QSpinBox()
        self.inventory_days_spinbox.setRange(1, 365)
        self.inventory_days_spinbox.setValue(30)  # Default to 30 days
        period_layout.addWidget(self.period_label)
        period_layout.addWidget(self.inventory_days_spinbox)
        i_layout.addLayout(period_layout)
        self.current_inventory_label = QtWidgets.QLabel(self.tr("Loading inventory summary..."))
        i_layout.addWidget(self.current_inventory_label)
        self.refresh_inventory_btn = QtWidgets.QPushButton(self.tr("Refresh Inventory Summary"))
        self.refresh_inventory_btn.clicked.connect(self.refresh_data)
        i_layout.addWidget(self.refresh_inventory_btn)
        self.archive_button = QtWidgets.QPushButton(self.tr("Archive Inventory"))
        self.archive_button.clicked.connect(self.archive_current_period)
        i_layout.addWidget(self.archive_button)
        # Button to show names of unpaid clients.
        self.show_unpaid_btn = QtWidgets.QPushButton(self.tr("Show Unpaid Clients"))
        self.show_unpaid_btn.clicked.connect(self.show_unpaid_clients)
        i_layout.addWidget(self.show_unpaid_btn)
        self.inventory_group.setLayout(i_layout)
        layout.addWidget(self.inventory_group)

        # --- Client Summary Section ---
        self.client_summary_group = QtWidgets.QGroupBox(self.tr("Client Summary"))
        cs_layout = QtWidgets.QVBoxLayout()
        self.client_summary_label = QtWidgets.QLabel(self.tr("Loading client summary..."))
        cs_layout.addWidget(self.client_summary_label)
        self.refresh_summary_btn = QtWidgets.QPushButton(self.tr("Refresh Client Summary"))
        self.refresh_summary_btn.clicked.connect(self.refresh_data)
        cs_layout.addWidget(self.refresh_summary_btn)
        self.client_summary_group.setLayout(cs_layout)
        layout.addWidget(self.client_summary_group)

        # --- Archive History Section ---
        self.archive_group = QtWidgets.QGroupBox(self.tr("Archived Inventory"))
        a_layout = QtWidgets.QVBoxLayout()
        self.archive_table = QtWidgets.QTableWidget()
        self.archive_table.setColumnCount(4)
        self.archive_table.setHorizontalHeaderLabels([
            self.tr("Period"), self.tr("Total Receipts"), self.tr("Total Outstanding"), self.tr("Unpaid Clients")
        ])
        self.archive_table.horizontalHeader().setStretchLastSection(True)
        self.archive_table.setAlternatingRowColors(True)
        a_layout.addWidget(self.archive_table)
        self.archive_group.setLayout(a_layout)
        layout.addWidget(self.archive_group)

        layout.addStretch()
        self.setLayout(layout)

    def refresh_data(self):
        clients = load_all_clients()

        # --- Outstanding Payments Calculation ---
        outstanding_clients = []
        for client in clients:
            try:
                total_amount = float(client.get("Total Amount", 0))
                total_paid = float(client.get("Total Paid", 0))
            except ValueError:
                total_amount = total_paid = 0
            if total_paid < total_amount:
                outstanding_clients.append({
                    "Name": client.get("Name", ""),
                    "Total Amount": total_amount,
                    "Total Paid": total_paid,
                    "Outstanding": total_amount - total_paid
                })
        num_outstanding = len(outstanding_clients)
        total_outstanding = sum(item["Outstanding"] for item in outstanding_clients)
        self.outstanding_label.setText(
            f"{self.tr('Patients with outstanding payments:')} {num_outstanding} | {self.tr('Total Outstanding:')} {total_outstanding:,.2f}"
        )
        self.populate_outstanding_table(outstanding_clients)

        # --- Inventory Summary Calculation ---
        days = self.inventory_days_spinbox.value()
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        total_paid_period = 0
        total_outstanding_period = 0
        num_unpaid_period = 0
        for client in clients:
            date_str = client.get("Date", "")
            if date_str:
                date_obj = QDate.fromString(date_str, "dd-MM-yyyy")
                if date_obj.isValid() and date_obj >= start_date and date_obj <= end_date:
                    try:
                        tp = float(client.get("Total Paid", 0))
                        ta = float(client.get("Total Amount", 0))
                    except ValueError:
                        tp = ta = 0
                    total_paid_period += tp
                    if tp < ta:
                        total_outstanding_period += (ta - tp)
                        num_unpaid_period += 1
        period_label = f"{start_date.toString('dd-MM-yyyy')} {self.tr('to')} {end_date.toString('dd-MM-yyyy')}"
        self.current_inventory_label.setText(
            f"{period_label} - {self.tr('Total Receipts:')} {total_paid_period:,.2f} | {self.tr('Outstanding:')} {total_outstanding_period:,.2f} | {self.tr('Unpaid Clients:')} {num_unpaid_period}"
        )

        # --- Client Summary Calculation ---
        total_clients = len(clients)
        total_age = 0
        count_age = 0
        total_revenue = 0
        total_outstanding_all = 0
        for client in clients:
            try:
                age = float(client.get("Age", 0))
                total_age += age
                count_age += 1
            except (ValueError, TypeError):
                pass
            try:
                tp = float(client.get("Total Paid", 0))
                ta = float(client.get("Total Amount", 0))
                total_revenue += tp
                if tp < ta:
                    total_outstanding_all += (ta - tp)
            except (ValueError, TypeError):
                pass
        avg_age = total_age / count_age if count_age > 0 else 0
        self.client_summary_label.setText(
            f"{self.tr('Total Clients:')} {total_clients} | {self.tr('Average Age:')} {avg_age:.1f} | {self.tr('Total Revenue:')} {total_revenue:,.2f} | {self.tr('Total Outstanding:')} {total_outstanding_all:,.2f}"
        )

    def populate_outstanding_table(self, data):
        self.archive_table.clearSelection()  # Clear any previous selection
        self.outstanding_table.setRowCount(0)
        for row, item in enumerate(data):
            self.outstanding_table.insertRow(row)
            self.outstanding_table.setItem(row, 0, QtWidgets.QTableWidgetItem(item["Name"]))
            self.outstanding_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{item['Total Amount']:,.2f}"))
            self.outstanding_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{item['Total Paid']:,.2f}"))
            self.outstanding_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{item['Outstanding']:,.2f}"))

    def show_unpaid_clients(self):
        days = self.inventory_days_spinbox.value()
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        unpaid_names = []
        clients = load_all_clients()
        for client in clients:
            date_str = client.get("Date", "")
            if date_str:
                date_obj = QDate.fromString(date_str, "dd-MM-yyyy")
                if date_obj.isValid() and date_obj >= start_date and date_obj <= end_date:
                    try:
                        tp = float(client.get("Total Paid", 0))
                        ta = float(client.get("Total Amount", 0))
                    except ValueError:
                        continue
                    if tp < ta:
                        unpaid_names.append(client.get("Name", self.tr("Unknown")))
        if unpaid_names:
            names_text = "\n".join(unpaid_names)
            QtWidgets.QMessageBox.information(self, self.tr("Unpaid Clients"),
                                              self.tr("Clients with outstanding payments:\n") + names_text)
        else:
            QtWidgets.QMessageBox.information(self, self.tr("Unpaid Clients"),
                                              self.tr("All clients have fully paid in the selected period."))

    def archive_current_period(self):
        days = self.inventory_days_spinbox.value()
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        period_label = f"{start_date.toString('dd-MM-yyyy')} {self.tr('to')} {end_date.toString('dd-MM-yyyy')}"
        clients = load_all_clients()
        total_paid_period = 0
        total_outstanding_period = 0
        num_unpaid_period = 0
        for client in clients:
            date_str = client.get("Date", "")
            if date_str:
                date_obj = QDate.fromString(date_str, "dd-MM-yyyy")
                if date_obj.isValid() and date_obj >= start_date and date_obj <= end_date:
                    try:
                        tp = float(client.get("Total Paid", 0))
                        ta = float(client.get("Total Amount", 0))
                    except ValueError:
                        tp = ta = 0
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
            with open(ARCHIVE_FILE, "r") as f:
                archive = json.load(f)
        updated = False
        for entry in archive:
            if entry.get("period") == period_label:
                entry.update(period_summary)
                updated = True
                break
        if not updated:
            archive.append(period_summary)
        with open(ARCHIVE_FILE, "w") as f:
            json.dump(archive, f, indent=4)
        self.load_archive()
        QtWidgets.QMessageBox.information(self, self.tr("Archive"), self.tr("Summary for ") + period_label + self.tr(" archived successfully."))

    def load_archive(self):
        archive = []
        if os.path.exists(ARCHIVE_FILE):
            with open(ARCHIVE_FILE, "r") as f:
                archive = json.load(f)
        self.archive_table.setRowCount(0)
        for row, entry in enumerate(archive):
            self.archive_table.insertRow(row)
            self.archive_table.setItem(row, 0, QtWidgets.QTableWidgetItem(entry.get("period", "")))
            self.archive_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{entry.get('total_receipts', 0):,.2f}"))
            self.archive_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{entry.get('total_outstanding', 0):,.2f}"))
            self.archive_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(entry.get("unpaid_clients", 0))))

    def retranslateUi(self):
        self.outstanding_group.setTitle(self.tr("Outstanding Payments"))
        self.outstanding_label.setText(self.tr("Loading outstanding payments..."))
        self.outstanding_table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Total Amount"), self.tr("Total Paid"), self.tr("Outstanding")
        ])
        self.refresh_outstanding_btn.setText(self.tr("Refresh Outstanding Payments"))
        self.inventory_group.setTitle(self.tr("Inventory Summary"))
        self.period_label.setText(self.tr("Inventory Period (days):"))
        self.current_inventory_label.setText(self.tr("Loading inventory summary..."))
        self.refresh_inventory_btn.setText(self.tr("Refresh Inventory Summary"))
        self.archive_button.setText(self.tr("Archive Inventory"))
        self.show_unpaid_btn.setText(self.tr("Show Unpaid Clients"))
        self.client_summary_group.setTitle(self.tr("Client Summary"))
        self.client_summary_label.setText(self.tr("Loading client summary..."))
        self.refresh_summary_btn.setText(self.tr("Refresh Client Summary"))
        self.archive_group.setTitle(self.tr("Archived Inventory"))
        self.archive_table.setHorizontalHeaderLabels([
            self.tr("Period"), self.tr("Total Receipts"), self.tr("Total Outstanding"), self.tr("Unpaid Clients")
        ])

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
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = DashboardTab()
    widget.show()
    sys.exit(app.exec_())