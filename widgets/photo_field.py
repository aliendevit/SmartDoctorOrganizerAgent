# widgets/photo_field.py
from PyQt5 import QtCore, QtGui, QtWidgets

ACCEPTED = ["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif"]

class PhotoField(QtWidgets.QFrame):
    imageChanged = QtCore.pyqtSignal(QtGui.QPixmap, str)  # (pixmap, path or "")

    def __init__(self, parent=None, *, min_size=(320, 180), max_px=512):
        super().__init__(parent)
        self.setObjectName("GlassPanel")           # picks up your glass style
        self.setAcceptDrops(True)
        self._max_px = max_px
        self._path = ""

        # --- critical: tell layouts how big we want to be
        self._min_w, self._min_h = min_size
        self.setMinimumSize(self._min_w, self._min_h)
        sp = self.sizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Fixed)   # <— keeps row height!
        self.setSizePolicy(sp)

        # UI
        self._preview = QtWidgets.QLabel("Drop photo here or Click ‘Choose’", self)
        self._preview.setAlignment(QtCore.Qt.AlignCenter)
        self._preview.setWordWrap(True)
        self._preview.setScaledContents(False)
        self._preview.setStyleSheet("QLabel{font-size:12px; color:#9AA4B2;}")

        self._choose = QtWidgets.QPushButton("Choose")
        self._clear  = QtWidgets.QPushButton("Clear")
        self._clear.setVisible(False)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self._choose)
        btns.addWidget(self._clear)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)
        lay.addWidget(self._preview, 1)
        lay.addLayout(btns, 0)

        # Visuals (works with dark/glass)
        self.setStyleSheet("""
        QFrame#GlassPanel {
            background: rgba(255,255,255,0.50);
            border-radius: 12px;
            border: 1px dashed rgba(122,119,255,0.6);
        }
        QFrame#GlassPanel:hover {
            border: 1px dashed rgba(58,141,255,0.9);
            background: rgba(255,255,255,0.60);
        }
        """)

        self._choose.clicked.connect(self._pick_file)
        self._clear.clicked.connect(self.clear_image)

    # --- size hints so the form reserves vertical space
    def sizeHint(self):
        return QtCore.QSize(self._min_w, self._min_h)

    def minimumSizeHint(self):
        return QtCore.QSize(self._min_w, self._min_h)

    # ---------- Public API ----------
    def imagePath(self) -> str:
        return self._path

    def setImagePath(self, path: str):
        if not path:
            self.clear_image(); return
        pm = QtGui.QPixmap(path)
        if pm.isNull():
            self._flash_error("Unsupported or missing image."); return
        self._set_pixmap(pm, path)

    # ---------- DnD ----------
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                lp = u.toLocalFile().lower()
                if any(lp.endswith(ext[1:]) for ext in ACCEPTED):
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e: QtGui.QDropEvent):
        for u in e.mimeData().urls():
            self.setImagePath(u.toLocalFile())
            break

    # ---------- Internals ----------
    def _pick_file(self):
        filt = "Images ({})".format(" ".join(ACCEPTED))
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Photo", "", filt)
        if path:
            self.setImagePath(path)

    def _set_pixmap(self, pm: QtGui.QPixmap, path: str):
        if max(pm.width(), pm.height()) > self._max_px:
            pm = pm.scaled(self._max_px, self._max_px,
                           QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self._preview.setPixmap(pm)
        self._preview.setText("")
        self._preview.setAlignment(QtCore.Qt.AlignCenter)
        self._clear.setVisible(True)
        self._path = path
        self.imageChanged.emit(pm, path)

    def clear_image(self):
        self._preview.clear()
        self._preview.setText("Drop photo here or Click ‘Choose’")
        self._preview.setAlignment(QtCore.Qt.AlignCenter)
        self._clear.setVisible(False)
        self._path = ""
        self.imageChanged.emit(QtGui.QPixmap(), "")

    def _flash_error(self, msg: str):
        old = self.styleSheet()
        self.setStyleSheet(old + "QFrame#GlassPanel{border:1px solid #FF6B6B;}")
        QtCore.QTimer.singleShot(800, lambda: self.setStyleSheet(old))
        QtWidgets.QToolTip.showText(self.mapToGlobal(self.rect().center()), msg, self)
