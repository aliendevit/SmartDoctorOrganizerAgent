import json
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QDate
from data.data import load_all_clients  # Also used by AccountsTab

# Robust archive path (relative to this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_FILE = os.path.normpath(os.path.join(BASE_DIR, "..", "json", "monthly_receipts_archive.json"))

def _polish(*widgets):
    """Re-apply QSS after setting dynamic properties (for ModernTheme dynamic props)."""
    for w in widgets:
        try:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()
        except Exception:
            pass

class DashboardTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_clients_cache = []
        self._outstanding_cache = []  # raw list for filtering
        self.setup_ui()
        self.load_archive()
        self.refresh_data()

    # Shared translation helper
    def tr(self, text):
        try:
            from translation_helper import tr
            return tr(text)
        except Exception:
            return text

    # --------------- UI ---------------
    def setup_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== Header (title + period quick presets + days spin + refresh all) =====
        header_card = QtWidgets.QFrame()
        header_card.setProperty("modernCard", True)
        h = QtWidgets.QHBoxLayout(header_card)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(10)

        self.title = QtWidgets.QLabel(self.tr("Practice Dashboard"))
        self.title.setStyleSheet("font-size: 18px; font-weight: 700;")
        h.addWidget(self.title)

        h.addStretch(1)

        # quick presets (don’t hard-code colors; use accent props)
        self.btn_7d = QtWidgets.QPushButton(self.tr("7d"))
        self.btn_30d = QtWidgets.QPushButton(self.tr("30d"))
        self.btn_90d = QtWidgets.QPushButton(self.tr("90d"))
        self.btn_365d = QtWidgets.QPushButton(self.tr("365d"))

        for b in (self.btn_7d, self.btn_30d, self.btn_90d, self.btn_365d):
            # b.setProperty("variant", "ghost")
            b.setProperty("accent", "slate")
            b.setCheckable(True)
        self.btn_30d.setChecked(True)  # default
        _polish(self.btn_7d, self.btn_30d, self.btn_90d, self.btn_365d)

        self._preset_group = QtWidgets.QButtonGroup(self)
        for b in (self.btn_7d, self.btn_30d, self.btn_90d, self.btn_365d):
            self._preset_group.addButton(b)
        self._preset_group.buttonClicked.connect(self._apply_preset_days)

        h.addWidget(self.btn_7d)
        h.addWidget(self.btn_30d)
        h.addWidget(self.btn_90d)
        h.addWidget(self.btn_365d)

        self.period_label = QtWidgets.QLabel(self.tr("Days:"))
        self.inventory_days_spinbox = QtWidgets.QSpinBox()
        self.inventory_days_spinbox.setRange(1, 365)
        self.inventory_days_spinbox.setValue(30)
        self.inventory_days_spinbox.valueChanged.connect(self.refresh_data)
        h.addWidget(self.period_label)
        h.addWidget(self.inventory_days_spinbox)

        self.btn_refresh_all = QtWidgets.QPushButton(self.tr("Refresh All"))
        self.btn_refresh_all.setProperty("accent", "violet")
        self.btn_refresh_all.clicked.connect(self.refresh_data)
        _polish(self.btn_refresh_all)

        h.addWidget(self.btn_refresh_all)
        root.addWidget(header_card)

        # ===== Splitter: Left (KPIs & Summary) | Right (Tables) =====
        split = QtWidgets.QSplitter()
        split.setOrientation(QtCore.Qt.Horizontal)
        root.addWidget(split, 1)

        # ----- LEFT COLUMN -----
        left = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(left)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(12)

        # KPI tiles (2x2 grid)
        kpi_card = QtWidgets.QFrame()
        kpi_card.setProperty("modernCard", True)
        kg = QtWidgets.QGridLayout(kpi_card)
        kg.setContentsMargins(12, 12, 12, 12)
        kg.setHorizontalSpacing(10)
        kg.setVerticalSpacing(10)

        def _make_kpi(title_text):
            box = QtWidgets.QFrame()
            box.setProperty("modernCard", True)
            vb = QtWidgets.QVBoxLayout(box)
            vb.setContentsMargins(10, 10, 10, 10)
            vb.setSpacing(6)
            value = QtWidgets.QLabel("—")
            value.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            value.setStyleSheet("font-size: 22px; font-weight: 700;")
            title = QtWidgets.QLabel(title_text)
            title.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            title.setStyleSheet("font-size: 12px; font-weight: 600;")
            vb.addWidget(value)
            vb.addWidget(title)
            return box, value

        self.kpi_total_clients_card, self.kpi_total_clients_value = _make_kpi(self.tr("Total Clients"))
        self.kpi_total_revenue_card, self.kpi_total_revenue_value = _make_kpi(self.tr("Total Revenue"))
        self.kpi_total_outstanding_card, self.kpi_total_outstanding_value = _make_kpi(self.tr("Total Outstanding"))
        self.kpi_unpaid_clients_card, self.kpi_unpaid_clients_value = _make_kpi(self.tr("Unpaid Clients"))

        kg.addWidget(self.kpi_total_clients_card,   0, 0)
        kg.addWidget(self.kpi_total_revenue_card,   0, 1)
        kg.addWidget(self.kpi_total_outstanding_card, 1, 0)
        kg.addWidget(self.kpi_unpaid_clients_card,  1, 1)

        l.addWidget(kpi_card)

        # Inventory / Period summary card (with actions)
        inv_card = QtWidgets.QFrame()
        inv_card.setProperty("modernCard", True)
        ily = QtWidgets.QVBoxLayout(inv_card)
        ily.setContentsMargins(12, 12, 12, 12)
        ily.setSpacing(8)

        self.inventory_title = QtWidgets.QLabel(self.tr("Inventory Summary"))
        self.inventory_title.setStyleSheet("font-weight: 700;")
        ily.addWidget(self.inventory_title)

        self.current_inventory_label = QtWidgets.QLabel(self.tr("Loading inventory summary..."))
        self.current_inventory_label.setStyleSheet("font-weight: 600;")
        ily.addWidget(self.current_inventory_label)

        il_actions = QtWidgets.QHBoxLayout()
        il_actions.setSpacing(8)

        self.show_unpaid_btn = QtWidgets.QPushButton(self.tr("Show Unpaid Clients"))
        self.show_unpaid_btn.setProperty("variant", "danger")   # red (theme)
        self.show_unpaid_btn.clicked.connect(self.show_unpaid_clients)

        self.archive_button = QtWidgets.QPushButton(self.tr("Archive Inventory"))
        self.archive_button.setProperty("variant", "warning")   # amber (theme)
        self.archive_button.clicked.connect(self.archive_current_period)

        il_actions.addWidget(self.show_unpaid_btn)
        il_actions.addStretch(1)
        il_actions.addWidget(self.archive_button)
        _polish(self.show_unpaid_btn, self.archive_button)

        ily.addLayout(il_actions)
        l.addWidget(inv_card)

        l.addStretch(1)
        split.addWidget(left)

        # ----- RIGHT COLUMN -----
        right = QtWidgets.QWidget()
        r = QtWidgets.QVBoxLayout(right)
        r.setContentsMargins(0, 0, 0, 0)
        r.setSpacing(12)

        # Outstanding card with search/filter + table + inline summary
        out_card = QtWidgets.QFrame()
        out_card.setProperty("modernCard", True)
        og = QtWidgets.QVBoxLayout(out_card)
        og.setContentsMargins(12, 12, 12, 12)
        og.setSpacing(8)

        out_top = QtWidgets.QHBoxLayout()
        out_top.setSpacing(8)
        out_title = QtWidgets.QLabel(self.tr("Outstanding Payments"))
        out_title.setStyleSheet("font-weight: 700;")
        out_top.addWidget(out_title)

        out_top.addStretch(1)

        self.search_line = QtWidgets.QLineEdit()
        self.search_line.setPlaceholderText(self.tr("Search by name…"))
        self.search_line.textChanged.connect(self._apply_outstanding_filters)
        out_top.addWidget(self.search_line)

        self.min_out_spin = QtWidgets.QDoubleSpinBox()
        self.min_out_spin.setRange(0.0, 10_000_000.0)
        self.min_out_spin.setDecimals(2)
        self.min_out_spin.setPrefix(self.tr("Min: "))
        self.min_out_spin.valueChanged.connect(self._apply_outstanding_filters)
        out_top.addWidget(self.min_out_spin)

        self.refresh_outstanding_btn = QtWidgets.QPushButton(self.tr("Refresh"))
        self.refresh_outstanding_btn.setProperty("accent", "violet")
        self.refresh_outstanding_btn.clicked.connect(self.refresh_data)
        _polish(self.refresh_outstanding_btn)
        out_top.addWidget(self.refresh_outstanding_btn)

        og.addLayout(out_top)

        # quick summary line for outstanding
        self.outstanding_label = QtWidgets.QLabel(self.tr("Loading outstanding payments..."))
        self.outstanding_label.setStyleSheet("font-weight: 600;")
        og.addWidget(self.outstanding_label)

        self.outstanding_table = QtWidgets.QTableWidget()
        self.outstanding_table.setColumnCount(4)
        self.outstanding_table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Total Amount"), self.tr("Total Paid"), self.tr("Outstanding")
        ])
        self.outstanding_table.horizontalHeader().setStretchLastSection(True)
        self.outstanding_table.verticalHeader().setVisible(False)
        self.outstanding_table.setAlternatingRowColors(True)
        self.outstanding_table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.outstanding_table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        og.addWidget(self.outstanding_table, 1)

        r.addWidget(out_card, 2)

        # Archive card (history)
        arch_card = QtWidgets.QFrame()
        arch_card.setProperty("modernCard", True)
        ag = QtWidgets.QVBoxLayout(arch_card)
        ag.setContentsMargins(12, 12, 12, 12)
        ag.setSpacing(8)

        arch_top = QtWidgets.QHBoxLayout()
        arch_top.setSpacing(8)
        arch_title = QtWidgets.QLabel(self.tr("Archived Inventory"))
        arch_title.setStyleSheet("font-weight: 700;")
        arch_top.addWidget(arch_title)
        arch_top.addStretch(1)

        self.btn_open_archive = QtWidgets.QPushButton(self.tr("Open Archive Folder"))
        # self.btn_open_archive.setProperty("variant", "ghost")
        self.btn_open_archive.setProperty("accent", "sky")
        self.btn_open_archive.clicked.connect(self._open_archive_folder)
        _polish(self.btn_open_archive)
        arch_top.addWidget(self.btn_open_archive)

        ag.addLayout(arch_top)

        self.archive_table = QtWidgets.QTableWidget()
        self.archive_table.setColumnCount(4)
        self.archive_table.setHorizontalHeaderLabels([
            self.tr("Period"), self.tr("Total Receipts"), self.tr("Total Outstanding"), self.tr("Unpaid Clients")
        ])
        self.archive_table.horizontalHeader().setStretchLastSection(True)
        self.archive_table.verticalHeader().setVisible(False)
        self.archive_table.setAlternatingRowColors(True)
        self.archive_table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.archive_table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        ag.addWidget(self.archive_table, 1)

        r.addWidget(arch_card, 1)
        split.addWidget(right)

        # make left column a bit narrower initially
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)

        root.addStretch(0)

    # --------------- Logic ---------------
    def _apply_preset_days(self, btn: QtWidgets.QAbstractButton):
        text = btn.text().lower()
        mapping = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
        self.inventory_days_spinbox.blockSignals(True)
        self.inventory_days_spinbox.setValue(mapping.get(text, 30))
        self.inventory_days_spinbox.blockSignals(False)
        self.refresh_data()

    def refresh_data(self):
        clients = load_all_clients()
        self._all_clients_cache = clients[:]  # for future extensions

        # --- Outstanding ---
        outstanding_clients = []
        for client in clients:
            try:
                total_amount = float(client.get("Total Amount", 0))
                total_paid = float(client.get("Total Paid", 0))
            except (ValueError, TypeError):
                total_amount = total_paid = 0.0
            if total_paid < total_amount:
                outstanding_clients.append({
                    "Name": client.get("Name", "") or self.tr("Unknown"),
                    "Total Amount": total_amount,
                    "Total Paid": total_paid,
                    "Outstanding": max(0.0, total_amount - total_paid)
                })

        self._outstanding_cache = outstanding_clients  # keep raw list for filters
        # Show filtered view according to current search/min
        self._apply_outstanding_filters()

        # --- Period summary (days window) ---
        days = self.inventory_days_spinbox.value()
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        total_paid_period = 0.0
        total_outstanding_period = 0.0
        num_unpaid_period = 0

        for client in clients:
            date_obj = QDate.fromString(client.get("Date", ""), "dd-MM-yyyy")
            if date_obj.isValid() and start_date <= date_obj <= end_date:
                try:
                    tp = float(client.get("Total Paid", 0))
                    ta = float(client.get("Total Amount", 0))
                except (ValueError, TypeError):
                    tp = ta = 0.0
                total_paid_period += tp
                if tp < ta:
                    total_outstanding_period += (ta - tp)
                    num_unpaid_period += 1

        period_label = f"{start_date.toString('dd-MM-yyyy')} {self.tr('to')} {end_date.toString('dd-MM-yyyy')}"
        self.current_inventory_label.setText(
            f"{period_label} — {self.tr('Total Receipts:')} {total_paid_period:,.2f} | "
            f"{self.tr('Outstanding:')} {total_outstanding_period:,.2f} | "
            f"{self.tr('Unpaid Clients:')} {num_unpaid_period}"
        )

        # --- Client Summary (overall) -> KPI tiles ---
        total_clients = len(clients)
        ages = []
        total_revenue = 0.0
        total_outstanding_all = 0.0
        total_unpaid = 0

        for client in clients:
            try:
                age_val = float(client.get("Age", 0))
                ages.append(age_val)
            except (ValueError, TypeError):
                pass
            try:
                tp = float(client.get("Total Paid", 0))
                ta = float(client.get("Total Amount", 0))
                total_revenue += tp
                if tp < ta:
                    total_outstanding_all += (ta - tp)
                    total_unpaid += 1
            except (ValueError, TypeError):
                pass

        self._update_kpis(
            total_clients=total_clients,
            total_revenue=total_revenue,
            total_outstanding=total_outstanding_all,
            unpaid_clients=total_unpaid
        )

    def _update_kpis(self, total_clients: int, total_revenue: float, total_outstanding: float, unpaid_clients: int):
        self.kpi_total_clients_value.setText(f"{total_clients:,}")
        self.kpi_total_revenue_value.setText(f"{total_revenue:,.2f}")
        self.kpi_total_outstanding_value.setText(f"{total_outstanding:,.2f}")
        self.kpi_unpaid_clients_value.setText(f"{unpaid_clients:,}")

    def _apply_outstanding_filters(self):
        # filter by name substring + min outstanding
        query = (self.search_line.text() or "").strip().lower()
        min_out = float(self.min_out_spin.value())
        data = []
        total_out = 0.0

        for item in self._outstanding_cache:
            if query and query not in (item["Name"] or "").lower():
                continue
            if item["Outstanding"] < min_out:
                continue
            data.append(item)
            total_out += item["Outstanding"]

        # Update quick line
        self.outstanding_label.setText(
            f"{self.tr('Patients with outstanding payments:')} {len(data)} | "
            f"{self.tr('Total Outstanding:')} {total_out:,.2f}"
        )
        self.populate_outstanding_table(data)

    def populate_outstanding_table(self, data):
        self.archive_table.clearSelection()
        self.outstanding_table.setRowCount(0)
        # highest outstanding on top
        for row, item in enumerate(sorted(data, key=lambda x: x["Outstanding"], reverse=True)):
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
        clients = self._all_clients_cache or load_all_clients()
        for client in clients:
            date_obj = QDate.fromString(client.get("Date", ""), "dd-MM-yyyy")
            if date_obj.isValid() and start_date <= date_obj <= end_date:
                try:
                    tp = float(client.get("Total Paid", 0))
                    ta = float(client.get("Total Amount", 0))
                except (ValueError, TypeError):
                    continue
                if tp < ta:
                    unpaid_names.append(client.get("Name", self.tr("Unknown")))
        if unpaid_names:
            QtWidgets.QMessageBox.information(
                self, self.tr("Unpaid Clients"),
                self.tr("Clients with outstanding payments:\n") + "\n".join(unpaid_names)
            )
        else:
            QtWidgets.QMessageBox.information(
                self, self.tr("Unpaid Clients"),
                self.tr("All clients have fully paid in the selected period.")
            )

    def archive_current_period(self):
        os.makedirs(os.path.dirname(ARCHIVE_FILE), exist_ok=True)
        days = self.inventory_days_spinbox.value()
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days)
        period_label = f"{start_date.toString('dd-MM-yyyy')} {self.tr('to')} {end_date.toString('dd-MM-yyyy')}"

        clients = self._all_clients_cache or load_all_clients()
        total_paid_period = 0.0
        total_outstanding_period = 0.0
        num_unpaid_period = 0

        for client in clients:
            date_obj = QDate.fromString(client.get("Date", ""), "dd-MM-yyyy")
            if date_obj.isValid() and start_date <= date_obj <= end_date:
                try:
                    tp = float(client.get("Total Paid", 0))
                    ta = float(client.get("Total Amount", 0))
                except (ValueError, TypeError):
                    tp = ta = 0.0
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
            try:
                with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                    archive = json.load(f)
            except Exception:
                archive = []

        # upsert
        updated = False
        for entry in archive:
            if entry.get("period") == period_label:
                entry.update(period_summary)
                updated = True
                break
        if not updated:
            archive.append(period_summary)

        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(archive, f, indent=4, ensure_ascii=False)

        self.load_archive()
        QtWidgets.QMessageBox.information(
            self, self.tr("Archive"),
            self.tr("Summary for ") + period_label + self.tr(" archived successfully.")
        )

    def _to_float(self, v):
        try:
            return float(str(v).replace(",", "").strip())
        except Exception:
            return 0.0

    def load_archive(self):
        archive = []
        if os.path.exists(ARCHIVE_FILE):
            try:
                with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                    archive = json.load(f)
            except Exception:
                archive = []

        self.archive_table.setRowCount(0)
        for row, entry in enumerate(archive):
            self.archive_table.insertRow(row)
            period = entry.get("period", "")
            receipts = self._to_float(entry.get("total_receipts", 0))
            outstanding = self._to_float(entry.get("total_outstanding", 0))
            unpaid = entry.get("unpaid_clients", 0)
            self.archive_table.setItem(row, 0, QtWidgets.QTableWidgetItem(period))
            self.archive_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{receipts:,.2f}"))
            self.archive_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{outstanding:,.2f}"))
            self.archive_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(unpaid)))

    def _open_archive_folder(self):
        folder = os.path.dirname(ARCHIVE_FILE)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))

    # --------------- i18n refresh ---------------
    def retranslateUi(self):
        self.title.setText(self.tr("Practice Dashboard"))
        self.btn_7d.setText(self.tr("7d"))
        self.btn_30d.setText(self.tr("30d"))
        self.btn_90d.setText(self.tr("90d"))
        self.btn_365d.setText(self.tr("365d"))
        self.period_label.setText(self.tr("Days:"))
        self.btn_refresh_all.setText(self.tr("Refresh All"))

        self.inventory_title.setText(self.tr("Inventory Summary"))
        self.current_inventory_label.setText(self.tr("Loading inventory summary..."))
        self.show_unpaid_btn.setText(self.tr("Show Unpaid Clients"))
        self.archive_button.setText(self.tr("Archive Inventory"))

        self.outstanding_label.setText(self.tr("Loading outstanding payments..."))
        self.outstanding_table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Total Amount"), self.tr("Total Paid"), self.tr("Outstanding")
        ])
        self.refresh_outstanding_btn.setText(self.tr("Refresh"))

        self.btn_open_archive.setText(self.tr("Open Archive Folder"))
        self.archive_table.setHorizontalHeaderLabels([
            self.tr("Period"), self.tr("Total Receipts"), self.tr("Total Outstanding"), self.tr("Unpaid Clients")
        ])

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        from modern_theme import ModernTheme
        ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
    except Exception:
        pass
    w = DashboardTab()
    w.resize(1100, 760)
    w.show()
    sys.exit(app.exec_())
