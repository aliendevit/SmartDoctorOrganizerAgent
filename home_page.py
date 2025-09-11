from __future__ import annotations
import importlib, importlib.util, sys, types, traceback
from typing import List, Optional, Tuple, Sequence
from PyQt5 import QtCore, QtGui, QtWidgets
from Tabs.chatbot_tab import ChatBotTab

def _ensure_translation_helper():
    try:
        from features.translation_helper import tr  # noqa
    except Exception:
        pkg = sys.modules.get("features")
        if pkg is None:
            pkg = types.ModuleType("features")
            sys.modules["features"] = pkg
        th = types.ModuleType("features.translation_helper")
        th.tr = lambda s: s
        sys.modules["features.translation_helper"] = th

_ensure_translation_helper()

try:
    from UI.design_system import COLORS as THEME
except Exception:
    THEME = {
        "bg": "#0b0f17",
        "panel": "#111318",
        "border": "#242938",
        "primary": "#3A8DFF",
        "text": "#e5e7eb",
        "subtitle": "#9aa3af",
    }

def _module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def _safe_create_widget(module_names: Sequence[str], class_candidates: Sequence[str]):
    errs = []
    for module_name in module_names:
        if not module_name or not isinstance(module_name, str):
            continue
        if not _module_exists(module_name):
            errs.append(f"{module_name}: not found")
            continue
        try:
            mod = importlib.import_module(module_name)
        except BaseException:
            errs.append(f"import {module_name}:\n{traceback.format_exc()}")
            continue
        for cls_name in class_candidates:
            if not cls_name or not isinstance(cls_name, str):
                continue
            try:
                cls = getattr(mod, cls_name, None)
                if cls is None:
                    errs.append(f"{module_name}.{cls_name}: class not found")
                    continue
                try:
                    w = cls()
                except TypeError:
                    w = cls(None)
                except BaseException:
                    errs.append(f"{module_name}.{cls_name} ctor:\n{traceback.format_exc()}")
                    continue
                if isinstance(w, QtWidgets.QWidget):
                    return w, None
                errs.append(f"{module_name}.{cls_name}: not a QWidget")
            except BaseException:
                errs.append(f"{module_name}.{cls_name}:\n{traceback.format_exc()}")
    return None, "\n\n".join(errs) if errs else "No candidates matched."

