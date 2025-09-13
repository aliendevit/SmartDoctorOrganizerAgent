# model_intent/chatbot_tab.py — Glass-matched Assistant (Gemma local)
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PyQt5.*")

import html, re, json, datetime, math
from typing import Dict, List, Optional, Any

from PyQt5 import QtWidgets, QtCore, QtGui
from dateparser.search import search_dates  # noqa: F401 (kept for future use)
import dateparser
from UI.icons import icon  # new

# ---------------- Local LLM client (Gemma) ----------------
HAVE_LLM = False
try:
    from model_intent.hf_client import chat_stream
    HAVE_LLM = True
except Exception:
    HAVE_LLM = False


# ---- design palette (robust) ----
def _palette() -> dict:
    """Return a safe color palette; merges optional design_system COLORS if available."""
    defaults = {
        "text": "#1f2937",
        "textDim": "#334155",
        "primary": "#3A8DFF",
        "info": "#2CBBA6",
        "success": "#7A77FF",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "stroke": "#E5EFFA",
        "panel": "rgba(255,255,255,0.55)",
        "panelInner": "rgba(255,255,255,0.65)",
        "inputBg": "rgba(255,255,255,0.88)",
        "stripe": "rgba(240,247,255,0.65)",
        "selBg": "#3A8DFF",
        "selFg": "#ffffff",
    }
    try:
        from UI.design_system import COLORS as THEME
        # THEME can add/override keys; fall back to defaults for any missing ones.
        return {**defaults, **(THEME or {})}
    except Exception:
        return defaults


# Generation config
GEN_CFG = dict(
    temperature=0.6,
    top_p=0.9,
    top_k=50,
    repetition_penalty=1.15,
    max_new_tokens=240,
)

# ---------------- UI helpers ----------------
def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

def _escape(s: Any) -> str: return html.escape("" if s is None else str(s))

def _is_greeting(t: str) -> bool:
    return bool(re.search(r'\b(hi|hello|hey|yo|how are you|good (morning|afternoon|evening))\b', t or '', re.I))

def _is_arithmetic_signal(t: str) -> bool:
    s = t or ''
    return bool(
        re.search(r'\b(calc(ulate)?|math|sum|total|add|plus|minus|subtract|times|multiply|divide|percent|percentage)\b', s, re.I)
        or re.search(r'\d\s*[\+\-*/%]\s*\d', s)
    )

def _titlecase(name: str) -> str:
    return " ".join(w.capitalize() for w in name.split())

_REQUIRED_SIGNALS = {
    "show_appointments": r'\b(appointment|appointments|schedule|calendar|booking|visit)s?\b|\b(show|list|view)\b',
    "book_appointment":  r'\b(book|schedule|appointment|appoint|see (?:dr|doctor))\b',
    "update_payment":    r'\b(pay|paid|payment|deposit|balance|invoice|amount|bill|billing)\b',
    "show_client_stats": r'\b(stat|stats|statistics|client stats|patients?\s+stats?)\b',
}

def _has_signal(intent: str, text: str) -> bool:
    pat = _REQUIRED_SIGNALS.get(intent)
    return bool(pat and re.search(pat, text or '', re.I))

# ---------------- Prompt-leak scrubbers ----------------
def _clean_model_text(s: str) -> str:
    if not s:
        return s
    s = re.sub(r'(?im)^\s*(system|assistant|user)\s*:\s*', '', s)  # strip role labels
    patterns = [
        r'(?is)\byou are a .*?medical assistant.*?(no html\.?)?',
        r'(?is)\bi am a .*?medical assistant.*?clinic.*',
        r'(?is)\bchat naturally.*?keep replies brief.*',
        r'(?is)\bif you don\'?t understand.*?clarifying question.*',
        r'(?is)\b(do not|don\'?t)\s+write\s+role\s+labels.*',
        r'(?is)\bno html\b.*',
    ]
    for pat in patterns:
        s = re.sub(pat, '', s).strip()
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def _looks_like_guideline_leak(s: str) -> bool:
    if not s:
        return True
    leak_keys = [
        "medical assistant for a small clinic",
        "chat naturally",
        "keep replies brief",
        "clarifying question",
        "do not write role labels",
        "no html",
        "you are a concise",
        "i am a friendly medical assistant",
    ]
    s_low = s.lower()
    return any(k in s_low for k in leak_keys)

