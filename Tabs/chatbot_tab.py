# Tabs/chatbot_tab.py — Chat tab wired to local HF client (robust, English-only)
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PyQt5.*")

import html, re, json
from typing import Dict, List, Optional, Any

import torch
from PyQt5 import QtWidgets, QtCore, QtGui

from tools.llm_router import answer_with_tools
from core import app_settings as AS
from UI.icons import icon

# ---------------- Local LLM client (Gemma) ----------------
hf = None
HAVE_LLM = False
try:
    import model_intent.hf_client as hf
    HAVE_LLM = bool(hf) and hasattr(hf, "configure_llm") and hasattr(hf, "chat_stream")
except Exception as e:
    import traceback
    print("hf_client import failed:", e)
    traceback.print_exc()
    HAVE_LLM = False

# ---- design palette ----
def _palette() -> dict:
    defaults = {
        "text": "#1f2937", "textDim": "#334155", "primary": "#3A8DFF",
        "info": "#2CBBA6", "success": "#7A77FF", "danger": "#EF4444",
        "warning": "#F59E0B", "stroke": "#E5EFFA",
        "panel": "rgba(255,255,255,0.55)", "panelInner": "rgba(255,255,255,0.65)",
        "inputBg": "rgba(255,255,255,0.88)", "stripe": "rgba(240,247,255,0.65)",
        "selBg": "#3A8DFF", "selFg": "#ffffff",
    }
    try:
        from UI.design_system import COLORS as THEME
        return {**defaults, **(THEME or {})}
    except Exception:
        return defaults

# Conservative defaults → reduce multilingual drift
GEN_CFG = dict(
    temperature=0.1,        # near-greedy
    top_p=1.0,
    top_k=0,                # disable top-k sampling
    repetition_penalty=1.05,
    max_new_tokens=220,
)

def _polish(*widgets):
    for w in widgets:
        try: w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception: pass

def _is_greeting(t: str) -> bool:
    return bool(re.search(r'\b(hi|hello|hey|yo|good (morning|afternoon|evening))\b', t or '', re.I))

# ---------------- Routing prompt ----------------
INTENT_PROMPT = (
    "You are a router for a clinic assistant. Return ONLY compact JSON for this user message.\n"
    "intents = ['small_talk','show_appointments','book_appointment','update_payment',"
    "'create_report','calc','get_time','show_client_stats']\n"
    "keys: intent, name?, date?, time?, amount?, report_type?, expression?\n"
    "- Use 'small_talk' for greetings/chit-chat.\n"
    "- Use 'calc' ONLY if the user clearly asks a math calc.\n"
    "- Use 'get_time' for date/time questions.\n"
    "No commentary, JSON only."
)

def _english_only(s: str) -> str:
    s = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _llm_route(user_text: str) -> Dict[str, Any]:
    if not HAVE_LLM: return {}
    msgs = [
        {"role": "system", "content": "Return JSON only."},
        {"role": "user", "content": INTENT_PROMPT + "\n\n" + user_text},
    ]
    buf = []
    try:
        for piece in hf.chat_stream(msgs, temperature=0.0, max_new_tokens=120):
            buf.append(piece)
        raw = "".join(buf).strip()
        m = re.search(r"\{.*\}", raw, flags=re.S)
        data = json.loads(m.group(0)) if m else {}
        if data.get("intent"):
            data["intent"] = str(data["intent"]).strip()
        return data
    except Exception:
        return {}

SYSTEM_PROMPT = (
    "You are a concise, friendly medical assistant for a small clinic. "
    "Always respond in clear, professional ENGLISH ONLY. "
    "Never reply in any other language or script. "
    "Keep replies brief. If you don't understand, ask one short clarifying question."
    "You are trained by Ali NOT google"
)

