# ui/safety.py
from PyQt5 import QtWidgets, QtCore
def confirm(parent, title, text) -> bool:
    return QtWidgets.QMessageBox.question(parent, title, text) == QtWidgets.QMessageBox.Yes

class UndoBanner(QtWidgets.QWidget):
    undone = QtCore.pyqtSignal()
    def __init__(self, msg="Deleted", parent=None):
        super().__init__(parent)
        lay = QtWidgets.QHBoxLayout(self); lay.setContentsMargins(10,6,10,6)
        lab = QtWidgets.QLabel(msg); btn = QtWidgets.QPushButton("Undo"); btn.setProperty("variant","ghost")
        lay.addWidget(lab); lay.addStretch(1); lay.addWidget(btn)
        btn.clicked.connect(self.undone.emit)