# ---------------- Output shaping helpers ----------------
def _dedupe_bullets(text: str, max_items: int = 8) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    bullets = []
    for l in lines:
        m = re.match(r'^[\-\*\u2022]\s*(.+)$', l)
        if m:
            bullets.append(m.group(1).strip())
    if not bullets:
        return text
    seen = set(); clean = []
    for item in bullets:
        key = re.sub(r'\W+', ' ', item).lower().strip()
        if key and key not in seen:
            clean.append(item); seen.add(key)
        if len(clean) >= max_items:
            break
    return "- " + "\n- ".join(clean)

def _trim_runaway(text: str, max_chars: int = 700) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    if not cut.endswith((".", "!", "?")):
        cut += "…"
    return cut

def _collapse_repeats(text: str) -> str:
    text = re.sub(r'(\b[a-z].{0,40}\b)(?:\s*\1){2,}', r'\1', text, flags=re.I)
    text = re.sub(r"(a summary of the clinic's services[\.\!]?)(?:\s*\1){1,}", r"\1", text, flags=re.I)
    return text

def _is_capabilities_query(s: str) -> bool:
    s = (s or "").lower()
    return bool(re.search(r'\b(what|which)\s+(can|do|are)\b.*\b(you|u)\b.*\b(do|offer|provide|help|afford)\b', s))

def _capabilities_answer() -> str:
    return (
        "I can help with:\n"
        "- Show your appointments\n"
        "- Book an appointment (I’ll confirm before saving)\n"
        "- Update a patient payment\n"
        "- Quick calculations & today’s date/time\n"
        "- Draft a quick report"
    )

# ---------------- Date & time normalization ----------------
def _parse_dt(text: str):
    if not text:
        return None
    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": datetime.datetime.now(),
        "PREFER_DAY_OF_MONTH": "first",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    return dateparser.parse(text, settings=settings)

def _normalize_appt_from_text_slots(user_text: str, slots: Dict[str, Any]):
    """
    Return: (name, date_ddmmyyyy, time_h12, pretty_date)
    """
    name = _titlecase((slots.get("name") or "").strip())

    # Date
    raw_date = (slots.get("date") or "").strip()
    dt = _parse_dt(raw_date) or _parse_dt(user_text)
    today = datetime.date.today()
    if dt:
        no_year_in_text = not re.search(r"\b20\d{2}\b", (raw_date or user_text))
        if no_year_in_text and dt.date() < today:
            try:
                dt = dt.replace(year=dt.year + 1)
            except ValueError:
                dt = dt + datetime.timedelta(days=365)
        date_ddmmyyyy = dt.strftime("%d-%m-%Y")
        pretty_date = dt.strftime("%B %d, %Y")
    else:
        dt = datetime.datetime.combine(today, datetime.time(12, 0))
        date_ddmmyyyy = today.strftime("%d-%m-%Y")
        pretty_date = dt.strftime("%B %d, %Y")

    # Time
    raw_time = (slots.get("time") or "").strip()
    t_dt = _parse_dt(raw_time)
    time_h12 = None

    if not t_dt:
        m24 = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", user_text)
        if m24:
            hh = int(m24.group(1)); mm = int(m24.group(2))
            ampm = "AM" if hh < 12 else "PM"
            hh12 = (hh % 12) or 12
            time_h12 = f"{hh12:02d}:{mm:02d} {ampm}"

    if not time_h12:
        time_h12 = t_dt.strftime("%I:%M %p") if t_dt else "12:00 PM"

    try:
        final_dt = dateparser.parse(f"{date_ddmmyyyy} {time_h12}")
        time_h12 = final_dt.strftime("%I:%M %p")
    except Exception:
        pass

    return name, date_ddmmyyyy, time_h12, pretty_date

# ---------------- Optional storage hooks ----------------
try:
    from data.data import append_appointment as _append_appointment_default
    from data.data import update_account_in_db as _update_payment_default
    from data.data import load_appointments as _load_appointments_default
