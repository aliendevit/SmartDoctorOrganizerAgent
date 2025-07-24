# home_page.py
from PyQt5 import QtWidgets, QtCore, QtGui
import traceback

# -------- translation (safe) --------
def _tr(text: str) -> str:
    try:
        from translation_helper import tr
        return tr(text)
    except Exception:
        return text

# -------- safe import helpers --------
def _try_import(class_name: str, candidates: list):
    """
    Try importing a class from several module paths.
    candidates = ["Tabs.dashboard_tab:DashboardTab", "dashboard_tab:DashboardTab"]
    """
    last_err = None
    for spec in candidates:
        try:
            mod_path, cls = spec.split(":")
            module = __import__(mod_path, fromlist=[cls])
            return getattr(module, cls)
        except Exception as e:
            last_err = e
    raise ImportError(f"Could not import {class_name}: {last_err}")

def _optional_tab(class_name: str, candidates: list, title: str):
    """
    Try to construct the tab. If it fails, return a placeholder error widget.
    """
    try:
        Cls = _try_import(class_name, candidates)
        return Cls()
    except Exception:
        # placeholder with error message so the app still runs
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        lab = QtWidgets.QLabel(
            _tr("⚠️ Failed to load '{0}'. See console for details.").format(title)
        )
        lab.setWordWrap(True)
        lab.setStyleSheet("color:#b91c1c; font-weight:600;")
        v.addWidget(lab)
        v.addStretch(1)
        traceback.print_exc()
        return w

# -------- HomePage --------
class HomePage(QtWidgets.QWidget):
    """
    Main container for tabs. Robust against missing modules.
    Wires Extraction ➜ Appointments:
      - appointmentProcessed(dict) ➜ AppointmentTab.add_appointment(dict)
      - switchToAppointments(name) ➜ switch tab + highlight row
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._wire_signals()

    def _build_ui(self):
        self.tabs = QtWidgets.QTabWidget(self)

        # Create tabs (robust to missing files)
        # Dashboard
        self.dashboard_tab = _optional_tab(
            "DashboardTab",
            ["Tabs.dashboard_tab:DashboardTab", "dashboard_tab:DashboardTab"],
            "Dashboard"
        )

        # Appointments (we will rely on add_appointment(...) & highlight_client(...))
        self.appointment_tab = _optional_tab(
            "AppointmentTab",
            ["appointment_tab:AppointmentTab", "Tabs.appointment_tab:AppointmentTab"],
            "Appointments"
        )

        # Accounts
        self.accounts_tab = _optional_tab(
            "AccountsTab",
            ["accounts_tab:AccountsTab", "Tabs.accounts_tab:AccountsTab"],
            "Accounts"
        )

        # Chatbot
        self.chatbot_tab = _optional_tab(
            "ChatBotTab",
            ["chatbot_tab:ChatBotTab", "Tabs.chatbot_tab:ChatBotTab"],
            "Assistant"
        )

        # Client stats
        self.stats_tab = _optional_tab(
            "ClientStatsTab",
            ["client_stats_tab:ClientStatsTab", "Tabs.client_stats_tab:ClientStatsTab"],
            "Client Stats"
        )

        # Extraction (agent-integrated)
        self.extraction_tab = _optional_tab(
            "ExtractionTab",
            ["extraction_tab:ExtractionTab", "Tabs.extraction_tab:ExtractionTab"],
            "Extraction"
        )

        # Add in the order you like
        self.tabs.addTab(self.dashboard_tab, _tr("Dashboard"))
        self.tabs.addTab(self.extraction_tab, _tr("Extraction"))
        self.tabs.addTab(self.appointment_tab, _tr("Appointments"))
        self.tabs.addTab(self.accounts_tab, _tr("Accounts"))
        self.tabs.addTab(self.stats_tab, _tr("Statistics"))
        self.tabs.addTab(self.chatbot_tab, _tr("Assistant"))

        # Layout
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.tabs)
        self.setLayout(lay)

        # Optional: a soft, modern base style for the page
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; }
            QTabWidget::pane { border: 1px solid #e5e7eb; border-radius: 8px; }
            QTabBar::tab { padding: 8px 14px; border: 1px solid #e5e7eb; border-bottom: none; }
            QTabBar::tab:selected { background: #f9fafb; font-weight: 600; }
        """)

    def _wire_signals(self):
        # Some placeholder tabs might not have these attributes; guard everything.
        ext = getattr(self, "extraction_tab", None)
        appt = getattr(self, "appointment_tab", None)

        # Extraction ➜ Appointments (add row)
        if ext is not None and hasattr(ext, "appointmentProcessed") and appt is not None and hasattr(appt, "add_appointment"):
            ext.appointmentProcessed.connect(appt.add_appointment)

        # Extraction ➜ switch to Appointments + highlight
        if ext is not None and hasattr(ext, "switchToAppointments"):
            ext.switchToAppointments.connect(self._switch_to_appointments)

        # Optionally: let Extraction refresh Dashboard after processing
        if ext is not None and hasattr(ext, "dataProcessed"):
            ext.dataProcessed.connect(lambda _: self._refresh_dashboard())

    # ---- helpers ----
    def _refresh_dashboard(self):
        dash = getattr(self.dashboard_tab, "refresh_data", None)
        if callable(dash):
            try:
                dash()
            except Exception:
                traceback.print_exc()

    @QtCore.pyqtSlot(str)
    def _switch_to_appointments(self, name: str):
        """Switch to Appointments tab and highlight the patient row."""
        if self.appointment_tab is not None:
            self.tabs.setCurrentWidget(self.appointment_tab)
            if hasattr(self.appointment_tab, "highlight_client"):
                try:
                    self.appointment_tab.highlight_client(name or "")
                except Exception:
                    traceback.print_exc()

    # ---- runtime translation support ----
    def retranslateUi(self):
        # Update tab titles when your translation changes
        idx = {
            "Dashboard": 0,
            "Extraction": 1,
            "Appointments": 2,
            "Accounts": 3,
            "Statistics": 4,
            "Assistant": 5
        }
        self.tabs.setTabText(idx["Dashboard"], _tr("Dashboard"))
        self.tabs.setTabText(idx["Extraction"], _tr("Extraction"))
        self.tabs.setTabText(idx["Appointments"], _tr("Appointments"))
        self.tabs.setTabText(idx["Accounts"], _tr("Accounts"))
        self.tabs.setTabText(idx["Statistics"], _tr("Statistics"))
        self.tabs.setTabText(idx["Assistant"], _tr("Assistant"))
        # Cascade to child tabs if they implement retranslateUi()
        for tab in (self.dashboard_tab, self.extraction_tab, self.appointment_tab,
                    self.accounts_tab, self.stats_tab, self.chatbot_tab):
            if hasattr(tab, "retranslateUi") and callable(tab.retranslateUi):
                try:
                    tab.retranslateUi()
                except Exception:
                    traceback.print_exc()

# ---- dev runner (optional) ----
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = HomePage()
    w.resize(1200, 800)
    w.setWindowTitle("Home")
    w.show()
    sys.exit(app.exec_())
