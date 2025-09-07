# PyInstaller hook to ensure SpeechRecognition's pocketsphinx (if any) is bundled
from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('speech_recognition')
