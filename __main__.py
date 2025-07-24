import sys
from PyQt5 import QtWidgets
from app.utils.logging_setup import setup_logging, hook_qt_messages
from utils.settings import load_settings
from utils.theme_guard import apply_theme

def main() -> int:
    setup_logging()
    hook_qt_messages()

    app = QtWidgets.QApplication(sys.argv)
    s = load_settings()
    apply_theme(app, mode=s.theme_mode, base_point_size=s.base_point_size, rtl=s.rtl)

    # your existing window creation
    from app.main import main as run_main
    return run_main(app)  # refactor main.py to expose main(app) -> int

if __name__ == "__main__":
    sys.exit(main())
