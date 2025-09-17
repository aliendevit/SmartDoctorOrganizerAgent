# nlp/gemma_text.py
import os, torch
from transformers import AutoTokenizer, AutoModelForCausalLM

HF_CACHE = os.getenv("HF_HOME") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
REPO_ID_DEFAULT = os.getenv("GEMMA_REPO_ID", "google/gemma-2b-it")  # not used offline unless you allow online

_tok = None
_model = None

def _resolve_local_snapshot():
    snap = (os.getenv("MEDICALDOC_LOCAL_MODEL") or "").strip()
    return snap if snap and os.path.exists(os.path.join(snap, "config.json")) else ""

def _load():
    global _tok, _model
    if _tok is not None and _model is not None:
        return _tok, _model

    local = _resolve_local_snapshot()
    if not local:
        raise RuntimeError("No local Gemma snapshot. Set MEDICALDOC_LOCAL_MODEL to the folder with config.json & *.safetensors.")

    _tok = AutoTokenizer.from_pretrained(local, local_files_only=True)
    _model = AutoModelForCausalLM.from_pretrained(local, local_files_only=True)
    return _tok, _model

def generate(prompt: str, max_new_tokens: int = 256) -> str:
    tok, model = _load()
    inputs = tok(prompt, return_tensors="pt")
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
    text = tok.decode(out[0], skip_special_tokens=True)
    # Trim echo
    if text.startswith(prompt): text = text[len(prompt):].lstrip()
    return text.strip()
