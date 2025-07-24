import logging, sys
from logging.handlers import RotatingFileHandler
from .app_paths import logs_dir

def setup_logging(level=logging.INFO) -> None:
    log_path = logs_dir() / "app.log"
    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Also stderr for dev
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)

def hook_qt_messages():
    from PyQt5 import QtCore
    def _handler(mode, ctx, msg):
        logging.getLogger("Qt").warning(f"{msg} ({ctx.file}:{ctx.line})")
    QtCore.qInstallMessageHandler(_handler)
