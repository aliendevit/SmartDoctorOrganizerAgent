from PyQt5 import QtWidgets, QtGui, QtCore
import os

class ClientAccountPage(QtWidgets.QDialog):
    """
    Modern client account dialog with image support.
    Expected to receive a client dict like:
      {"Name": "...", "Age": 34, "Total Paid": 200, "Owed": 50, "Total Amount": 250, "Image": "path/to.jpg"}
    """
    def __init__(self, client=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Client Account")
        self.resize(700, 520)
        self.client = client or {}
        self._build()

    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Top card with image + basics
        top = QtWidgets.QFrame()
        top.setProperty("modernCard", True)
        tly = QtWidgets.QHBoxLayout(top)
        tly.setContentsMargins(12, 12, 12, 12)
        tly.setSpacing(12)

        # Image
        self.image_label = QtWidgets.QLabel()
        self.image_label.setFixedSize(140, 140)
        self.image_label.setStyleSheet("border-radius: 12px;")
        self.image_label.setScaledContents(True)
        img_path = self.client.get("Image")
        if img_path and os.path.exists(img_path):
            self.image_label.setPixmap(QtGui.QPixmap(img_path))
        else:
            # Placeholder
            pm = QtGui.QPixmap(140, 140)
            pm.fill(QtGui.QColor("#1f2937"))
            painter = QtGui.QPainter(pm)
            painter.setPen(QtGui.QColor("#9ca3af"))
            painter.drawText(pm.rect(), QtCore.Qt.AlignCenter, "No\nPhoto")
            painter.end()
            self.image_label.setPixmap(pm)

        img_col = QtWidgets.QVBoxLayout()
        change_btn = QtWidgets.QPushButton("Change photo")
        change_btn.setProperty("variant", "ghost")
        change_btn.clicked.connect(self._choose_image)
        img_col.addWidget(self.image_label, alignment=QtCore.Qt.AlignCenter)
        img_col.addWidget(change_btn, alignment=QtCore.Qt.AlignCenter)

        tly.addLayout(img_col, 0)

        # Basic info form
        info = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(info)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.name_edit = QtWidgets.QLineEdit(self.client.get("Name", ""))
        self.age_spin  = QtWidgets.QSpinBox()
        self.age_spin.setRange(0, 120)
        self.age_spin.setValue(int(self.client.get("Age", 0)))

        self.paid_spin = QtWidgets.QDoubleSpinBox()
        self.paid_spin.setRange(0, 1e9)
        self.paid_spin.setDecimals(2)
        self.paid_spin.setValue(float(self.client.get("Total Paid", 0)))

        self.owed_spin = QtWidgets.QDoubleSpinBox()
        self.owed_spin.setRange(0, 1e9)
        self.owed_spin.setDecimals(2)
        self.owed_spin.setValue(float(self.client.get("Owed", 0)))

        self.total_spin = QtWidgets.QDoubleSpinBox()
        self.total_spin.setRange(0, 1e9)
        self.total_spin.setDecimals(2)
        self.total_spin.setValue(float(self.client.get("Total Amount", 0)))

        self.notes_edit = QtWidgets.QTextEdit(self.client.get("Notes", ""))
        self.notes_edit.setFixedHeight(80)

        form.addRow("Name", self.name_edit)
        form.addRow("Age", self.age_spin)
        form.addRow("Total Paid", self.paid_spin)
        form.addRow("Owed", self.owed_spin)
        form.addRow("Total Amount", self.total_spin)
        form.addRow("Notes", self.notes_edit)

        tly.addWidget(info, 1)

        lay.addWidget(top)

        # Actions
        bar = QtWidgets.QHBoxLayout()
        bar.addStretch(1)
        self.save_btn = QtWidgets.QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setProperty("variant", "ghost")
        self.cancel_btn.clicked.connect(self.reject)
        bar.addWidget(self.cancel_btn)
        bar.addWidget(self.save_btn)

        lay.addLayout(bar)

    def _choose_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose photo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.client["Image"] = path
            self.image_label.setPixmap(QtGui.QPixmap(path))

    def get_updated_client(self):
        # Return updated dict (does not persist to DB here)
        out = dict(self.client)
        out.update({
            "Name": self.name_edit.text().strip(),
            "Age": self.age_spin.value(),
            "Total Paid": float(self.paid_spin.value()),
            "Owed": float(self.owed_spin.value()),
            "Total Amount": float(self.total_spin.value()),
            "Notes": self.notes_edit.toPlainText().strip(),
        })
        return out
