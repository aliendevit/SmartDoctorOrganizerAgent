from PyQt5 import QtWidgets, QtCore
import json, os

# Use your data layer if present; else write to a local JSON file as a fallback
try:
    from data.data import insert_client
except Exception:
    def insert_client(client_dict):
        path = "clients_local.json"
        data = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.append(client_dict)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

class ClientManagementTab(QtWidgets.QWidget):
    """Manual add/load client tab wrapped in a modern card."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        card = QtWidgets.QFrame()
        card.setProperty("modernCard", True)
        ly = QtWidgets.QFormLayout(card)
        ly.setLabelAlignment(QtCore.Qt.AlignLeft)
        ly.setContentsMargins(12, 12, 12, 12)
        ly.setSpacing(10)

        self.name = QtWidgets.QLineEdit()
        self.age  = QtWidgets.QSpinBox(); self.age.setRange(0, 120)
        self.date = QtWidgets.QDateEdit(QtCore.QDate.currentDate()); self.date.setCalendarPopup(True)
        self.time = QtWidgets.QTimeEdit(QtCore.QTime.currentTime())
        self.symp = QtWidgets.QLineEdit()
        self.total = QtWidgets.QDoubleSpinBox(); self.total.setRange(0, 1e9); self.total.setDecimals(2)
        self.paid  = QtWidgets.QDoubleSpinBox(); self.paid.setRange(0, 1e9); self.paid.setDecimals(2)
        self.owed  = QtWidgets.QDoubleSpinBox(); self.owed.setRange(0, 1e9); self.owed.setDecimals(2)

        ly.addRow("Client name", self.name)
        ly.addRow("Age", self.age)
        ly.addRow("Date", self.date)
        ly.addRow("Time", self.time)
        ly.addRow("Symptoms", self.symp)
        ly.addRow("Total Amount", self.total)
        ly.addRow("Total Paid", self.paid)
        ly.addRow("Owed", self.owed)

        btns = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("Load from JSON…")
        self.load_btn.setProperty("variant", "ghost")
        self.load_btn.clicked.connect(self._load_from_json)

        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.setProperty("variant", "ghost")
        self.clear_btn.clicked.connect(self._clear_form)

        self.add_btn = QtWidgets.QPushButton("Add client")
        self.add_btn.clicked.connect(self._add_client)

        btns.addWidget(self.load_btn)
        btns.addStretch(1)
        btns.addWidget(self.clear_btn)
        btns.addWidget(self.add_btn)

        root.addWidget(card)
        root.addLayout(btns)

        self.status = QtWidgets.QLabel("")
        root.addWidget(self.status)

    def _clear_form(self):
        self.name.clear()
        self.age.setValue(0)
        self.date.setDate(QtCore.QDate.currentDate())
        self.time.setTime(QtCore.QTime.currentTime())
        self.symp.clear()
        self.total.setValue(0)
        self.paid.setValue(0)
        self.owed.setValue(0)

    def _add_client(self):
        c = {
            "Name": self.name.text().strip(),
            "Age": int(self.age.value()),
            "Date": self.date.date().toString("dd-MM-yyyy"),
            "Time": self.time.time().toString("HH:mm"),
            "Symptoms": [s.strip() for s in self.symp.text().split(",") if s.strip()],
            "Total Amount": float(self.total.value()),
            "Total Paid": float(self.paid.value()),
            "Owed": float(self.owed.value()),
        }
        ok = insert_client(c)
        self.status.setText("✅ Client added" if ok else "❌ Failed to add client")

    def _load_from_json(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose JSON file", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            for item in data if isinstance(data, list) else [data]:
                if insert_client(item):
                    count += 1
            self.status.setText(f"✅ Imported {count} clients from JSON")
        except Exception as e:
            self.status.setText(f"❌ Failed: {e}")