class _Streamer(QtCore.QThread):
    done  = QtCore.pyqtSignal(str)
    failed= QtCore.pyqtSignal(str)
    chunk = QtCore.pyqtSignal(str)     # stream chunks as they arrive
    def __init__(self, messages: List[Dict[str, str]], temperature: float = 0.1, parent=None):
        super().__init__(parent)
        self.messages = messages
        self.temperature = max(float(temperature), 0.0)
        self._stop = False
    def run(self):
        if not HAVE_LLM:
            try:
                user = next((m["content"] for m in reversed(self.messages) if m.get("role") == "user"), "")
                reply = "Hello! How can I help you today?" if _is_greeting(user) else "Got it. How else can I help?"
                for ch in reply:
                    if self._stop:
                        break
                    self.chunk.emit(ch)
                    QtCore.QThread.msleep(10)
                self.done.emit(reply)
            except Exception as e:
                self.failed.emit(str(e))
            return
        try:
            acc = []
            for piece in hf.chat_stream(
                self.messages,
                system=SYSTEM_PROMPT,
                temperature=self.temperature,
                top_p=GEN_CFG["top_p"],
                top_k=GEN_CFG["top_k"],
                repetition_penalty=GEN_CFG["repetition_penalty"],
                max_new_tokens=GEN_CFG["max_new_tokens"],
                english_only=True,
            ):
                if self._stop:
                    break
                acc.append(piece)
                self.chunk.emit(piece)
            self.done.emit("".join(acc))
        except Exception as e:
            self.failed.emit(str(e))
    def stop(self): self._stop = True

