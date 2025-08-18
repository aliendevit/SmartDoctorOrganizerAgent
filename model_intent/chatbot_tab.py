# model_intent/chatbot_tab.py
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PyQt5.*")

import html, re, json, datetime
from typing import Dict, List, Optional

from PyQt5 import QtWidgets, QtCore, QtGui
from dateparser.search import search_dates
import dateparser

# ---------------- Optional local LLM client (Gemma) ----------------
HAVE_LLM = False
try:
    # Your local streaming helper for Gemma-3 270M (hf_client.py)
    from model_intent.hf_client import chat_stream
    HAVE_LLM = True
except Exception:
    HAVE_LLM = False


# ---------------- Utilities ----------------
def _polish(*widgets):
    for w in widgets:
        try:
            w.style().unpolish(w); w.style().polish(w); w.update()
        except Exception:
            pass

def _escape(s: str) -> str:
    return html.escape("" if s is None else str(s))

def _titlecase(name: str) -> str:
    return " ".join(w.capitalize() for w in name.split())

def _is_greeting_or_smalltalk(t: str) -> bool:
    tl = t.strip().lower()
    # Very lenient: short messages or classic greetings/thanks
    if len(tl) <= 2:
        return True
    if re.fullmatch(r"(hi|hello|hey|yo|sup|thanks|thank you|good (morning|evening|afternoon))[\.\!\s]*", tl):
        return True
    return False

def _has_booking_cue(t: str) -> bool:
    tl = t.lower()
    return bool(re.search(
        r"\b(book|schedule|appointment|appt|reserve|set\s*up|arrange|make\s+an?\s+appointment|see\s+(?:dr|doctor))\b",
        tl
    ))

def _looks_like_show_appts(t: str) -> bool:
    tl = t.lower()
    return bool(re.search(r"\b(show|list|view|see|display)\b.*\b(appointments|appts)\b", tl))

def _looks_like_payment(t: str) -> bool:
    tl = t.lower()
    return bool(re.search(r"\b(pay|paid|payment|deposit|balance|invoice|amount|receipt)\b", tl))

def _clean_stream_chunk(s: str) -> str:
    """Strip accidental role labels the tiny model sometimes emits."""
    s = s.replace("\r", "")
    # Remove leading 'system:'/'assistant:'/'user:' labels at start-of-line
    s = re.sub(r"(?m)^\s*(system|assistant|user)\s*:\s*", "", s)
    return s


# ---------------- Regex-first extraction (model still leads) ----------------
def _guess_intent(t: str) -> str:
    if _looks_like_show_appts(t):
        return "show_appointments"
    if _has_booking_cue(t):
        return "book_appointment"
    if _looks_like_payment(t):
        return "update_payment"
    if re.search(r"\b(report|summary|note|letter|prescription)\b", t, flags=re.I):
        return "create_report"
    return "small_talk"

def _find_name(t: str) -> str:
    tl = t.lower()
    pats = [
        r"\b(?:person\s+name|patient\s+name|client\s+name|name\s+is)\s+(?P<n>[a-z][\w'\-]*(?:\s+[a-z][\w'\-]*){0,3})",
        r"\bfor\s+(?P<n>[a-z][\w'\-]*(?:\s+[a-z][\w'\-]*){0,3})",
    ]
    for p in pats:
        m = re.search(p, tl, flags=re.I)
        if m:
            return _titlecase(m.group("n").strip())
    return ""

def _find_amount(t: str) -> str:
    if not _looks_like_payment(t):
        return ""
    m = re.search(r"\$?\s*(\d{1,3}(?:[,\d]{3})*(?:\.\d+)?)", t)
    return m.group(1) if m else ""

