# agent_viewer.py
from collections import deque
from PyQt5 import QtWidgets, QtCore
from native_tools import open_native, notify


class AgentWorker(QtCore.QThread):
    finished_ok = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, agent, plan, ctx):
        super().__init__()
        self.agent = agent
        self.plan = plan
        self.ctx = dict(ctx or {})

    def run(self):
        try:
            out = self.agent.run_plan(self.plan, self.ctx)
            self.finished_ok.emit(out)
        except Exception as e:
            self.failed.emit(str(e))


class AgentRunDialog(QtWidgets.QDialog):
    def __init__(self, agent, plan, ctx, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.plan = plan
        self.ctx = dict(ctx or {})
        self.setWindowTitle("Agent Run")
        self.resize(650, 480)

        # --- drip logging state ---
        self._pending_lines = deque()
        self._log_timer = QtCore.QTimer(self)
        self._log_timer.setInterval(700)  # 0.7 second per line
        self._log_timer.timeout.connect(self._drain_log_queue)

        self._files_row_widget = None  # dynamic row with "Open PDF/JSON" buttons

        # ---- UI ----
        v = QtWidgets.QVBoxLayout(self)
        self.log_view = QtWidgets.QTextEdit(readOnly=True)
        v.addWidget(self.log_view)

        btns = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("Run plan")
        self.btn_close = QtWidgets.QPushButton("Close")
        btns.addWidget(self.btn_run)
        btns.addStretch(1)
        btns.addWidget(self.btn_close)
        v.addLayout(btns)

        self.btn_close.clicked.connect(self.close)
        self.btn_run.clicked.connect(self._run)

        # Wire agent logs into the drip queue
        try:
            self.agent.log.connect(self._enqueue_log)
            self.agent.step_started.connect(lambda n: self._enqueue_log(f"--- {n} START ---"))
            self.agent.step_finished.connect(lambda n, r: self._enqueue_log(f"--- {n} END ---\n{r}\n"))
            self.agent.errored.connect(self._enqueue_log)
        except Exception:
            # If signals aren’t present, skip wiring.
            pass

    # ---------- drip logging ----------
    def _enqueue_log(self, msg: str):
        """
        Queue message(s) for paced display.
        Splits on newlines so each line is shown with the 0.7s cadence.
        """
        text = "" if msg is None else str(msg)
        for line in text.splitlines() or [""]:
            self._pending_lines.append(line)
        if not self._log_timer.isActive():
            self._log_timer.start()

    def _drain_log_queue(self):
        if self._pending_lines:
            line = self._pending_lines.popleft()
            self.log_view.append(line)
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
        else:
            self._log_timer.stop()

    def _clear_files_row(self):
        if self._files_row_widget is not None:
            self.layout().removeWidget(self._files_row_widget)
            self._files_row_widget.deleteLater()
            self._files_row_widget = None

    # ---------- run flow ----------
    def _run(self):
        self.btn_run.setEnabled(False)
        self._enqueue_log("Running plan…")
        self._clear_files_row()

        self.worker = AgentWorker(self.agent, self.plan, dict(self.ctx))
        self.worker.finished_ok.connect(self._done)
        self.worker.failed.connect(self._fail)
        self.worker.start()

    def _done(self, ctx_out: dict):
        self._enqueue_log("")  # blank spacer
        self._enqueue_log("✅ PLAN COMPLETE")

        # Report created files (if any)
        pdf = ctx_out.get("pdf_path")
        jsn = ctx_out.get("json_path")
        if pdf:
            self._enqueue_log(f"PDF: {pdf}")
        if jsn:
            self._enqueue_log(f"JSON: {jsn}")

        # Fresh row of buttons to open files
        self._clear_files_row()
        if pdf or jsn:
            row = QtWidgets.QWidget(self)
            h = QtWidgets.QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            if pdf:
                btn_pdf = QtWidgets.QPushButton("Open PDF")
                btn_pdf.clicked.connect(lambda: open_native(pdf, self))
                h.addWidget(btn_pdf)
            if jsn:
                btn_json = QtWidgets.QPushButton("Open JSON")
                btn_json.clicked.connect(lambda: open_native(jsn, self))
                h.addWidget(btn_json)
            h.addStretch(1)
            self.layout().addWidget(row)
            self._files_row_widget = row

            # Native toast (immediate)
            paths = [p for p in (pdf, jsn) if p]
            notify(self, "Agent", "Created:\n" + "\n".join(paths))

        self.btn_run.setEnabled(True)

    def _fail(self, err: str):
        self._enqueue_log(f"❌ FAILED: {err}")
        QtWidgets.QMessageBox.critical(self, "Agent", err)
        self.btn_run.setEnabled(True)