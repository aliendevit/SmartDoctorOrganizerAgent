from __future__ import annotations
import importlib, importlib.util, sys, types, traceback, contextlib
from typing import List, Optional, Tuple, Sequence
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from Tabs.chatbot_tab import ChatBotTab
from pathlib import Path
import importlib, importlib.util, importlib.machinery
ROOT = Path(__file__).resolve().parent

def _module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def _import_any(module_name: str, filename_candidates=None):
    """
    Try normal import first. If that fails, try loading by filename
    relative to project root (and Tabs/).
    Returns a module or raises ImportError.
    """
    if _module_exists(module_name):
        return importlib.import_module(module_name)

    filename_candidates = filename_candidates or []
    # derive a default guess from module_name like "Tabs.account_tab" -> "Tabs/account_tab.py"
    parts = module_name.split(".")
    guess = ROOT.joinpath(*parts[:-1], parts[-1] + ".py")
    candidates = [guess] + [
        ROOT / fc for fc in filename_candidates
    ]

    for path in candidates:
        try:
            if path.exists():
                loader = importlib.machinery.SourceFileLoader(module_name, str(path))
                spec = importlib.util.spec_from_loader(module_name, loader)
                mod = importlib.util.module_from_spec(spec)
                loader.exec_module(mod)
                sys.modules[module_name] = mod
                return mod
        except Exception:
            continue
    raise ImportError(f"{module_name}: not found")

def _safe_create_widget(module_names: Sequence[str], class_candidates: Sequence[str]):
    errs = []
    for module_name in module_names:
        if not module_name or not isinstance(module_name, str):
            continue
        try:
            # try import by name; if not found, load file variants
            extra_files = []
            # for common Tabs.* names also try a raw path fallback
            if module_name.startswith("Tabs."):
                suffix = module_name.split(".", 1)[1] + ".py"
                extra_files = [Path("Tabs") / suffix]
            mod = _import_any(module_name, filename_candidates=extra_files)
        except BaseException:
            errs.append(f"{module_name}: not found")
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
                if isinstance(w, QtWidgets.QWidget):
                    return w, None
                errs.append(f"{module_name}.{cls_name}: not a QWidget")
            except BaseException as e:
                errs.append(f"{module_name}.{cls_name}: {e}")
    return None, "\n\n".join(errs) if errs else "No candidates matched."

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
        "text":        "#1f2937",
        "textDim":     "#334155",
        "primary":     "#3A8DFF",
        "info":        "#2CBBA6",
        "success":     "#7A77FF",
        "stroke":      "#E5EFFA",
        "panel":       "rgba(255,255,255,0.55)",
        "panelInner":  "rgba(255,255,255,0.65)",
        "inputBg":     "rgba(255,255,255,0.88)",
        "stripe":      "rgba(240,247,255,0.65)",
        "selBg":       "#3A8DFF",
        "selFg":       "#ffffff",
        "danger":      "#EF4444",
    }

# ---------- SVG icons ----------
_ICONS = {
    "extraction": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M7 8h10M7 12h10M7 16h6"/></svg>""",
    "appointments": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="4.5" width="17" height="16" rx="3"/><path d="M8 3v4M16 3v4M3.5 9.5h17"/></svg>""",
    "dashboard": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 13a8 8 0 1 1 16 0"/><path d="M12 13l4-4"/><circle cx="12" cy="13" r="1.2" fill="currentColor"/></svg>""",
    "account": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M3.5 9h17M8 13h4M8 16h8"/></svg>""",
    "stats": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 20V6M10 20V10M16 20V4M22 20H2"/></svg>""",
    "settings": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.02.02a2 2 0 1 1-2.83 2.83l-.02-.02A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .18 1.8 1.8 0 0 1-2 0 1.8 1.8 0 0 0-1-.18 1.8 1.8 0 0 0-1 .18 1.8 1.8 0 0 1-2 0 1.8 1.8 0 0 0-1 .18 1.8 1.8 0 0 0-1.98-.36l-.02.02a2 2 0 1 1-2.83-2.83l.02-.02A1.8 1.8 0 0 0 4.6 15c0-.33-.06-.66-.18-.98a1.8 1.8 0 0 0 0-1.99c.12-.32.18-.65.18-.98a1.8 1.8 0 0 0-.36-1.98l-.02-.02a2 2 0 1 1 2.83-2.83l.02.02C6.34 5.24 6.67 5.12 7 5.12c.33 0 .66-.06.98-.18a1.8 1.8 0 0 0 1.99 0c.32-.12.65-.18 1.02-.18s.66.06.98.18a1.8 1.8 0 0 0 1.99 0c.32-.12.65-.18 1.02-.18.33 0 .66.06.98.18l.02-.02a2 2 0 1 1 2.83 2.83l-.02.02c.24.3.36.63.36.98 0 .33.06.66.18.98a1.8 1.8 0 0 0 0 1.99c-.12.32-.18.65-.18.98Z"/></svg>""",
    "back": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M15 18l-6-6 6-6"/><path d="M21 12H9"/></svg>""",
}

