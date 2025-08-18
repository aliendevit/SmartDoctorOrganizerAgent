# main.py
import sys, warnings, importlib, traceback
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui

warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- ensure project root on sys.path ---
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- safe translation helper ---
def _ensure_translation_helper():
    try:
        import translation_helper  # noqa
    except Exception:
        import types
        th = types.ModuleType("translation_helper")
        th.tr = lambda s: s
        sys.modules["translation_helper"] = th
_ensure_translation_helper()

def _tr(s: str) -> str:
    try:
        from translation_helper import tr
        return tr(s)
    except Exception:
        return s

# --- import utils with error capture ---
def _import_first_or_report(title: str, candidates):
    """
    Try importing [(module, class), ...] in order.
    Returns (cls_or_None, error_str_or_None).
    """
    errors = []
    for mod, cls in candidates:
        try:
            m = importlib.import_module(mod)
            c = getattr(m, cls, None)
            if c:
                print(f"[main] Loaded {mod}.{cls}")
                return c, None
            errors.append(f"{mod}.{cls}: class not found")
        except Exception:
            tb = traceback.format_exc()
            errors.append(f"{mod}.{cls} -> import error:\n{tb}")
    return None, "\n\n".join(errors) if errors else f"No import candidates for {title}"

# ---- candidates (local, Tabs.*, and model_intent.* for ChatBot) ----
ExtractionTab , ERR_EX  = _import_first_or_report("Extraction", [
    ("extraction_tab", "ExtractionTab"),
    ("Tabs.extraction_tab", "ExtractionTab"),
])
DashboardTab  , ERR_DB  = _import_first_or_report("Dashboard", [
    ("dashboard_tab", "DashboardTab"),
    ("Tabs.dashboard_tab", "DashboardTab"),
])
AppointmentTab, ERR_APT = _import_first_or_report("Appointments", [
    ("appointment_tab", "AppointmentTab"),
    ("Tabs.appointment_tab", "AppointmentTab"),
])
AccountsTab   , ERR_ACC = _import_first_or_report("Accounts", [
    ("accounts_tab", "AccountsTab"),
    ("account_tab",  "AccountsTab"),
    ("Tabs.accounts_tab", "AccountsTab"),
    ("Tabs.account_tab",  "AccountsTab"),
])
ClientStatsTab, ERR_CS  = _import_first_or_report("Client Stats", [
    ("client_stats_tab",  "ClientStatsTab"),
    ("clients_stats_tab", "ClientStatsTab"),
    ("Tabs.client_stats_tab",  "ClientStatsTab"),
    ("Tabs.clients_stats_tab", "ClientStatsTab"),
])
ChatBotTab    , ERR_CB  = _import_first_or_report("ChatBot", [
    ("model_intent.chatbot_tab", "ChatBotTab"),   # <-- bot here
    ("chatbot_tab",              "ChatBotTab"),
    ("Tabs.chatbot_tab",         "ChatBotTab"),
])

