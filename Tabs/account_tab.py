import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QStyledItemDelegate, QLineEdit
from PyQt5.QtGui import QDoubleValidator
from data.data import load_all_clients, update_account_in_db
from widgets.clientWidget import ClientAccountPage
from data.data import load_all_clients, update_account_in_db
from widgets.clientWidget import ClientAccountPage  # must be a QDialog

def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

def _to_float(val) -> float:
    try:
        s = "" if val is None else str(val)
        s = s.replace(",", "").strip()
        return float(s) if s else 0.0
    except Exception:
        return 0.0

class NumberDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, decimals=2, bottom=0.0, top=1e12):
        super().__init__(parent)
        self.decimals = decimals; self.bottom = bottom; self.top = top
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        v = QDoubleValidator(self.bottom, self.top, self.decimals, editor)
        v.setNotation(QDoubleValidator.StandardNotation)
        editor.setValidator(v)
        return editor
    def setModelData(self, editor, model, index):
        val = _to_float(editor.text())
        model.setData(index, str(val))

class AccountsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.appointments = load_all_clients() or []
        self.updating_table = False
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
        root.setContentsMargins(16, 16, 16, 16); root.setSpacing(12)

        # Header
        header = QtWidgets.QFrame(); header.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(header); hly.setContentsMargins(12, 12, 12, 12)
        self.header = QtWidgets.QLabel(self.tr("Client Accounts"))
        self.header.setStyleSheet("font-size: 16pt; font-weight: 700;")
        hly.addWidget(self.header); hly.addStretch(1)
        self.refresh_btn = QtWidgets.QPushButton(self.tr("Refresh"))
        # self.refresh_btn.setProperty("variant", "ghost");
        self.refresh_btn.setProperty("accent", "violet")
        self.refresh_btn.clicked.connect(self._refresh_from_db)
        hly.addWidget(self.refresh_btn); _polish(self.refresh_btn)
        root.addWidget(header)

        # Table
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

        # 👉 Open account on double-click / Enter (itemActivated) / context menu
        self.table.doubleClicked.connect(self.open_account_detail)                       # double-click cell
        self.table.itemActivated.connect(lambda it: self.open_account_detail(it.row()))  # Enter/Return
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_menu)

        # numeric delegates
        num_delegate = NumberDelegate(self, decimals=2, bottom=0.0, top=1e12)
        self.table.setItemDelegateForColumn(2, num_delegate)  # Total Paid
        self.table.setItemDelegateForColumn(4, num_delegate)  # Total Amount

        tly.addWidget(self.table)
        root.addWidget(table_card, 1)

        # Actions
        actions = QtWidgets.QFrame(); actions.setProperty("modernCard", True)
        aly = QtWidgets.QHBoxLayout(actions); aly.setContentsMargins(12, 12, 12, 12)
        self.open_btn = QtWidgets.QPushButton(self.tr("Open Selected"))
        self.open_btn.setProperty("variant", "info")
        self.open_btn.clicked.connect(self._open_selected)
        self.save_all_btn = QtWidgets.QPushButton(self.tr("Save All Changes"))
        self.save_all_btn.setProperty("variant", "success")
        self.save_all_btn.clicked.connect(self.save_all_changes)
        aly.addWidget(self.open_btn); aly.addStretch(1); aly.addWidget(self.save_all_btn)
        _polish(self.save_all_btn, self.open_btn)
        root.addWidget(actions)
        root.addStretch(1)

    # Context menu
    def _on_table_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction(self.tr("Open Account"))
        act = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if act == act_open:
            self.open_account_detail(idx)

    # Data ops
    def _refresh_from_db(self):
        self.appointments = load_all_clients() or []
        self.update_table()

    def update_table(self):
        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.updating_table = True
        self.table.setRowCount(0)

        for i, account in enumerate(self.appointments):
            self.table.insertRow(i)
            def _item(text, right=False):
                it = QtWidgets.QTableWidgetItem("" if text is None else str(text))
                if right: it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                return it

            total_paid = _to_float(account.get("Total Paid", 0))
            total_amount = _to_float(account.get("Total Amount", 0))
            owed_val = total_amount - total_paid

            self.table.setItem(i, 0, _item(account.get("Name", "")))
            self.table.setItem(i, 1, _item(account.get("Age", "")))
            self.table.setItem(i, 2, _item(total_paid, True))
            self.table.setItem(i, 3, _item(owed_val, True))
            self.table.setItem(i, 4, _item(total_amount, True))

        self.updating_table = False
        self.table.setSortingEnabled(was_sorting)
        if was_sorting:
            self.table.sortItems(0, QtCore.Qt.AscendingOrder)
        self.table.resizeColumnsToContents()

    def on_cell_changed(self, row, column):
        if self.updating_table or column not in (2, 4):
            return
        total_paid = _to_float(self._txt(row, 2))
        total_amount = _to_float(self._txt(row, 4))
        owed = total_amount - total_paid
        self.table.blockSignals(True)
        item = QtWidgets.QTableWidgetItem(str(owed))
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.table.setItem(row, 3, item)
        self.table.blockSignals(False)
        name = self._txt(row, 0).strip().lower()
        for a in self.appointments:
            if (a.get("Name", "") or "").strip().lower() == name:
                a["Total Paid"] = total_paid; a["Total Amount"] = total_amount; a["Owed"] = owed
                break

    def _txt(self, r, c):
        it = self.table.item(r, c)
        return it.text() if it else ""

    # Open flows
    def _open_selected(self):
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            QtWidgets.QMessageBox.information(self, self.tr("Open"), self.tr("Select a client row first."))
            return
        self.open_account_detail(idxs[0])

    def open_account_detail(self, index):
        row = index.row() if isinstance(index, QtCore.QModelIndex) else int(index)
        if row < 0 or row >= self.table.rowCount():
            QtWidgets.QMessageBox.warning(self, self.tr("Open"), self.tr("Invalid row."))
            return
        client_name = (self.table.item(row, 0) or QtWidgets.QTableWidgetItem("")).text().strip()
        if not client_name:
            QtWidgets.QMessageBox.warning(self, self.tr("Open"), self.tr("No client name in this row."))
            return

        account_data = next((acc for acc in self.appointments
                             if (acc.get("Name", "") or "").strip().lower() == client_name.lower()), None)
        if not account_data:
            QtWidgets.QMessageBox.warning(self, self.tr("Open"),
                                          self.tr("Could not find this client in memory: ") + client_name)
            return

        try:
            dialog = ClientAccountPage(account_data, parent=self)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, self.tr("Open"),
                                           self.tr("Failed to open ClientAccountPage:\n") + str(e))
            return

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            updated_data = (dialog.get_updated_data() if hasattr(dialog, "get_updated_data")
                            else dialog.get_updated_client() if hasattr(dialog, "get_updated_client")
                            else account_data)
            update_account_in_db(client_name, updated_data)
            self._refresh_from_db()
            self.highlight_client(client_name)

    def highlight_client(self, client_name):
        key = (client_name or "").strip().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text().strip().lower() == key:
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it: it.setBackground(QtGui.QBrush(QtGui.QColor("#fff3cd")))
                self.table.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)
                break

    def save_all_changes(self):
        for row in range(self.table.rowCount()):
            name = self._txt(row, 0).strip()
            updated_data = {
                "Name": name,
                "Age": self._txt(row, 1).strip(),
                "Total Paid": self._txt(row, 2).strip(),
                "Owed": self._txt(row, 3).strip(),
                "Total Amount": self._txt(row, 4).strip(),
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