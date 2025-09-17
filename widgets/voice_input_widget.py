import io
import sys
from typing import Optional

from PyQt5 import QtWidgets, QtCore, QtGui
import speech_recognition as sr

from speech.soundvoice import SOUNDVOICE_OK, SoundVoiceRecorder


class _TranscriptionWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str, str)

    def __init__(self, wav_bytes: bytes, language: str):
        super().__init__()
        self._wav_bytes = wav_bytes
        self._language = language

    @QtCore.pyqtSlot()
    def run(self) -> None:
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(io.BytesIO(self._wav_bytes)) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language=self._language)
        except sr.WaitTimeoutError:
            self.failed.emit("Listening timed out.", "Listening timed out. Please try again.")
        except sr.UnknownValueError:
            self.failed.emit(
                "Could not understand the audio.",
                "Could not understand the audio. Please speak clearly.",
            )
        except sr.RequestError as exc:
            self.failed.emit(
                "Service unavailable.",
                f"Could not request results from the speech service: {exc}",
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.failed.emit("An unexpected error occurred.", str(exc))
        else:
            self.finished.emit(text)


class _MicrophoneWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str, str)

    def __init__(self, language: str):
        super().__init__()
        self._language = language

    @QtCore.pyqtSlot()
    def run(self) -> None:
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=7, phrase_time_limit=30)
            text = recognizer.recognize_google(audio, language=self._language)
        except sr.WaitTimeoutError:
            self.failed.emit("Listening timed out.", "Listening timed out. Please try again.")
        except sr.UnknownValueError:
            self.failed.emit(
                "Could not understand the audio.",
                "Could not understand the audio. Please speak clearly.",
            )
        except sr.RequestError as exc:
            self.failed.emit(
                "Service unavailable.",
                f"Could not request results from the speech service: {exc}",
            )
        except OSError as exc:
            self.failed.emit("Microphone unavailable.", f"Could not access the microphone: {exc}")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.failed.emit("An unexpected error occurred.", str(exc))
        else:
            self.finished.emit(text)