# ---- placeholder tab that shows the real error text in a scroll ----
class _MissingTab(QtWidgets.QWidget):
    def __init__(self, title: str, error_text: str, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel(f"<b>{title}</b>")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setTextFormat(QtCore.Qt.RichText)
        txt = QtWidgets.QPlainTextEdit(error_text or "Unknown import error")
        txt.setReadOnly(True); txt.setMinimumHeight(220)
        lay.addStretch(1); lay.addWidget(lbl); lay.addWidget(txt); lay.addStretch(1)

class Notifier(QtCore.QObject):
    def __init__(self, tray_icon: QtWidgets.QSystemTrayIcon, parent=None):
        super().__init__(parent); self.tray = tray_icon
    def info(self, title, msg, msecs=3500):
        try: self.tray.showMessage(title, msg, QtWidgets.QSystemTrayIcon.Information, msecs)
        except Exception: pass

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MedicalDoc AI"); self.resize(1200, 800)

        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        menu = QtWidgets.QMenu(); menu.addAction("Show", self.showNormal); menu.addAction("Quit", QtWidgets.qApp.quit)
        self.tray_icon.setContextMenu(menu); self.tray_icon.show()
        self.notifier = Notifier(self.tray_icon, self)

        self.tabs = QtWidgets.QTabWidget(); self.setCentralWidget(self.tabs)
        self._make_tabs()
        self.statusBar().showMessage("Ready")
        self._load_settings()

    def _load_settings(self):
        s = QtCore.QSettings("YourOrg", "MedicalDocAI")
        g = s.value("main/geometry");  self.restoreGeometry(g) if g else None
    def _save_settings(self):
        s = QtCore.QSettings("YourOrg", "MedicalDocAI")
        s.setValue("main/geometry", self.saveGeometry())
    def closeEvent(self, e: QtGui.QCloseEvent):
        self._save_settings(); super().closeEvent(e)

    def _make_tabs(self):
        self.extraction  = ExtractionTab() if ExtractionTab else _MissingTab("Extraction", ERR_EX or "extraction_tab")
        # Appointments
        if AppointmentTab:
            try:
                self.appointments = AppointmentTab(tray_icon=self.tray_icon)
            except TypeError:
                self.appointments = AppointmentTab()
                if hasattr(self.appointments, "set_tray_icon"):
                    try: self.appointments.set_tray_icon(self.tray_icon)
                    except Exception: pass
        else:
            self.appointments = _MissingTab("Appointments", ERR_APT or "appointment_tab")

        self.dashboard   = DashboardTab()  if DashboardTab  else _MissingTab("Dashboard",   ERR_DB  or "dashboard_tab")
        self.accounts    = AccountsTab()   if AccountsTab   else _MissingTab("Accounts",    ERR_ACC or "accounts_tab")
        self.client_stats= ClientStatsTab()if ClientStatsTab else _MissingTab("Client Stats",ERR_CS  or "client_stats_tab")

        # --- Shared “bridge” so ChatBot uses the SAME data + can drive the UI ---
        try:
            from data.data import load_appointments, append_appointment, update_account_in_db
        except Exception:
            def load_appointments(): return []
            def append_appointment(appt): return False
            def update_account_in_db(name, payload): return False

        def _switch_to_appts(name=None):
            self._switch_to_appointments(name or "")

        def _refresh_accounts():
            if hasattr(self.accounts, "update_table"):
                self.accounts.update_table()

        bridge = {
            "load_appointments": load_appointments,
            "append_appointment": append_appointment,
            "update_payment": update_account_in_db,
            "switch_to_appointments": _switch_to_appts,
            "refresh_accounts": _refresh_accounts,
        }

        # ChatBot
        if ChatBotTab:
            try:
                self.chatbot = ChatBotTab(bridge=bridge)
            except Exception:
                self.chatbot = _MissingTab("ChatBot", f"Constructor failed:\n{traceback.format_exc()}\n\n{ERR_CB or ''}")
        else:
            self.chatbot = _MissingTab("ChatBot", ERR_CB or "chatbot_tab")

        self.tabs.addTab(self.extraction,   _tr("Extraction"))
        self.tabs.addTab(self.appointments, _tr("Appointments"))
        self.tabs.addTab(self.dashboard,    _tr("Dashboard"))
        self.tabs.addTab(self.accounts,     _tr("Accounts"))
        self.tabs.addTab(self.client_stats, _tr("Client Stats"))
        self.tabs.addTab(self.chatbot,      _tr("Assistant Bot"))

        # wire signals if available
        for sig, slot in [
            ("dataProcessed",          self._on_data_processed),
            ("appointmentProcessed",   self._on_appointment_processed),
            ("switchToAppointments",   self._switch_to_appointments),
        ]:
            if hasattr(self.extraction, sig):
                try: getattr(self.extraction, sig).connect(slot)
                except Exception: pass

        if hasattr(self.chatbot, "appointmentCreated"):
            try: self.chatbot.appointmentCreated.connect(self._on_appointment_processed)
            except Exception: pass

    def _normalize_appointment(self, data: dict) -> dict:
        appt = dict(data or {})
        name = (appt.get("Name") or "").strip() or "Unknown"
        date = (appt.get("Appointment Date") or "").strip() or QtCore.QDate.currentDate().toString("dd-MM-yyyy")
        time = (appt.get("Appointment Time") or "").strip() or "12:00 PM"
        appt.update({"Name": name, "Appointment Date": date, "Appointment Time": time})
        return appt

    @QtCore.pyqtSlot(dict)
    def _on_data_processed(self, data: dict):
        for w, m in [(getattr(self, "dashboard", None), "refresh_data"),
                     (getattr(self, "accounts", None), "update_table"),
                     (getattr(self, "client_stats", None), "refresh_data")]:
            if w and hasattr(w, m):
                try: getattr(w, m)()
                except Exception: pass
        self.notifier.info("Extraction", f"Processed data for {data.get('Name','Unknown')}")

    @QtCore.pyqtSlot(dict)
    def _on_appointment_processed(self, data: dict):
        appt = self._normalize_appointment(data)
        try:
            if hasattr(self.appointments, "add_appointment"):
                self.appointments.add_appointment(appt)
        except Exception: pass
        self._switch_to_appointments(appt.get("Name","Unknown"))

    @QtCore.pyqtSlot(str)
    def _switch_to_appointments(self, client_name: str):
        idx = self.tabs.indexOf(self.appointments)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)
            if hasattr(self.appointments, "highlight_client"):
                try: self.appointments.highlight_client(client_name)
                except Exception: pass
        self.notifier.info("Automation", f"Switched to Appointments for {client_name}")

def apply_theme(app: QtWidgets.QApplication):
    try:
        from modern_theme import ModernTheme
        ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
    except Exception:
        app.setStyle("Fusion")

def main():
    QtCore.QCoreApplication.setOrganizationName("YourOrg")
    QtCore.QCoreApplication.setApplicationName("MedicalDocAI")
    app = QtWidgets.QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow(); win.show()
    try: win.notifier.info("MedicalDoc AI", "Ready.")
    except Exception: pass
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
