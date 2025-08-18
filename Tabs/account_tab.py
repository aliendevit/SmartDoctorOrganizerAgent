import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from data.data import load_all_clients, update_account_in_db
# Keep your existing dialog path; supports either method name
from widgets.clientWidget import ClientAccountPage  # shows detailed account info

def _polish(*widgets):
    for w in widgets:
        w.style().unpolish(w); w.style().polish(w); w.update()

class AccountsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.appointments = load_all_clients() or []  # Load stored client accounts
        self.updating_table = False  # guard to block cellChanged recursion
        self._build()
        self.update_table()
        self.table.cellChanged.connect(self.on_cell_changed)

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
        self.header = QtWidgets.QLabel(self.tr("Client Accounts"))
        self.header.setStyleSheet("font-size: 16pt; font-weight: 700;")
        hly.addWidget(self.header); hly.addStretch(1)

        self.refresh_btn = QtWidgets.QPushButton(self.tr("Refresh"))
        self.refresh_btn.setProperty("variant", "ghost")
        self.refresh_btn.setProperty("accent", "violet")
        self.refresh_btn.clicked.connect(self._refresh_from_db)
        hly.addWidget(self.refresh_btn); _polish(self.refresh_btn)
        root.addWidget(header)

        # -------- Table card --------
        table_card = QtWidgets.QFrame(); table_card.setProperty("modernCard", True)
        tly = QtWidgets.QVBoxLayout(table_card); tly.setContentsMargins(12, 12, 12, 12)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Age"), self.tr("Total Paid"), self.tr("Owed"), self.tr("Total Amount")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QTableWidget.AllEditTriggers)
        self.table.setSortingEnabled(True)
        tly.addWidget(self.table)

        root.addWidget(table_card, 1)

        # -------- Actions card --------
        actions = QtWidgets.QFrame(); actions.setProperty("modernCard", True)
        aly = QtWidgets.QHBoxLayout(actions); aly.setContentsMargins(12, 12, 12, 12)

        self.save_all_btn = QtWidgets.QPushButton(self.tr("Save All Changes"))
        self.save_all_btn.setProperty("variant", "success")  # green
        self.save_all_btn.clicked.connect(self.save_all_changes)

        self.open_btn = QtWidgets.QPushButton(self.tr("Open Selected"))
        self.open_btn.setProperty("variant", "info")
        self.open_btn.clicked.connect(self._open_selected)

        aly.addWidget(self.open_btn)
        aly.addStretch(1)
        aly.addWidget(self.save_all_btn)
        _polish(self.save_all_btn, self.open_btn)

        root.addWidget(actions)
        root.addStretch(1)

    # -------- Data/table ops --------
    def _refresh_from_db(self):
        self.appointments = load_all_clients() or []
        self.update_table()

    def update_table(self):
        self.updating_table = True
        self.table.setRowCount(0)
        for i, account in enumerate(self.appointments):
            self.table.insertRow(i)

            def _item(text, align_right=False):
                it = QtWidgets.QTableWidgetItem("" if text is None else str(text))
                if align_right:
                    it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                return it

            self.table.setItem(i, 0, _item(account.get("Name", "")))
            self.table.setItem(i, 1, _item(account.get("Age", "")))
            self.table.setItem(i, 2, _item(account.get("Total Paid", "0"), True))
            # compute owed safely
            try:
                total_paid = float(account.get("Total Paid", 0) or 0)
                total_amount = float(account.get("Total Amount", 0) or 0)
                owed_val = total_amount - total_paid
            except (ValueError, TypeError):
                owed_val = account.get("Owed", "0")
            self.table.setItem(i, 3, _item(owed_val, True))
            self.table.setItem(i, 4, _item(account.get("Total Amount", "0"), True))
        self.updating_table = False
        self.table.sortItems(0, QtCore.Qt.AscendingOrder)

    def on_cell_changed(self, row, column):
        if self.updating_table:
            return
        # Only recalc if Total Paid or Total Amount changed
        if column not in (2, 4):
            return
        try:
            total_paid = float(self.table.item(row, 2).text())
            total_amount = float(self.table.item(row, 4).text())
            owed = total_amount - total_paid
        except (ValueError, AttributeError):
            owed = ""
        self.table.blockSignals(True)
        owed_item = QtWidgets.QTableWidgetItem(str(owed))
        owed_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.table.setItem(row, 3, owed_item)
        self.table.blockSignals(False)

        # Update cached data
        name_item = self.table.item(row, 0)
        if name_item:
            client_name = name_item.text().strip()
            for account in self.appointments:
                if account.get("Name", "").strip().lower() == client_name.lower():
                    account["Total Paid"] = total_paid
                    account["Total Amount"] = total_amount
                    account["Owed"] = owed
                    break

    def _open_selected(self):
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            QtWidgets.QMessageBox.information(self, self.tr("Open"), self.tr("Select a client row first."))
            return
        self.open_account_detail(idxs[0])

    def open_account_detail(self, index):
        row = index.row() if isinstance(index, QtCore.QModelIndex) else index
        client_name = self.table.item(row, 0).text().strip()
        account_data = next((acc for acc in self.appointments
                             if acc.get("Name", "").strip().lower() == client_name.lower()), None)
        if not account_data:
            return
        dialog = ClientAccountPage(account_data, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Support either method name, depending on your dialog implementation
            if hasattr(dialog, "get_updated_data"):
                updated_data = dialog.get_updated_data()
            else:
                updated_data = dialog.get_updated_client()
            update_account_in_db(client_name, updated_data)
            self._refresh_from_db()
            self.highlight_client(client_name)

    def highlight_client(self, client_name):
        client_name = client_name.strip().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().strip().lower() == client_name:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it:
                        it.setBackground(QtGui.QBrush(QtGui.QColor("#fff3cd")))
                self.table.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

    def save_all_changes(self):
        for row in range(self.table.rowCount()):
            name = (self.table.item(row, 0) or QtWidgets.QTableWidgetItem("")).text().strip()
            updated_data = {
                "Name": name,
                "Age": (self.table.item(row, 1) or QtWidgets.QTableWidgetItem("")).text().strip(),
                "Total Paid": (self.table.item(row, 2) or QtWidgets.QTableWidgetItem("0")).text().strip(),
                "Owed": (self.table.item(row, 3) or QtWidgets.QTableWidgetItem("0")).text().strip(),
                "Total Amount": (self.table.item(row, 4) or QtWidgets.QTableWidgetItem("0")).text().strip(),
            }
            update_account_in_db(name, updated_data)
        QtWidgets.QMessageBox.information(self, self.tr("Save All"),
                                          self.tr("All changes have been saved to the database."))
        self._refresh_from_db()

    def retranslateUi(self):
        self.header.setText(self.tr("Client Accounts"))
        self.table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Age"), self.tr("Total Paid"), self.tr("Owed"), self.tr("Total Amount")
        ])
        self.save_all_btn.setText(self.tr("Save All Changes"))
        self.open_btn.setText(self.tr("Open Selected"))
        self.refresh_btn.setText(self.tr("Refresh"))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    try:
        from modern_theme import ModernTheme
        ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
    except Exception:
        pass
    window = AccountsTab()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec_())
