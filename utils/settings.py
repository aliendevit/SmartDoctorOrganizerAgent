from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
from .app_paths import user_data_dir

SETTINGS_FILE = user_data_dir() / "settings.yaml"

@dataclass
class AppSettings:
    theme_mode: str = "dark"        # dark|light
    base_point_size: int = 11
    rtl: bool = False
    asr_engine: str = "whisper"     # whisper|google|auto
    whisper_model: str = "base"

def load_settings() -> AppSettings:
    if SETTINGS_FILE.exists():
        try:
            data = yaml.safe_load(SETTINGS_FILE.read_text(encoding="utf-8")) or {}
            return AppSettings(**{**asdict(AppSettings()), **data})
        except Exception:
            pass
    return AppSettings()

def save_settings(s: AppSettings) -> None:
    SETTINGS_FILE.write_text(yaml.safe_dump(asdict(s), sort_keys=True, allow_unicode=True), encoding="utf-8")
