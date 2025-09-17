import io
import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import speech_recognition as sr

from speech.soundvoice import SOUNDVOICE_OK, SoundVoiceRecorder


class VoiceInputWidget(QtWidgets.QWidget):
    # Signal to emit recognized text
    textReady = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, language="en-US"):
        """
        language: A BCP-47 language code, e.g., "en-US" for English or "ar-SA" for Arabic.
        """
        super().__init__(parent)
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recorder = SoundVoiceRecorder()
        self._recording = False
        self._has_recorded = False
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        self.voice_button = QtWidgets.QPushButton("Start Recording")
        self.voice_button.setFont(QtGui.QFont("Segoe UI", 14))
        self.voice_button.clicked.connect(self.start_voice_input)
        layout.addWidget(self.voice_button)

        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(8)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_and_transcribe)
        self.stop_button.setEnabled(False)
        controls.addWidget(self.stop_button)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_recording)
        self.cancel_button.setEnabled(False)
        controls.addWidget(self.cancel_button)

        layout.addLayout(controls)

        self.status_label = QtWidgets.QLabel("Tap Start to capture audio with SoundVoice.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        if not SOUNDVOICE_OK:
            self.status_label.setText("SoundVoice requires the optional 'sounddevice' package.")

        self.setLayout(layout)

    def start_voice_input(self):
        if self._recording:
            return
        if not SOUNDVOICE_OK:
            QtWidgets.QMessageBox.warning(
                self,
                "SoundVoice",
                "SoundVoice is unavailable. Install the 'sounddevice' package to enable recording.",
            )
            return
        try:
            self.recorder.start()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "SoundVoice", f"Could not start recording: {e}")
            return

        self._recording = True
        self.voice_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Recording… press Stop when you are finished.")

    def stop_and_transcribe(self):
        self._finish_recording(finalize=True)

    def cancel_recording(self):
        self._finish_recording(finalize=False)

    def _finish_recording(self, finalize: bool):
        if not self._recording:
            return
        self.stop_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        QtWidgets.QApplication.processEvents()
        try:
            raw_audio = self.recorder.stop()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "SoundVoice", f"Could not stop recording: {e}")
            raw_audio = b""
        self._recording = False
        self.voice_button.setEnabled(True)
        next_label = "Continue Recording" if self._has_recorded else "Start Recording"
        self.voice_button.setText(next_label)

        if not finalize:
            self.status_label.setText("Recording cancelled.")
            return

        wav_bytes = self.recorder.to_wav(raw_audio)
        if not wav_bytes:
            self.status_label.setText("No audio captured.")
            QtWidgets.QMessageBox.information(self, "SoundVoice", "No audio detected. Try recording again.")
            return

        self.status_label.setText("Transcribing…")
        QtWidgets.QApplication.processEvents()

        for status in self.recorder.status_messages:
            print(f"SoundVoice status: {status.message}")

        try:
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                audio = self.recognizer.record(source)
            text = self.recognizer.recognize_google(audio, language=self.language)
        except sr.WaitTimeoutError:
            self.status_label.setText("Listening timed out.")
            QtWidgets.QMessageBox.warning(self, "SoundVoice", "Listening timed out. Please try again.")
            return
        except sr.UnknownValueError:
            self.status_label.setText("Could not understand the audio.")
            QtWidgets.QMessageBox.warning(
                self,
                "SoundVoice",
                "Could not understand the audio. Please speak clearly.",
            )
            return
        except sr.RequestError as e:
            self.status_label.setText("Service unavailable.")
            QtWidgets.QMessageBox.warning(
                self,
                "SoundVoice",
                f"Could not request results from the speech service: {e}",
            )
            return
        except Exception as e:
            self.status_label.setText("An unexpected error occurred.")
            QtWidgets.QMessageBox.warning(self, "SoundVoice", f"An unexpected error occurred: {e}")
            return

        self._has_recorded = True
        self.status_label.setText("Transcription complete.")
        self.textReady.emit(text)


# ------------------- Example Usage -------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(window)

    voice_widget = VoiceInputWidget(language="en-US")
    layout.addWidget(voice_widget)

    text_edit = QtWidgets.QTextEdit()
    layout.addWidget(text_edit)

    voice_widget.textReady.connect(lambda text: text_edit.setPlainText(text))

    window.setWindowTitle("Voice Input Demo")
    window.resize(400, 320)
    window.show()
    sys.exit(app.exec_())
