"""Backward-compatible launcher for SmartDoctorOrganizerAgent."""
from __future__ import annotations

import sys

from SmartDoctorOrganizerAgent.__main__ import _main as main

if __name__ == "__main__":  # pragma: no cover - module entry point
    sys.exit(main())
