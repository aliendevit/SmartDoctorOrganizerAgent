"""Executable module for ``python -m SmartDoctorOrganizerAgent``."""
from __future__ import annotations

import sys

from PyQt5 import QtCore, QtWidgets

from .utils.logging_setup import hook_qt_messages, setup_logging
from .utils.settings import load_settings
from .utils.theme_guard import ensure_theme
from .main import main as run_main


def main() -> int:
    """Launch the SmartDoctorOrganizerAgent Qt application."""
    setup_logging()
    hook_qt_messages()

    app = QtWidgets.QApplication(sys.argv)
    settings = load_settings()

    if settings.base_point_size:
        font = app.font()
        font.setPointSize(settings.base_point_size)
        app.setFont(font)

    app.setLayoutDirection(
        QtCore.Qt.RightToLeft if settings.rtl else QtCore.Qt.LeftToRight
    )

    ensure_theme(app)
    return run_main(app)


def _main() -> int:
    """Private helper to preserve backwards compatibility."""
    return main()


if __name__ == "__main__":  # pragma: no cover - module entry point
    sys.exit(main())
