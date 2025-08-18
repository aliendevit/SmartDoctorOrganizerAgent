import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from home_page import HomePage
from Tabs.notification_tab import NotificationManager


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MediAgent AI: Home version 1.0")
        self.resize(1200, 900)
        self.setup_notifications()
        self.setup_ui()
        self.setup_menus()
        self.apply_styles()

    def setup_notifications(self):
        self.tray_icon = NotificationManager(self.get_icon(), self)
        self.tray_icon.show()
        self.tray_icon.show_notification("MediAgent AI", "Application started successfully!")

    def get_icon(self):
        icon = QtGui.QIcon("icon.png")
        if icon.isNull():
            pixmap = QtGui.QPixmap(64, 64)
            pixmap.fill(QtGui.QColor("blue"))
            icon = QtGui.QIcon(pixmap)
        return icon

    def setup_ui(self):
        self.home_page = HomePage()
        self.setCentralWidget(self.home_page)

    def setup_menus(self):
        menubar = self.menuBar()
        # language_menu = menubar.addMenu(tr("Language"))
        # english_action = QtWidgets.QAction("English", self)
        # arabic_action = QtWidgets.QAction("العربية", self)
        # english_action.triggered.connect(lambda: self.switch_language("en"))
        # arabic_action.triggered.connect(lambda: self.switch_language("ar"))
        # language_menu.addAction(english_action)
        # language_menu.addAction(arabic_action)

    def switch_language(self, lang):
        import translation_helper
        translation_helper.current_lang = lang
        if lang == "ar":
            self.setLayoutDirection(QtCore.Qt.RightToLeft)
        else:
            self.setLayoutDirection(QtCore.Qt.LeftToRight)
        for index in range(self.home_page.tabs.count()):
            widget = self.home_page.tabs.widget(index)
            if hasattr(widget, "retranslateUi"):
                widget.retranslateUi()
            current_title = self.home_page.tabs.tabText(index)
            self.home_page.tabs.setTabText(index, translation_helper.tr(current_title))

    def apply_styles(self):
        style = """
        QMainWindow {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #F7F8FA,
                stop:1 #E6EBF1
            );
        }
        QWidget {
            color: #202123;
            font-family: "Inter", "Segoe UI", Arial, sans-serif;
            font-size: 12px;
        }
        QLabel {
            color: #202123;
        }
        QTextEdit, QLineEdit {
            background-color: #FFFFFF;
            color: #202123;
            border: 1px solid #E1E4E8;
            border-radius: 8px;
            padding: 12px;
        }
        QPushButton {
            background-color: #007AFF;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 16px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #005BB5;
        }
        QTableWidget {
            background-color: #FFFFFF;
            color: #202123;
            border: 1px solid #E1E4E8;
            border-radius: 8px;
        }
        QHeaderView::section {
            background-color: #F0F0F0;
            padding: 10px;
            border: none;
            font-size: 16px;
            color: #202123;
        }
        QTabWidget::pane {
            border: 1px solid #E1E4E8;
            border-radius: 8px;
            margin-top: -1px;
        }
        QTabBar::tab {
            background: #FFFFFF;
            padding: 10px 20px;
            margin: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border: 1px solid #E1E4E8;
        }
        QTabBar::tab:selected {
            background: #007AFF;
            color: white;
        }
        """
        self.setStyleSheet(style)

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