class VoiceInputWidget(QtWidgets.QWidget):
    # Signal to emit recognized text
    textReady = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, language="en-US"):
        """
        language: A BCP-47 language code, e.g., "en-US" for English or "ar-SA" for Arabic.
        """
        super().__init__(parent)
        self.language = language
        self._soundvoice_available = SOUNDVOICE_OK
        self.recorder: Optional[SoundVoiceRecorder] = SoundVoiceRecorder() if SOUNDVOICE_OK else None
        self._session_active = False
        self._is_paused = False
        self._transcribing = False
        self._has_recorded = False
        self._transcription_thread: Optional[QtCore.QThread] = None
        self._mic_icon = QtGui.QIcon()
        self._pause_icon = QtGui.QIcon()
        self._resume_icon = QtGui.QIcon()
        self._processing_icon = QtGui.QIcon()
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        self.voice_button = QtWidgets.QPushButton()
        self.voice_button.setObjectName("voiceButton")
        self.voice_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.voice_button.setIconSize(QtCore.QSize(32, 32))
        self.voice_button.setMinimumHeight(72)
        self.voice_button.setCheckable(self._soundvoice_available)
        if self._soundvoice_available:
            self.voice_button.clicked.connect(self._handle_primary_press)
        else:
            self.voice_button.clicked.connect(self._start_basic_capture)
        self._apply_record_button_style()
        self._init_icons()
        self._set_record_button_state()
        layout.addWidget(self.voice_button)

        self.stop_button: Optional[QtWidgets.QPushButton]
        self.cancel_button: Optional[QtWidgets.QPushButton]
        if self._soundvoice_available:
            controls = QtWidgets.QHBoxLayout()
            controls.setSpacing(8)

            self.stop_button = QtWidgets.QPushButton("Stop")
            self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
            self.stop_button.setIconSize(QtCore.QSize(24, 24))
            self.stop_button.clicked.connect(self.stop_and_transcribe)
            self.stop_button.setEnabled(False)
            controls.addWidget(self.stop_button)

            self.cancel_button = QtWidgets.QPushButton("Cancel")
            self.cancel_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton))
            self.cancel_button.setIconSize(QtCore.QSize(24, 24))
            self.cancel_button.clicked.connect(self.cancel_recording)
            self.cancel_button.setEnabled(False)
            controls.addWidget(self.cancel_button)

            layout.addLayout(controls)
        else:
            self.stop_button = None
            self.cancel_button = None

        self.status_label = QtWidgets.QLabel("Tap Start to capture audio with SoundVoice.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        if not self._soundvoice_available:
            self.status_label.setText(
                "Recording uses the default microphone backend. Install 'sounddevice' to enable SoundVoice controls."
            )

        self.setLayout(layout)
        self._update_controls()

    def _init_icons(self) -> None:
        mic = QtGui.QIcon.fromTheme("audio-input-microphone")
        if mic.isNull():
            mic = self.style().standardIcon(QtWidgets.QStyle.SP_MediaRecord)
        self._mic_icon = mic
        self._pause_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause)
        self._resume_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        self._processing_icon = self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)

    def _handle_primary_press(self):
        if self._transcribing:
            return
        if not self._soundvoice_available or self.recorder is None:
            return

        if not self._session_active:
            self._begin_recording()
        elif self._is_paused:
            self._resume_recording()
        else:
            self._pause_recording()

    def _begin_recording(self) -> None:
        if self.recorder is None:
            return
        try:
            self.recorder.start()
        except Exception as exc:
            self.voice_button.setChecked(False)
            QtWidgets.QMessageBox.warning(self, "SoundVoice", f"Could not start recording: {exc}")
            return

        self._session_active = True
        self._is_paused = False
        self.status_label.setText("Recording… press Stop when you are finished.")
        self._set_record_button_state()
        self._update_controls()

    def _pause_recording(self) -> None:
        if self.recorder is None:
            return
        try:
            self.recorder.pause()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "SoundVoice", f"Could not pause recording: {exc}")
            return

        self._is_paused = True
        self.status_label.setText("Recording paused. Press Resume to continue or Stop to finish.")
        self._set_record_button_state()
        self._update_controls()

    def _resume_recording(self) -> None:
        if self.recorder is None:
            return
        try:
            self.recorder.resume()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "SoundVoice", f"Could not resume recording: {exc}")
            return

        self._is_paused = False
        self.status_label.setText("Recording… press Stop when you are finished.")
        self._set_record_button_state()
        self._update_controls()

    def stop_and_transcribe(self):
        self._finish_recording(finalize=True)

    def cancel_recording(self):
        self._finish_recording(finalize=False)

    def _finish_recording(self, finalize: bool):
        if not self._soundvoice_available or self.recorder is None:
            return
        if not self._session_active:
            return
        QtWidgets.QApplication.processEvents()
        raw_audio = b""
        try:
            if finalize:
                raw_audio = self.recorder.stop()
            else:
                self.recorder.discard()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "SoundVoice", f"Could not stop recording: {e}")
        self._session_active = False
        self._is_paused = False
        if self.voice_button.isCheckable():
            self.voice_button.setChecked(False)
        self._set_record_button_state()
        self._update_controls()

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

        self._transcribing = True
        self._set_record_button_state()
        self._update_controls()
        self._launch_transcription(wav_bytes)

    def _launch_transcription(self, wav_bytes: bytes) -> None:
        if not wav_bytes:
            return
        worker = _TranscriptionWorker(wav_bytes, self.language)
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_transcription_succeeded)
        worker.failed.connect(self._on_transcription_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self._transcription_thread = thread

    def _on_transcription_succeeded(self, text: str) -> None:
        self._transcription_thread = None
        self._transcribing = False
        self._has_recorded = True
        self.status_label.setText("Transcription complete.")
        self._set_record_button_state()
        self._update_controls()
        self.textReady.emit(text)

    def _on_transcription_failed(self, status_text: str, detail: str) -> None:
        self._transcription_thread = None
        self._transcribing = False
        self.status_label.setText(status_text)
        self._set_record_button_state()
        self._update_controls()
        QtWidgets.QMessageBox.warning(self, "SoundVoice", detail)

    def _set_record_button_state(self):
        if not self._soundvoice_available:
            if self._transcribing:
                state = "processing"
                icon = self._processing_icon
                text = "Listening…"
            else:
                state = "idle"
                icon = self._mic_icon
                text = "Record Again" if self._has_recorded else "Start Recording"
            checked = False
        elif self._transcribing:
            state = "processing"
            icon = self._processing_icon
            text = "Transcribing…"
            checked = False
        elif not self._session_active:
            state = "idle"
            icon = self._mic_icon
            text = "Start New Recording" if self._has_recorded else "Start Recording"
            checked = False
        elif self._is_paused:
            state = "paused"
            icon = self._resume_icon
            text = "Resume Recording"
            checked = False
        else:
            state = "recording"
            icon = self._pause_icon
            text = "Pause Recording"
            checked = True

        self.voice_button.setProperty("recordState", state)
        self.voice_button.setIcon(icon)
        self.voice_button.setText(text)
        if self.voice_button.isCheckable():
            self.voice_button.setChecked(checked)
        self.voice_button.style().unpolish(self.voice_button)
        self.voice_button.style().polish(self.voice_button)

    def _update_controls(self) -> None:
        self.voice_button.setEnabled(not self._transcribing)
        if self._soundvoice_available and self.stop_button and self.cancel_button:
            self.stop_button.setEnabled(self._session_active and not self._transcribing)
            self.cancel_button.setEnabled(self._session_active and not self._transcribing)

    def _apply_record_button_style(self):
        self.voice_button.setStyleSheet(
            """
            QPushButton#voiceButton {
                border: none;
                border-radius: 36px;
                padding: 20px 32px;
                font-size: 18px;
                font-weight: 600;
                letter-spacing: 0.5px;
                color: #FFFFFF;
                background-color: #1976D2;
                qproperty-iconSize: 32px 32px;
            }
            QPushButton#voiceButton:hover {
                background-color: #1565C0;
            }
            QPushButton#voiceButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton#voiceButton[recordState="recording"] {
                background-color: #C62828;
            }
            QPushButton#voiceButton[recordState="recording"]:hover {
                background-color: #B71C1C;
            }
            QPushButton#voiceButton[recordState="recording"]:pressed {
                background-color: #7F0000;
            }
            QPushButton#voiceButton[recordState="paused"] {
                background-color: #F9A825;
                color: #1F2933;
            }
            QPushButton#voiceButton[recordState="paused"]:hover {
                background-color: #F57F17;
            }
            QPushButton#voiceButton[recordState="paused"]:pressed {
                background-color: #E65100;
            }
            QPushButton#voiceButton[recordState="processing"] {
                background-color: #455A64;
            }
            QPushButton#voiceButton:disabled {
                background-color: #90A4AE;
                color: #ECEFF1;
            }
        """
        )

    def _start_basic_capture(self) -> None:
        if self._transcribing:
            return
        self._transcribing = True
        self.status_label.setText("Listening… speak now.")
        self._set_record_button_state()
        self._update_controls()

        worker = _MicrophoneWorker(self.language)
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_basic_capture_succeeded)
        worker.failed.connect(self._on_basic_capture_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self._transcription_thread = thread

    def _on_basic_capture_succeeded(self, text: str) -> None:
        self._transcription_thread = None
        self._transcribing = False
        self._has_recorded = True
        self.status_label.setText("Transcription complete.")
        self._set_record_button_state()
        self._update_controls()
        self.textReady.emit(text)

    def _on_basic_capture_failed(self, status_text: str, detail: str) -> None:
        self._transcription_thread = None
        self._transcribing = False
        self.status_label.setText(status_text)
        self._set_record_button_state()
        self._update_controls()
        QtWidgets.QMessageBox.warning(self, "Voice Input", detail)


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
