from __future__ import annotations

from pathlib import Path

_APP_DIR_NAME = "smartdoctororganizer"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def base_dir() -> Path:
    """Return the root directory used for storing user data and logs."""
    return _ensure_dir(Path.home() / f".{_APP_DIR_NAME}")


def user_data_dir() -> Path:
    """Directory that stores user editable data such as settings."""
    return _ensure_dir(base_dir() / "data")


def logs_dir() -> Path:
    """Directory that stores rotating log files."""
    return _ensure_dir(base_dir() / "logs")


def cache_dir() -> Path:
    """Cache directory for temporary files."""
    return _ensure_dir(base_dir() / "cache")


__all__ = [
    "base_dir",
    "user_data_dir",
    "logs_dir",
    "cache_dir",
]
