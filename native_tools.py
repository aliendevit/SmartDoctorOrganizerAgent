# native_tools.py
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

def open_native(path: str, parent=None):
    if not path:
        QtWidgets.QMessageBox.information(parent, "Open", "No file to open.")
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def notify(parent, title: str, body: str):
    # Uses tray if available; falls back to dialog
    tray = getattr(parent, "_tray", None)
    if tray is None:
        tray = QtWidgets.QSystemTrayIcon(parent)
        tray.setIcon(parent.windowIcon() if parent and parent.windowIcon() else QtGui.QIcon())
        tray.setVisible(True)
        parent._tray = tray
    tray.showMessage(title, body, QtWidgets.QSystemTrayIcon.Information, 5000)
