# core/ai_assistant.py
from __future__ import annotations
import json, re, ast, threading
from datetime import datetime
from typing import Dict, Optional, Any

try:
    # Pull settings to find the local model path & runtime params
    from . import app_settings as AS
except Exception:
    AS = None

# ---- Simple local LLM wrapper (llama.cpp or ctransformers) -------------------
class _LocalLLM:
    def __init__(self, model_path: str = "", max_new_tokens: int = 240, temperature: float = 0.6):
        self.model_path = model_path
        self.max_new_tokens = int(max_new_tokens)
        self.temperature = float(temperature)

        self._engine = None
        self._lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        """Try llama-cpp first, then ctransformers. Keep it minimal & local."""
        if not self.model_path:
            return
        try:
            # llama.cpp python
            from llama_cpp import Llama
            self._engine = ("llama_cpp", Llama(
                model_path=self.model_path,
                n_ctx=4096,
                logits_all=False,
                verbose=False
            ))
            return
        except Exception:
            pass
        try:
            # ctransformers (GGUF)
            from ctransformers import AutoModelForCausalLM
            eng = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                model_type="llama",  # Gemma uses llama-ish tokenizer; adjust if you use a gemma build
                gpu_layers=0
            )
            self._engine = ("ctrans", eng)
        except Exception:
            self._engine = None

    def chat(self, system: Optional[str], user: str) -> str:
        """Single-turn prompt. Keep it deterministic enough for extraction."""
        if self._engine is None:
            # Last resort: return a message to avoid crashes.
            return "ERROR: No local LLM engine initialized (check Settings → AI model path)."

        kind, eng = self._engine
        prompt = user if system is None else f"<<SYS>>\n{system}\n<</SYS>>\n\n{user}"

        with self._lock:
            if kind == "llama_cpp":
                out = eng.create_completion(
                    prompt=prompt,
                    max_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                    stop=["</json>", "\n\n\n"]
                )
                return out["choices"][0]["text"].strip()
            else:
                # ctransformers: simple generate
                return eng(
                    prompt,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                ).strip()

# ---- Singleton & helpers -----------------------------------------------------
_AI_SINGLETON: Optional[_LocalLLM] = None

def get_ai() -> _LocalLLM:
    global _AI_SINGLETON
    if _AI_SINGLETON is None:
        mp, mx, tt = "", 240, 0.6
        if AS:
            try:
                cfg = AS.read_all()
                mp = str(cfg.get("ai/model_path", "") or "")
                mx = int(cfg.get("ai/max_tokens", 240))
                tt = float(cfg.get("ai/temperature", 0.6))
            except Exception:
                pass
        _AI_SINGLETON = _LocalLLM(mp, mx, tt)
    return _AI_SINGLETON

# ---- Extraction: robust JSON with regex fallback -----------------------------
_JSON_INSTRUCTIONS = """You are a clinical scribe. Extract a clean JSON object from the given clinical text.
Keys and formats:
- "Name": string (best guess, else "Unknown")
- "Age": integer (years) or null
- "Symptoms": array of short strings (lowercase nouns/phrases)
- "Notes": concise one-paragraph summary
- "General Date": "dd-MM-yyyy" or null
- "Appointment Date": "dd-MM-yyyy" or null
- "Appointment Time": "hh:mm AP" (e.g., "09:30 AM") or null
- "Follow-Up Date": "dd-MM-yyyy" or null

Return ONLY JSON. Do not add commentary. If not present, use null or sensible empty values."""

_DATE_IN = [
    ("%d-%m-%Y", r"\b(\d{2}-\d{2}-\d{4})\b"),
    ("%d/%m/%Y", r"\b(\d{2}/\d{2}/\d{4})\b"),
    ("%Y-%m-%d", r"\b(\d{4}-\d{2}-\d{2})\b"),
]
_TIME_PAT = r"\b(?:([01]?\d):([0-5]\d)\s?(AM|PM|am|pm)|([01]\d|2[0-3]):([0-5]\d))\b"

