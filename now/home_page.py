from PyQt5 import QtWidgets
from Tabs.dashboard_tab import DashboardTab
from Tabs.extraction_tab import ExtractionTab
from Tabs.appointment_tab import AppointmentTab
from model_intent.chatbot_tab import ChatBotTab
from Tabs.account_tab import AccountsTab
from Tabs.client_management_tab import ClientManagementTab
from translation_helper import tr

class HomePage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()

        self.extraction_tab = ExtractionTab()
        self.tabs.addTab(self.extraction_tab, tr("Data Extraction"))

        self.appointment_tab = AppointmentTab()
        self.tabs.addTab(self.appointment_tab, tr("Appointments"))

        self.chatbot_tab = ChatBotTab()
        self.tabs.addTab(self.chatbot_tab, tr("Assistant Bot"))

        self.accounts_tab = AccountsTab()
        self.tabs.addTab(self.accounts_tab, tr("Accounts"))

        self.client_management_tab = ClientManagementTab()
        self.tabs.addTab(self.client_management_tab, tr("Client Management"))

        self.dashboard_tab = DashboardTab()
        self.tabs.addTab(self.dashboard_tab, tr("Dashboard"))

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Connect tab change signal to update the active tab's content.
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.tabs.currentChanged.connect( lambda index: self.tabs.widget(index).retranslateUi() if hasattr(self.tabs.widget(index),"retranslateUi") else None)

    def on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if hasattr(widget, "retranslateUi"):
            widget.retranslateUi()

    def retranslateUi(self):
        self.tabs.setTabText(0, tr("Data Extraction"))
        self.tabs.setTabText(1, tr("Appointments"))
        self.tabs.setTabText(2, tr("Assistant Bot"))
        self.tabs.setTabText(3, tr("Accounts"))
        self.tabs.setTabText(4, tr("Client Management"))
        self.tabs.setTabText(5, tr("Dashboard"))
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, "retranslateUi"):
            current_widget.retranslateUi()