# ---------------- ChatBot UI ----------------
class ChatBotTab(QtWidgets.QWidget):
    # signals (useful if a parent window wants to react, optional)
    appointmentCreated  = QtCore.pyqtSignal(dict)
    requestCreateReport = QtCore.pyqtSignal(str, str)
    openClientStatsRequested = QtCore.pyqtSignal()

    def __init__(self, bridge: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        print(f"DEBUG: ChatBotTab initialized. Bridge received: {bridge is not None}")

        # ---- hooks into your app (provided by HomePage)
        bridge = bridge or {}
        self._load_appointments = bridge.get("load_appointments", lambda: [])
        self._append_appointment = bridge.get("append_appointment", lambda appt: False)
        self._update_payment = bridge.get("update_payment", lambda name, payload: False)

        # UI hooks (can remain no-ops if not wired)
        self._switch_to_appts = bridge.get("switch_to_appointments", lambda name=None: None)
        self._refresh_accounts = bridge.get("refresh_accounts", lambda: None)
        self._switch_to_client_stats = bridge.get("switch_to_client_stats", lambda: None)

        # ---- state
        self._messages: List[Dict[str, str]] = []   # ONLY user/assistant turns
        self._stream: Optional[_Streamer] = None
        self._model_path = ""
        self._gen_cfg_override = {}

        # typing animation
        self._typing_cursor: Optional[QtGui.QTextCursor] = None
        self._typing_queue: list[str] = []
        self._typing_buffer: list[str] = []
        self._typing_timer = QtCore.QTimer(self)
        self._typing_timer.setInterval(30)
        self._typing_timer.timeout.connect(self._flush_typing_queue)

        self._typing_indicator_timer = QtCore.QTimer(self)
        self._typing_indicator_timer.setInterval(350)
        self._typing_indicator_timer.timeout.connect(self._tick_typing_indicator)
        self._typing_phase = 0

        self._build_ui()

    # ---------- device/mode helpers ----------
    def _compute_mode_from_settings(self) -> str:
        """Return 'cuda' or 'cpu' based on Settings (ai/compute_mode: auto|gpu|cpu)."""
        try:
            mode = str(AS.read_all().get("ai/compute_mode", "auto")).lower()
        except Exception:
            mode = "auto"
        if mode == "gpu" and torch.cuda.is_available():
            return "cuda"
        if mode == "cpu":
            return "cpu"
        # auto
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _device_badge_text(self) -> str:
        # what user selected
        try:
            choice = str(AS.read_all().get("ai/compute_mode", "auto")).lower()
        except Exception:
            choice = "auto"
        resolved = self._compute_mode_from_settings()
        resolved_label = "GPU" if resolved == "cuda" else "CPU"
        choice_short = {"auto":"auto", "gpu":"GPU", "cpu":"CPU"}.get(choice, "auto")
        return f"Compute: {resolved_label} ({choice_short})"

    def _refresh_device_label(self):
        if not hasattr(self, "lbl_device"):
            return
        text = self._device_badge_text()
        color = "#10b981" if "GPU" in text else "#64748b"
        self.lbl_device.setText(text)
        self.lbl_device.setStyleSheet(f"font-weight:600; color:{color};")

    # ---------- bridge ----------
    def set_chat_bridge(self, bridge: dict):
        bridge = bridge or {}
        self._load_appointments = bridge.get('load_appointments', self._load_appointments)
        self._append_appointment = bridge.get('append_appointment', self._append_appointment)
        self._update_payment = bridge.get('update_payment', self._update_payment)
        self._switch_to_appts = bridge.get('switch_to_appointments', self._switch_to_appts)
        self._refresh_accounts = bridge.get('refresh_accounts', self._refresh_accounts)
        self._switch_to_client_stats = bridge.get('switch_to_client_stats', self._switch_to_client_stats)
        print('DEBUG: Chat bridge wired ✅')

    # ---------- UI ----------
    def _build_ui(self):
        p = _palette()
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QtWidgets.QFrame(); header.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(header); hly.setContentsMargins(12, 12, 12, 12)
        title = QtWidgets.QLabel(self.tr("Assistant Bot (Gemma-3 local)"))
        title.setStyleSheet("font-size:16pt; font-weight:700;")
        self.lbl_mode = QtWidgets.QLabel("LLM: ON" if HAVE_LLM else "LLM: OFF (fallback)")
        self.lbl_mode.setStyleSheet("font-weight:600; color:#10b981;" if HAVE_LLM else "font-weight:600; color:#ef4444;")
        self.lbl_device = QtWidgets.QLabel("")  # will be set below
        self.lbl_intent = QtWidgets.QLabel("")
        self.lbl_intent.setStyleSheet("opacity:0.9;")

        hly.addWidget(title)
        hly.addStretch(1)
        hly.addWidget(self.lbl_mode)
        hly.addSpacing(12)
        hly.addWidget(self.lbl_device)
        hly.addSpacing(12)
        hly.addWidget(self.lbl_intent)
        root.addWidget(header)

        # set the device label now that widget exists
        self._refresh_device_label()

        # Quick chips
        qa_card = QtWidgets.QFrame(); qa_card.setProperty("modernCard", True)
        qa = QtWidgets.QGridLayout(qa_card); qa.setContentsMargins(10,10,10,10); qa.setHorizontalSpacing(8); qa.setVerticalSpacing(8)
        chips = [
            ("calendar", "Show appointments", "show my appointments"),
            ("plus",     "Book: Jane, Fri 10:30 AM", "book appointment for Jane Smith on Friday at 10:30 AM"),
            ("payment",  "Update payment (John, 200)", "update payment for John Doe to 200"),
            ("stats",    "Client stats", "show client stats"),
            ("time",     "What time is it?", "what is the time now?"),
            ("calc",     "Calculate 12.5*(3+2)", "calc 12.5*(3+2)"),
            ("report",   "Draft report (Mary)", "create report for Mary Johnson"),
            ("chat",     "Hello", "hello"),
        ]
        for i, (key, label, payload) in enumerate(chips):
            btn = self._make_chip(label, payload, "")
            btn.setIcon(icon({
                "calendar":"appointments","plus":"appointments","payment":"payment","stats":"stats","time":"time",
                "calc":"calc","report":"report","chat":"chat"}.get(key,"dashboard"), size=16, color="#0f172a"))
            btn.setIconSize(QtCore.QSize(16, 16))
            qa.addWidget(btn, i//4, i%4)
        root.addWidget(qa_card)

        # Transcript
        card = QtWidgets.QFrame(); card.setProperty("modernCard", True)
        v = QtWidgets.QVBoxLayout(card); v.setContentsMargins(12, 12, 12, 12)
        self.view = QtWidgets.QTextBrowser(); self.view.setOpenExternalLinks(True)
        self.view.setStyleSheet("font: 12pt 'Segoe UI'; border:0;")
        self.typing_label = QtWidgets.QLabel("")
        self.typing_label.setStyleSheet("color:#64748b; font-style:italic; padding:3px 6px;")
        v.addWidget(self.view, 1)
        v.addWidget(self.typing_label)
        root.addWidget(card, 1)

        # Input row
        row = QtWidgets.QHBoxLayout()
        self.input = QtWidgets.QLineEdit(); self.input.setPlaceholderText(self.tr("Type your message…"))
        self.btn_send = QtWidgets.QPushButton(self.tr("Send")); self.btn_send.setProperty("variant", "success")
        self.btn_stop = QtWidgets.QPushButton(self.tr("Stop")); self.btn_stop.setProperty("variant", "danger"); self.btn_stop.setEnabled(False)
        _polish(self.btn_send, self.btn_stop)
        row.addWidget(self.input, 1); row.addWidget(self.btn_send); row.addWidget(self.btn_stop)
        root.addLayout(row)
        self.btn_send.clicked.connect(self._on_send)
        self.btn_stop.clicked.connect(self._on_stop)
        self.input.returnPressed.connect(self._on_send)

        # First message
        self._append_assistant(
            "Hello! I can show appointments, book (with confirmation), update payments, do quick calculations, "
            "tell time/date, and draft quick reports."
        )

        # Styles
        self.setStyleSheet(f"""
        QWidget {{ color:{p.get('text','#1f2937')}; font-family:'Segoe UI', Arial; font-size:14px; }}
        QFrame[modernCard="true"] {{
            background:{p.get('panel','rgba(255,255,255,0.55)')};
            border:1px solid rgba(255,255,255,0.45);
            border-radius:12px;
        }}
        QLineEdit {{
            background:{p.get('inputBg','rgba(255,255,255,0.88)')}; color:#0f172a;
            border:1px solid {p.get('stroke','#E5EFFA')}; border-radius:10px; padding:9px 12px;
            selection-background-color:{p.get('selBg','#3A8DFF')}; selection-color:{p.get('selFg','#ffffff')};
        }}
        QLineEdit:focus {{ border:1px solid {p.get('primary','#3A8DFF')}; }}
        QPushButton {{
            border-radius:10px; padding:9px 14px; font-weight:600; border:1px solid transparent;
            background:{p.get('primary','#3A8DFF')}; color:white;
        }}
        QPushButton[variant="success"] {{ background:{p.get('info','#2CBBA6')}; color:white; }}
        QPushButton[variant="danger"]  {{ background:{p.get('danger','#EF4444')}; color:white; }}
        QPushButton[chip="true"] {{
            background:{p.get('stripe','rgba(240,247,255,0.65)')};
            color:{p.get('text','#1f2937')};
            border:1px solid {p.get('stroke','#E5EFFA')};
            border-radius:12px;
            padding:8px 12px;
            text-align:left;
        }}
        QPushButton[chip="true"]:hover {{
            border-color:{p.get('primary','#3A8DFF')};
            box-shadow: 0 0 0 2px rgba(58,141,255,0.15);
        }}
        """)

    # ---------- typing helpers ----------
    def _begin_typing(self):
        if self._typing_cursor is not None:
            return
        p = _palette()
        open_html = (
            f"<div style='display:flex;justify-content:flex-start;margin:6px 0'>"
            f"<div style='max-width:72%;background:{p.get('stripe', 'rgba(240,247,255,0.65)')};"
            f"color:#0f172a;border-radius:14px 14px 14px 2px;padding:8px 12px;"
            f"border:1px solid {p.get('stroke', '#E5EFFA')};'>"
        )
        self._insert_new_block()
        self.view.insertHtml(open_html)

        self._typing_cursor = self.view.textCursor()
        self._typing_queue.clear()
        self._typing_buffer.clear()

        self._typing_phase = 0
        self.typing_label.setText("Assistant is typing")
        self._typing_indicator_timer.start()
        self._typing_timer.start()

    def _end_typing(self):
        if self._typing_cursor is None:
            return
        self.view.moveCursor(QtGui.QTextCursor.End)
        self.view.insertHtml("</div></div>")
        self.view.moveCursor(QtGui.QTextCursor.End)

        self._typing_cursor = None
        self._typing_timer.stop()
        self._typing_indicator_timer.stop()
        self.typing_label.setText("")
        self._insert_new_block()

    def _insert_new_block(self):
        cur = self.view.textCursor()
        cur.movePosition(QtGui.QTextCursor.End)
        cur.insertBlock()
        self.view.setTextCursor(cur)

    def _on_chunk(self, piece: str):
        if piece:
            self._typing_queue.append(piece)
            self._typing_buffer.append(piece)

    def _flush_typing_queue(self):
        if self._typing_cursor is None:
            return
        if not self._typing_queue:
            return
        batch = []
        chars_budget = 24
        while self._typing_queue and chars_budget > 0:
            s = self._typing_queue.pop(0)
            batch.append(s)
            chars_budget -= len(s)
        text = "".join(batch)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        parts = text.split("\n")
        for i, seg in enumerate(parts):
            if seg:
                self._typing_cursor.insertText(seg)
            if i < len(parts) - 1:
                self._typing_cursor.insertHtml("<br/>")
        self.view.ensureCursorVisible()

    def _tick_typing_indicator(self):
        self._typing_phase = (self._typing_phase + 1) % 4
        dots = "." * self._typing_phase
        self.typing_label.setText(f"Assistant is typing{dots}")

    def _open_stats_ui(self):
        opened = False
        try:
            if callable(self._switch_to_client_stats):
                self._switch_to_client_stats()
                opened = True
        except Exception:
            pass
        try:
            self.openClientStatsRequested.emit()
        except Exception:
            pass
        if not opened:
            try:
                w = self.window()
                for name in ("_open_client_stats_tab", "open_client_stats_tab",
                             "_switch_to_client_stats", "switch_to_client_stats"):
                    fn = getattr(w, name, None)
                    if callable(fn):
                        fn()
                        opened = True
                        break
            except Exception:
                pass

    # ---------- helpers to render bubbles ----------
    def _append_user(self, text: str):
        p = _palette()
        self.view.append(
            f"<div style='display:flex;justify-content:flex-end;margin:6px 0'>"
            f"<div style='max-width:70%;background:{p.get('primary','#3A8DFF')};color:#fff;"
            f"border-radius:14px 14px 2px 14px;padding:8px 12px;'>{html.escape(text)}</div></div>"
        )

    def _bot_say(self, msg: str):
        self._append_assistant(msg)
        self._messages.append({"role": "assistant", "content": msg})

    def _append_assistant(self, text: str):
        p = _palette()
        self.view.append(
            f"<div style='display:flex;justify-content:flex-start;margin:6px 0'>"
            f"<div style='max-width:72%;background:{p.get('stripe','rgba(240,247,255,0.65)')};color:#0f172a;"
            f"border-radius:14px 14px 14px 2px;padding:8px 12px;border:1px solid {p.get('stroke','#E5EFFA')};'>"
            f"{html.escape(text)}</div></div>"
        )

    # ---------- SEND ----------
    def _build_chat_messages(self) -> List[Dict[str, str]]:
        return [*self._messages[-12:]]

    def _on_send(self):
        user_text = (self.input.text() or "").strip()
        if not user_text:
            return

        self._append_user(user_text)
        self.input.clear()
        self._messages.append({"role": "user", "content": user_text})

        # 0) FIRST: try tool-based answer (Option B)
        try:
            tool_reply = (answer_with_tools(user_text) or "").strip()
        except Exception:
            tool_reply = ""

        if tool_reply and tool_reply.lower() not in {"done.", "done", "ok"}:
            self._bot_say(tool_reply)
            return

        # 1) Intent route for built-in actions
        route = _llm_route(user_text)
        handled = self._handle_intent(route)

        # 2) If not handled, fall back to normal LLM chat
        if HAVE_LLM and not handled:
            self.btn_send.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self._begin_typing()
            self._stream = _Streamer(self._build_chat_messages(), temperature=GEN_CFG["temperature"], parent=self)
            self._stream.chunk.connect(self._on_chunk)
            self._stream.done.connect(self._on_stream_done)
            self._stream.failed.connect(self._on_stream_failed)
            self._stream.start()
        elif not HAVE_LLM and not handled:
            reply = "Hello! How can I help you today?" if _is_greeting(user_text) else "Got it. How else can I help?"
            self._on_stream_done(reply)

    def _on_stream_done(self, full_text: str):
        tail = self._drain_typing_queue()
        if self._typing_buffer:
            final = "".join(self._typing_buffer)
        else:
            final = _english_only((full_text or "").strip())
            if self._typing_cursor is not None and final and not tail:
                for i, seg in enumerate(final.split("\n")):
                    if seg: self._typing_cursor.insertText(seg)
                    if i < final.count("\n"): self._typing_cursor.insertHtml("<br/>")
        self._end_typing()
        if final:
            self._messages.append({"role": "assistant", "content": _english_only(final)})
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._stream = None

    def _on_stream_failed(self, err: str):
        self._end_typing()
        self._append_assistant(f"[error] {err}")
        if self._messages and self._messages[-1].get("role") == "user":
            self._messages.pop()
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._stream = None

    def _on_stop(self):
        if self._stream:
            self._stream.stop()
        self._end_typing()
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._append_assistant("⏹️ Stopped.")

    def _drain_typing_queue(self) -> str:
        if self._typing_cursor is None or not self._typing_queue:
            return ""
        text = "".join(self._typing_queue)
        self._typing_queue.clear()
        t = text.replace("\r\n", "\n").replace("\r", "\n")
        for i, seg in enumerate(t.split("\n")):
            if seg: self._typing_cursor.insertText(seg)
            if i < t.count("\n"): self._typing_cursor.insertHtml("<br/>")
        self.view.ensureCursorVisible()
        return text

    # ---------- ACTIONS (bridge wiring) ----------
    def _handle_intent(self, route: Dict[str, Any]) -> bool:
        intent = (route or {}).get("intent", "").strip().lower()

        # Small talk → let the LLM chat
        if intent in ("", "small_talk"):
            return False

        # SHOW APPOINTMENTS
        if intent == "show_appointments":
            try:
                appts = list(self._load_appointments() or [])
            except Exception:
                appts = []
            if not appts:
                msg = "You have no appointments."
            else:
                def _g(a, k1, k2=None, default="?"):
                    return a.get(k1) or (a.get(k2) if k2 else None) or default
                lines = [
                    f"• {_g(a, 'Appointment Date', 'date')} {_g(a, 'Appointment Time', 'time')} — {_g(a, 'Name', 'name')}"
                    for a in appts
                ]
                msg = "Your upcoming appointments:\n" + "\n".join(lines)
            self._append_assistant(msg)
            self._messages.append({"role": "assistant", "content": msg})
            QtCore.QTimer.singleShot(0, lambda: self._switch_to_appts(None))
            return True

        # BOOK APPOINTMENT
        if intent == "book_appointment":
            name = route.get("name") or "Unknown"
            date = route.get("date") or "TBD"
            time = route.get("time") or "TBD"
            appt = {"Name": name, "Appointment Date": date or "Not Specified", "Appointment Time": time or "Not Specified"}
            ok = bool(self._append_appointment(appt))
            msg = (f"Booked {name} on {date} at {time}." if ok else "Sorry, I couldn't save that appointment.")
            self._append_assistant(msg)
            self._messages.append({"role": "assistant", "content": msg})
            try: self.appointmentCreated.emit(appt)
            except Exception: pass
            QtCore.QTimer.singleShot(0, lambda: self._switch_to_appts(name))
            return True

        # UPDATE PAYMENT
        if intent == "update_payment":
            name = route.get("name") or "Unknown"
            amount = route.get("amount")
            payload = {"amount": amount}
            ok = False
            try: ok = bool(self._update_payment(name, payload))
            except Exception: ok = False
            msg = (f"Updated payment for {name} to {amount}." if ok else "Sorry, I couldn't update that payment.")
            self._append_assistant(msg)
            self._messages.append({"role": "assistant", "content": msg})
            try: self._refresh_accounts()
            except Exception: pass
            return True

        # CLIENT STATS
        if intent == "show_client_stats":
            try:
                from data.data import load_all_clients as _lac
                clients = _lac() or []
                def f(x):
                    try: return float(str(x).replace(',', '').strip() or 0)
                    except: return 0.0
                total = len(clients)
                total_paid = sum(f(c.get("Total Paid", 0)) for c in clients)
                total_amt = sum(f(c.get("Total Amount", 0)) for c in clients)
                total_owed = sum(f(c.get("Owed", total_amt - total_paid)) for c in clients)
                msg = (f"Opening client stats…\n"
                       f"- Clients: {total}\n"
                       f"- Total Paid: {total_paid:.2f}\n"
                       f"- Total Amount: {total_amt:.2f}\n"
                       f"- Total Owed: {total_owed:.2f}")
            except Exception:
                msg = "Opening client stats…"
            self._append_assistant(msg)
            self._messages.append({"role": "assistant", "content": msg})
            QtCore.QTimer.singleShot(0, self._open_stats_ui)
            return True

        return False

    # ---------- public helpers ----------
    def set_llm_enabled(self, enabled: bool):
        global HAVE_LLM
        can_enable = bool(enabled) and (hf is not None) and hasattr(hf, "chat_stream")
        HAVE_LLM = can_enable
        self.lbl_mode.setText("LLM: ON" if HAVE_LLM else "LLM: OFF (fallback)")
        self.lbl_mode.setStyleSheet("font-weight:600; color:#10b981;" if HAVE_LLM else "font-weight:600; color:#ef4444;")
        self._refresh_device_label()

    def set_bridge(self, bridge: Dict[str, Any]):
        bridge = bridge or {}
        self._load_appointments   = bridge.get('load_appointments', self._load_appointments)
        self._append_appointment  = bridge.get('append_appointment', self._append_appointment)
        self._update_payment      = bridge.get('update_payment', self._update_payment)
        self._switch_to_appts     = bridge.get('switch_to_appointments', self._switch_to_appts)
        self._refresh_accounts    = bridge.get('refresh_accounts', self._refresh_accounts)
        self._switch_to_client_stats = bridge.get('switch_to_client_stats', self._switch_to_client_stats)
        print('DEBUG: Chat bridge wired ✅')

    def set_model_config(self, cfg: dict):
        """Call this once after creating the widget; flips 'LLM: ON' only if smoke test succeeds."""
        try:
            self._model_path = cfg.get("model_path", "")
            self._gen_cfg_override = {
                "max_new_tokens": int(cfg.get("max_new_tokens", GEN_CFG["max_new_tokens"])),
                "temperature": float(cfg.get("temperature", GEN_CFG["temperature"])),
            }
            if hf is None or not hasattr(hf, "configure_llm"):
                print("hf_client not available; skipping configure_llm.")
                self.set_llm_enabled(False)
                return

            print("[LLM] configure_llm start:", self._model_path)
            kwargs = dict(
                model_path=self._model_path,
                max_new_tokens=self._gen_cfg_override["max_new_tokens"],
                temperature=self._gen_cfg_override["temperature"],
                top_p=GEN_CFG["top_p"],
                top_k=GEN_CFG["top_k"],
                local_files_only=True,
            )
            # device mode (preferred on newer hf_client)
            device_mode = self._compute_mode_from_settings()
            try:
                kwargs["device_mode"] = device_mode
                hf.configure_llm(**kwargs)
            except TypeError:
                kwargs.pop("device_mode", None)
                hf.configure_llm(**kwargs)

            # Smoke test: system + user → 1 token
            try:
                msgs = [{"role":"user","content":"ping"}]
                for _ in hf.chat_stream(msgs, system=SYSTEM_PROMPT, max_new_tokens=1, temperature=0.0):
                    break
                print("[LLM] smoke test OK")
                self.set_llm_enabled(True)
            except Exception as e:
                import traceback
                print("[LLM] smoke test failed:", e)
                traceback.print_exc()
                self.set_llm_enabled(False)
        except Exception as e:
            import traceback
            print("set_model_config error:", e)
            traceback.print_exc()
            self.set_llm_enabled(False)

    def set_model_from_settings(self):
        """Re-apply the model with current Settings; safe to call after Settings → Save."""
        try:
            kwargs = dict(
                model_path=self._model_path,
                max_new_tokens=self._gen_cfg_override.get("max_new_tokens", GEN_CFG["max_new_tokens"]),
                temperature=self._gen_cfg_override.get("temperature", GEN_CFG["temperature"]),
                top_p=GEN_CFG["top_p"],
                top_k=GEN_CFG["top_k"],
                local_files_only=True,
            )
            try:
                kwargs["device_mode"] = self._compute_mode_from_settings()
                hf.configure_llm(**kwargs)
            except TypeError:
                kwargs.pop("device_mode", None)
                hf.configure_llm(**kwargs)
            self.set_llm_enabled(True)
        except Exception as e:
            print("set_model_from_settings failed:", e)
            self.set_llm_enabled(False)

    def external_send(self, text: str):
        self.input.setText(text)
        self._on_send()

    def _make_chip(self, label: str, payload: str, tooltip: str = "") -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(label)
        btn.setProperty("chip", True)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        if tooltip:
            btn.setToolTip(tooltip + "\nTip: Shift-click to insert without sending.")
        _polish(btn)
        def on_click():
            mods = QtWidgets.QApplication.keyboardModifiers()
            self.input.setText(payload)
            if not (mods & QtCore.Qt.ShiftModifier):
                self._on_send()
        btn.clicked.connect(on_click)
        return btn

    def tr(self, t):
        try:
            from features.translation_helper import tr
            return tr(t)
        except Exception:
            return t


# ---- quick test ----
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = ChatBotTab()
    try:
        w.set_model_config({
            "model_path": r"C:\Users\asult\.cache\huggingface\hub\models--gemma-3--270m-it",
            "max_new_tokens": 220,
            "temperature": 0.1,
        })
    except Exception as e:
        print("Quick-test model config failed:", e)
    w.resize(820, 620)
    w.show()
    sys.exit(app.exec_())
