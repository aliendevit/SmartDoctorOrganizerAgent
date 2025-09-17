# core/app_settings.py
from PyQt5 import QtCore, QtWidgets
from typing import Dict  # <-- add this

APP_ORG  = "YourOrg"
APP_NAME = "MedicalDocAI Demo v1.9.3"

def qsettings() -> QtCore.QSettings:
    """Return the global QSettings object for this app."""
    return QtCore.QSettings(APP_ORG, APP_NAME)

DEFAULTS = {
    "clinic/name": "My Clinic",
    "clinic/phone": "",
    "clinic/email": "",
    "clinic/address": "",
    "clinic/logo": "",
    "clinic/timezone": "UTC",
    "clinic/datetime_fmt": "dd-MM-yyyy hh:mm AP",

    "ui/theme": "Light",
    "ui/base_pt": 12,
    "ui/accent": "#3A8DFF",
    "ui/glassy": False,

    "ai/enabled": False,
    "ai/model_path": "",
    "ai/max_tokens": 220,
    "ai/temperature": 0.1,
    "ai/autostart": False,
    "ai/compute_mode": "auto",  # new key

    "appts/default_len": 30,
    "appts/day_start": "07:00",
    "appts/day_end": "21:00",
    "appts/week_starts": "Sun",

    "bill/currency": "USD",
    "bill/tax_pct": 0.0,
    "bill/default_method": "Cash",

    "notify/toasts": True,
    "notify/daily_time": "09:00",

    "lang/code": "en",
    "lang/rtl": False,
}

def _seed_if_missing(s: QtCore.QSettings):
    """Ensure every DEFAULTS key exists at least once."""
    dirty = False
    for k, v in DEFAULTS.items():
        if s.value(k, None) is None:
            s.setValue(k, v)
            dirty = True
    if dirty:
        s.sync()

def read_all() -> dict:
    s = qsettings()
    _seed_if_missing(s)

    def _b(key):  # bool
        return str(s.value(key, DEFAULTS[key])).strip().lower() in ("1","true","yes","on")

    def _i(key):  # int
        try: return int(s.value(key, DEFAULTS[key]))
        except: return int(DEFAULTS[key])

    def _f(key):  # float
        try: return float(s.value(key, DEFAULTS[key]))
        except: return float(DEFAULTS[key])

    def _s(key):  # str
        v = s.value(key, DEFAULTS[key])
        return str(v) if v is not None else str(DEFAULTS[key])

    out = {
        # clinic
        "clinic/name":         _s("clinic/name"),
        "clinic/phone":        _s("clinic/phone"),
        "clinic/email":        _s("clinic/email"),
        "clinic/address":      _s("clinic/address"),
        "clinic/logo":         _s("clinic/logo"),
        "clinic/timezone":     _s("clinic/timezone"),
        "clinic/datetime_fmt": _s("clinic/datetime_fmt"),

        # ui
        "ui/theme":   _s("ui/theme"),
        "ui/base_pt": _i("ui/base_pt"),
        "ui/accent":  _s("ui/accent"),
        "ui/glassy":  _b("ui/glassy"),

        # ai
        "ai/enabled":     _b("ai/enabled"),
        "ai/model_path":  _s("ai/model_path"),
        "ai/max_tokens":  _i("ai/max_tokens"),
        "ai/temperature": _f("ai/temperature"),
        "ai/autostart":   _b("ai/autostart"),
        "ai/compute_mode":_s("ai/compute_mode"),  # auto|gpu|cpu

        # appts
        "appts/default_len": _i("appts/default_len"),
        "appts/day_start":   _s("appts/day_start"),
        "appts/day_end":     _s("appts/day_end"),
        "appts/week_starts": _s("appts/week_starts"),

        # billing
        "bill/currency":       _s("bill/currency"),
        "bill/tax_pct":        _f("bill/tax_pct"),
        "bill/default_method": _s("bill/default_method"),

        # notifications
        "notify/toasts":     _b("notify/toasts"),
        "notify/daily_time": _s("notify/daily_time"),

        # lang
        "lang/code": _s("lang/code"),
        "lang/rtl":  _b("lang/rtl"),
    }
    return out


def apply_to_app(cfg: Dict[str, object], app: QtWidgets.QApplication):
    # Font size (immediate)
    f = app.font()
    f.setPointSize(int(cfg.get("ui/base_pt", 11)))
    app.setFont(f)

    # Optional: re-apply your global theme (keeps your palette/QSS consistent)
    try:
        from UI import design_system
        design_system.apply_global_theme(app, base_point_size=int(cfg.get("ui/base_pt", 11)))
    except Exception:
        pass

    # Locale / RTL
    code = str(cfg.get("lang/code", "en"))
    QtCore.QLocale.setDefault(QtCore.QLocale(code))
    app.setLayoutDirection(QtCore.Qt.RightToLeft if cfg.get("lang/rtl") else QtCore.Qt.LeftToRight)

def apply_to_home(cfg: Dict[str, object], home_widget: QtWidgets.QWidget):
    # Chatbot (Gemma)
    bot = getattr(home_widget, "chatbot", None)
    if bot and hasattr(bot, "set_llm_enabled"):
        bot.set_llm_enabled(bool(cfg.get("ai/enabled", True)))
    # If your ChatBotTab exposes model settings, pass them through safely
    if bot and hasattr(bot, "set_model_config"):
        bot.set_model_config({
            "model_path": cfg.get("ai/model_path", ""),
            "max_new_tokens": int(cfg.get("ai/max_tokens", 240)),
            "temperature": float(cfg.get("ai/temperature", 0.6)),
        })

    # Appointments defaults (only if the tab exposes these hooks)
    if hasattr(home_widget, "set_appointments_defaults"):
        home_widget.set_appointments_defaults({
            "default_len": int(cfg.get("appts/default_len", 30)),
            "day_start": str(cfg.get("appts/day_start", "07:00")),
            "day_end": str(cfg.get("appts/day_end", "21:00")),
            "week_starts": str(cfg.get("appts/week_starts", "Mon")),
        })

    # Billing context for Accounts tab (if available)
    if hasattr(home_widget, "set_billing_context"):
        home_widget.set_billing_context({
            "currency": str(cfg.get("bill/currency", "USD")),
            "tax_pct": float(cfg.get("bill/tax_pct", 0.0)),
            "default_method": str(cfg.get("bill/default_method", "Cash")),
        })

def schedule_daily_summary(cfg: Dict[str, object], parent: QtCore.QObject, callback):
    # cancel existing timer if any
    t = getattr(parent, "_daily_summary_timer", None)
    if t:
        t.stop()
        t.deleteLater()
        setattr(parent, "_daily_summary_timer", None)

    hhmm = str(cfg.get("notify/daily_time", "09:00"))
    try:
        h, m = [int(x) for x in hhmm.split(":", 1)]
    except Exception:
        h, m = 9, 0

    timer = QtCore.QTimer(parent)
    timer.setSingleShot(False)

    def _arm():
        now = QtCore.QTime.currentTime()
        target = QtCore.QTime(h, m)
        ms = now.msecsTo(target)
        if ms <= 0:
            ms += 24 * 60 * 60 * 1000
        QtCore.QTimer.singleShot(ms, lambda: (callback(), timer.start(24*60*60*1000)))

    _arm()
    setattr(parent, "_daily_summary_timer", timer)