def _qicon(name: str, size=18, color="#0f172a") -> QtGui.QIcon:
    svg = _ICONS.get(name, _ICONS["dashboard"]).replace("currentColor", color)
    r = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    img = QtGui.QImage(size, size, QtGui.QImage.Format_ARGB32)
    img.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(img)
    p.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
    r.render(p)
    p.end()
    return QtGui.QIcon(QtGui.QPixmap.fromImage(img))

# ---------- ALIAS LAYER: map whatever exists to expected names ----------
def _alias_module(src_candidates: Sequence[str], dst_names: Sequence[str], class_map: Sequence[Tuple[str,str]]):
    existing = next((m for m in src_candidates if _module_exists(m)), None)
    if not existing:
        return
    mod = importlib.import_module(existing)
    for dst in dst_names:
        if dst not in sys.modules:
            sys.modules[dst] = mod
    # ensure class names expected by callers exist
    for want_name, actual_name in class_map:
        if getattr(mod, want_name, None) is None and getattr(mod, actual_name, None) is not None:
            setattr(mod, want_name, getattr(mod, actual_name))

def _install_aliases():
    # Accounts: accounts_tab vs account_tab, class AccountsTab (sometimes AccountsWidget)
    _alias_module(
        ["Tabs.account_tab", "account_tab", "Tabs.account_tab", "account_tab"],
        ["Tabs.account_tab", "account_tab", "Tabs.account_tab", "account_tab"],
        [("AccountTab","AccountTab"), ("AccountWidget","AccountWidget")]
    )
    # Client Stats: client_stats_tab vs clients_stats_tab
    _alias_module(
        ["Tabs.clients_stats_tab", "clients_stats_tab", "Tabs.clients_stats_tab", "clients_stats_tab"],
        ["Tabs.clients_stats_tab", "clients_stats_tab", "Tabs.clients_stats_tab", "clients_stats_tab"],
        [("ClientStatsTab","ClientStatsTab"), ("ClientStatsWidget","ClientStatsWidget")]
    )

_install_aliases()

# ---------- prevent accidental external windows during import/ctor ----------
@contextlib.contextmanager
def _no_external_windows():
    orig_mw_show = QtWidgets.QMainWindow.show
    orig_dlg_show = QtWidgets.QDialog.show
    orig_dlg_exec = QtWidgets.QDialog.exec_
    try:
        QtWidgets.QMainWindow.show = lambda self: None
        QtWidgets.QDialog.show = lambda self: None
        QtWidgets.QDialog.exec_ = lambda self: 0
        yield
    finally:
        QtWidgets.QMainWindow.show = orig_mw_show
        QtWidgets.QDialog.show = orig_dlg_show
        QtWidgets.QDialog.exec_ = orig_dlg_exec

def _safe_create_widget(module_names: Sequence[str], class_candidates: Sequence[str]):
    errs = []
    for module_name in module_names:
        if not module_name or not isinstance(module_name, str):
            continue
        if not _module_exists(module_name):
            errs.append(f"{module_name}: not found")
            continue
        try:
            with _no_external_windows():
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
                    with _no_external_windows():
                        w = cls()
                except TypeError:
                    with _no_external_windows():
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