def _find_datetime(t: str) -> Dict[str, str]:
    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": datetime.datetime.now(),
        "PREFER_DAY_OF_MONTH": "first",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    found = search_dates(t, settings=settings)
    if not found:
        return {}
    dt = found[0][1]
    out = {"date": dt.strftime("%d-%m-%Y")}
    if re.search(r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b", t, flags=re.I):
        out["time"] = dt.strftime("%I:%M %p")
    return out

def route_regex(text: str) -> Dict[str, str]:
    slots: Dict[str, str] = {"intent": _guess_intent(text)}
    name = _find_name(text)
    if name:
        slots["name"] = name
    slots.update(_find_datetime(text))
    amt = _find_amount(text)
    if amt:
        slots["amount"] = amt
    return slots


# ---------------- LLM-assisted routing (model core with gentle rails) ----------------
INTENT_PROMPT = """
You are an intent/slot extractor for a clinic assistant.
Return ONLY compact JSON with:
  intent: one of ['show_appointments','book_appointment','update_payment','create_report','small_talk']
  name? : patient/client name if present
  date? : dd-mm-yyyy if present (convert natural dates)
  time? : hh:mm AM/PM if present
  amount?: number if about payments (no currency symbol)

Rules:
- Greetings/chit-chat/uncertain → small_talk.
- Only book_appointment when the user clearly wants to schedule (booking verbs OR says they want an appointment) AND a real date/time is present or implied.
- “show/list/view appointments” → show_appointments.
No commentary.

Examples:
User: "hi"
{"intent":"small_talk"}

User: "hello there"
{"intent":"small_talk"}

User: "show my appointments"
{"intent":"show_appointments"}

User: "book muhammad on 13 july at 3pm"
{"intent":"book_appointment","name":"Muhammad","date":"13-07-2025","time":"03:00 PM"}
""".strip()

def _llm_route(text: str) -> Dict[str, str]:
    if not HAVE_LLM:
        return {}
    msgs = [
        {"role": "system", "content": INTENT_PROMPT},
        {"role": "user", "content": text},
    ]
    buf = []
    try:
        # Deterministic for routing
        for piece in chat_stream(msgs, temperature=1e-6, max_new_tokens=160):
            buf.append(piece)
        raw = "".join(buf).strip()
        m = re.search(r"\{.*\}", raw, flags=re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}

def route_hybrid(text: str) -> Dict[str, str]:
    # 1) let model try first (to keep it model-centric)
    model_slots = _llm_route(text) or {}
    # 2) then fill/patch with light regex (no heavy rules)
    slots = route_regex(text)
    # prefer model intent if present
    if model_slots.get("intent"):
        slots["intent"] = model_slots["intent"]
    for k in ("name", "date", "time", "amount"):
        if model_slots.get(k):
            slots[k] = model_slots[k]

    # final guardrails: greetings → small_talk; don't book without cues
    if _is_greeting_or_smalltalk(text):
        slots["intent"] = "small_talk"
    if slots.get("intent") == "book_appointment":
        # require booking cue OR the model explicitly set book intent with a real date
        if not _has_booking_cue(text) and not (slots.get("date") or slots.get("time")):
            slots["intent"] = "small_talk"
    return slots


# ---------------- Normalize date/time (fix 2024→2025, 24h→AM/PM, etc.) ----------------
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

def _normalize_appt_from_text_slots(user_text: str, slots: Dict[str, str]):
    """
    Return: (name, date_ddmmyyyy, time_h12, pretty_date)
    - If year omitted and parsed date is past -> bump year forward.
    - Convert 24h times to AM/PM.
    - Default time → 12:00 PM if missing.
    """
    name = (slots.get("name") or "").strip()
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

    # time
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

    # finalize
    try:
        final_dt = dateparser.parse(f"{date_ddmmyyyy} {time_h12}")
        time_h12 = final_dt.strftime("%I:%M %p")
    except Exception:
        pass

    return name, date_ddmmyyyy, time_h12, pretty_date


# ---------------- Data access ----------------
try:
    from data.data import load_appointments, append_appointment, update_account_in_db
except Exception:
    load_appointments = None
    append_appointment = None
    update_account_in_db = None


# ---------------- Streaming worker ----------------
SYSTEM_PROMPT = (
    "You are a concise, friendly medical assistant for a small clinic. "
    "You can chat naturally, but keep replies brief. If you don't understand or miss key details, "
    "ask a short clarifying question. If the user asks what you can do, briefly list: "
    "show appointments, book appointments (with confirmation), update payments, and draft quick reports. "
    "Do not write role labels. No HTML."
)

class _Streamer(QtCore.QThread):
    token = QtCore.pyqtSignal(str)
    done  = QtCore.pyqtSignal(str)
    failed= QtCore.pyqtSignal(str)

    def __init__(self, messages: List[Dict[str, str]], temperature: float = 0.7, parent=None):
        super().__init__(parent)
        self.messages = messages
        self.temperature = max(float(temperature), 1e-6)  # 0 not allowed in transformers
        self._stop = False

    def run(self):
        if not HAVE_LLM:
            try:
                user = next((m["content"] for m in reversed(self.messages) if m["role"] == "user"), "")
                reply = "Hello! How can I help you today?" if _is_greeting_or_smalltalk(user) else "Got it. How else can I help?"
                self.token.emit(reply); self.done.emit(reply); return
            except Exception as e:
                self.failed.emit(str(e)); return
        try:
            acc = []
            for piece in chat_stream(
                self.messages,
                temperature=self.temperature,
                max_new_tokens=320,
                system=SYSTEM_PROMPT,
            ):
                if self._stop:
                    break
                piece = _clean_stream_chunk(piece)
                if not piece:
                    continue
                acc.append(piece)
                self.token.emit(piece)
            self.done.emit("".join(acc))
        except Exception as e:
            self.failed.emit(str(e))

    def stop(self): self._stop = True


# ---------------- ChatBot UI ----------------
class ChatBotTab(QtWidgets.QWidget):
    appointmentCreated  = QtCore.pyqtSignal(dict)
    requestCreateReport = QtCore.pyqtSignal(str, str)

    # AFTER
    class ChatBotTab(QtWidgets.QWidget):
        def __init__(self, parent=None, bridge=None):
            super().__init__(parent)
            self.bridge = bridge  # <-- store it (optional to use)
            self._messages = []
            self._pending_appt = None
            self._stream = None
            self._build_ui()

    def tr(self, t):
        try:
            from translation_helper import tr
            return tr(t)
        except Exception:
            return t

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16); root.setSpacing(10)

        header = QtWidgets.QFrame(); header.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(header); hly.setContentsMargins(12, 12, 12, 12)
        title = QtWidgets.QLabel(self.tr("Assistant Bot (Gemma-3 local)"))
        title.setStyleSheet("font-size:16pt; font-weight:700;")
        self.lbl_mode = QtWidgets.QLabel("LLM: ON" if HAVE_LLM else "LLM: OFF (fallback)")
        self.lbl_mode.setStyleSheet("font-weight:600; color:#10b981;" if HAVE_LLM else "font-weight:600; color:#ef4444;")
        self.lbl_intent = QtWidgets.QLabel("")
        self.lbl_intent.setStyleSheet("opacity:0.9;")
        hly.addWidget(title); hly.addStretch(1); hly.addWidget(self.lbl_mode); hly.addSpacing(12); hly.addWidget(self.lbl_intent)
        root.addWidget(header)

        card = QtWidgets.QFrame(); card.setProperty("modernCard", True)
        v = QtWidgets.QVBoxLayout(card); v.setContentsMargins(12, 12, 12, 12)
        self.view = QtWidgets.QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.setStyleSheet("font: 12pt 'Segoe UI';")
        v.addWidget(self.view, 1)
        root.addWidget(card, 1)

        row = QtWidgets.QHBoxLayout()
        self.input = QtWidgets.QLineEdit(); self.input.setPlaceholderText(self.tr("Type your message…"))
        self.btn_send = QtWidgets.QPushButton(self.tr("Send")); self.btn_send.setProperty("accent", "violet")
        self.btn_stop = QtWidgets.QPushButton(self.tr("Stop")); self.btn_stop.setProperty("variant", "danger"); self.btn_stop.setEnabled(False)
        _polish(self.btn_send, self.btn_stop)
        row.addWidget(self.input, 1); row.addWidget(self.btn_send); row.addWidget(self.btn_stop)
        root.addLayout(row)

        self.btn_send.clicked.connect(self._on_send)
        self.btn_stop.clicked.connect(self._on_stop)
        self.input.returnPressed.connect(self._on_send)

        self._append_assistant("Hello! I can show appointments, book with confirmation, update payments, or draft quick reports. How can I help?")

    # ---- UI helpers
    def _append_user(self, text: str):
        self.view.append(f"<p><b>You:</b> {_escape(text)}</p>")
    def _append_assistant(self, text: str):
        self.view.append(f"<p style='color:#93c5fd'><b>Assistant:</b> {_escape(text)}</p>")
    def _append_stream(self, chunk: str):
        cursor = self.view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(chunk)
        self.view.setTextCursor(cursor)
        self.view.ensureCursorVisible()

    # ---- Render appointments
    def _render_appts_table(self, items: List[dict]) -> str:
        if not items:
            return "No appointments found."
        rows = []
        for it in items:
            rows.append(
                f"<tr>"
                f"<td style='padding:4px 8px'>{_escape(it.get('Name','Unknown'))}</td>"
                f"<td style='padding:4px 8px'>{_escape(it.get('Appointment Date',''))}</td>"
                f"<td style='padding:4px 8px'>{_escape(it.get('Appointment Time',''))}</td>"
                f"</tr>"
            )
        html_tbl = (
            "<table border='0' cellspacing='0' cellpadding='0' style='border-collapse:collapse;margin-top:6px'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:4px 8px'>Name</th>"
            "<th style='text-align:left;padding:4px 8px'>Date</th>"
            "<th style='text-align:left;padding:4px 8px'>Time</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
        return html_tbl

    # ---- Send
    def _on_send(self):
        user_text = self.input.text().strip()
        if not user_text:
            return

        # If waiting for confirmation to book
        if self._pending_appt:
            yn = user_text.lower()
            if yn in ("yes", "y", "ok", "okay", "confirm", "sure"):
                appt = self._pending_appt
                if append_appointment:
                    try: append_appointment(appt)
                    except Exception: pass
                try: self.appointmentCreated.emit(appt)
                except Exception: pass
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
            # else fall through to normal handling

        self._append_user(user_text)
        self.input.clear()

        # ROUTE (model-first with gentle rails)
        slots = route_hybrid(user_text) or {}
        intent = (slots.get("intent") or "small_talk").strip()

        # Show quick extracted hints in header (debug/UX)
        hints = []
        for k in ("name", "date", "time", "amount"):
            if slots.get(k):
                hints.append(f"{k}={slots[k]}")
        self.lbl_intent.setText(self.tr(f"Intent: {intent}") + ("  |  " + ", ".join(hints) if hints else ""))

        # ---- Actions
        if intent == "show_appointments":
            if load_appointments:
                try:
                    items = load_appointments() or []
                except Exception:
                    items = []
            else:
                items = []
            self._append_assistant("Here are the appointments:")
            self.view.append(self._render_appts_table(items))
            return

        if intent == "book_appointment":
            name, date_ddmmyyyy, time_h12, pretty_date = _normalize_appt_from_text_slots(user_text, slots)
            if not name:
                self._append_assistant("Who is the appointment for?")
                self._pending_appt = {"Name": "", "Appointment Date": "", "Appointment Time": ""}
                return
            appt = {"Name": name, "Appointment Date": date_ddmmyyyy, "Appointment Time": time_h12}
            self._pending_appt = appt
            self._append_assistant(f"Would you like me to book {name} on {pretty_date} at {time_h12}? (yes/no)")
            return

        if intent == "update_payment":
            name = (slots.get("name") or "").strip()
            amt  = slots.get("amount")
            if not name:
                self._append_assistant("Whose payment should I update?")
                return
            try:
                amt_val = float(str(amt).replace(",", "")) if amt is not None else None
            except Exception:
                amt_val = None
            if amt_val is None:
                self._append_assistant(f"How much did {name} pay?")
                return
            if update_account_in_db:
                try:
                    update_account_in_db(name, {"Name": name, "Total Paid": amt_val})
                    self._append_assistant(f"💾 Updated payment for {name}: {amt_val:.2f}.")
                except Exception as e:
                    self._append_assistant(f"⚠️ Couldn't update payment: {e}")
            else:
                self._append_assistant(f"(dev) Would update {name} with {amt_val:.2f}.")
            return

        if intent == "create_report":
            name  = (slots.get("name") or "Unknown").strip()
            rtype = "visit"
            self._append_assistant(f"📝 Preparing a {rtype} report for {name}…")
            try: self.requestCreateReport.emit(name, rtype)
            except Exception: pass
            return

        # ---- Small talk or unclear → LLM (or short canned)
        if re.search(r"\b(what can you do|help me with|capabilities|tasks)\b", user_text, flags=re.I):
            self._append_assistant(
                "I can show appointments, book appointments (with confirmation), update payments, and draft quick reports."
            )
            return

        self._messages.append({"role": "user", "content": user_text})
        self.btn_send.setEnabled(False); self.btn_stop.setEnabled(True)

        self._stream = _Streamer(self._build_chat_messages(), temperature=0.7, parent=self)
        self._stream.token.connect(self._append_stream)
        self._stream.done.connect(self._on_done)
        self._stream.failed.connect(self._on_failed)
        self._append_assistant("")  # placeholder; stream writes into it
        self._stream.start()

    def _build_chat_messages(self) -> List[Dict[str, str]]:
        # Only include ONE system message + recent history
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs.extend(self._messages[-10:])  # short memory
        return msgs

    def _on_stop(self):
        if self._stream: self._stream.stop()

    def _on_failed(self, err: str):
        self._append_assistant(f"[error] {err}")
        self.btn_send.setEnabled(True); self.btn_stop.setEnabled(False)
        self._stream = None

    def _on_done(self, full_text: str):
        self._messages.append({"role": "assistant", "content": full_text})
        self.btn_send.setEnabled(True); self.btn_stop.setEnabled(False)
        self._stream = None