class TileButton(QtWidgets.QPushButton):
    def __init__(self, emoji: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setCheckable(False)
        self._build(emoji, title, subtitle)

    def _build(self, emoji: str, title: str, subtitle: str):
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.setMinimumSize(140, 120)
        self.setMaximumHeight(140)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {THEME.get('panel','#111318')};
                border: 1px solid {THEME.get('border','#242938')};
                border-radius: 16px;
                padding: 12px;
                text-align: left;
            }}
            QPushButton:hover {{ border-color: {THEME.get('primary','#3A8DFF')}; }}
            QLabel {{ color:{THEME.get('text','#e5e7eb')}; }}
            #emoji {{ font-size:28px; }}
            #title {{ font-size:15px; font-weight:700; }}
            #subtitle {{ font-size:12px; color:{THEME.get('subtitle','#9aa3af')}; }}
            """
        )
        col = QtWidgets.QVBoxLayout(self); col.setSpacing(6)
        emo = QtWidgets.QLabel(emoji); emo.setObjectName("emoji")
        ttl = QtWidgets.QLabel(title); ttl.setObjectName("title")
        sub = QtWidgets.QLabel(subtitle); sub.setObjectName("subtitle"); sub.setWordWrap(True)
        col.addWidget(emo); col.addWidget(ttl)
        if subtitle: col.addWidget(sub)
        col.addStretch(1)

class HomePage(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._tiles: List[Tuple[str, str, str, List[str], List[str]]] = []
        self._chat = ChatBotTab()
        self._floating_windows: List[QtWidgets.QWidget] = []
        self._build()

    @property
    def chatbot(self) -> ChatBotTab:
        return self._chat

    def set_chat_bridge(self, bridge: dict):
        try:
            self._chat.set_bridge(bridge)
        except Exception:
            pass

    def _build(self):
        self.setObjectName("HomePage")
        self.setStyleSheet(
            f"""
            QWidget#HomePage {{
                background: {THEME.get('bg','#0b0f17')};
                color: {THEME.get('text','#e5e7eb')};
            }}
            QScrollArea {{ border:none; }}
            QFrame[modernCard="true"] {{
                background: {THEME.get('panel','#111318')};
                border: 1px solid {THEME.get('border','#242938')};
                border-radius: 16px;
            }}
            """
        )

        root = QtWidgets.QHBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(16)

        left_wrapper = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_wrapper); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(12)
        header = QtWidgets.QLabel("🏠 Home – Workspaces"); header.setStyleSheet("font-size:18px;font-weight:800;padding-left:6px")
        left_layout.addWidget(header)

        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); left_layout.addWidget(scroll, 1)
        grid_host = QtWidgets.QWidget()
        self._grid = QtWidgets.QGridLayout(grid_host); self._grid.setContentsMargins(4,4,4,4); self._grid.setHorizontalSpacing(10); self._grid.setVerticalSpacing(10)
        scroll.setWidget(grid_host)

        root.addWidget(left_wrapper, 0)

        right_card = QtWidgets.QFrame(); right_card.setProperty("modernCard", True)
        right_layout = QtWidgets.QVBoxLayout(right_card); right_layout.setContentsMargins(16,16,16,16); right_layout.setSpacing(8)
        bar = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("🤖 Chatbot"); title.setStyleSheet("font-size:16px;font-weight:800")
        bar.addWidget(title); bar.addStretch(1)
        right_layout.addLayout(bar); right_layout.addWidget(self._chat, 1)
        root.addWidget(right_card, 1)
        root.setStretch(0,0); root.setStretch(1,1)

        self._tiles = [
            ("🔎","Extraction","Parse notes, auto-structure",
             ["Tabs.extraction_tab"],
             ["ExtractionTab","MainWidget","ExtractionWidget"]),
            ("📅","Appointments","List / manage",
             ["Tabs.appointment_tab"],
             ["AppointmentTab","MainWidget"]),
            ("📊","Dashboard","KPIs & charts",
             ["Tabs.dashboard_tab"],
             ["DashboardTab","MainWidget"]),
            ("🧾","Accounts","Billing & payments",
             ["Tabs.account_tab"],   # if your repo uses account_tab instead, change to Tabs.account_tab
             ["AccountsTab","MainWidget"]),
            ("📈","Client Stats","Statistics & cohorts",
             ["Tabs.clients_stats_tab"],
             ["ClientStatsTab","MainWidget"]),
            ("⚙️","Settings","Preferences & integrations",
             ["Tabs.settings_tab"],
             ["SettingsTab","SettingsWidget","MainWidget"]),
        ]
        self._populate_tiles()

    def _populate_tiles(self):
        row = 0; col = 0
        for emoji, title, subtitle, mods, classes in self._tiles:
            btn = TileButton(emoji, title, subtitle)
            btn.clicked.connect(lambda _=None, m=list(mods), t=title, c=list(classes): self._open_in_dialog(m, t, c))
            self._grid.addWidget(btn, row, col)
            col += 1
            if col >= 2:
                col = 0; row += 1

    def _open_in_dialog(self, module_names: List[str], title: str, class_candidates: List[str]):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(title); dlg.setModal(False)
        dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose, True); dlg.resize(1000, 720)

        outer = QtWidgets.QVBoxLayout(dlg); outer.setContentsMargins(12,12,12,12); outer.setSpacing(8)
        header = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(title); lbl.setStyleSheet("font-size:16px;font-weight:800")
        header.addWidget(lbl); header.addStretch(1)
        close_btn = QtWidgets.QPushButton("Close"); close_btn.clicked.connect(dlg.close)
        header.addWidget(close_btn); outer.addLayout(header)

        frame = QtWidgets.QFrame(); frame.setProperty("modernCard", True)
        lay = QtWidgets.QVBoxLayout(frame); lay.setContentsMargins(12,12,12,12)
        loading = QtWidgets.QLabel("Loading…"); loading.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(loading); outer.addWidget(frame, 1)

        def create_and_swap():
            try:
                widget, err = _safe_create_widget(module_names, class_candidates)
                if widget is None:
                    txt = QtWidgets.QPlainTextEdit(err or "Unknown error")
                    txt.setReadOnly(True); txt.setMinimumHeight(260)
                    lay.replaceWidget(loading, txt); loading.setParent(None)
                    return
                lay.replaceWidget(loading, widget); loading.setParent(None)
            except BaseException:
                txt = QtWidgets.QPlainTextEdit(traceback.format_exc())
                txt.setReadOnly(True); txt.setMinimumHeight(260)
                lay.replaceWidget(loading, txt); loading.setParent(None)

        QtCore.QTimer.singleShot(0, create_and_swap)

        gp = self.geometry(); pt = self.mapToGlobal(gp.topRight())
        dlg.move(max(0, pt.x() - dlg.width()), pt.y() + 64)
        self._floating_windows.append(dlg); dlg.show()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow(); win.setWindowTitle("MedicalDocAI – Home (Chat on Right)")
    page = HomePage(); win.setCentralWidget(page)
    win.resize(1200, 760); win.show()
    sys.exit(app.exec_())
