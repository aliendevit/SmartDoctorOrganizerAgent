# model_intent/hf_client.py
# Local HuggingFace client for Gemma-3 270M-IT with:
# - chat template usage (apply_chat_template)
# - temperature guard (greedy if temp<=0)
# - stop sequences to prevent "user:" self-dialogue
import os
import threading
from typing import Iterable, List, Dict, Tuple

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TextIteratorStreamer,
    StoppingCriteria,
    StoppingCriteriaList,
)

# You can override via env: HFGEMMA_DIR
_DEFAULT_MODEL_DIR = os.environ.get(
    "HFGEMMA_DIR",
    r"C:\Users\asult\.cache\huggingface\hub\models--gemma-3--270m-it",
)

_CACHE = {"tok": None, "model": None, "device": None, "dir": None}


def _resolve_model_dir() -> str:
    md = _DEFAULT_MODEL_DIR
    if not os.path.exists(md):
        raise FileNotFoundError(
            f"Model dir not found: {md}\n"
            f"Set HFGEMMA_DIR env var to your local folder."
        )
    return md


def _load_model(model_dir: str) -> Tuple[AutoTokenizer, AutoModelForCausalLM, torch.device]:
    if _CACHE["model"] is not None and _CACHE["dir"] == model_dir:
        return _CACHE["tok"], _CACHE["model"], _CACHE["device"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_dir, local_files_only=True)
    model.to(device)
    _CACHE.update({"tok": tok, "model": model, "device": device, "dir": model_dir})
    return tok, model, device


def _format_with_chat_template(tok: AutoTokenizer, messages: List[Dict[str, str]], system: str = None) -> str:
    # prepend system if provided
    msgs = list(messages)
    if system:
        msgs = [{"role": "system", "content": system}] + msgs
    # Use model's own template if present
    try:
        return tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    except Exception:
        # Fallback: minimal dialogue
        lines = []
        if system:
            lines.append(f"system: {system.strip()}")
        for m in messages:
            lines.append(f"{(m.get('role') or 'user').strip()}: {(m.get('content') or '').strip()}")
        lines.append("assistant:")
        return "\n".join(lines)


class _StopOnAnySequence(StoppingCriteria):
    """Stop when any of the given token-id sequences appears at the end."""
    def __init__(self, stop_seqs_ids: List[List[int]]):
        super().__init__()
        self.stop_seqs_ids = stop_seqs_ids

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        ids = input_ids[0].tolist()
        for seq in self.stop_seqs_ids:
            L = len(seq)
            if L and ids[-L:] == seq:
                return True
        return False


def _make_stop_criteria(tok: AutoTokenizer) -> StoppingCriteriaList:
    # Stop if the model tries to start a new user turn.
    stop_strs = ["\nuser:", "\nUser:", "\nUSER:", "\n user:"]
    stop_ids = [tok.encode(s, add_special_tokens=False) for s in stop_strs]
    return StoppingCriteriaList([_StopOnAnySequence(stop_ids)])


def chat_stream(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    top_p: float = 0.95,
    max_new_tokens: int = 256,
    system: str = None,
    **extra,
) -> Iterable[str]:
    """
    Stream assistant text tokens for a chat list of messages.
    - Uses chat template
    - Greedy if temperature<=0
    - Stops when model starts 'user:' again
    """
    model_dir = _resolve_model_dir()
    tok, model, device = _load_model(model_dir)

    prompt = _format_with_chat_template(tok, messages, system=system)
    inputs = tok([prompt], return_tensors="pt").to(device)

    use_sampling = (temperature is not None) and (float(temperature) > 1e-8)
    gen_kwargs = dict(
        max_new_tokens=int(max_new_tokens),
        do_sample=use_sampling,
        pad_token_id=tok.eos_token_id,
        stopping_criteria=_make_stop_criteria(tok),
    )
    if use_sampling:
        gen_kwargs["temperature"] = float(temperature)
        gen_kwargs["top_p"] = float(top_p)
    # propagate safe extras
    for k, v in (extra or {}).items():
        if k in ("temperature", "top_p"):
            continue
        gen_kwargs[k] = v

    model.eval()
    with torch.no_grad():
        streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
        kwargs_stream = dict(inputs, streamer=streamer, **gen_kwargs)
        t = threading.Thread(target=model.generate, kwargs=kwargs_stream)
        t.start()
        for piece in streamer:
            yield piece


def chat_once(
    user_text: str,
    system: str = None,
    temperature: float = 0.2,
    max_new_tokens: int = 256,
) -> str:
    msgs = [{"role": "user", "content": user_text}]
    buf = []
    for ch in chat_stream(
        msgs,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        system=system,
    ):
        buf.append(ch)
    return "".join(buf)
