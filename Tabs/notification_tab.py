from PyQt5 import QtWidgets, QtGui, QtCore

class NotificationManager(QtWidgets.QSystemTrayIcon):
    """
    Cross-platform system tray notifications.
    Usage:
        tray = NotificationManager(icon, parent_window)
        tray.show()
        tray.show_notification("Message", title="MediAgent AI")
    """
    def __init__(self, icon: QtGui.QIcon, parent=None):
        super().__init__(icon, parent)
        self.parent_window = parent
        self.setToolTip("MediAgent AI")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QtWidgets.QMenu()
        action_show = menu.addAction("Show")
        action_show.triggered.connect(self._show_parent)
        action_hide = menu.addAction("Hide")
        action_hide.triggered.connect(self._hide_parent)
        menu.addSeparator()
        action_quit = menu.addAction("Quit")
        action_quit.triggered.connect(QtWidgets.QApplication.instance().quit)
        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            if self.parent_window and self.parent_window.isVisible():
                self.parent_window.hide()
            else:
                self._show_parent()

    def _show_parent(self):
        if self.parent_window:
            self.parent_window.showNormal()
            self.parent_window.raise_()
            self.parent_window.activateWindow()

    def _hide_parent(self):
        if self.parent_window:
            self.parent_window.hide()

    def show_notification(self, message: str, title: str = "MediAgent AI", msecs: int = 4000):
        if self.supportsMessages():
            self.showMessage(title, message, QtWidgets.QSystemTrayIcon.Information, msecs)
        else:
            if self.parent_window and hasattr(self.parent_window, "statusBar"):
                try:
                    self.parent_window.statusBar().showMessage(f"{title}: {message}", msecs)
                except Exception:
                    pass