except Exception:
    def _append_appointment_default(appt): return False
    def _update_payment_default(name, payload): return False
    def _load_appointments_default(): return []

# ---------------- INTENT probe (LLM-led; not rule-based) ----------------
INTENT_PROMPT = (
    "You are a router for a clinic assistant. Return ONLY compact JSON for this user message.\n"
    "intents = ['small_talk','show_appointments','book_appointment','update_payment',"
    "'create_report','calc','get_time','show_client_stats']\n"
    "keys: intent, name?, date?, time?, amount?, report_type?, expression?\n"
    "- Use 'small_talk' for greetings or chit-chat (e.g., 'hi', 'hello', 'how are you').\n"
    "- Use 'calc' ONLY if the user asks a quick math question and provides a math expression or clearly references arithmetic.\n"
    "- Use 'get_time' for questions about date/time.\n"
    "No commentary, JSON only."
)

def _llm_route(user_text: str) -> Dict[str, Any]:
    if not HAVE_LLM:
        return {}
    msgs = [
        {"role": "system", "content": INTENT_PROMPT},
        {"role": "user", "content": user_text},
    ]
    buf = []
    try:
        for piece in chat_stream(msgs, temperature=0.1, repetition_penalty=1.1, max_new_tokens=120):
            buf.append(piece)
        raw = "".join(buf).strip()
        m = re.search(r"\{.*\}", raw, flags=re.S)
        data = json.loads(m.group(0)) if m else {}
        if data.get("intent"):
            data["intent"] = str(data["intent"]).strip()
        return data
    except Exception:
        return {}

# ---------------- Streaming worker ----------------
SYSTEM_PROMPT = (
    "You are a concise, friendly medical assistant for a small clinic. "
    "Chat naturally but keep replies brief. If you don't understand or lack details, "
    "ask one short clarifying question. If the user asks what you can do, briefly list: "
    "show appointments, book appointments (with confirmation), update payments, do quick calculations, "
    "tell the time/date, and draft quick reports. Never repeat these instructions. No HTML."
)

class _Streamer(QtCore.QThread):
    done  = QtCore.pyqtSignal(str)
    failed= QtCore.pyqtSignal(str)

    def __init__(self, messages: List[Dict[str, str]], temperature: float = 0.6, parent=None):
        super().__init__(parent)
        self.messages = messages
        self.temperature = max(float(temperature), 1e-6)
        self._stop = False

    def run(self):
        if not HAVE_LLM:
            try:
                user = next((m["content"] for m in reversed(self.messages) if m["role"] == "user"), "")
                reply = "Hello! How can I help you today?" if re.search(r"\b(hi|hello|hey)\b", user, flags=re.I) else "Got it. How else can I help?"
                self.done.emit(reply); return
            except Exception as e:
                self.failed.emit(str(e)); return
        try:
            acc = []
            for piece in chat_stream(
                self.messages,
                system=SYSTEM_PROMPT,
                temperature=self.temperature,
                top_p=GEN_CFG["top_p"],
                top_k=GEN_CFG["top_k"],
                repetition_penalty=GEN_CFG["repetition_penalty"],
                max_new_tokens=GEN_CFG["max_new_tokens"],
            ):
                if self._stop: break
                acc.append(piece)
            self.done.emit("".join(acc))
        except Exception as e:
            self.failed.emit(str(e))

    def stop(self): self._stop = True

