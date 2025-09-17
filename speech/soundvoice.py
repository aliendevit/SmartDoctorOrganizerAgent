"""Utility helpers for capturing microphone audio with manual control."""
from __future__ import annotations

import io
import queue
import threading
import wave
from dataclasses import dataclass
from typing import List, Optional

try:  # pragma: no cover - optional dependency
    import sounddevice as _sd
except Exception:  # pragma: no cover - the widget will surface a friendly error
    _sd = None

SOUNDVOICE_OK = _sd is not None


@dataclass
class SoundVoiceStatus:
    """Represents warnings or notes emitted by the recorder backend."""

    message: str


class SoundVoiceRecorder:
    """High-level wrapper above ``sounddevice`` providing start/stop controls."""

    def __init__(self, samplerate: int = 16_000, channels: int = 1):
        self.samplerate = int(samplerate)
        self.channels = int(channels)
        self.dtype = "int16"
        self._queue: "queue.Queue[Optional[bytes]]" = queue.Queue()
        self._frames: List[bytes] = []
        self._stream = None
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._running = False
        self._status: List[SoundVoiceStatus] = []

    @property
    def status_messages(self) -> List[SoundVoiceStatus]:
        """Return and clear backend status messages accumulated so far."""

        with self._lock:
            msgs = list(self._status)
            self._status.clear()
        return msgs

    def _enqueue(self, data: Optional[bytes]):
        try:
            self._queue.put_nowait(data)
        except queue.Full:  # pragma: no cover - should not occur, but guard anyway
            pass

    def start(self) -> None:
        """Begin recording from the system microphone."""

        if not SOUNDVOICE_OK:
            raise RuntimeError("sounddevice is not available; install 'sounddevice' to enable SoundVoice.")
        if self._running:
            return

        self._frames = []
        self._queue = queue.Queue()
        self._running = True

        def _callback(indata, frames, time, status):  # pragma: no cover - callback executed by sounddevice
            if status:
                with self._lock:
                    self._status.append(SoundVoiceStatus(str(status)))
            self._enqueue(bytes(indata))

        self._stream = _sd.RawInputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype=self.dtype,
            callback=_callback,
            blocksize=0,
        )
        self._stream.start()
        self._reader_thread = threading.Thread(target=self._drain_queue, daemon=True)
        self._reader_thread.start()

    def _drain_queue(self) -> None:
        while self._running:
            try:
                chunk = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if chunk is None:
                break
            with self._lock:
                self._frames.append(chunk)

    def stop(self) -> bytes:
        """Stop recording and return raw PCM data."""

        if not self._running:
            return b""
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
            finally:
                self._stream.close()
            self._stream = None
        self._enqueue(None)
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)
        self._reader_thread = None
        with self._lock:
            raw = b"".join(self._frames)
            self._frames = []
        return raw

    def discard(self) -> None:
        """Abort recording and drop buffered audio without returning it."""

        self.stop()
        with self._lock:
            self._frames = []

    def to_wav(self, raw: Optional[bytes]) -> bytes:
        """Convert raw PCM bytes into a WAV byte stream."""

        raw = raw or b""
        if not raw:
            return b""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16
            wf.setframerate(self.samplerate)
            wf.writeframes(raw)
        return buffer.getvalue()


__all__ = ["SOUNDVOICE_OK", "SoundVoiceRecorder", "SoundVoiceStatus"]
