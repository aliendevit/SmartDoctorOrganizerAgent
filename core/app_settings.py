# core/app_settings.py
from __future__ import annotations
from PyQt5 import QtCore, QtGui, QtWidgets
from typing import Optional, Dict

ORG = "Innova"
APP = "MedicalDocAI"

def qsettings() -> QtCore.QSettings:
    return QtCore.QSettings(ORG, APP)

# Same keys used in Tabs/settings_tab.py
DEFAULTS = {
    "clinic/name": "",
    "clinic/phone": "",
    "clinic/email": "",
    "clinic/address": "",
    "clinic/logo": "",
    "clinic/timezone": "UTC",
    "clinic/datetime_fmt": "dd-MM-yyyy hh:mm AP",

    "ui/theme": "Light",
    "ui/base_pt": 11,
    "ui/accent": "#3A8DFF",
    "ui/glassy": True,

    "ai/enabled": True,
    "ai/model_path": "",
    "ai/max_tokens": 240,
    "ai/temperature": 0.6,
    "ai/autostart": True,

    "appts/default_len": 30,
    "appts/day_start": "07:00",
    "appts/day_end": "21:00",
    "appts/week_starts": "Mon",

    "bill/currency": "USD",
    "bill/tax_pct": 0.0,
    "bill/default_method": "Cash",

    "notify/toasts": True,
    "notify/daily_time": "09:00",

    "lang/code": "en",
    "lang/rtl": False,
}

def read_all() -> Dict[str, object]:
    s = qsettings()
    out = {}
    for k, dv in DEFAULTS.items():
        out[k] = s.value(k, dv)
    # normalize a few types:
    out["ui/base_pt"] = int(out["ui/base_pt"])
    out["ai/enabled"] = str(out["ai/enabled"]).lower() in ("1","true","yes")
    out["ai/max_tokens"] = int(float(out["ai/max_tokens"]))
    out["ai/temperature"] = float(out["ai/temperature"])
    out["ai/autostart"] = str(out["ai/autostart"]).lower() in ("1","true","yes")
    out["appts/default_len"] = int(float(out["appts/default_len"]))
    out["bill/tax_pct"] = float(out["bill/tax_pct"])
    out["notify/toasts"] = str(out["notify/toasts"]).lower() in ("1","true","yes")
    out["lang/rtl"] = str(out["lang/rtl"]).lower() in ("1","true","yes")
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