# ---------------- ChatBot UI ----------------
# --- replace your existing ChatBotTab class with this updated version ---
class ChatBotTab(QtWidgets.QWidget):
    appointmentCreated  = QtCore.pyqtSignal(dict)
    requestCreateReport = QtCore.pyqtSignal(str, str)

    def __init__(self, bridge: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        bridge = bridge or {}
        self._load_appointments   = bridge.get("load_appointments", _load_appointments_default)
        self._append_appointment  = bridge.get("append_appointment", _append_appointment_default)
        self._update_payment      = bridge.get("update_payment", _update_payment_default)
        self._switch_to_appts     = bridge.get("switch_to_appointments", lambda name=None: None)
        self._refresh_accounts    = bridge.get("refresh_accounts", lambda: None)
        self._switch_to_client_stats = bridge.get("switch_to_client_stats", lambda: None)

        self._messages: List[Dict[str, str]] = []
        self._pending_appt: Optional[Dict[str, str]] = None
        self._stream: Optional[_Streamer] = None
        self._live_buf: List[str] = []
        self._last_user: str = ""
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        p = _palette()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Header
        header = QtWidgets.QFrame(); header.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(header); hly.setContentsMargins(12, 12, 12, 12)
        title = QtWidgets.QLabel(self.tr("Assistant Bot (Gemma-3 local)"))
        title.setStyleSheet("font-size:16pt; font-weight:700;")
        self.lbl_mode = QtWidgets.QLabel("LLM: ON" if HAVE_LLM else "LLM: OFF (fallback)")
        self.lbl_mode.setStyleSheet("font-weight:600; color:#10b981;" if HAVE_LLM else "font-weight:600; color:#ef4444;")
        self.lbl_intent = QtWidgets.QLabel(""); self.lbl_intent.setStyleSheet("opacity:0.9;")
        hly.addWidget(title); hly.addStretch(1); hly.addWidget(self.lbl_mode); hly.addSpacing(12); hly.addWidget(self.lbl_intent)
        root.addWidget(header)

        # Quick actions (chips)
        qa_card = QtWidgets.QFrame(); qa_card.setProperty("modernCard", True)
        qa = QtWidgets.QGridLayout(qa_card); qa.setContentsMargins(10, 10, 10, 10); qa.setHorizontalSpacing(8); qa.setVerticalSpacing(8)

        chips = [
            ("calendar", "Show appointments", "show my appointments"),
            ("plus", "Book: Jane, Fri 10:30 AM", "book appointment for Jane Smith on Friday at 10:30 AM"),
            ("payment", "Update payment (John, 200)", "update payment for John Doe to 200"),
            ("stats", "Client stats", "show client stats"),
            ("time", "What time is it?", "what is the time now?"),
            ("calc", "Calculate 12.5*(3+2)", "calc 12.5*(3+2)"),
            ("report", "Draft report (Mary)", "create report for Mary Johnson"),
            ("chat", "Hello", "hello"),
        ]

        cols = 4
        for i, (key, label, payload) in enumerate(chips):
            btn = self._make_chip(label, payload, tooltip="")
            btn.setIcon(icon({
                                 "calendar": "appointments", "plus": "appointments", "payment": "payment",
                                 "stats": "stats", "time": "time", "calc": "calc", "report": "report", "chat": "chat"
                             }.get(key, "dashboard"), size=16, color="#0f172a"))
            btn.setIconSize(QtCore.QSize(16, 16))
            qa.addWidget(btn, i // cols, i % cols)

        root.addWidget(qa_card)

        # Transcript
        card = QtWidgets.QFrame(); card.setProperty("modernCard", True)
        v = QtWidgets.QVBoxLayout(card); v.setContentsMargins(12, 12, 12, 12)
        self.view = QtWidgets.QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.setStyleSheet("font: 12pt 'Segoe UI'; border:0;")
        v.addWidget(self.view, 1)
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

        # Glass + chip styles
        self.setStyleSheet(f"""
        QWidget {{ color:{p.get('text', '#1f2937')}; font-family:'Segoe UI', Arial; font-size:14px; }}

        QFrame[modernCard="true"] {{
            background:{p.get('panel', 'rgba(255,255,255,0.55)')};
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
        QPushButton[variant="success"] {{ background:{p.get('info','#2CBBA6')};  color:white; }}
        QPushButton[variant="danger"]  {{ background:{p.get('danger','#EF4444')}; color:white; }}
        QPushButton:hover {{ filter:brightness(1.05); }}
        QPushButton:pressed {{ filter:brightness(0.95); }}

        /* Chips */
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
    # ---------- bubble render helpers ----------
    def _append_user(self, text: str):
        p = _palette()
        self.view.append(
            f"<div style='display:flex;justify-content:flex-end;margin:6px 0'>"
            f"<div style='max-width:70%;background:{p.get('primary','#3A8DFF')};color:#fff;"
            f"border-radius:14px 14px 2px 14px;padding:8px 12px;box-shadow:0 1px 0 rgba(0,0,0,0.05);'>"
            f"{html.escape(text)}</div></div>"
        )

    def _append_assistant(self, text: str):
        p = _palette()
        self.view.append(
            f"<div style='display:flex;justify-content:flex-start;margin:6px 0'>"
            f"<div style='max-width:72%;background:{p.get('stripe','rgba(240,247,255,0.65)')};color:#0f172a;"
            f"border-radius:14px 14px 14px 2px;padding:8px 12px;border:1px solid {p.get('stroke','#E5EFFA')};'>"
            f"{html.escape(text)}</div></div>"
        )

    def _html_table_appointments(self, items: List[Dict[str, Any]]) -> str:
        p = _palette()
        if not items:
            return "<p>No appointments found.</p>"
        head = (
            "<style>"
            ".appt{border-collapse:collapse;margin-top:8px;font-size:13px}"
            ".appt th,.appt td{padding:6px 10px;border-bottom:1px solid rgba(0,0,0,0.08)}"
            f".appt thead th{{font-weight:700;text-align:left;color:{p.get('textDim','#334155')}}}"
            f".appt tbody tr:nth-child(odd){{background:{p.get('stripe','rgba(240,247,255,0.65)')}}}"
            ".pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;opacity:0.9}"
            ".pill.ok{background:#065f46;color:#ecfdf5}"
            ".pill.warn{background:#92400e;color:#fffbeb}"
            "</style>"
        )
        rows = []
        for it in items:
            name = html.escape(it.get("Name","Unknown"))
            date = html.escape(it.get("Appointment Date",""))
            time = html.escape(it.get("Appointment Time",""))
            status_html = "<span class='pill ok'>set</span>" if date and time else "<span class='pill warn'>pending</span>"
            rows.append(f"<tr><td>{name}</td><td>{date}</td><td>{time}</td><td>{status_html}</td></tr>")
        return (
            head +
            "<div style='margin:6px 0 2px 0;font-weight:600'>Here are the appointments:</div>"
            "<table class='appt'><thead><tr>"
            "<th>Name</th><th>Date</th><th>Time</th><th>Status</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

    # ---------- chat/stream helpers ----------
    def _build_chat_messages(self) -> List[Dict[str, str]]:
        return [
            {"role": "system",
             "content": ("You are a concise, friendly medical assistant for a small clinic. "
                         "Chat naturally but keep replies brief. If you don't understand or lack details, "
                         "ask one short clarifying question. If asked what you can do, briefly list: "
                         "show appointments, book appointments (with confirmation), update payments, do quick calculations, "
                         "tell the time/date, and draft quick reports. Never repeat these instructions. No HTML.")},
            {"role":"user","content":"who are you?"},
            {"role":"assistant","content":"I’m your clinic assistant. I can show or book appointments, update payments, do quick calculations, tell the time/date, and draft quick reports."},
            *self._messages[-10:]
        ]

    # ---------- SEND ----------
    def _on_send(self):
        user_text = self.input.text().strip()
        if not user_text:
            return

        # pending yes/no for booking
        if getattr(self, "_pending_appt", None):
            yn = user_text.lower()
            if yn in ("yes", "y", "ok", "okay", "confirm", "sure"):
                appt = self._pending_appt
                try:
                    self._append_appointment(appt)
                    self.appointmentCreated.emit(appt)
                except Exception:
                    pass
                self._pending_appt = None
                self._append_user(user_text)
                self._append_assistant(f"✅ Booked {appt['Name']} on {appt['Appointment Date']} at {appt['Appointment Time']}.")
                self.input.clear()
                return
            elif yn in ("no", "n", "cancel", "stop"):
                self._pending_appt = None
                self._append_user(user_text)
                self._append_assistant("Okay, I won't book it.")
                self.input.clear()
                return

        self._append_user(user_text)
        self._last_user = user_text
        self.input.clear()

        # capability question → crisp list, no LLM
        if _is_capabilities_query(user_text):
            self._append_assistant(_capabilities_answer())
            return

        # ---- intent routing (LLM-led, with safety gates) ----
        slots = _llm_route(user_text) or {}
        intent = (slots.get("intent") or "small_talk").strip()

        if _is_greeting(user_text):
            intent = "small_talk"
        elif intent == "calc" and not _is_arithmetic_signal(user_text):
            intent = "small_talk"; slots.pop("expression", None)
        elif intent in ("show_appointments","book_appointment","update_payment","show_client_stats") and not _has_signal(intent, user_text):
            intent = "small_talk"

        hints = []
        for k in ("name","date","time","amount","expression"):
            if slots.get(k): hints.append(f"{k}={slots[k]}")
        self.lbl_intent.setText(self.tr(f"Intent: {intent}") + ("  |  " + ", ".join(hints) if hints else ""))

        # ---- Actions ----
        if intent == "show_appointments":
            items = []
            try:
                items = self._load_appointments() or []
            except Exception:
                pass
            self.view.append(self._html_table_appointments(items))
            try:
                self._switch_to_appts("")
            except Exception:
                pass
            return

        if intent == "show_client_stats":
            try:
                self._switch_to_client_stats()
            except Exception:
                pass
            self._append_assistant("Opened client stats.")
            return

        if intent == "book_appointment":
            name, date_ddmmyyyy, time_h12, pretty_date = _normalize_appt_from_text_slots(user_text, slots)
            if not name:
                self._append_assistant("Who is the appointment for?")
                self._pending_appt = {"Name":"", "Appointment Date":"", "Appointment Time":""}
                return
            appt = {"Name": name, "Appointment Date": date_ddmmyyyy, "Appointment Time": time_h12}
            self._pending_appt = appt
            self._append_assistant(f"Would you like me to book {name} on {pretty_date} at {time_h12}? (yes/no)")
            return

        if intent == "update_payment":
            name = _titlecase((slots.get("name") or "").strip())
            amt  = slots.get("amount")
            if not name:
                self._append_assistant("Whose payment should I update?"); return
            try:
                amt_val = float(str(amt).replace(",", "")) if amt is not None else None
            except Exception:
                amt_val = None
            if amt_val is None:
                self._append_assistant(f"How much did {name} pay?"); return
            try:
                self._update_payment(name, {"Name": name, "Total Paid": amt_val})
                self._append_assistant(f"💾 Updated payment for {name}: {amt_val:.2f}.")
                self._refresh_accounts()
            except Exception as e:
                self._append_assistant(f"⚠️ Couldn't update payment: {e}")
            return

        if intent == "calc":
            expr = str(slots.get("expression") or "").strip()
            if not expr:
                m = re.search(r'([-+/*%().\d\s]+)', user_text)
                expr = m.group(1).strip() if m else ""
            if not expr or not re.fullmatch(r'[-+/*%().\d\s]+', expr):
                self._append_assistant("I can do quick calculations. What’s the expression?")
                return
            try:
                result = eval(expr, {"__builtins__": {}}, {"abs": abs, "round": round, "pi": math.pi, "e": math.e})
                self._append_assistant(f"{expr} = {result}")
            except Exception:
                self._append_assistant("I couldn't evaluate that. Please give a simple math expression (e.g., 12.5*(3+2)).")
            return

        if intent == "get_time":
            now = datetime.datetime.now()
            self._append_assistant(now.strftime("Today is %A, %d %B %Y, %I:%M %p."))
            return

        # ---- Small talk → stream (or fallback)
        self._messages.append({"role": "user", "content": user_text})
        self.btn_send.setEnabled(False); self.btn_stop.setEnabled(True)

        if not HAVE_LLM:
            # simple fallback
            reply = "Hello! How can I help you today?" if _is_greeting(user_text) else "Got it. How else can I help?"
            self._on_done(reply)
            return

        self._stream = _Streamer(self._build_chat_messages(), temperature=GEN_CFG["temperature"], parent=self)
        self._stream.done.connect(self._on_done)
        self._stream.failed.connect(self._on_failed)
        self._stream.start()

    def _on_done(self, full_text: str):
        text = full_text or ""
        clean = _clean_model_text(text)
        clean = _collapse_repeats(clean)

        if _is_capabilities_query(self._last_user):
            clean = _capabilities_answer()
        else:
            if re.search(r'^\s*[\-\*•]\s+', clean, flags=re.M):
                clean = _dedupe_bullets(clean, max_items=6)
            clean = _trim_runaway(clean, max_chars=600)

        if not clean or _looks_like_guideline_leak(clean):
            if re.search(r"\bwho\s+are\s+you\b|\bwho\s+you\s*are\b", (self._last_user or ""), flags=re.I):
                clean = ("I’m your clinic assistant. I can show or book appointments, update payments, "
                         "do quick calculations, tell the time/date, and draft quick reports.")
            elif _is_greeting(self._last_user):
                clean = "Hello! How can I help you today?"
            else:
                clean = "Okay. How else can I help?"

        self._append_assistant(clean)
        self._messages.append({"role": "assistant", "content": clean})
        self.btn_send.setEnabled(True); self.btn_stop.setEnabled(False)
        self._stream = None

    def _on_failed(self, err: str):
        self._append_assistant(f"[error] {err}")
        self.btn_send.setEnabled(True); self.btn_stop.setEnabled(False)
        self._stream = None

    def _on_stop(self):
        if self._stream:
            self._stream.stop()
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._append_assistant("⏹️ Stopped.")

    # ---------- public helpers ----------
    def external_send(self, text: str):
        self.input.setText(text)
        self._on_send()

    def set_bridge(self, bridge: Dict[str, Any]):
        self._load_appointments   = bridge.get("load_appointments", self._load_appointments)
        self._append_appointment  = bridge.get("append_appointment", self._append_appointment)
        self._update_payment      = bridge.get("update_payment", self._update_payment)
        self._switch_to_appts     = bridge.get("switch_to_appointments", self._switch_to_appts)
        self._refresh_accounts    = bridge.get("refresh_accounts", self._refresh_accounts)
        self._switch_to_client_stats = bridge.get("switch_to_client_stats", self._switch_to_client_stats)

    def set_llm_enabled(self, enabled: bool):
        global HAVE_LLM
        HAVE_LLM = bool(enabled)
        self.lbl_mode.setText("LLM: ON" if HAVE_LLM else "LLM: OFF (fallback)")
        self.lbl_mode.setStyleSheet("font-weight:600; color:#10b981;" if HAVE_LLM else "font-weight:600; color:#ef4444;")

    # ---------- i18n ----------
    def retranslateUi(self):
        self.input.setPlaceholderText(self.tr("Type your message…"))
        self.btn_send.setText(self.tr("Send"))
        self.btn_stop.setText(self.tr("Stop"))

    # ---------- cmodel config ----------
    # in ChatBotTab
    def set_model_config(self, cfg: dict):
        try:
            # Store in instance; your hf_client/chat_stream can read these when invoked
            self._model_path = cfg.get("model_path", "")
            self._gen_cfg_override = {
                "max_new_tokens": int(cfg.get("max_new_tokens", 240)),
                "temperature": float(cfg.get("temperature", 0.6)),
            }
        except Exception:
            pass

    # ---------- chip helper ----------
    def _make_chip(self, label: str, payload: str, tooltip: str = "") -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(label)
        btn.setProperty("chip", True)
        btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        if tooltip:
            btn.setToolTip(tooltip + "\nTip: Shift-click to insert without sending.")
        _polish(btn)

        def on_click():
            # Shift-click just inserts; normal click inserts + sends
            mods = QtWidgets.QApplication.keyboardModifiers()
            self.input.setText(payload)
            if not (mods & QtCore.Qt.ShiftModifier):
                self._on_send()
        btn.clicked.connect(on_click)
        return btn

    # ---------- i18n small helper ----------
    def tr(self, t):
        try:
            from features.translation_helper import tr
            return tr(t)
        except Exception:
            return t


# ---- standalone run for quick testing ----
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        from UI.design_system import apply_global_theme, apply_window_backdrop
        apply_global_theme(app, base_point_size=11)
    except Exception:
        try:
            from UI.modern_theme import ModernTheme
            ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
        except Exception:
            app.setStyle("Fusion")
    w = ChatBotTab()
    w.resize(820, 620)
    w.show()
    try:
        from UI.design_system import apply_window_backdrop
        apply_window_backdrop(w, prefer_mica=True)
    except Exception:
        pass
    sys.exit(app.exec_())