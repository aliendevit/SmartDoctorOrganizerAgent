# nlp/local_gemma_it.py
import os, re, json
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from core import app_settings as AS

HF_CACHE = os.getenv("HF_HOME") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
REPO_ID_DEFAULT = "google/gemma-2b-it"  # not used if you have a local snapshot

# ---------------- path resolution ----------------
def _resolve_local_snapshot() -> str:
    def first_snapshot_with_config(p: Path) -> str:
        snaps = p / "snapshots"
        if snaps.exists():
            cands = [d for d in snaps.iterdir() if (d / "config.json").exists()]
            if cands:
                cands.sort(key=lambda d: d.stat().st_mtime, reverse=True)
                return str(cands[0])
        return ""

    # honor env vars (snapshot folder OR model root)
    for env in ("MEDICALDOC_LOCAL_MODEL", "GEMMA_LOCAL_SNAPSHOT", "LLM_LOCAL_SNAPSHOT"):
        raw = (os.getenv(env) or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if p.exists():
            if (p / "config.json").exists():
                return str(p)
            snap = first_snapshot_with_config(p)
            if snap:
                return snap

    # common HF cache layouts
    for model_id in ("gemma-3--270m-it","gemma-3-270m-it","google--gemma-3-270m-it",
                     "google--gemma-2b-it","gemma-2b-it"):
        base = Path(HF_CACHE) / "hub" / f"models--{model_id}"
        if base.exists():
            snap = first_snapshot_with_config(base)
            if snap:
                return snap
    return ""

# ---------------- device from settings ----------------
def _resolve_device_from_settings() -> str:
    try:
        mode = str(AS.read_all().get("ai/compute_mode", "auto")).lower()
    except Exception:
        mode = "auto"
    if mode == "gpu" and torch.cuda.is_available():
        return "cuda"
    if mode == "cpu":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"

# ---------------- globals ----------------
_INIT_LOCK = Lock()
_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None
_DEVICE: str = "cpu"  # updated on load

# ---------------- model load (single, thread-safe) ----------------
def _load():
    global _tokenizer, _model, _DEVICE
    with _INIT_LOCK:
        if _tokenizer is not None and _model is not None:
            return _tokenizer, _model

        local_snap = _resolve_local_snapshot()
        if not local_snap:
            # allow pointing directly to a folder with config.json
            alt = (os.getenv("MEDICALDOC_LOCAL_MODEL") or "").strip()
            if alt:
                local_snap = alt
        if not local_snap or not (Path(local_snap) / "config.json").exists():
            raise RuntimeError(
                "No local Gemma snapshot found. Point MEDICALDOC_LOCAL_MODEL to a directory containing "
                "config.json and *.safetensors (or a HF 'snapshots/<hash>' dir)."
            )

        _DEVICE = _resolve_device_from_settings()
        dtype = torch.float16 if _DEVICE == "cuda" else torch.float32

        _tokenizer = AutoTokenizer.from_pretrained(local_snap, local_files_only=True)
        _model = AutoModelForCausalLM.from_pretrained(
            local_snap, local_files_only=True, torch_dtype=dtype, low_cpu_mem_usage=True
        ).to(_DEVICE).eval()

        # Gemma often needs pad_token_id set to eos_token_id
        if getattr(_model.generation_config, "pad_token_id", None) is None:
            _model.generation_config.pad_token_id = _tokenizer.eos_token_id
        return _tokenizer, _model

# ---------------- prompting & parsing ----------------
SCHEMA = """{
 "Name": string,
 "Age": integer or null,
 "Symptoms": [string],
 "Notes": string,
 "Date": string (dd-mm-yyyy),
 "Appointment Date": string or null,
 "Appointment Time": string or null,
 "Follow-Up Date": string or null
}"""

EXAMPLE = """Input:
Patient Emily Chen, age 31, complains of migraine and photophobia.
Appointment 15/05/2026 09:00 AM. Follow-up 29/05/2026.
Notes: Keep diary.

JSON:
{"Name":"Emily Chen","Age":31,"Symptoms":["migraine","photophobia"],"Notes":"Keep diary","Date":"15-05-2026","Appointment Date":"15-05-2026","Appointment Time":"09:00 AM","Follow-Up Date":"29-05-2026"}"""

_RX_JSON = re.compile(r"\{[\s\S]*?\}", re.M)

def _make_messages(text: str):
    system = (
        "You are a clinical extractor. Return ONLY valid JSON.\n"
        "No explanations, no code fences, no extra text. Use this schema strictly:\n"
        f"{SCHEMA}\n\nExample:\n{EXAMPLE}\n"
        "Rules: If something is missing, use null or empty values. Date format must be dd-mm-yyyy."
    )
    user = f"INPUT:\n{text}\n\nReturn JSON now:"
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]

def _generate(text: str, max_new_tokens: int = 256) -> str:
    tok, model = _load()
    prompt = tok.apply_chat_template(
        _make_messages(text),
        tokenize=False,
        add_generation_prompt=True
    )
    inputs = tok(prompt, return_tensors="pt")
    # send to the SAME device as the model
    inputs = {k: v.to(next(model.parameters()).device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
            eos_token_id=tok.eos_token_id,
            pad_token_id=tok.eos_token_id,
        )

    gen_ids = out[0][inputs["input_ids"].shape[-1]:]
    reply = tok.decode(gen_ids, skip_special_tokens=True).strip()
    return reply

def extract_fields(text: str) -> Dict[str, Any]:
    raw = _generate(text)

    # strip accidental code fences
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = re.sub(r"^json\s*", "", s, flags=re.I).strip()

    m = _RX_JSON.search(s)
    cand = m.group(0) if m else s
    try:
        data = json.loads(cand)
    except Exception:
        print("[Gemma RAW]", s[:400])
        return {}

    # normalize types/fields
    if not isinstance(data.get("Symptoms", []), list):
        data["Symptoms"] = [str(data.get("Symptoms"))] if data.get("Symptoms") else []
    if data.get("Age", None) is not None:
        try:
            data["Age"] = int(data["Age"])
        except Exception:
            data["Age"] = None

    for k in ("Name", "Notes", "Date", "Appointment Date", "Appointment Time", "Follow-Up Date"):
        v = data.get(k, None)
        data[k] = "" if v is None else str(v)

    return data