def _norm_date_to_ddmmyyyy(text: str) -> Optional[str]:
    if not text:
        return None
    s = text.strip()
    # Try known formats
    for fmt, _ in _DATE_IN:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d-%m-%Y")
        except Exception:
            pass
    # try to detect one inside the string
    for fmt, rx in _DATE_IN:
        m = re.search(rx, s)
        if m:
            try:
                dt = datetime.strptime(m.group(1), fmt)
                return dt.strftime("%d-%m-%Y")
            except Exception:
                pass
    return None

def _norm_time_hhmm_ap(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(_TIME_PAT, text)
    if not m:
        return None
    if m.group(1) and m.group(2) and m.group(3):
        # already 12h with AM/PM
        hh = int(m.group(1)); mm = int(m.group(2)); ap = m.group(3).upper()
        return f"{hh:02d}:{mm:02d} {ap}"
    # 24h case
    hh = int(m.group(4)); mm = int(m.group(5))
    ap = "AM"
    if hh == 0:
        hh12 = 12; ap = "AM"
    elif 1 <= hh < 12:
        hh12 = hh; ap = "AM"
    elif hh == 12:
        hh12 = 12; ap = "PM"
    else:
        hh12 = hh - 12; ap = "PM"
    return f"{hh12:02d}:{mm:02d} {ap}"

def _safe_json_loads(s: str) -> Optional[Dict[str, Any]]:
    s = s.strip()
    # Trim potential fence
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)
    # Try JSON first
    try:
        obj = json.loads(s)
        if isinstance(obj, dict): return obj
    except Exception:
        pass
    # Try Python literal (some models sneak single quotes)
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, dict): return obj
    except Exception:
        pass
    # Try to find a JSON object substring
    m = re.search(r"\{.*\}", s, flags=re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict): return obj
        except Exception:
            pass
    return None

def extract_structured(text: str) -> Dict[str, Any]:
    """
    Main entry: ask the LLM for JSON, then normalize/patch with regex fallbacks.
    """
    user = f"{_JSON_INSTRUCTIONS}\n\nTEXT:\n{text}\n"
    raw = get_ai().chat(None, user)

    data = _safe_json_loads(raw) or {}

    # Normalize keys & defaults
    out: Dict[str, Any] = {
        "Name":           (data.get("Name") or "").strip() or "Unknown",
        "Age":            data.get("Age"),
        "Symptoms":       data.get("Symptoms") or [],
        "Notes":          (data.get("Notes") or "").strip(),
        "General Date":   data.get("General Date"),
        "Appointment Date": data.get("Appointment Date"),
        "Appointment Time": data.get("Appointment Time"),
        "Follow-Up Date": data.get("Follow-Up Date"),
    }

    # Fallbacks via regex if LLM missed something
    if not out["Age"]:
        m = re.search(r"\b(\d{1,3})\s*(?:y/o|yo|years? old)\b", text, re.I)
        if m:
            try: out["Age"] = int(m.group(1))
            except Exception: pass

    # Symptoms: try comma/semicolon lists if empty
    if not out["Symptoms"]:
        m = re.search(r"(symptom[s]?:?\s*)(.+)", text, re.I)
        if m:
            parts = re.split(r"[,;•\n]+", m.group(2))
            out["Symptoms"] = [p.strip().lower() for p in parts if p.strip()]

    # Dates & Time normalization
    for k in ("General Date", "Appointment Date", "Follow-Up Date"):
        out[k] = _norm_date_to_ddmmyyyy(out.get(k)) or out.get(k) or None
    out["Appointment Time"] = _norm_time_hhmm_ap(out.get("Appointment Time")) or out.get("Appointment Time") or None

    # Ensure proper types
    if isinstance(out["Symptoms"], str):
        out["Symptoms"] = [s.strip() for s in re.split(r"[,;]+", out["Symptoms"]) if s.strip()]

    return out

# Optional: a short summary helper if you need it elsewhere
def summarize(text: str, lang: str = "en") -> str:
    prompt = (f"Summarize the following clinical note for handover in {lang}. "
              f"Be concise, 3–5 lines max.\n\n{text}")
    return get_ai().chat(None, prompt)
