import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import speech_recognition as sr


class VoiceInputWidget(QtWidgets.QWidget):
    # Signal to emit recognized text
    textReady = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, language="en-US"):
        """
        language: A BCP-47 language code, e.g., "en-US" for English or "ar-SA" for Arabic.
        """
        super().__init__(parent)
        self.language = language
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Create a button and assign it to self.voice_button.
        self.voice_button = QtWidgets.QPushButton("Voice Input")
        self.voice_button.setFont(QtGui.QFont("Segoe UI", 14))
        self.voice_button.clicked.connect(self.start_voice_input)
        layout.addWidget(self.voice_button)
        self.setLayout(layout)

    def start_voice_input(self):
        # Use self.voice_button (not self.record_button) to update the text.
        self.voice_button.setText("Listening...")
        QtWidgets.QApplication.processEvents()

        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                print("Adjusting for ambient noise...")
                r.adjust_for_ambient_noise(source, duration=0.5)
                print("Listening for speech (timeout=7 seconds)...")
                audio = r.listen(source, timeout=7)
                print("Recognizing speech...")
                text = r.recognize_google(audio, language=self.language)
                print(f"Recognized text: {text}")
                # Emit the recognized text.
                self.textReady.emit(text)
                # Reset button text.
                self.voice_button.setText("Voice Input")
        except sr.WaitTimeoutError:
            QtWidgets.QMessageBox.warning(self, "Voice Input Error", "Listening timed out. Please try again.")
            print("Error: WaitTimeoutError")
            self.voice_button.setText("Voice Input")
        except sr.UnknownValueError:
            QtWidgets.QMessageBox.warning(self, "Voice Input Error",
                                          "Could not understand the audio. Please speak clearly.")
            print("Error: UnknownValueError")
            self.voice_button.setText("Voice Input")
        except sr.RequestError as e:
            QtWidgets.QMessageBox.warning(self, "Voice Input Error", f"Could not request results; {e}")
            print(f"Error: RequestError: {e}")
            self.voice_button.setText("Voice Input")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Voice Input Error", f"An unexpected error occurred: {e}")
            print(f"Unexpected error: {e}")
            self.voice_button.setText("Voice Input")


# ------------------- Example Usage -------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(window)

    # Create a VoiceInputWidget (set language as desired; "en-US" for English, "ar-SA" for Arabic)
    voice_widget = VoiceInputWidget(language="en-US")
    layout.addWidget(voice_widget)

    # Create a QTextEdit to display the recognized text.
    text_edit = QtWidgets.QTextEdit()
    layout.addWidget(text_edit)

    # Connect the textReady signal to update the text edit.
    voice_widget.textReady.connect(lambda text: text_edit.setPlainText(text))

    window.setWindowTitle("Voice Input Demo")
    window.resize(400, 300)
    window.show()
    sys.exit(app.exec_())
