# model_intent/hf_client.py
# Minimal, robust HF local loader + simple streaming API (English-friendly).

from __future__ import annotations
from typing import Iterable, List, Dict, Optional
import os, glob

# Keep Transformers from pulling optional deps on Py3.13
os.environ.setdefault("TRANSFORMERS_NO_AUDIO", "1")
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

# pip install --upgrade transformers accelerate safetensors
# CPU Torch on Windows:
# pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# ---------- Role normalization ----------
_VALID_ROLES = {"system", "user", "assistant"}

def _normalize_dialog(messages, system=None, keep_last=24):
    """Strict alternation (system?) → user → assistant → user …
       * Collapses consecutive same-role turns
       * Ensures first non-system is 'user'
       * Ensures last is 'user' (so model generates an assistant reply)"""
    msgs = []
    if system:
        msgs.append({"role": "system", "content": str(system)})

    cleaned = [{"role": m.get("role","user"), "content": str(m.get("content",""))}
               for m in (messages or []) if m and m.get("role") in _VALID_ROLES]

    for m in cleaned:
        if msgs and msgs[-1]["role"] == m["role"] and m["role"] != "system":
            msgs[-1]["content"] = (msgs[-1]["content"] + "\n" + m["content"]).strip()
        else:
            msgs.append(m)

    i = 1 if (msgs and msgs[0]["role"] == "system") else 0
    if len(msgs) <= i or msgs[i]["role"] != "user":
        msgs.insert(i, {"role": "user", "content": ""})

    alt = []
    expect = "system" if (msgs and msgs[0]["role"] == "system") else "user"
    for m in msgs:
        if m["role"] == "system":
            if not alt: alt.append(m)
            expect = "user"; continue
        if m["role"] != expect:
            alt.append({"role": expect, "content": ""})
            expect = "assistant" if expect == "user" else "user"
        alt.append(m)
        expect = "assistant" if expect == "user" else "user"

    if alt and alt[-1]["role"] != "user":
        alt.append({"role": "user", "content": ""})

    if keep_last and keep_last > 0:
        head = alt[:1] if alt and alt[0]["role"] == "system" else []
        tail = alt[1:] if head else alt
        alt = head + tail[-keep_last:]
    return alt

# ---------------- Globals ----------------
_MODEL: Optional[torch.nn.Module] = None
_TOKENIZER: Optional[AutoTokenizer] = None
_CFG: Dict[str, object] = {
    "model_path": "",
    "max_new_tokens": 220,
    "temperature": 0.1,     # steady, near-greedy
    "top_p": 1.0,
    "top_k": 0,             # 0 disables top-k sampling
    "repetition_penalty": 1.05,
}

# ---------------- Utils ----------------
def _require_snapshot_dir(path: str):
    if not path or not os.path.isdir(path):
        raise FileNotFoundError(f"Model path not found: {path}")
    must = ["config.json", "generation_config.json"]
    missing = [m for m in must if not os.path.exists(os.path.join(path, m))]
    if missing:
        raise FileNotFoundError(f"Incomplete model directory: {path}\nMissing: {missing}")
    if not glob.glob(os.path.join(path, "*.safetensors")):
        raise FileNotFoundError(f"No *.safetensors found in: {path}")

def _select_dtype(dtype: str):
    if dtype == "auto": return "auto"
    try: return getattr(torch, dtype)
    except Exception: return "auto"

def _english_sanitize(s: str) -> str:
    import re
    s = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# ---------------- Public API ----------------
def configure_llm(
    model_path: str,
    max_new_tokens: int = 220,
    temperature: float = 0.1,
    top_p: float = 1.0,
    top_k: int = 0,
    repetition_penalty: float = 1.05,
    device_map: str = "auto",
    torch_dtype: str = "auto",
    local_files_only: bool = True,
) -> None:
    """Load tokenizer & model from a local snapshot directory."""
    global _MODEL, _TOKENIZER, _CFG

    _require_snapshot_dir(model_path)
    _CFG.update(dict(
        model_path=model_path,
        max_new_tokens=int(max_new_tokens),
        temperature=float(temperature),
        top_p=float(top_p),
        top_k=int(top_k),
        repetition_penalty=float(repetition_penalty),
    ))

    # Prefer FAST tokenizer (avoids sentencepiece on Py3.13)
    def _load_tok(local_only: bool):
        return AutoTokenizer.from_pretrained(
            model_path,
            use_fast=True,
            trust_remote_code=True,
            local_files_only=local_only,
        )

    try:
        _TOKENIZER = _load_tok(local_files_only)
    except Exception:
        # one-time fetch for tokenizer.json if needed
        _TOKENIZER = _load_tok(False)

    gen_kwargs = dict(
        trust_remote_code=True,
        local_files_only=True,
        device_map=device_map,
    )
    td = _select_dtype(torch_dtype)
    if td != "auto":
        gen_kwargs["dtype"] = td   # use modern kwarg

    _MODEL = AutoModelForCausalLM.from_pretrained(model_path, **gen_kwargs)
    _MODEL.eval()
    _ = _TOKENIZER.eos_token_id  # sanity

def _ensure_ready():
    if _MODEL is None or _TOKENIZER is None:
        raise RuntimeError("LLM not configured. Call configure_llm() successfully first.")

def _apply_chat_template(messages: List[Dict[str, str]]) -> Dict[str, torch.Tensor]:
    # After normalization, roles should already alternate
    if hasattr(_TOKENIZER, "apply_chat_template"):
        text = _TOKENIZER.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = _TOKENIZER(text, return_tensors="pt")
    else:
        parts = [f"{m.get('role','user')}: {m.get('content','')}" for m in messages]
        parts.append("assistant:")
        inputs = _TOKENIZER("\n".join(parts), return_tensors="pt")
    device = _MODEL.device
    for k in inputs: inputs[k] = inputs[k].to(device)
    return inputs

def chat_stream(messages,
                system=None,
                max_new_tokens=None,
                temperature=None,
                top_p=None,
                top_k=None,
                repetition_penalty=None,
                english_only: bool = True) -> Iterable[str]:
    """Yield a single decoded string (whole completion)."""
    _ensure_ready()

    cfg = _CFG.copy()
    if max_new_tokens is not None:      cfg["max_new_tokens"] = int(max_new_tokens)
    if temperature is not None:         cfg["temperature"] = float(temperature)
    if top_p is not None:               cfg["top_p"] = float(top_p)
    if top_k is not None:               cfg["top_k"] = int(top_k)
    if repetition_penalty is not None:  cfg["repetition_penalty"] = float(repetition_penalty)

    msgs = _normalize_dialog(messages, system=system)
    inputs = _apply_chat_template(msgs)

    # Only pass sampling flags when sampling is enabled (prevents warnings)
    do_sample = (cfg["temperature"] >= 0.2) or (cfg["top_k"] and cfg["top_k"] > 0)
    gen_kwargs = dict(
        max_new_tokens=cfg["max_new_tokens"],
        do_sample=do_sample,
        top_p=cfg["top_p"],
        repetition_penalty=cfg["repetition_penalty"],
        pad_token_id=_TOKENIZER.eos_token_id,
        eos_token_id=_TOKENIZER.eos_token_id,
    )
    if do_sample:
        gen_kwargs["temperature"] = cfg["temperature"]
        if cfg["top_k"] > 0:
            gen_kwargs["top_k"] = cfg["top_k"]

    with torch.no_grad():
        output_ids = _MODEL.generate(**inputs, **gen_kwargs)

    new_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
    text = _TOKENIZER.decode(new_ids, skip_special_tokens=True)
    if english_only:
        text = _english_sanitize(text)
    yield text