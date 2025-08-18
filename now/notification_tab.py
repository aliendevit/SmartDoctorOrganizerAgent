# notification_tab.py
from PyQt5 import QtWidgets, QtGui, QtCore

class NotificationManager(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)
        self.setToolTip("MediNote AI Notifications")
        menu = QtWidgets.QMenu(parent)
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(QtWidgets.qApp.quit)
        self.setContextMenu(menu)

    def show_notification(self, title, message, duration=5000):
        self.showMessage(title, message, QtGui.QIcon(), duration)
