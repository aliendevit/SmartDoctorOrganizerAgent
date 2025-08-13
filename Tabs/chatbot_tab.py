# chatbot_tab.py
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime, timedelta
import re, os

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

# Use your database APIs
from data.database import load_all_clients, insert_client

# ----- spaCy (graceful fallback if model missing) -----
try:
    import spacy

    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = spacy.blank("en")
except Exception:
    nlp = None


# ------------------- Helpers -------------------

def _polish(*widgets):
    """Re-apply QSS after setting dynamic properties so ModernTheme picks them up."""
    for w in widgets:
        w.style().unpolish(w)
        w.style().polish(w)
        w.update()


def normalize_time_str(time_str):
    """
    Converts a time string into a standardized 12-hour format without a leading zero.
    Supports "09:00 AM", "9:00AM", or "13:13".
    """
    formats_to_try = ["%I:%M %p", "%I:%M%p", "%H:%M"]
    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(time_str.strip(), fmt)
            return dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            continue
    return time_str.strip().upper()


def get_available_time_slots(appointments, date_str, slot_duration=30):
    """
    Returns available time slots for a given date based on current appointments.
    Work hours: 09:00–17:00.
    """
    start_hour, end_hour = 9, 17
    slots = []
    current = datetime.strptime(f"{date_str} {start_hour}:00", "%d-%m-%Y %H:%M")
    end_time = datetime.strptime(f"{date_str} {end_hour}:00", "%d-%m-%Y %H:%M")
    while current < end_time:
        slot = current.strftime("%I:%M %p")
        slots.append(normalize_time_str(slot))
        current += timedelta(minutes=slot_duration)

    taken = []
    for appt in appointments:
        if appt.get("Appointment Date") == date_str:
            taken.append(normalize_time_str(appt.get("Appointment Time", "")))

    taken_set = {t.upper().strip() for t in taken}
    return [s for s in slots if s.upper().strip() not in taken_set]


def summarize_slots(slots):
    """
    Group consecutive 30-min slots into ranges.
    ["9:30 AM","10:00 AM","10:30 AM","11:30 AM"] -> "9:30 AM to 10:30 AM, 11:30 AM"
    """
    if not slots:
        return ""
    fmt = "%I:%M %p"
    times = []
    for slot in slots:
        try:
            times.append(datetime.strptime(slot, fmt))
        except Exception:
            pass
    if not times:
        return ""
    times.sort()
    ranges, start, prev = [], times[0], times[0]
    for t in times[1:]:
        if (t - prev) == timedelta(minutes=30):
            prev = t
        else:
            ranges.append((start, prev))
            start = prev = t
    ranges.append((start, prev))
    parts = []
    for s, e in ranges:
        if s == e:
            parts.append(s.strftime(fmt).lstrip("0"))
        else:
            parts.append(f"{s.strftime(fmt).lstrip('0')} to {e.strftime(fmt).lstrip('0')}")
    return ", ".join(parts)


# ------------------- Chat Bubble -------------------

