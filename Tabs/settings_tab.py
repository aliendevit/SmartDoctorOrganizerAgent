# Tabs/settings_tab.py
from __future__ import annotations
from PyQt5 import QtCore, QtGui, QtWidgets
from typing import Dict, Any
from core import app_settings as AS

class SettingsTab(QtWidgets.QWidget):
    themeChanged        = QtCore.pyqtSignal(dict)
    llmEnabledChanged   = QtCore.pyqtSignal(bool)
    appointmentsChanged = QtCore.pyqtSignal(dict)
    billingChanged      = QtCore.pyqtSignal(dict)
    notificationsChanged= QtCore.pyqtSignal(dict)
    languageChanged     = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("modernCard", False)
        self._building = True
        self._build_ui()
        self._load()
        self._building = False

    # ---------- helpers ----------
    def _card(self, title: str) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox(title)
        g.setProperty("modernCard", True)
        g.setLayout(QtWidgets.QFormLayout())
        g.layout().setLabelAlignment(QtCore.Qt.AlignLeft)
        g.layout().setFormAlignment(QtCore.Qt.AlignTop)
        g.layout().setHorizontalSpacing(14)
        g.layout().setVerticalSpacing(8)
        g.layout().setContentsMargins(12, 12, 12, 12)
        return g

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 1) Clinic profile
        self.card_clinic = self._card("Clinic profile")
        self.ed_name    = QtWidgets.QLineEdit()
        self.ed_phone   = QtWidgets.QLineEdit()
        self.ed_email   = QtWidgets.QLineEdit()
        self.ed_address = QtWidgets.QLineEdit()
        self.ed_logo    = QtWidgets.QLineEdit(); self.ed_logo.setReadOnly(True)
        btn_logo = QtWidgets.QPushButton("Browse…"); btn_logo.setProperty("variant", "ghost")
        btn_logo.clicked.connect(self._pick_logo)
        logo_row = QtWidgets.QHBoxLayout(); logo_row.addWidget(self.ed_logo, 1); logo_row.addWidget(btn_logo)
        self.cmb_tz = QtWidgets.QComboBox(); self.cmb_tz.addItems(["UTC","Africa/Cairo","Europe/Berlin","Europe/London","America/New_York","Asia/Dubai"])
        self.ed_fmt = QtWidgets.QLineEdit("dd-MM-yyyy hh:mm AP")
        f = self.card_clinic.layout()
        f.addRow("Clinic name", self.ed_name)
        f.addRow("Phone", self.ed_phone)
        f.addRow("Email", self.ed_email)
        f.addRow("Address", self.ed_address)
        f.addRow("Logo", logo_row)
        f.addRow("Default timezone", self.cmb_tz)
        f.addRow("Date/time format", self.ed_fmt)

        # 2) Appearance
        self.card_ui = self._card("Appearance")
        self.cmb_theme = QtWidgets.QComboBox(); self.cmb_theme.addItems(["Light"])
        self.spin_base = QtWidgets.QSpinBox(); self.spin_base.setRange(9, 18)
        self.btn_accent= QtWidgets.QPushButton("Pick color…"); self.btn_accent.setProperty("variant","ghost")
        self.lbl_accent= QtWidgets.QLabel("#3A8DFF"); self.lbl_accent.setMinimumWidth(80)
        self.chk_glass = QtWidgets.QCheckBox("Glassy panels")
        accent_row = QtWidgets.QHBoxLayout(); accent_row.addWidget(self.lbl_accent); accent_row.addStretch(1); accent_row.addWidget(self.btn_accent)
        fu = self.card_ui.layout()
        fu.addRow("Theme", self.cmb_theme)
        fu.addRow("Base font size", self.spin_base)
        fu.addRow("Accent color", accent_row)
        fu.addRow("", self.chk_glass)
        self.btn_accent.clicked.connect(self._pick_accent)

        # 3) Assistant (Gemma)
        self.card_ai = self._card("Assistant (Gemma)")
        self.chk_ai   = QtWidgets.QCheckBox("Enable local LLM")
        self.ed_model = QtWidgets.QLineEdit(); self.ed_model.setPlaceholderText("Path to model")
        btn_model = QtWidgets.QPushButton("Browse…"); btn_model.setProperty("variant","ghost")
        btn_model.clicked.connect(self._pick_model)
        md = QtWidgets.QHBoxLayout(); md.addWidget(self.ed_model, 1); md.addWidget(btn_model)
        self.spin_max  = QtWidgets.QSpinBox(); self.spin_max.setRange(32, 4096)
        self.dbl_temp  = QtWidgets.QDoubleSpinBox(); self.dbl_temp.setRange(0.0, 2.0); self.dbl_temp.setSingleStep(0.05)
        self.chk_autostart = QtWidgets.QCheckBox("Start assistant on launch")
        fa = self.card_ai.layout()
        fa.addRow("", self.chk_ai)
        fa.addRow("Model path", md)
        fa.addRow("Max tokens", self.spin_max)
        fa.addRow("Temperature", self.dbl_temp)
        fa.addRow("", self.chk_autostart)

        # 4) Appointments
        self.card_appt = self._card("Appointments")
        self.spin_len   = QtWidgets.QSpinBox(); self.spin_len.setRange(5, 180)
        self.ed_day_start = QtWidgets.QTimeEdit(QtCore.QTime(7,0));  self.ed_day_start.setDisplayFormat("HH:mm")
        self.ed_day_end   = QtWidgets.QTimeEdit(QtCore.QTime(21,0)); self.ed_day_end.setDisplayFormat("HH:mm")
        self.cmb_week   = QtWidgets.QComboBox(); self.cmb_week.addItems(["Sun","Mon"])
        fp = self.card_appt.layout()
        fp.addRow("Default visit length (mins)", self.spin_len)
        fp.addRow("Scheduling window start", self.ed_day_start)
        fp.addRow("Scheduling window end",   self.ed_day_end)
        fp.addRow("First day of week", self.cmb_week)

        # 5) Billing & currency
        self.card_bill = self._card("Billing & currency")
        self.cmb_curr = QtWidgets.QComboBox(); self.cmb_curr.addItems(["USD","EUR","EGP","GBP","SAR","AED"])
        self.dbl_tax  = QtWidgets.QDoubleSpinBox(); self.dbl_tax.setRange(0.0, 100.0); self.dbl_tax.setSuffix(" %")
        self.cmb_method = QtWidgets.QComboBox(); self.cmb_method.addItems(["Cash","Card","Wire","Insurance"])
        fb = self.card_bill.layout()
        fb.addRow("Currency", self.cmb_curr)
        fb.addRow("Tax %", self.dbl_tax)
        fb.addRow("Default payment method", self.cmb_method)

        # 6) Notifications
        self.card_not = self._card("Notifications")
        self.chk_toast = QtWidgets.QCheckBox("Desktop toasts on new/updated appointment")
        self.ed_daily  = QtWidgets.QTimeEdit(QtCore.QTime(9,0)); self.ed_daily.setDisplayFormat("HH:mm")
        fn = self.card_not.layout()
        fn.addRow("", self.chk_toast)
        fn.addRow("Daily summary time", self.ed_daily)

        # 7) Language
        self.card_lang = self._card("Language")
        self.cmb_lang = QtWidgets.QComboBox(); self.cmb_lang.addItems(["en","ar","de","es","fr"])
        self.chk_rtl  = QtWidgets.QCheckBox("Enable RTL layout")
        fl = self.card_lang.layout()
        fl.addRow("App language", self.cmb_lang)
        fl.addRow("", self.chk_rtl)

        self.cmb_compute = QtWidgets.QComboBox()
        self.cmb_compute.addItems(["auto", "gpu", "cpu"])
        self.cmb_compute.addItem("GPU", "gpu")
        self.cmb_compute.addItem("CPU", "cpu")
        fa.addRow("Compute mode", self.cmb_compute)  # add to the Assistant card
        # Buttons
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        self.btn_save = QtWidgets.QPushButton("Save")
        self.btn_save.clicked.connect(self._save)
        btns.addWidget(self.btn_save)

        # Layout
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12); grid.setVerticalSpacing(12)
        grid.addWidget(self.card_clinic, 0, 0)
        grid.addWidget(self.card_ui,     0, 1)
        grid.addWidget(self.card_ai,     1, 0)
        grid.addWidget(self.card_appt,   1, 1)
        grid.addWidget(self.card_bill,   2, 0)
        grid.addWidget(self.card_not,    2, 1)
        grid.addWidget(self.card_lang,   3, 0, 1, 2)

        root.addLayout(grid, 1)
        root.addLayout(btns)

    # ---------- pickers ----------
    def _pick_logo(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Pick logo", "", "Images (*.png *.jpg *.jpeg *.svg)")
        if path:
            self.ed_logo.setText(path)

    def _pick_model(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Pick model file", "", "All files (*)")
        if path:
            self.ed_model.setText(path)

    def _pick_accent(self):
        col = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.lbl_accent.text()), self, "Pick accent color")
        if col.isValid():
            self.lbl_accent.setText(col.name())

    # ---------- load/save ----------
    def _load(self):
        cfg = AS.read_all()

        self.ed_name.setText(cfg.get("clinic/name", ""))
        self.ed_phone.setText(cfg.get("clinic/phone", ""))
        self.ed_email.setText(cfg.get("clinic/email", ""))
        self.ed_address.setText(cfg.get("clinic/address", ""))
        self.ed_logo.setText(cfg.get("clinic/logo", ""))

        idx = max(0, self.cmb_tz.findText(cfg.get("clinic/timezone", "UTC")))
        self.cmb_tz.setCurrentIndex(idx)
        self.ed_fmt.setText(cfg.get("clinic/datetime_fmt", "dd-MM-yyyy hh:mm AP"))

        self.spin_base.setValue(int(cfg.get("ui/base_pt", 11)))
        self.lbl_accent.setText(str(cfg.get("ui/accent", "#3A8DFF")))
        self.chk_glass.setChecked(bool(cfg.get("ui/glassy", True)))

        self.chk_ai.setChecked(bool(cfg.get("ai/enabled", False)))
        self.ed_model.setText(str(cfg.get("ai/model_path", "")))
        self.spin_max.setValue(int(cfg.get("ai/max_tokens", 220)))
        self.dbl_temp.setValue(float(cfg.get("ai/temperature", 0.1)))
        self.chk_autostart.setChecked(bool(cfg.get("ai/autostart", False)))

        self.spin_len.setValue(int(cfg.get("appts/default_len", 30)))
        self.ed_day_start.setTime(QtCore.QTime.fromString(str(cfg.get("appts/day_start", "07:00")), "HH:mm"))
        self.ed_day_end.setTime(QtCore.QTime.fromString(str(cfg.get("appts/day_end", "21:00")), "HH:mm"))
        idx = max(0, self.cmb_week.findText(str(cfg.get("appts/week_starts", "Sun"))))
        self.cmb_week.setCurrentIndex(idx)

        self.cmb_curr.setCurrentText(str(cfg.get("bill/currency", "USD")))
        self.dbl_tax.setValue(float(cfg.get("bill/tax_pct", 0.0)))
        self.cmb_method.setCurrentText(str(cfg.get("bill/default_method", "Cash")))

        self.chk_toast.setChecked(bool(cfg.get("notify/toasts", True)))
        self.ed_daily.setTime(QtCore.QTime.fromString(str(cfg.get("notify/daily_time", "09:00")), "HH:mm"))

        self.cmb_lang.setCurrentText(str(cfg.get("lang/code", "en")))
        self.chk_rtl.setChecked(bool(cfg.get("lang/rtl", False)))

        self.cmb_compute.setCurrentText(str(cfg.get("ai/compute_mode", "auto")))

    def _save(self):
        s = AS.qsettings()
        s.setValue("clinic/name", self.ed_name.text().strip())
        s.setValue("clinic/phone", self.ed_phone.text().strip())
        s.setValue("clinic/email", self.ed_email.text().strip())
        s.setValue("clinic/address", self.ed_address.text().strip())
        s.setValue("clinic/logo", self.ed_logo.text().strip())
        s.setValue("clinic/timezone", self.cmb_tz.currentText())
        s.setValue("clinic/datetime_fmt", self.ed_fmt.text().strip())

        s.setValue("ui/theme", self.cmb_theme.currentText())
        s.setValue("ui/base_pt", self.spin_base.value())
        s.setValue("ui/accent", self.lbl_accent.text())
        s.setValue("ui/glassy", self.chk_glass.isChecked())

        s.setValue("ai/compute_mode", self.cmb_compute.currentText())

        s.setValue("ai/enabled", self.chk_ai.isChecked())
        s.setValue("ai/model_path", self.ed_model.text().strip())
        s.setValue("ai/max_tokens", self.spin_max.value())
        s.setValue("ai/temperature", self.dbl_temp.value())
        s.setValue("ai/autostart", self.chk_autostart.isChecked())

        s.setValue("appts/default_len", self.spin_len.value())
        s.setValue("appts/day_start", self.ed_day_start.time().toString("HH:mm"))
        s.setValue("appts/day_end", self.ed_day_end.time().toString("HH:mm"))
        s.setValue("appts/week_starts", self.cmb_week.currentText())

        s.setValue("bill/currency", self.cmb_curr.currentText())
        s.setValue("bill/tax_pct", self.dbl_tax.value())
        s.setValue("bill/default_method", self.cmb_method.currentText())

        s.setValue("notify/toasts", self.chk_toast.isChecked())
        s.setValue("notify/daily_time", self.ed_daily.time().toString("HH:mm"))

        s.setValue("lang/code", self.cmb_lang.currentText())
        s.setValue("lang/rtl", self.chk_rtl.isChecked())

        s.sync()

        cfg = AS.read_all()
        self.themeChanged.emit({"base_point_size": cfg["ui/base_pt"],
                                "accent": cfg["ui/accent"],
                                "glassy": cfg["ui/glassy"]})
        self.llmEnabledChanged.emit(bool(cfg["ai/enabled"]))
        self.appointmentsChanged.emit({
            "default_len": cfg["appts/default_len"],
            "day_start": cfg["appts/day_start"],
            "day_end": cfg["appts/day_end"],
            "week_starts": cfg["appts/week_starts"],
        })
        self.billingChanged.emit({
            "currency": cfg["bill/currency"],
            "tax_pct": cfg["bill/tax_pct"],
            "default_method": cfg["bill/default_method"],
        })
        self.notificationsChanged.emit({
            "toasts": cfg["notify/toasts"],
            "daily_time": cfg["notify/daily_time"],
        })
        self.languageChanged.emit({
            "code": cfg["lang/code"],
            "rtl":  cfg["lang/rtl"],
        })

        QtWidgets.QMessageBox.information(self, "Settings", "Saved.")