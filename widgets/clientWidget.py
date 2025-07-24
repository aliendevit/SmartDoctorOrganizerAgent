# widgets/clientWidget.py
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import os, datetime

# Optional native helpers (open file / notify). Fall back if not present.
try:
    from native_tools import open_native, notify
except Exception:
    def open_native(path, parent=None):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
    def notify(parent, title, msg):
        QtWidgets.QMessageBox.information(parent, title, msg)

# data layer
try:
    from data.data import update_account_in_db
except Exception:
    def update_account_in_db(name, payload): return False

def _tr(s):
    try:
        from features.translation_helper import tr
        return tr(s)
    except Exception:
        return s

_RED_FLAG_TERMS = [
    "severe chest pain","shortness of breath","vision loss","worst headache",
    "stroke","facial droop","weakness one side","uncontrolled bleeding",
    "anaphylaxis","airway compromise","loss of consciousness"
]

_QUICK_CHIPS = [
    "No acute distress.",
    "Stable; continue current meds.",
    "Start antibiotics today.",
    "Discussed risks/benefits.",
    "Return if fever or worsening.",
    "Follow‑up in 1 week.",
]

def _has_red_flags(text: str) -> bool:
    t = (text or "").lower()
    return any(term in t for term in _RED_FLAG_TERMS)

