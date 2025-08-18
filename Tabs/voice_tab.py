# voice_tab.py
import speech_recognition as sr
from PyQt5 import QtWidgets, QtCore, QtGui


def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Speak now...")
        audio = r.listen(source)
    try:
        text = r.recognize_google(audio)
        print("You said:", text)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return ""
    except sr.RequestError as e:
        print("Could not request results; {0}".format(e))
        return ""


class VoiceTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QLabel("Voice Input")
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        layout.addWidget(header)

        self.record_button = QtWidgets.QPushButton("Start Voice Input")
        self.record_button.clicked.connect(self.start_voice_input)
        layout.addWidget(self.record_button)

        self.result_label = QtWidgets.QLabel("Recognized text will appear here.")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        layout.addStretch()

    def start_voice_input(self):
        text = recognize_speech()
        if text:
            self.result_label.setText(f"You said: {text}")
