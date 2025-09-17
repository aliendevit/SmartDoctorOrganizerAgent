import sys
from PyQt5 import QtCore, QtWidgets
from SmartDoctorOrganizerAgent.utils.logging_setup import setup_logging, hook_qt_messages
from SmartDoctorOrganizerAgent.utils.settings import load_settings
from SmartDoctorOrganizerAgent.utils.theme_guard import ensure_theme
from SmartDoctorOrganizerAgent.main import main as run_main

def main() -> int:
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

if __name__ == "__main__":
    sys.exit(main())
