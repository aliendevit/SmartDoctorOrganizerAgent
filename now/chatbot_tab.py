# chatbot_tab.py
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime, timedelta
import re, os
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from data.database import load_all_clients, insert_client
import spacy

# Load spaCy language model (using a small model for speed; upgrade if needed)
nlp = spacy.load("en_core_web_sm")

# ------------------- Helper Functions -------------------

def normalize_time_str(time_str):
    """
    Converts a time string into a standardized 12-hour format without a leading zero.
    Supports formats such as "09:00 AM", "9:00AM", or "13:13" (24-hour format).
    """
    formats_to_try = ["%I:%M %p", "%I:%M%p", "%H:%M"]
    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(time_str.strip(), fmt)
            return dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            continue
    print(f"Time normalization error for '{time_str}': could not match any format.")
    return time_str.strip().upper()

def get_available_time_slots(appointments, date_str, slot_duration=30):
    """
    Returns available time slots for a given date based on current appointments.
    Assumes working hours from 09:00 to 17:00.
    """
    start_hour = 9
    end_hour = 17
    slots = []
    current = datetime.strptime(f"{date_str} {start_hour}:00", "%d-%m-%Y %H:%M")
    end_time = datetime.strptime(f"{date_str} {end_hour}:00", "%d-%m-%Y %H:%M")
    while current < end_time:
        slot = current.strftime("%I:%M %p")
        norm_slot = normalize_time_str(slot)
        slots.append(norm_slot)
        current += timedelta(minutes=slot_duration)

    taken = []
    for appt in appointments:
        if appt.get("Appointment Date") == date_str:
            t = appt.get("Appointment Time", "")
            norm_taken = normalize_time_str(t)
            taken.append(norm_taken)

    available = [slot for slot in slots if slot.upper().strip() not in [t.upper().strip() for t in taken]]
    return available

def summarize_slots(slots):
    """
    Groups consecutive time slots into ranges and returns a summary string.
    For example, if slots = ["9:30 AM", "10:00 AM", "10:30 AM", "11:30 AM", "12:00 PM"],
    it returns: "9:30 AM to 10:30 AM, 11:30 AM to 12:00 PM".
    """
    if not slots:
        return ""
    fmt = "%I:%M %p"
    times = []
    for slot in slots:
        try:
            dt = datetime.strptime(slot, fmt)
            times.append(dt)
        except Exception:
            continue
    if not times:
        return ""
    times.sort()
    ranges = []
    start = times[0]
    prev = times[0]
    for t in times[1:]:
        if (t - prev) == timedelta(minutes=30):
            prev = t
        else:
            ranges.append((start, prev))
            start = t
            prev = t
    ranges.append((start, prev))
    result_parts = []
    for s, e in ranges:
        if s == e:
            result_parts.append(s.strftime(fmt).lstrip("0"))
        else:
            result_parts.append(f"{s.strftime(fmt).lstrip('0')} to {e.strftime(fmt).lstrip('0')}")
    return ", ".join(result_parts)

# ------------------- Chat Bubble Widget -------------------

class ChatBubble(QtWidgets.QWidget):
    """A widget representing a chat bubble for a single message."""
    def __init__(self, text, is_user=False, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)
        self.label = QtWidgets.QLabel(self.text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        font = QtGui.QFont("Inter", 18)
        font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 110)
        self.label.setFont(font)
        if self.is_user:
            self.label.setStyleSheet("""
                background-color: #DCF8C6;
                padding: 12px;
                border-radius: 15px;
                color: #202124;
            """)
            layout.addStretch()
            layout.addWidget(self.label)
        else:
            self.label.setStyleSheet("""
                background-color: #FFFFFF;
                padding: 12px;
                border-radius: 15px;
                color: #202124;
            """)
            layout.addWidget(self.label)
            layout.addStretch()
        self.setLayout(layout)

    def update_text(self, new_text):
        self.label.setText(new_text)

# ------------------- ChatBotTab Widget -------------------