# ---------- tile button ----------
class TileButton(QtWidgets.QPushButton):
    def __init__(self, icon_key: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setCheckable(False)
        self._build(icon_key, title, subtitle)

    def _build(self, icon_key: str, title: str, subtitle: str):
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.setMinimumSize(160, 118)
        self.setMaximumHeight(148)
        n1, n2, n3 = "#E8F0F2", "#CFE7E2", "#BFE5D6"
        h1, h2, h3 = "#F4F8F9", "#D6EFE8", "#A9DFC7"
        p1, p2, p3 = "#D4DEE0", "#B8D6CC", "#90C9B5"
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {n1}, stop:0.5 {n2}, stop:1 {n3});
                border: 2px solid #C8DCD3;
                border-radius: 18px;
                padding: 12px;
                text-align: left;
                color: {THEME.get('text','#1f2937')};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {h1}, stop:0.5 {h2}, stop:1 {h3});
                border: 2px solid #92BFA8;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {p1}, stop:0.5 {p2}, stop:1 {p3});
                border: 2px solid #6FA28B;
            }}
            """
        )
        eff = QtWidgets.QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(12); eff.setOffset(0, 3)
        eff.setColor(QtGui.QColor(160, 190, 170, 70))
        self.setGraphicsEffect(eff)
        col = QtWidgets.QVBoxLayout(self); col.setSpacing(8)
        badge = QtWidgets.QFrame(); badge.setFixedSize(38, 38)
        badge.setStyleSheet("""
            QFrame { border-radius: 10px;
                     background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                         stop:0 rgba(44,187,166,0.16), stop:1 rgba(58,141,255,0.14));
                     border: 1px solid rgba(44,187,166,0.25); }
        """)
        bl = QtWidgets.QHBoxLayout(badge); bl.setContentsMargins(6,6,6,6)
        ib = QtWidgets.QToolButton(); ib.setAutoRaise(True)
        ib.setIcon(_qicon(icon_key, 18)); ib.setIconSize(QtCore.QSize(18,18)); ib.setEnabled(False)
        bl.addWidget(ib, 0, QtCore.Qt.AlignCenter)
        t = QtWidgets.QLabel(title)
        f = QtGui.QFont(); f.setFamilies(["Segoe UI Variable", "Segoe UI", "Inter", "Arial"])
        f.setPointSize(14); f.setWeight(QtGui.QFont.DemiBold); t.setFont(f); t.setStyleSheet("color:#0f172a;")
        s = QtWidgets.QLabel(subtitle); s.setWordWrap(True)
        sf = QtGui.QFont(); sf.setFamilies(["Segoe UI", "Inter", "Arial"]); sf.setPointSize(11); s.setFont(sf)
        s.setStyleSheet("color:#475569;")
        col.addWidget(badge, 0, QtCore.Qt.AlignLeft)
        col.addWidget(t)
        if subtitle: col.addWidget(s)
        col.addStretch(1)

# ---------- Home Page ----------
class HomePage(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._tiles: List[Tuple[str, str, str, List[str], List[str]]] = []
        self._chat = ChatBotTab()
        self._grid_column_hint = 2
        self._stack = QtWidgets.QStackedWidget(self)
        self._home_page = QtWidgets.QWidget()
        self._detail_page = QtWidgets.QWidget()
        self._detail_container = None
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
        rootv = QtWidgets.QVBoxLayout(self)
        rootv.setContentsMargins(0, 0, 0, 0)
        rootv.addWidget(self._stack)
        self._build_home()
        self._build_detail()
        self._stack.addWidget(self._home_page)
        self._stack.addWidget(self._detail_page)
        self._stack.setCurrentIndex(0)

    def _build_home(self):
        self._home_page.setObjectName("HomePage")
        self._home_page.setStyleSheet(
            f"""
            QWidget#HomePage {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #F5F9FA, stop:0.5 #E3F1ED, stop:1 #D7EBE2);
                color: {THEME.get('text','#1f2937')};
            }}
            QScrollArea {{ border:none; }}
            QFrame[modernCard="true"] {{
                background: {THEME.get('panel','rgba(255,255,255,0.55)')};
                border: 1px solid rgba(200,220,210,0.55);
                border-radius: 12px;
            }}
            """
        )
        v = QtWidgets.QVBoxLayout(self._home_page)
        v.setContentsMargins(16, 12, 16, 16); v.setSpacing(12)
        topbar = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("MedicalDocAI")
        tf = QtGui.QFont(); tf.setFamilies(["Segoe UI Variable","Segoe UI","Inter","Arial"])
        tf.setPointSize(18); tf.setWeight(QtGui.QFont.DemiBold); title.setFont(tf)
        topbar.addWidget(title); topbar.addStretch(1)
        settings_btn = QtWidgets.QToolButton(); settings_btn.setAutoRaise(True)
        settings_btn.setIcon(_qicon("settings", 18)); settings_btn.setIconSize(QtCore.QSize(18,18))
        settings_btn.setCursor(QtCore.Qt.PointingHandCursor); settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet("""
            QToolButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #E8F0F2, stop:0.5 #CFE7E2, stop:1 #BFE5D6);
                border: 1px solid #C8DCD3; border-radius: 8px; padding: 4px 6px; }
            QToolButton:hover { border-color:#92BFA8; }
            QToolButton:pressed { border-color:#6FA28B; }
        """)
        settings_btn.clicked.connect(lambda: self._open_in_place(
            ["Tabs.settings_tab", "settings_tab", "Tabs.Settings", "Settings"],
            "Settings",
            ["SettingsTab", "SettingsWidget", "MainWidget"]
        ))
        topbar.addWidget(settings_btn)
        v.addLayout(topbar)

        self._main = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self._main.setContentsMargins(0, 0, 0, 0)
        self._main.setSpacing(16)
        v.addLayout(self._main, 1)

        left_scroll = QtWidgets.QScrollArea(); left_scroll.setWidgetResizable(True)
        left_host = QtWidgets.QWidget(); left_scroll.setWidget(left_host)
        left_layout = QtWidgets.QVBoxLayout(left_host)
        left_layout.setContentsMargins(0, 0, 0, 0); left_layout.setSpacing(12)
        header = QtWidgets.QLabel("Home – Workspaces")
        hf = QtGui.QFont(); hf.setFamilies(["Segoe UI","Inter","Arial"])
        hf.setPointSize(15); hf.setWeight(QtGui.QFont.DemiBold); header.setFont(hf)
        left_layout.addWidget(header)
        grid_host = QtWidgets.QWidget()
        self._grid = QtWidgets.QGridLayout(grid_host)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        left_layout.addWidget(grid_host, 0)

        right_scroll = QtWidgets.QScrollArea(); right_scroll.setWidgetResizable(True)
        right_card = QtWidgets.QFrame(); right_card.setProperty("modernCard", True)
        right_scroll.setWidget(right_card)
        right_layout = QtWidgets.QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16); right_layout.setSpacing(8)
        chat_title = QtWidgets.QLabel("Chatbot")
        cf = QtGui.QFont(); cf.setFamilies(["Segoe UI","Inter","Arial"])
        cf.setPointSize(16); cf.setWeight(QtGui.QFont.DemiBold); chat_title.setFont(cf)
        right_layout.addWidget(chat_title)
        right_layout.addWidget(self._chat, 1)

        self._main.addWidget(left_scroll, 0)
        self._main.addWidget(right_scroll, 1)
        self._main.setStretch(0, 0)
        self._main.setStretch(1, 1)

        self._tiles = [
            ("extraction","Extraction","Parse notes, auto-structure",
             ["Tabs.extraction_tab", "extraction_tab", "Tabs.Extraction", "Extraction"],
             ["ExtractionTab","MainWidget","ExtractionWidget"]),
            ("appointments","Appointments","List / manage",
             ["Tabs.appointment_tab", "appointment_tab", "Tabs.Appointments", "Appointments"],
             ["AppointmentTab","MainWidget"]),
            ("dashboard","Dashboard","KPIs & charts",
             ["Tabs.dashboard_tab", "dashboard_tab", "Tabs.Dashboard", "Dashboard"],
             ["DashboardTab","MainWidget"]),
            ("accounts", "Accounts", "Billing & payments",
             ["Tabs.account_tab", "account_tab"],  # module candidates
             ["AccountsTab", "AccountsWidget", "MainWidget"]),

            # Client Stats  (matches Tabs/clients_stats_tab.py)
            ("stats", "Client Stats", "Statistics & cohorts",
             ["Tabs.clients_stats_tab", "clients_stats_tab"],
             ["ClientStatsTab", "ClientStatsWidget", "MainWidget"]),
        ]
        self._populate_tiles()
        self._apply_breakpoints()

    def _build_detail(self):
        lay = QtWidgets.QVBoxLayout(self._detail_page)
        lay.setContentsMargins(16, 12, 16, 16); lay.setSpacing(10)
        hdr = QtWidgets.QHBoxLayout()
        self._back_btn = QtWidgets.QToolButton()
        self._back_btn.setAutoRaise(True)
        self._back_btn.setIcon(_qicon("back", 18)); self._back_btn.setIconSize(QtCore.QSize(18,18))
        self._back_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._back_btn.setToolTip("Back")
        self._back_btn.setStyleSheet("""
            QToolButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #E8F0F2, stop:0.5 #CFE7E2, stop:1 #BFE5D6);
                border: 1px solid #C8DCD3; border-radius: 8px; padding: 4px 8px; }
            QToolButton:hover { border-color:#92BFA8; }
            QToolButton:pressed { border-color:#6FA28B; }
        """)
        self._back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        self._detail_title = QtWidgets.QLabel("Module")
        f = QtGui.QFont(); f.setFamilies(["Segoe UI","Inter","Arial"]); f.setPointSize(16); f.setWeight(QtGui.QFont.DemiBold)
        self._detail_title.setFont(f)
        hdr.addWidget(self._back_btn); hdr.addSpacing(6)
        hdr.addWidget(self._detail_title); hdr.addStretch(1)
        lay.addLayout(hdr)
        surf = QtWidgets.QFrame(); surf.setProperty("modernCard", True)
        self._detail_container = QtWidgets.QVBoxLayout(surf)
        self._detail_container.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(surf, 1)

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        self._apply_breakpoints()

    def _apply_breakpoints(self):
        w = self.width()
        self._main.setDirection(QtWidgets.QBoxLayout.TopToBottom if w < 980 else QtWidgets.QBoxLayout.LeftToRight)
        cols = 1 if w < 520 else 2
        if cols != self._grid_column_hint:
            self._grid_column_hint = cols
            self._populate_tiles()

    def _populate_tiles(self):
        while self._grid.count():
            it = self._grid.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()
        cols = max(1, self._grid_column_hint)
        row = col = 0
        for icon_key, title, subtitle, mods, classes in self._tiles:
            btn = TileButton(icon_key, title, subtitle)
            btn.clicked.connect(lambda _=None, m=list(mods), t=title, c=list(classes): self._open_in_place(m, t, c))
            self._grid.addWidget(btn, row, col)
            col += 1
            if col >= cols:
                col = 0; row += 1

    def _open_in_place(self, module_names: List[str], title: str, class_candidates: List[str]):
        widget, err = _safe_create_widget(module_names, class_candidates)
        for i in reversed(range(self._detail_container.count())):
            w = self._detail_container.itemAt(i).widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        if widget is None:
            txt = QtWidgets.QPlainTextEdit(err or "Unknown error")
            txt.setReadOnly(True); txt.setMinimumHeight(260)
            self._detail_container.addWidget(txt, 1)
            self._detail_title.setText(title)
            self._stack.setCurrentIndex(1)
            return
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        if isinstance(widget, QtWidgets.QMainWindow):
            widget.setParent(container)
            widget.setWindowFlags(QtCore.Qt.Widget)
            widget.show()
            lay.addWidget(widget)
        elif isinstance(widget, QtWidgets.QDialog):
            widget.setParent(container)
            widget.setModal(False)
            widget.setWindowFlags(QtCore.Qt.Widget)
            widget.show()
            lay.addWidget(widget)
        else:
            lay.addWidget(widget)

        self._detail_container.addWidget(container, 1)
        self._detail_title.setText(title)
        self._stack.setCurrentIndex(1)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        from UI import design_system
        design_system.apply_global_theme(app, base_point_size=11)
    except Exception:
        pass
    win = QtWidgets.QMainWindow()
    win.setWindowTitle("MedicalDocAI – Home (In-Place Navigation + Aliases)")
    win.resize(1200, 760)
    page = HomePage()
    win.setCentralWidget(page)
    win.show()
    sys.exit(app.exec_())