class ChatBubble(QtWidgets.QFrame):
    """A chat bubble card with left/right alignment."""

    def __init__(self, text, is_user=False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.setProperty("modernCard", True)  # picks up ModernTheme card styling
        self._build(text)

    def _build(self, text):
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        inner = QtWidgets.QLabel(text)
        inner.setWordWrap(True)
        inner.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        f = QtGui.QFont("Inter", 14)
        f.setLetterSpacing(QtGui.QFont.PercentageSpacing, 104)
        inner.setFont(f)

        bubble_wrap = QtWidgets.QHBoxLayout()
        bubble_wrap.setContentsMargins(10, 8, 10, 8)
        bubble_wrap.setSpacing(0)

        # Accent border for user messages so they pop a bit
        if self.is_user:
            self.setStyleSheet(
                self.styleSheet() + "QFrame { border-width: 2px; border-style: solid; border-color: #8b5cf6; }")
            lay.addStretch(1)
            lay.addWidget(inner, 0, QtCore.Qt.AlignRight)
        else:
            lay.addWidget(inner, 0, QtCore.Qt.AlignLeft)
            lay.addStretch(1)

    def update_text(self, new_text):
        # find the label child and update
        for child in self.children():
            if isinstance(child, QtWidgets.QLabel):
                child.setText(new_text)
                break


# ------------------- ChatBotTab -------------------

class ChatBotTab(QtWidgets.QWidget):
    """
    Smart assistant with natural-language commands in a modern chat UI.
    """

    def __init__(self, appointments=None, reports=None, parent=None):
        super().__init__(parent)
        self.appointments = appointments if appointments is not None else []
        self.reports = reports if reports is not None else {}
        self._thinking_timer = QtCore.QTimer(self)
        self._thinking_timer.timeout.connect(self._update_thinking_message)
        self._thinking_dots = 0
        self._build()

    # translation hook (optional)
    def tr(self, text):
        try:
            from translation_helper import tr
            return tr(text)
        except Exception:
            return text

    def _build(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ---- Header card ----
        header = QtWidgets.QFrame()
        header.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(header)
        hly.setContentsMargins(12, 12, 12, 12)
        title = QtWidgets.QLabel(self.tr("Your Power Assistant"))
        title.setStyleSheet("font-size: 18pt; font-weight: 800;")
        hly.addWidget(title)
        hly.addStretch(1)

        self.clear_btn = QtWidgets.QPushButton(self.tr("Clear Chat"))
        # self.clear_btn.setProperty("variant", "ghost")
        self.clear_btn.setProperty("accent", "rose")
        self.clear_btn.clicked.connect(self._clear_chat)
        hly.addWidget(self.clear_btn)
        _polish(self.clear_btn)

        root.addWidget(header)

        # ---- Chat area (card) ----
        chat_card = QtWidgets.QFrame()
        chat_card.setProperty("modernCard", True)
        cly = QtWidgets.QVBoxLayout(chat_card)
        cly.setContentsMargins(8, 8, 8, 8)
        cly.setSpacing(6)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.chatContainer = QtWidgets.QWidget()
        self.chatLayout = QtWidgets.QVBoxLayout(self.chatContainer)
        self.chatLayout.setAlignment(QtCore.Qt.AlignTop)
        self.scrollArea.setWidget(self.chatContainer)
        cly.addWidget(self.scrollArea)

        root.addWidget(chat_card, 1)

        # ---- Input row (card) ----
        input_card = QtWidgets.QFrame()
        input_card.setProperty("modernCard", True)
        ily = QtWidgets.QHBoxLayout(input_card)
        ily.setContentsMargins(12, 10, 12, 10)
        ily.setSpacing(8)

        self.chat_input = QtWidgets.QLineEdit()
        self.chat_input.setPlaceholderText(self.tr("Type your command here…"))
        self.chat_input.returnPressed.connect(self.handle_command)
        ily.addWidget(self.chat_input, 1)

        self.send_btn = QtWidgets.QPushButton(self.tr("Send"))
        self.send_btn.setProperty("accent", "emerald")
        self.send_btn.clicked.connect(self.handle_command)
        ily.addWidget(self.send_btn)
        _polish(self.send_btn)

        root.addWidget(input_card)

        # welcome
        self._add_message(self.tr("Hi! I can add clients, show schedules, find free slots, and open reports."),
                          is_user=False)

    # ---- Messaging helpers ----
    def _add_message(self, text, is_user=False):
        bubble = ChatBubble(text, is_user=is_user)
        self.chatLayout.addWidget(bubble)
        QtCore.QTimer.singleShot(0, lambda: self.scrollArea.verticalScrollBar().setValue(
            self.scrollArea.verticalScrollBar().maximum()))
        return bubble

    def _clear_chat(self):
        while self.chatLayout.count():
            item = self.chatLayout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._add_message(self.tr("Chat cleared."), is_user=False)

    # ---- Command handling ----
    def handle_command(self):
        command = self.chat_input.text().strip()
        if not command:
            return
        self._add_message(command, is_user=True)

        # quick greetings/farewells
        greeting_response = self._maybe_greeting(command)
        if greeting_response:
            self._add_message(greeting_response, is_user=False)
            self.chat_input.clear()
            return

        # nlp analysis (safe even if nlp is None)
        tokens = []
        if nlp:
            try:
                tokens = [t.lemma_.lower() for t in nlp(command)]
            except Exception:
                tokens = command.lower().split()
        else:
            tokens = command.lower().split()

        if any(t in ("add", "create") for t in tokens) and any(t in ("user", "client") for t in tokens):
            response = self.add_client_from_command(command)
        elif any(t in ("free", "available") for t in tokens) and any(t in ("time", "slot", "slots") for t in tokens):
            response = self.get_free_time_slots(datetime.today())
        elif "schedule" in command.lower():
            response = self.get_schedule_for_date(datetime.today())
        elif "report" in command.lower():
            name = self.extract_patient_name(command)
            response = self.open_report_for_patient(name) if name else self.tr(
                "Please specify the patient's name for the report.")
        else:
            response = self.tr("I didn't understand your request. Please rephrase it?")

        # animated thinking message
        self._thinking_bubble = self._add_message(self.tr("AI is thinking"), is_user=False)
        self._thinking_dots = 0
        self._thinking_timer.start(400)
        self.chat_input.setDisabled(True)
        self.send_btn.setDisabled(True)
        QtCore.QTimer.singleShot(1200, lambda: self._emit_response(response))

    def _maybe_greeting(self, command):
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening",
                     "howdy", "what's up", "greetings", "salutations"]
        farewells = ["bye", "goodbye", "see you", "farewell", "later", "take care", "peace out"]
        lc = command.lower()
        if any(g in lc for g in greetings):
            return self.tr("Hello! How can I help today?")
        if any(f in lc for f in farewells):
            return self.tr("Goodbye! Have a great day.")
        return ""

    def _update_thinking_message(self):
        self._thinking_dots = (self._thinking_dots + 1) % 4
        dots = "." * self._thinking_dots
        self._thinking_bubble.update_text(self.tr("AI is thinking") + dots)

    def _emit_response(self, response):
        self._thinking_timer.stop()
        if hasattr(self, "_thinking_bubble") and self._thinking_bubble:
            self._thinking_bubble.hide()
        self._add_message(response, is_user=False)
        self.chat_input.setDisabled(False)
        self.send_btn.setDisabled(False)
        self.chat_input.clear()
        self.chat_input.setFocus()

    # ---- Domain actions ----
    def add_client_from_command(self, command):
        """
        Parses commands like:
          "add user John Doe with time 10:30 AM on 25-11-2023"
        Adds a client; default date = today if omitted.
        """
        pattern = r"add (?:user|client)\s+([\w\s]+?)\s+with time\s+([\d:APMapm\s]+)(?:\s+on\s+(\d{1,2}-\d{1,2}-\d{2,4}))?"
        match = re.search(pattern, command, re.IGNORECASE)
        if not match:
            return self.tr("Use: add user John Doe with time 10:30 AM on 25-11-2023")

        name = match.group(1).strip()
        time_str = match.group(2).strip()
        norm_time = normalize_time_str(time_str)
        date_str = match.group(3)

        if not date_str:
            date_obj = datetime.today()
        else:
            for fmt in ("%d-%m-%Y", "%d-%m-%y"):
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    date_obj = None
            if date_obj is None:
                return self.tr("Invalid date. Please use dd-mm-YYYY format.")

        appointment_date = date_obj.strftime("%d-%m-%Y")
        client_data = {
            "Name": name,
            "Appointment Date": appointment_date,
            "Appointment Time": norm_time,
            "Age": "",
            "Symptoms": [],
            "Notes": "",
            "Date": appointment_date,
            "Summary": "",
            "Follow-Up Date": ""
        }

        try:
            insert_client(client_data)
        except Exception as e:
            return self.tr(f"There was an error adding the client: {e}")

        # refresh caches
        try:
            self.appointments = load_all_clients()
        except Exception:
            pass
        self.reports[name.lower()] = ""
        return self.tr(f"Added {name} on {appointment_date} at {norm_time}. 👍")

    def get_schedule_for_date(self, date_obj):
        date_str = date_obj.strftime("%d-%m-%Y")
        try:
            self.appointments = load_all_clients()
        except Exception:
            self.appointments = []
        names = [appt.get("Name", "") for appt in self.appointments if appt.get("Appointment Date") == date_str]
        if names:
            return self.tr(f"Schedule for {date_str}:\n") + "\n".join(names)
        return self.tr(f"No appointments scheduled for {date_str}.")

    def get_free_time_slots(self, date_obj):
        date_str = date_obj.strftime("%d-%m-%Y")
        try:
            self.appointments = load_all_clients()
        except Exception:
            self.appointments = []
        slots = get_available_time_slots(self.appointments, date_str)
        if slots:
            return self.tr(f"Free on {date_str}:\n") + summarize_slots(slots)
        return self.tr(f"No free time slots on {date_str}.")

    def extract_patient_name(self, text):
        m = re.search(r"report\s+(?:for|of)\s+(?:patient\s+)?([\w\s]+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def open_report_for_patient(self, patient_name):
        if not patient_name:
            return self.tr("Please provide a patient name.")
        clean = patient_name.replace("_report", "").replace("_", " ").strip()
        base = "".join(c for c in clean if c.isalnum() or c in (" ", "_")).replace(" ", "_") or "Unknown"

        # Look in common locations
        candidates = [
            os.path.join("reports", f"{base}_report.pdf"),
            os.path.join(os.path.expanduser("~"), "Desktop", "reports", f"{base}_report.pdf"),
        ]
        for path in candidates:
            if os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path)))
                return self.tr(f"Opening the report for {clean}…")
        return self.tr(f"Report not found for {clean}.")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # Apply ModernTheme automatically if available
    try:
        from modern_theme import ModernTheme

        ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
    except Exception:
        pass
    w = ChatBotTab()
    w.resize(900, 720)
    w.show()
    sys.exit(app.exec_())
