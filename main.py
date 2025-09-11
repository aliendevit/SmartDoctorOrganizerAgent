# main.py
import sys, warnings, importlib, traceback
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui

from Tabs.account_tab import update_account_in_db
from Tabs.appointment_tab import load_appointments, append_appointment

warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- ensure project root on sys.path ---
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- design system (best-effort import) ---
def _apply_theme(app: QtWidgets.QApplication):
    """
    Try your UI.design_system first; then UI.modern_theme; else Fusion.
    """
    # 1) design_system.apply_global_theme(app, base_point_size=11)
    try:
        from UI import design_system
        design_system.apply_global_theme(app, base_point_size=11)
        return
    except Exception:
        pass
    # 2) Modern theme fallback
    try:
        from UI.modern_theme import ModernTheme
        ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
        return
    except Exception:
        pass
    # 3) Qt Fusion (last resort)
    app.setStyle("Fusion")

# --- translation helper (safe no-op fallback) ---
def _ensure_translation_helper():
    try:
        from features import translation_helper  # noqa: F401
    except Exception:
        import types
        th = types.ModuleType("translation_helper")
        th.tr = lambda s: s
        sys.modules["translation_helper"] = th
_ensure_translation_helper()

def _tr(s: str) -> str:
    try:
        from features.translation_helper import tr
        return tr(s)
    except Exception:
        return s

# --- import HomePage (support both names: home_page.py or homepage.py) ---
def _import_homepage_class():
    errors = []
    for mod, cls in [("home_page", "HomePage"), ("homepage", "HomePage")]:
        try:
            m = importlib.import_module(mod)
            if hasattr(m, cls):
                c = getattr(m, cls)
                print(f"[main] Loaded {mod}.{cls}")
                return c, None
            errors.append(f"{mod}.{cls}: class not found")
        except Exception:
            errors.append(f"{mod}.HomePage -> import error:\n{traceback.format_exc()}")
    return None, "\n\n".join(errors) if errors else "HomePage not found"

HomePage, _ERR_HOME = _import_homepage_class()

# ---- lightweight notifier for tray toasts ----
class Notifier(QtCore.QObject):
    def __init__(self, tray_icon: QtWidgets.QSystemTrayIcon, parent=None):
        super().__init__(parent)
        self.tray = tray_icon

    def info(self, title, msg, msecs=3500):
        try:
            self.tray.showMessage(title, msg, QtWidgets.QSystemTrayIcon.Information, msecs)
        except Exception:
            pass

# ---- Main Window using HomePage as the central widget ----
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MedicalDoc AI – Home")
        self.resize(1200, 800)

        # System tray + quick menu
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        menu = QtWidgets.QMenu()
        menu.addAction(_tr("Show"), self.showNormal)
        menu.addAction(_tr("Quit"), QtWidgets.qApp.quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        self.notifier = Notifier(self.tray_icon, self)

        # Central content: HomePage (tiles + chatbot)
        if HomePage is None:
            self._build_missing_home(_ERR_HOME or "Could not import HomePage")
        else:
            self.home = HomePage()
            self.setCentralWidget(self.home)
            self._wire_chatbot()

        self.statusBar().showMessage(_tr("Ready"))
        self._load_settings()

    # ---- persistence ----
    def _load_settings(self):
        s = QtCore.QSettings("InnovationLabs", "MedicalDocAI")
        g = s.value("main/geometry")
        if g:
            self.restoreGeometry(g)

    def _save_settings(self):
        s = QtCore.QSettings("InnovationLabs", "MedicalDocAI")
        s.setValue("main/geometry", self.saveGeometry())

    def closeEvent(self, e: QtGui.QCloseEvent):
        self._save_settings()
        super().closeEvent(e)

    # ---- fallback panel if HomePage import fails ----
    def _build_missing_home(self, error_text: str):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lbl = QtWidgets.QLabel("<b>HomePage import error</b>")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        txt = QtWidgets.QPlainTextEdit(error_text)
        txt.setReadOnly(True)
        txt.setMinimumHeight(220)
        lay.addStretch(1)
        lay.addWidget(lbl)
        lay.addWidget(txt)
        lay.addStretch(1)
        self.setCentralWidget(w)

    # ---- connect chatbot to a simple echo handler (replace with real agent) ----
    def _wire_chatbot(self):
        if not hasattr(self.home, "chatbot"):
            return
        try:
            self.home.chatbot.messageSubmitted.connect(self._on_chat_message)
        except Exception:
            pass

    @QtCore.pyqtSlot(str)
    def _on_chat_message(self, msg: str):
        """
        Replace this with your real agent logic (e.g., agents.agent_actions).
        """
        try:
            # Example: dynamic import of your agent
            # from agents.agent_actions import run_agent
            # reply = run_agent(msg)
            reply = f"Assistant response to: {msg}"
        except Exception as e:
            reply = f"(agent error) {e}"

        # Append to transcript safely
        try:
            self.home.chatbot.transcript.append(f"<b>Assistant:</b> {reply}")
        except Exception:
            pass
def install_excepthook():
    def _hook(exc_type, exc, tb):
        msg = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            QtWidgets.QMessageBox.critical(None, "Unhandled Error", msg)
        except Exception:
            print(msg, file=sys.stderr)
    sys.excepthook = _hook

def main():
    app = QtWidgets.QApplication(sys.argv)
    install_excepthook()

    win = QtWidgets.QMainWindow()
    win.setWindowTitle("MedicalDocAI – Home")

    # Optional: your data functions; stub if missing
    def load_appointments(): return []
    def append_appointment(x): return False
    def update_account_in_db(n, p): return False
    def _switch_to_appts(name=""): pass
    def _refresh_accounts(): pass
    def _switch_to_client_stats(): pass

    home = HomePage()
    home.set_chat_bridge({
        "load_appointments": load_appointments,
        "append_appointment": append_appointment,
        "update_payment": update_account_in_db,
        "switch_to_appointments": _switch_to_appts,
        "refresh_accounts": _refresh_accounts,
        "switch_to_client_stats": _switch_to_client_stats,
    })
    win.setCentralWidget(home)
    win.resize(1200, 760); win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()