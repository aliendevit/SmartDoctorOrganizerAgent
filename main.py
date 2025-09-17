from __future__ import annotations
import importlib, importlib.util, sys, types, traceback, base64
from typing import List, Optional, Tuple, Sequence
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from Tabs.chatbot_tab import ChatBotTab
from home_page import _resolve_hf_snapshot_dir


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
        "muted":       "#64748b",
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

# ---------------- SVG ICONS (monochrome, embedded) ----------------
# Simple, readable healthcare/ops shapes (24x24 viewBox)
ICONS = {
    "extraction": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="3.5" width="17" height="17" rx="3"/>
  <path d="M7 8h10M7 12h10M7 16h6"/>
</svg>
""",
    "appointments": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="4.5" width="17" height="16" rx="3"/>
  <path d="M8 3v4M16 3v4M3.5 9.5h17"/>
  <circle cx="12" cy="14" r="3.2"/>
  <path d="M12 12.2V14l1.2 1.2"/>
</svg>
""",
    "dashboard": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 13a8 8 0 1 1 16 0"/>
  <path d="M12 13l4-4"/>
  <circle cx="12" cy="13" r="1.2" fill="currentColor"/>
  <path d="M3 21h18"/>
</svg>
""",
    "accounts": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3.5" y="5" width="17" height="14" rx="2.5"/>
  <path d="M3.5 9h17M8 13h4M8 16h8"/>
</svg>
""",
    "stats": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 20V6M10 20V10M16 20V4M22 20H2"/>
</svg>
""",
    "settings": """
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3.2"/>
  <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.02.02a2 2 0 1 1-2.83 2.83l-.02-.02A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .18 1.8 1.8 0 0 1-2 0A1.8 1.8 0 0 0 11 19.4a1.8 1.8 0 0 0-1 .18 1.8 1.8 0 0 1-2 0A1.8 1.8 0 0 0 7 19.4a1.8 1.8 0 0 0-1.98-.36l-.02.02a2 2 0 1 1-2.83-2.83l.02-.02A1.8 1.8 0 0 0 4.6 15c0-.33-.06-.66-.18-.98a1.8 1.8 0 0 0 0-1.99c.12-.32.18-.65.18-.98a1.8 1.8 0 0 0-.36-1.98l-.02-.02a2 2 0 1 1 2.83-2.83l.02.02A1.8 1.8 0 0 0 7 4.6c.33 0 .66-.06.98-.18a1.8 1.8 0 0 0 1.99 0C10.3 4.54 10.63 4.48 11 4.48c.33 0 .66.06.98.18a1.8 1.8 0 0 0 1.99 0C14.3 4.54 14.63 4.48 15 4.48c.33 0 .66.06.98.18l.02-.02a2 2 0 1 1 2.83 2.83l-.02.02c.24.3.36.63.36.98 0 .33.06.66.18.98a1.8 1.8 0 0 0 0 1.99c-.12.32-.18.65-.18.98Z"/>
</svg>
""",
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

# ---------------- Icon view ----------------
class SvgIcon(QtWidgets.QLabel):
    def __init__(self, svg_markup: str, size: int = 28, color: str = "#0f172a", parent=None):
        super().__init__(parent)
        self._svg = svg_markup
        self._size = size
        self._color = color
        self.setFixedSize(size, size)
        self.setScaledContents(True)

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self)
        p.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        svg = self._svg.replace("currentColor", self._color)
        ba = QtCore.QByteArray(svg.encode("utf-8"))
        r = QtSvg.QSvgRenderer(ba)
        r.render(p, QtCore.QRectF(0, 0, self._size, self._size))

# ---------------- Tile Button ----------------
class TileButton(QtWidgets.QPushButton):
    def __init__(self, icon_key: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setCheckable(False)
        self._build(icon_key, title, subtitle)

    def _build(self, icon_key: str, title: str, subtitle: str):
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.setMinimumSize(170, 124)
        self.setMaximumHeight(148)

        normal1, normal2, normal3 = "#E8F0F2", "#CFE7E2", "#BFE5D6"
        hover1,  hover2,  hover3  = "#F4F8F9", "#D6EFE8", "#A9DFC7"
        press1,  press2,  press3  = "#D4DEE0", "#B8D6CC", "#90C9B5"

        self.setStyleSheet(
            f"""
            QPushButton {{
                background:
                    qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 {normal1}, stop:0.5 {normal2}, stop:1 {normal3});
                border: 2px solid #C8DCD3;
                border-radius: 18px;
                padding: 14px;
                text-align: left;
                color: {THEME.get('text','#1f2937')};
            }}
            QPushButton:hover {{
                background:
                    qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 {hover1}, stop:0.5 {hover2}, stop:1 {hover3});
                border: 2px solid #92BFA8;
            }}
            QPushButton:pressed {{
                background:
                    qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 {press1}, stop:0.5 {press2}, stop:1 {press3});
                border: 2px solid #6FA28B;
            }}
            """
        )

        eff = QtWidgets.QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(14)
        eff.setOffset(0, 4)
        eff.setColor(QtGui.QColor(160, 190, 170, 80))
        self.setGraphicsEffect(eff)

        col = QtWidgets.QVBoxLayout(self)
        col.setSpacing(8)

        # icon badge
        badge = QtWidgets.QFrame()
        badge.setFixedSize(40, 40)
        badge.setStyleSheet("""
            QFrame {
                border-radius: 10px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(44,187,166,0.16),
                    stop:1 rgba(58,141,255,0.14));
                border: 1px solid rgba(44,187,166,0.25);
            }
        """)
        bl = QtWidgets.QHBoxLayout(badge); bl.setContentsMargins(6,6,6,6)
        icon = SvgIcon(ICONS.get(icon_key, ICONS["dashboard"]), 28, color="#0f172a")
        bl.addWidget(icon, 0, QtCore.Qt.AlignCenter)

        # typography
        title_lbl = QtWidgets.QLabel(title)
        subtitle_lbl = QtWidgets.QLabel(subtitle)
        title_font = QtGui.QFont()
        # Prefer Segoe UI Variable / Segoe UI / Inter
        title_font.setFamilies(["Segoe UI Variable", "Segoe UI", "Inter", "Arial"])
        title_font.setPointSize(15)
        title_font.setWeight(QtGui.QFont.DemiBold)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color:#0f172a;")

        sub_font = QtGui.QFont()
        sub_font.setFamilies(["Segoe UI", "Inter", "Arial"])
        sub_font.setPointSize(11)
        sub_font.setWeight(QtGui.QFont.Normal)
        subtitle_lbl.setFont(sub_font)
        subtitle_lbl.setStyleSheet("color:#475569;")
        subtitle_lbl.setWordWrap(True)

        col.addWidget(badge, 0, QtCore.Qt.AlignLeft)
        col.addWidget(title_lbl)
        if subtitle:
            col.addWidget(subtitle_lbl)
        col.addStretch(1)

# ---------------- Home Page ----------------
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
            """
            QWidget#HomePage {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F5F9FA,
                    stop:0.5 #E3F1ED,
                    stop:1  #D7EBE2
                );
                color: #1f2937;
            }
            QScrollArea { border:none; }
            QFrame[modernCard="true"] {
                background: rgba(255,255,255,0.55);
                border: 1px solid rgba(200,220,210,0.55);
                border-radius: 12px;
            }
            """
        )

        rootv = QtWidgets.QVBoxLayout(self)
        rootv.setContentsMargins(16, 12, 16, 16)
        rootv.setSpacing(12)

        # Top bar
        topbar = QtWidgets.QHBoxLayout()
        app_title = QtWidgets.QLabel("MedicalDocAI")
        tf = QtGui.QFont()
        tf.setFamilies(["Segoe UI Variable", "Segoe UI", "Inter", "Arial"])
        tf.setPointSize(18); tf.setWeight(QtGui.QFont.DemiBold)
        app_title.setFont(tf)
        app_title.setStyleSheet("letter-spacing:0.2px;")
        topbar.addWidget(app_title)
        topbar.addStretch(1)

        # settings icon (SVG, not emoji)
        settings_btn = QtWidgets.QToolButton()
        settings_btn.setAutoRaise(True)
        settings_btn.setCursor(QtCore.Qt.PointingHandCursor)
        settings_btn.setToolTip("Settings")
        settings_btn.setIcon(self._make_svg_icon(ICONS["settings"], "#0f172a"))
        settings_btn.setIconSize(QtCore.QSize(18,18))
        settings_btn.setStyleSheet("""
            QToolButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #E8F0F2, stop:0.5 #CFE7E2, stop:1 #BFE5D6);
                border: 1px solid #C8DCD3;
                border-radius: 8px;
                padding: 4px 6px;
            }
            QToolButton:hover { border-color:#92BFA8; }
            QToolButton:pressed { border-color:#6FA28B; }
        """)
        settings_btn.clicked.connect(lambda: self._open_in_dialog(
            ["Tabs.settings_tab"], "Settings", ["SettingsTab", "SettingsWidget", "MainWidget"]
        ))
        topbar.addWidget(settings_btn)
        rootv.addLayout(topbar)

        root = QtWidgets.QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        rootv.addLayout(root, 1)

        # Left: tiles
        left_wrapper = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_wrapper)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        hdr = QtWidgets.QHBoxLayout()
        h = QtWidgets.QLabel("Home – Workspaces")
        hf = QtGui.QFont()
        hf.setFamilies(["Segoe UI", "Inter", "Arial"])
        hf.setPointSize(15); hf.setWeight(QtGui.QFont.DemiBold)
        h.setFont(hf)
        h.setStyleSheet("color:#0f172a;")
        hdr.addWidget(h)
        hdr.addStretch(1)
        left_layout.addLayout(hdr)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        left_layout.addWidget(scroll, 1)

        grid_host = QtWidgets.QWidget()
        self._grid = QtWidgets.QGridLayout(grid_host)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        scroll.setWidget(grid_host)

        root.addWidget(left_wrapper, 0)

        # Right: chatbot (kept as-is)
        right_card = QtWidgets.QFrame()
        right_card.setProperty("modernCard", True)
        right_layout = QtWidgets.QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(8)

        chat_title = QtWidgets.QLabel("Chatbot")
        cf = QtGui.QFont()
        cf.setFamilies(["Segoe UI", "Inter", "Arial"])
        cf.setPointSize(16); cf.setWeight(QtGui.QFont.DemiBold)
        chat_title.setFont(cf)
        right_layout.addWidget(chat_title)
        right_layout.addWidget(self._chat, 1)

        root.addWidget(right_card, 1)
        root.setStretch(0, 0)
        root.setStretch(1, 1)

        # Tiles (only Tabs.*)
        self._tiles = [
            ("extraction","Extraction","Parse notes, auto-structure",
             ["Tabs.extraction_tab"], ["ExtractionTab","MainWidget","ExtractionWidget"]),
            ("appointments","Appointments","List / manage",
             ["Tabs.appointment_tab"], ["AppointmentTab","MainWidget"]),
            ("dashboard","Dashboard","KPIs & charts",
             ["Tabs.dashboard_tab"], ["DashboardTab","MainWidget"]),
            ("accounts","Accounts","Billing & payments",
             ["Tabs.account_tab"], ["AccountsTab","MainWidget"]),
            ("stats","Client Stats","Statistics & cohorts",
             ["Tabs.clients_stats_tab"], ["ClientStatsTab","MainWidget"]),
        ]
        self._populate_tiles()

    def _make_svg_icon(self, svg_markup: str, color: str) -> QtGui.QIcon:
        svg = svg_markup.replace("currentColor", color)
        renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
        img = QtGui.QImage(24, 24, QtGui.QImage.Format_ARGB32)
        img.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(img)
        p.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        renderer.render(p)
        p.end()
        return QtGui.QIcon(QtGui.QPixmap.fromImage(img))

    def _populate_tiles(self):
        row = 0; col = 0
        for icon_key, title, subtitle, mods, classes in self._tiles:
            btn = TileButton(icon_key, title, subtitle)
            btn.clicked.connect(lambda _=None, m=list(mods), t=title, c=list(classes): self._open_in_dialog(m, t, c))
            self._grid.addWidget(btn, row, col)
            col += 1
            if col >= 2:
                col = 0; row += 1

    def _open_in_dialog(self, module_names: List[str], title: str, class_candidates: List[str]):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setModal(False)
        dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        dlg.resize(1000, 720)

        outer = QtWidgets.QVBoxLayout(dlg)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        header = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(title)
        tf = QtGui.QFont()
        tf.setFamilies(["Segoe UI", "Inter", "Arial"]); tf.setPointSize(16); tf.setWeight(QtGui.QFont.DemiBold)
        lbl.setFont(tf)
        header.addWidget(lbl)
        header.addStretch(1)
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setProperty("variant", "ghost")
        close_btn.clicked.connect(dlg.close)
        header.addWidget(close_btn)
        outer.addLayout(header)

        frame = QtWidgets.QFrame(); frame.setProperty("modernCard", True)
        lay = QtWidgets.QVBoxLayout(frame); lay.setContentsMargins(12, 12, 12, 12)
        loading = QtWidgets.QLabel("Loading…"); loading.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(loading)
        outer.addWidget(frame, 1)

        def create_and_swap():
            try:
                widget, err = _safe_create_widget(module_names, class_candidates)
                if widget is None:
                    txt = QtWidgets.QPlainTextEdit(err or "Unknown error")
                    txt.setReadOnly(True); txt.setMinimumHeight(260)
                    lay.replaceWidget(loading, txt); loading.setParent(None); return
                lay.replaceWidget(loading, widget); loading.setParent(None)
            except BaseException:
                txt = QtWidgets.QPlainTextEdit(traceback.format_exc())
                txt.setReadOnly(True); txt.setMinimumHeight(260)
                lay.replaceWidget(loading, txt); loading.setParent(None)

        QtCore.QTimer.singleShot(0, create_and_swap)
        gp = self.geometry(); pt = self.mapToGlobal(gp.topRight())
        dlg.move(max(0, pt.x() - dlg.width()), pt.y() + 64)
        self._floating_windows.append(dlg)
        dlg.show()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # make sure global theme is applied
    try:
        from UI import design_system

        design_system.apply_global_theme(app, base_point_size=11)
    except Exception:
        pass

    win = QtWidgets.QMainWindow()
    win.setWindowTitle("MedicalDOC.AI – V1.9.9demo")
    page = HomePage()
    win.setCentralWidget(page)
    win.resize(1200, 760)
    win.show()

    # >>> LLM CONFIG HERE (after widget exists) <<<
    try:
        base_path = r"C:\Users\asult\.cache\huggingface\hub\models--gemma-3--270m-it"
        snapshot = _resolve_hf_snapshot_dir(base_path)
        print(f"[main] Configuring ChatBot with snapshot:\n  {snapshot}")
        page.chatbot.set_model_config({
            "model_path": snapshot,
            "max_new_tokens": 220,
            "temperature": 0.1,  # stable English, minimal drift
        })
        # Do NOT call set_llm_enabled(True); ChatBotTab flips to ON only after smoke test passes.
    except Exception as e:
        print("[main] LLM configure error:", e)
        traceback.print_exc()

    sys.exit(app.exec_())