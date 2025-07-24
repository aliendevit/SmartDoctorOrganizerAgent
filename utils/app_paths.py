from __future__ import annotations
import os, platform
from pathlib import Path

APP_NAME = "ClinicAssistant"

def user_data_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    p = base / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def user_cache_dir() -> Path:
    p = user_data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p

def logs_dir() -> Path:
    p = user_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

def reports_dir() -> Path:
    p = user_data_dir() / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p
