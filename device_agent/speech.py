"""Offline speech I/O: push-to-talk recording + Vosk speech-to-text, and
espeak-ng for text-to-speech. Both run entirely on the Pi - no audio goes
to any API, so this costs nothing and needs no internet connection."""

import json
import queue
import subprocess

import sounddevice as sd
from vosk import KaldiRecognizer, Model

SAMPLE_RATE = 16000
# Download a small model (e.g. vosk-model-small-de-0.15) and unpack it here -
# see README.md "USB-C Device Agent" -> hardware/setup.
VOSK_MODEL_PATH = "/home/pi/vosk-model-small-de-0.15"


class PushToTalkRecorder:
    """Call start() on button-press, stop() on button-release - stop()
    returns the transcribed text."""

    def __init__(self, model_path: str = VOSK_MODEL_PATH):
        self._model = Model(model_path)
        self._recognizer = None
        self._stream = None
        self._frames = queue.Queue()

    def _callback(self, indata, frames, time_info, status):
        self._frames.put(bytes(indata))

    def start(self) -> None:
        self._recognizer = KaldiRecognizer(self._model, SAMPLE_RATE)
        self._frames = queue.Queue()
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> str:
        self._stream.stop()
        self._stream.close()
        while not self._frames.empty():
            self._recognizer.AcceptWaveform(self._frames.get())
        result = json.loads(self._recognizer.FinalResult())
        return result.get("text", "")


def speak(text: str, voice: str = "de") -> None:
    """Text-to-speech via espeak-ng. Swap this one function for Piper or a
    cloud TTS later if you want a more natural-sounding voice."""
    if not text:
        return
    subprocess.run(["espeak-ng", "-v", voice, text], check=False)
