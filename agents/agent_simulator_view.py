# agent_simulator_view.py
from PyQt5 import QtWidgets, QtCore, QtGui
from agent_core import Agent, AgentPlan
from native_tools import open_native, notify

class _Typer(QtCore.QObject):
    """Appends queued lines to a QTextEdit with a fixed delay (default 700ms)."""
    def __init__(self, text_edit: QtWidgets.QTextEdit, delay_ms=700, parent=None):
        super().__init__(parent)
        self._edit = text_edit
        self._delay = int(delay_ms)
        self._queue = []
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)

    def add_lines(self, lines):
        if isinstance(lines, str):
            lines = [lines]
        self._queue.extend([str(l) for l in lines])
        if not self._timer.isActive():
            self._timer.start(self._delay)

    def _tick(self):
        if not self._queue:
            self._timer.stop()
            return
        line = self._queue.pop(0)
        self._edit.append(line)

class AgentWorker(QtCore.QThread):
    finished_ok = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, agent: Agent, plan: AgentPlan, ctx: dict):
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
    """
    Real-time, LLM-narrated agent run:
    - Streams short narration from Gemma before each action
    - Executes your existing actions (real work)
    - Appends the action logs and any generated files
    """
    def __init__(self, agent: Agent, steps: List[str], ctx: Dict, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.steps = steps
        self.ctx = dict(ctx or {})
        self.setWindowTitle("Agent (real-time)")
        self.resize(820, 600)

        v = QtWidgets.QVBoxLayout(self)
        head = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel("Visit → Report → Archive (Live)")
        self.title.setStyleSheet("font-size:18px; font-weight:700;")
        head.addWidget(self.title); head.addStretch(1)

        self.btn_run = QtWidgets.QPushButton("Run")
        self.btn_close = QtWidgets.QPushButton("Close")
        head.addWidget(self.btn_run); head.addWidget(self.btn_close)
        v.addLayout(head)
        self.btn_close.clicked.connect(self.reject)

        self.view = QtWidgets.QTextBrowser()
        self.view.setStyleSheet("font-family: Consolas, Menlo, monospace;")
        v.addWidget(self.view, 1)

        self.files_row = QtWidgets.QHBoxLayout()
        self.files_row.addStretch(1)
        v.addLayout(self.files_row)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, max(1, len(self.steps)))
        self.progress.setValue(0)
        v.addWidget(self.progress)

        self.btn_run.clicked.connect(self._run)
        self._narrator: Optional[_Narrator] = None
        self._running = False

        # a compact narrator system prompt
        self._sys = (
            "You are a concise assistant narrating an automated clinic workflow.\n"
            "Keep each message 1–2 sentences, plain English, no emojis.\n"
            "Be specific but brief about what will happen next.\n"
        )

    def _append(self, line: str):
        self.view.append(QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss] ") + line)

    def _start_narration(self, user_text: str, max_tokens=90):
        if self._narrator:
            try: self._narrator.stop()
            except Exception: pass
        self._narrator = _Narrator(self._sys, user_text, max_new_tokens=max_tokens, temperature=0.1)
        self._narrator.chunk.connect(lambda s: self._append(s))
        self._narrator.done.connect(lambda: self._append(""))
        self._narrator.failed.connect(lambda e: self._append(f"[narration error] {e}"))
        self._narrator.start()

    def _run(self):
        if self._running: return
        self._running = True
        self.btn_run.setEnabled(False)
        QtCore.QTimer.singleShot(0, self._drive)

    def _add_file_button(self, label: str, path: str):
        btn = QtWidgets.QPushButton(label)
        btn.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path)))
        self.files_row.insertWidget(self.files_row.count()-1, btn)

    def _drive(self):
        try:
            for i, step_name in enumerate(self.steps, 1):
                # 1) narrate what's about to happen (streamed)
                self._append(f"\n▶️  {step_name}")
                preview = f"Next: '{step_name}'. Explain briefly what this action will do with the current patient data."
                self._start_narration(preview)

                # Let narration render a bit (non-blocking short wait)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(150)

                # 2) actually run the action
                fn = self.agent._actions.get(step_name)
                if not fn:
                    self._append(f"⚠️ step '{step_name}' not found; skipped")
                    self.progress.setValue(i)
                    continue

                new_ctx, lines = fn(dict(self.ctx))
                self.ctx.update(new_ctx or {})
                for ln in (lines or []):
                    self._append("   " + ln)

                # 3) optional: summarize result in 1 line (LLM)
                if HAVE_LLM_NARRATOR:
                    summ = (
                        "Summarize the outcome of this step in one short sentence, "
                        "mentioning any dates/files if relevant."
                    )
                    self._start_narration(summ, max_tokens=50)
                    QtCore.QThread.msleep(120)

                # show any produced files
                pdf = self.ctx.get("pdf_path"); jsn = self.ctx.get("json_path")
                if pdf: self._add_file_button("Open PDF", pdf)
                if jsn: self._add_file_button("Open JSON", jsn)

                self.progress.setValue(i)
                QtWidgets.QApplication.processEvents()

            self._append("\n✅ Plan complete.")
        except Exception as e:
            self._append(f"\n❌ FAILED: {e}")
        finally:
            self._running = False
            self.btn_run.setEnabled(True)


    # --- signal handlers ---
    def _on_step_started(self, name: str):
        self._mark_step(name, started=True)
        self.typer.add_lines(f"--- {name} START ---")

    def _on_step_finished(self, name: str, info: str):
        self.typer.add_lines([info or "(no output)", f"--- {name} END ---", ""])

    def _mark_step(self, name: str, started=False, done=False):
        # find row text begins with "○ name" or already toggled
        for i in range(self.step_list.count()):
            it = self.step_list.item(i)
            raw = it.text()
            if raw.endswith(name) or raw.lstrip("●✓○ ").endswith(name):
                if done:
                    it.setText(f"✓ {name}")
                    it.setForeground(QtGui.QBrush(QtGui.QColor("#16a34a")))
                elif started:
                    it.setText(f"● {name}")
                    it.setForeground(QtGui.QBrush(QtGui.QColor("#f59e0b")))
                return

    # --- actions ---
    def _simulate(self):
        """Fake the run: just play the timeline with 0.7s cadence."""
        self.console.clear()
        self.typer.add_lines([f"🧪 Simulating plan: {self.plan.name}", ""])
        delay = 0
        for step in self.plan.steps:
            QtCore.QTimer.singleShot(delay, lambda s=step: self._on_step_started(s))
            QtCore.QTimer.singleShot(delay + 700, lambda s=step: self._on_step_finished(s, "(simulated)"))
            delay += 1400
        QtCore.QTimer.singleShot(delay, lambda: self.typer.add_lines("✅ Simulation finished"))

    def _run(self):
        self.console.clear()
        self.btn_run.setEnabled(False)
        self.btn_sim.setEnabled(False)
        self.typer.add_lines([f"🚀 Executing plan: {self.plan.name}", ""])
        self.worker = AgentWorker(self.agent, self.plan, dict(self.ctx))
        self.worker.finished_ok.connect(self._done)
        self.worker.failed.connect(self._fail)
        self.worker.start()

    def _done(self, ctx_out: dict):
        self.typer.add_lines(["", "✅ PLAN COMPLETE"])
        # Buttons to open file outputs if present
        pdf = ctx_out.get("pdf_path")
        jsn = ctx_out.get("json_path")
        if pdf or jsn:
            row = QtWidgets.QHBoxLayout()
            if pdf:
                b = QtWidgets.QPushButton("Open PDF")
                b.clicked.connect(lambda: open_native(pdf, self))
                row.addWidget(b)
            if jsn:
                b = QtWidgets.QPushButton("Open JSON")
                b.clicked.connect(lambda: open_native(jsn, self))
                row.addWidget(b)
            self.layout().addLayout(row)
            notify(self, "Agent", "Created:\n" + "\n".join([p for p in (pdf, jsn) if p]))
        # mark all steps as done in the list
        for step in self.plan.steps:
            self._mark_step(step, done=True)
        self.btn_run.setEnabled(True)
        self.btn_sim.setEnabled(True)
        self.done_ctx.emit(ctx_out)

    def _fail(self, err: str):
        self.typer.add_lines(["", f"❌ FAILED: {err}"])
        QtWidgets.QMessageBox.critical(self, "Agent", err)
        self.btn_run.setEnabled(True)
        self.btn_sim.setEnabled(True)