class ClientAccountPage(QtWidgets.QDialog):
    """
    Modern patient profile with:
      - Photo timeline
      - Quick note chips
      - Red‑flag indicator
      - Export PDF / Share
      - Optional voice-to-notes
    """
    def __init__(self, client=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_tr("Client Account"))
        self.resize(860, 620)
        self.client = dict(client or {})
        self._build()
        self._refresh_ui_from_client()

    # ---------- UI ----------
    def _build(self):
        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(14,14,14,14); v.setSpacing(10)

        # Top bar with name + red‑flag pill
        top = QtWidgets.QHBoxLayout()
        self.title_lbl = QtWidgets.QLabel("—")
        self.title_lbl.setStyleSheet("font: 700 18pt 'Segoe UI';")
        self.flag_lbl = QtWidgets.QLabel("")  # shown only if flags
        self.flag_lbl.setStyleSheet("padding:4px 8px; border-radius:10px; background:#fef3c7; color:#92400e; font-weight:600;")
        self.flag_lbl.setVisible(False)
        top.addWidget(self.title_lbl); top.addStretch(1); top.addWidget(self.flag_lbl)
        v.addLayout(top)

        # Card with left (photo timeline) + right (form)
        card = QtWidgets.QFrame(); card.setProperty("modernCard", True)
        split = QtWidgets.QSplitter(Qt.Horizontal, card); split.setChildrenCollapsible(False)
        split.setSizes([300, 540])

        # ----- LEFT: Photos -----
        left = QtWidgets.QWidget()
        lly = QtWidgets.QVBoxLayout(left); lly.setContentsMargins(12,12,12,12); lly.setSpacing(8)

        self.photo_big = QtWidgets.QLabel()
        self.photo_big.setFixedSize(260, 200)
        self.photo_big.setAlignment(Qt.AlignCenter)
        self.photo_big.setStyleSheet("border-radius:12px;")
        self.photo_big.setScaledContents(True)
        lly.addWidget(self.photo_big, alignment=Qt.AlignCenter)

        self.thumb_list = QtWidgets.QListWidget()
        self.thumb_list.setIconSize(QtCore.QSize(84, 84))
        self.thumb_list.setViewMode(QtWidgets.QListView.IconMode)
        self.thumb_list.setResizeMode(QtWidgets.QListView.Adjust)
        self.thumb_list.setMovement(QtWidgets.QListView.Static)
        self.thumb_list.setSpacing(8)
        self.thumb_list.itemSelectionChanged.connect(self._on_thumb_selected)
        lly.addWidget(self.thumb_list, 1)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add_photo = QtWidgets.QPushButton(_tr("Add Photo…"))
        self.btn_add_photo.setProperty("variant","ghost")
        self.btn_add_photo.clicked.connect(self._add_photo)
        self.btn_open_photo = QtWidgets.QPushButton(_tr("Open"))
        self.btn_open_photo.setProperty("variant","ghost")
        self.btn_open_photo.clicked.connect(lambda: open_native(self._current_photo_path(), self))
        btn_row.addWidget(self.btn_add_photo); btn_row.addWidget(self.btn_open_photo); btn_row.addStretch(1)
        lly.addLayout(btn_row)

        # ----- RIGHT: Info form -----
        right = QtWidgets.QWidget()
        rly = QtWidgets.QVBoxLayout(right); rly.setContentsMargins(12,12,12,12); rly.setSpacing(8)

        form = QtWidgets.QFormLayout(); form.setLabelAlignment(Qt.AlignLeft); form.setSpacing(6)
        self.name_edit = QtWidgets.QLineEdit()
        self.age_spin  = QtWidgets.QSpinBox(); self.age_spin.setRange(0, 120)

        self.paid_spin = QtWidgets.QDoubleSpinBox();  self.paid_spin.setRange(0,1e9);  self.paid_spin.setDecimals(2)
        self.owed_spin = QtWidgets.QDoubleSpinBox();  self.owed_spin.setRange(0,1e9);  self.owed_spin.setDecimals(2)
        self.total_spin= QtWidgets.QDoubleSpinBox();  self.total_spin.setRange(0,1e9); self.total_spin.setDecimals(2)

        # Quick chips row
        chip_wrap = QtWidgets.QWidget(); chip_l = QtWidgets.QHBoxLayout(chip_wrap); chip_l.setContentsMargins(0,0,0,0)
        for txt in _QUICK_CHIPS:
            b = QtWidgets.QPushButton(txt); b.setProperty("variant","ghost")
            b.clicked.connect(lambda _, t=txt: self._append_note(t))
            chip_l.addWidget(b)
        chip_l.addStretch(1)

        self.notes_edit = QtWidgets.QTextEdit(); self.notes_edit.setFixedHeight(120)

        form.addRow(_tr("Name"), self.name_edit)
        form.addRow(_tr("Age"),  self.age_spin)
        form.addRow(_tr("Total Paid"), self.paid_spin)
        form.addRow(_tr("Owed"), self.owed_spin)
        form.addRow(_tr("Total Amount"), self.total_spin)
        rly.addLayout(form)
        rly.addWidget(chip_wrap)
        rly.addWidget(QtWidgets.QLabel(_tr("Notes")))
        rly.addWidget(self.notes_edit, 1)

        # Actions: Export / Share / Save / Cancel (+ optional Voice)
        actions = QtWidgets.QHBoxLayout()
        self.btn_export = QtWidgets.QPushButton(_tr("Export PDF"))
        self.btn_export.setProperty("variant","info")
        self.btn_export.clicked.connect(self._export_pdf)

        self.btn_share = QtWidgets.QPushButton(_tr("Share Summary"))
        self.btn_share.setProperty("variant","ghost")
        self.btn_share.clicked.connect(self._share_summary)

        self.btn_voice = QtWidgets.QPushButton(_tr("Voice → Notes"))
        self.btn_voice.setProperty("variant","ghost")
        self.btn_voice.clicked.connect(self._voice_to_notes)
        self.btn_voice.setVisible(self._speech_available())

        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_share)
        actions.addWidget(self.btn_voice)
        actions.addStretch(1)

        self.cancel_btn = QtWidgets.QPushButton(_tr("Cancel")); self.cancel_btn.setProperty("variant","ghost")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn   = QtWidgets.QPushButton(_tr("Save"))
        self.save_btn.clicked.connect(self._on_save)
        actions.addWidget(self.cancel_btn); actions.addWidget(self.save_btn)

        rly.addLayout(actions)

        split.addWidget(left); split.addWidget(right)

        lay_card = QtWidgets.QVBoxLayout(card); lay_card.setContentsMargins(8,8,8,8); lay_card.addWidget(split)
        v.addWidget(card)

        # style
        self.setStyleSheet("""
        QWidget { font-family: 'Segoe UI', Arial; font-size: 14px; }
        QFrame[modernCard="true"] { background:#0f172a; border:1px solid #1f2937; border-radius:12px; }
        QLabel { color:#e5e7eb; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
            background:#0b1020; color:#e5e7eb; border:1px solid #1f2937; border-radius:8px; padding:6px 8px;
        }
        QListWidget { background:#0b1020; color:#e5e7eb; border:1px solid #1f2937; border-radius:8px; }
        QPushButton { background:#0ea5e9; color:white; border:none; border-radius:8px; padding:8px 14px; font-weight:600; }
        QPushButton[variant="ghost"] { background:#0b1020; color:#cbd5e1; border:1px solid #1f2937; }
        QPushButton[variant="info"] { background:#22c55e; }
        QPushButton[variant="danger"] { background:#ef4444; }
        QPushButton:hover { filter:brightness(1.08); }
        """)

        # Wiring
        self.thumb_list.itemSelectionChanged.connect(self._on_thumb_selected)

    # ---------- data wiring ----------
    def _refresh_ui_from_client(self):
        name = self.client.get("Name","").strip() or "—"
        self.title_lbl.setText(name)
        self.name_edit.setText(self.client.get("Name",""))
        self.age_spin.setValue(int(self.client.get("Age", 0)))
        self.paid_spin.setValue(float(self.client.get("Total Paid", 0)))
        self.owed_spin.setValue(float(self.client.get("Owed", 0)))
        self.total_spin.setValue(float(self.client.get("Total Amount", 0)))
        self.notes_edit.setPlainText(self.client.get("Notes", ""))

        # Red‑flag pill visibility
        self.flag_lbl.setVisible(_has_red_flags(self.notes_edit.toPlainText()))

        # Photos: support legacy single "Image" and new list "Photos"
        photos = []
        legacy = (self.client.get("Image") or "").strip()
        if legacy:
            photos.append({"path": legacy, "date": ""})
        for p in (self.client.get("Photos") or []):
            if isinstance(p, dict) and p.get("path"):
                photos.append(p)
            elif isinstance(p, str):
                photos.append({"path": p, "date": ""})
        self._set_thumbs(photos)

    # ---------- photos ----------
    def _set_thumbs(self, photos: list):
        self._photos = list(photos or [])
        self.thumb_list.clear()
        if not self._photos:
            self.photo_big.setPixmap(self._placeholder(260, 200, "No\nPhoto"))
            return
        for rec in self._photos:
            path = rec.get("path", "")
            item = QtWidgets.QListWidgetItem()
            item.setText(os.path.basename(path) if path else "—")
            if path and os.path.exists(path):
                icon = QtGui.QIcon(QtGui.QPixmap(path).scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                icon = QtGui.QIcon(self._placeholder(84, 84, "X"))
            item.setIcon(icon)
            item.setData(Qt.UserRole, path)
            self.thumb_list.addItem(item)
        self.thumb_list.setCurrentRow(0)
        self._update_big_photo()

    def _on_thumb_selected(self):
        self._update_big_photo()

    def _update_big_photo(self):
        path = self._current_photo_path()
        if path and os.path.exists(path):
            self.photo_big.setPixmap(QtGui.QPixmap(path).scaled(260, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.photo_big.setPixmap(self._placeholder(260, 200, "No\nPhoto"))

    def _current_photo_path(self):
        it = self.thumb_list.currentItem()
        return it.data(Qt.UserRole) if it else ""

    # ---------- notes / chips ----------
    def _append_note(self, text):
        cur = self.notes_edit.toPlainText().rstrip()
        self.notes_edit.setPlainText((cur + ("\n" if cur else "") + text).strip())
        self.notes_edit.moveCursor(QtGui.QTextCursor.End)
        self.flag_lbl.setVisible(_has_red_flags(self.notes_edit.toPlainText()))

    # ---------- add photo ----------
    def _add_photo(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, _tr("Choose photo"), "",
                                                        "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        stamp = datetime.datetime.now().strftime("%d-%m-%Y")
        photos = list(self.client.get("Photos") or [])
        photos.append({"path": path, "date": stamp, "tag": ""})
        self.client["Photos"] = photos
        if not self.client.get("Image"):
            self.client["Image"] = path  # keep legacy single preview
        self._refresh_ui_from_client()

    # ---------- share / export ----------
    def _share_summary(self):
        # Simple, local-friendly handoff (WhatsApp Web or default handler)
        name = self.name_edit.text().strip() or "Patient"
        msg = f"{name} — summary:\n" \
              f"Paid: {self.paid_spin.value():.2f} / Total: {self.total_spin.value():.2f}\n" \
              f"Notes: {self.notes_edit.toPlainText().strip()[:240]}"
        url = QtCore.QUrl(f"https://wa.me/?text={QtCore.QUrl.toPercentEncoding(msg).data().decode('utf-8')}")
        QtGui.QDesktopServices.openUrl(url)

    def _export_pdf(self):
        # Try your agent pipeline if available; otherwise fall back to JSON snapshot
        try:
            from agents.agent_core import Agent, AgentPlan
            from agents.agent_actions import register_actions
            agent = Agent(self);
            register_actions(agent)
            plan = AgentPlan("Patient passport", ["make_pdf"])
            ctx = {"data": self._collect_payload()}
            out = agent.run_plan(plan, ctx)
            pdf = out.get("pdf_path")
            if pdf:
                notify(self, _tr("Export"), _tr("PDF created:\n") + pdf)
                open_native(pdf, self)
                return
        except Exception:
            pass
        # Fallback: save JSON to Desktop/reports
        try:
            import json
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            out_dir = os.path.join(desktop, "reports");
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, (self.name_edit.text().strip() or "Unknown") + "_report.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_payload(), f, indent=2, ensure_ascii=False)
            notify(self, _tr("Export"), _tr("Saved JSON:\n") + path)
            open_native(path, self)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _tr("Export"), str(e))

    # ---------- save ----------
    def _on_save(self):
        payload = self._collect_payload()
        update_account_in_db(payload["Name"], payload)
        self.accept()

    def _collect_payload(self):
        out = dict(self.client)
        out.update({
            "Name": self.name_edit.text().strip() or "Unknown",
            "Age": int(self.age_spin.value()),
            "Total Paid": float(self.paid_spin.value()),
            "Owed": float(self.owed_spin.value()),
            "Total Amount": float(self.total_spin.value()),
            "Notes": self.notes_edit.toPlainText().strip(),
        })
        # persist photos
        if hasattr(self, "_photos"):
            out["Photos"] = self._photos
        # keep legacy single image for quick checks
        if not out.get("Image") and out.get("Photos"):
            try:
                out["Image"] = out["Photos"][0]["path"]
            except Exception:
                pass
        return out

    # ---------- utils ----------
    def _placeholder(self, w, h, text=""):
        pm = QtGui.QPixmap(w, h);
        pm.fill(QtGui.QColor("#1f2937"))
        p = QtGui.QPainter(pm);
        p.setPen(QtGui.QColor("#9ca3af"))
        p.drawText(pm.rect(), Qt.AlignCenter, text);
        p.end()
        return pm

    # ---------- voice (optional) ----------
    def _speech_available(self):
        try:
            import speech_recognition  # noqa
            return True
        except Exception:
            return False

    def _voice_to_notes(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                QtWidgets.QMessageBox.information(self, _tr("Voice"), _tr("Speak…"))
                audio = r.listen(source, timeout=6, phrase_time_limit=30)
            text = r.recognize_google(audio, language="en-US")
            self._append_note(text)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, _tr("Voice"), _tr("Voice input unavailable: ") + str(e))

    # For compatibility with AccountsTab logic
    def get_updated_client(self):
        return self._collect_payload()