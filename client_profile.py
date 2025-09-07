# client_profile.py
from PyQt5 import QtWidgets, QtGui, QtCore
import os

class ClientProfile(QtWidgets.QDialog):
    def __init__(self, client: dict, parent=None):
        super().__init__(parent)
        self.client = dict(client or {})
        self.setWindowTitle("Client Profile"); self.resize(720, 520)
        self._build()

    def _build(self):
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(16,16,16,16)
        v.setSpacing(12)

        # Header card with image + basics
        top = QtWidgets.QFrame(); top.setProperty("modernCard", True)
        t = QtWidgets.QHBoxLayout(top); t.setContentsMargins(12,12,12,12); t.setSpacing(12)

        # Image
        self.img = QtWidgets.QLabel(); self.img.setFixedSize(140,140); self.img.setScaledContents(True)
        self._set_pix(self.client.get("Image"))
        pick = QtWidgets.QPushButton("Change photo"); pick.setProperty("variant", "ghost")
        pick.clicked.connect(self._pick)
        imgcol = QtWidgets.QVBoxLayout(); imgcol.addWidget(self.img, alignment=QtCore.Qt.AlignCenter); imgcol.addWidget(pick)
        t.addLayout(imgcol, 0)

        # Form
        formw = QtWidgets.QWidget(); form = QtWidgets.QFormLayout(formw); form.setSpacing(8)
        self.name = QtWidgets.QLineEdit(self.client.get("Name",""))
        self.age  = QtWidgets.QSpinBox(); self.age.setRange(0,120); self.age.setValue(int(self.client.get("Age",0)))
        self.total = QtWidgets.QDoubleSpinBox(); self.total.setRange(0,1e9); self.total.setDecimals(2); self.total.setValue(float(self.client.get("Total Amount",0)))
        self.paid  = QtWidgets.QDoubleSpinBox(); self.paid.setRange(0,1e9); self.paid.setDecimals(2); self.paid.setValue(float(self.client.get("Total Paid",0)))
        self.owed  = QtWidgets.QDoubleSpinBox(); self.owed.setRange(0,1e9); self.owed.setDecimals(2); self.owed.setValue(float(self.client.get("Owed",0)))
        self.notes = QtWidgets.QTextEdit(self.client.get("Notes","")); self.notes.setFixedHeight(100)

        form.addRow("Name", self.name)
        form.addRow("Age", self.age)
        form.addRow("Total Amount", self.total)
        form.addRow("Total Paid", self.paid)
        form.addRow("Owed", self.owed)
        form.addRow("Notes", self.notes)
        t.addWidget(formw, 1)

        v.addWidget(top)

        # Footer
        bar = QtWidgets.QHBoxLayout()
        bar.addStretch(1)
        cancel = QtWidgets.QPushButton("Cancel"); cancel.setProperty("variant","ghost"); cancel.clicked.connect(self.reject)
        save   = QtWidgets.QPushButton("Save"); save.clicked.connect(self.accept)
        bar.addWidget(cancel); bar.addWidget(save)
        v.addLayout(bar)

    def _set_pix(self, path):
        if path and os.path.exists(path):
            self.img.setPixmap(QtGui.QPixmap(path))
        else:
            pm = QtGui.QPixmap(140,140); pm.fill(QtGui.QColor("#1f2937"))
            p = QtGui.QPainter(pm); p.setPen(QtGui.QColor("#9ca3af"))
            p.drawText(pm.rect(), QtCore.Qt.AlignCenter, "No\nPhoto"); p.end()
            self.img.setPixmap(pm)

    def _pick(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose photo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if p:
            self.client["Image"] = p
            self._set_pix(p)

    def updated(self) -> dict:
        out = dict(self.client)
        out.update({
            "Name": self.name.text().strip() or "Unknown",
            "Age": int(self.age.value()),
            "Total Amount": float(self.total.value()),
            "Total Paid": float(self.paid.value()),
            "Owed": float(self.owed.value()),
            "Notes": self.notes.toPlainText().strip(),
        })
        return out
