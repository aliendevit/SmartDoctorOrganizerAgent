from typing import Optional, Tuple

def try_transcribe(wav_path: str, language: Optional[str], model_size="base", translate=False) -> Tuple[bool, str]:
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return False, "Whisper not installed"
    try:
        model = WhisperModel(model_size, device="auto", compute_type="float16")
        segments, _ = model.transcribe(
            wav_path, language=language,
            vad_filter=True, beam_size=5,
            condition_on_previous_text=False,
            task=("translate" if translate else "transcribe")
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return True, text
    except Exception as e:
        return False, str(e)