class ChatBotTab(QtWidgets.QWidget):
    """
    A smart assistant bot that uses spaCy to help interpret natural language commands
    in a chat-room style interface with decorated chat bubbles.
    """
    def __init__(self, appointments=None, reports=None, parent=None):
        super().__init__(parent)
        self.appointments = appointments if appointments is not None else []
        self.reports = reports if reports is not None else {}
        self.setup_ui()
        self.apply_styles()
        self.thinking_timer = QtCore.QTimer(self)
        self.thinking_timer.timeout.connect(self.update_thinking_message)
        self.thinking_dots = 0

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Large, powerful title
        header = QtWidgets.QLabel("Your Power Assistant")
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setFont(QtGui.QFont("Inter", 32, QtGui.QFont.Bold))
        layout.addWidget(header)

        # Chat area with a scroll area for chat bubbles.
        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.chatContainer = QtWidgets.QWidget()
        self.chatLayout = QtWidgets.QVBoxLayout(self.chatContainer)
        self.chatLayout.setAlignment(QtCore.Qt.AlignTop)
        self.scrollArea.setWidget(self.chatContainer)
        layout.addWidget(self.scrollArea)

        # Input area
        self.chat_input = QtWidgets.QLineEdit()
        self.chat_input.setPlaceholderText("Type your command here...")
        self.chat_input.returnPressed.connect(self.handle_command)
        layout.addWidget(self.chat_input)

        layout.addStretch()
        self.setLayout(layout)

    def apply_styles(self):
        # Modern, ChatGPT-inspired style with decorated scrollbars.
        style = """
        QWidget {
            background-color: #F7F7F8;
            color: #202123;
            font-family: "Inter", sans-serif;
            font-size: 15px;
        }
        QLineEdit {
            background-color: white;
            border: 1px solid #E1E4E8;
            border-radius: 8px;
            padding: 12px;
        }
        QScrollArea {
            background-color: #F7F7F8;
            border: none;
        }
        QScrollBar:vertical {
            background: #E1E4E8;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #C4C9CC;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #A0A5A8;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """
        self.setStyleSheet(style)

    def add_message(self, text, is_user=False):
        """Creates and adds a chat bubble to the chat area."""
        bubble = ChatBubble(text, is_user=is_user)
        self.chatLayout.addWidget(bubble)
        self.scrollArea.verticalScrollBar().setValue(self.scrollArea.verticalScrollBar().maximum())
        return bubble

    def handle_command(self):
        command = self.chat_input.text().strip()
        if not command:
            return
        self.add_message(command, is_user=True)
        # First, check for common greetings or farewells.
        greeting_response = self.check_for_greetings_and_farewells(command)
        if greeting_response:
            self.add_message(greeting_response, is_user=False)
            self.chat_input.clear()
            return

        # Use spaCy to analyze the command for more natural understanding.
        doc = nlp(command)
        # (A simple approach: check for keywords in the doc's tokens)
        if any(token.lemma_.lower() in ["add", "create"] for token in doc) and \
           any(token.lemma_.lower() in ["user", "client"] for token in doc):
            response = self.add_client_from_command(command)
        elif any(token.lemma_.lower() in ["free", "available"] for token in doc) and \
             any(token.lemma_.lower() in ["time", "slot"] for token in doc):
            response = self.get_free_time_slots(datetime.today())
        elif "schedule" in command.lower():
            response = self.get_schedule_for_date(datetime.today())
        elif "report" in command.lower():
            name = self.extract_patient_name(command)
            if name:
                response = self.open_report_for_patient(name)
            else:
                response = "Could you please specify the patient's name for the report?"
        else:
            response = "I'm sorry, I didn't understand your request. Could you please rephrase it?"

        # Show animated "AI is thinking" message.
        self.thinking_bubble = self.add_message("AI is thinking", is_user=False)
        self.thinking_dots = 0
        self.thinking_timer.start(500)
        self.chat_input.setDisabled(True)
        QtCore.QTimer.singleShot(2000, lambda: self.generate_response(response))

    def update_thinking_message(self):
        """Animate the 'AI is thinking' message."""
        self.thinking_dots = (self.thinking_dots + 1) % 4
        dots = "." * self.thinking_dots
        self.thinking_bubble.update_text(f"AI is thinking{dots}")

    def generate_response(self, response):
        self.thinking_timer.stop()
        self.thinking_bubble.hide()
        self.add_message(response, is_user=False)
        self.chat_input.setDisabled(False)
        self.chat_input.clear()
        self.chat_input.setFocus()

    def check_for_greetings_and_farewells(self, command):
        # Expanded list of greetings and farewells for a more human-like interaction.
        greetings = [
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "howdy", "what's up", "greetings", "salutations"
        ]
        farewells = [
            "bye", "goodbye", "see you", "farewell", "later", "take care", "peace out"
        ]
        lower_command = command.lower()
        for word in greetings:
            if word in lower_command:
                return "Hello there! How can I assist you today?"
        for word in farewells:
            if word in lower_command:
                return "Goodbye! It was great talking with you."
        return ""

    def check_for_goodbye(self, command):
        farewells = ["bye", "goodbye", "see you", "farewell", "later", "take care", "peace out"]
        return any(word in command.lower() for word in farewells)

    def add_client_from_command(self, command):
        """
        Parses a command like:
          "add user John Doe with time 10:30 AM on 25-11-2023"
        and adds the new client to the database.
        If no date is provided, it defaults to today.
        """
        pattern = r"add (?:user|client)\s+([\w\s]+?)\s+with time\s+([\d:APMapm\s]+)(?:\s+on\s+(\d{1,2}-\d{1,2}-\d{2,4}))?"
        match = re.search(pattern, command, re.IGNORECASE)
        if not match:
            return ("I'm sorry, I couldn't understand your command. "
                    "Please use the format: add user John Doe with time 10:30 AM on 25-11-2023")
        name = match.group(1).strip()
        time_str = match.group(2).strip()
        norm_time = normalize_time_str(time_str)
        date_str = match.group(3)
        if not date_str:
            date_obj = datetime.today()
        else:
            try:
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_str, "%d-%m-%y")
                except ValueError:
                    return "I'm sorry, I couldn't understand the date. Please use dd-mm-YYYY format."
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
            from data.database import insert_client
            insert_client(client_data)
        except Exception as e:
            return f"Oops, there was an error adding the client: {e}"
        self.appointments = load_all_clients()
        self.reports[name.lower()] = ""
        return f"Fantastic! I've added {name} with an appointment on {appointment_date} at {norm_time}. Have a great day!"

    def get_schedule_for_date(self, date_obj):
        date_str = date_obj.strftime("%d-%m-%Y")
        self.appointments = load_all_clients()
        names = [appt["Name"] for appt in self.appointments if appt.get("Appointment Date") == date_str]
        if names:
            return f"Here's the schedule for {date_str}:\n" + "\n".join(names)
        else:
            return f"Looks like there are no appointments scheduled for {date_str}."

    def get_free_time_slots(self, date_obj):
        date_str = date_obj.strftime("%d-%m-%Y")
        self.appointments = load_all_clients()
        available_slots = get_available_time_slots(self.appointments, date_str)
        if available_slots:
            ranges = summarize_slots(available_slots)
            return f"Good news! You're free on {date_str} during the following periods:\n{ranges}"
        else:
            return f"Unfortunately, there are no free time slots on {date_str}."

    def extract_patient_name(self, text):
        match = re.search(r"report\s+(?:for|of)\s+(?:patient\s+)?([\w\s]+)", text)
        if match:
            return match.group(1).strip()
        return None

    def open_report_for_patient(self, patient_name):
        patient_name = patient_name.replace("_report", "").replace("_", " ").strip()
        base_filename = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).replace(" ", "_")
        if not base_filename:
            base_filename = "Unknown"
        report_file_path = os.path.join("reports", f"{base_filename}_report.pdf")
        if os.path.exists(report_file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(report_file_path))
            return f"Sure thing! Opening the report for {patient_name}..."
        else:
            return f"Sorry, I couldn't find a report for patient {patient_name}."

# Required for URL opening.
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
