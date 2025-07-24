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

class AgentSimDialog(QtWidgets.QDialog):
    done_ctx = QtCore.pyqtSignal(dict)

    def __init__(self, agent: Agent, plan: AgentPlan, ctx: dict, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.plan = plan
        self.ctx = dict(ctx or {})
        self.setWindowTitle("Agent Simulation")
        self.resize(820, 560)

        # --- UI ---
        v = QtWidgets.QVBoxLayout(self)

        # Title + subtitle
        head = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("🧠 Autonomous Agent")
        title.setStyleSheet("font: 700 20pt 'Segoe UI';")
        subtitle = QtWidgets.QLabel("watch the plan execute in real-time")
        subtitle.setStyleSheet("color:#6b7280;")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(subtitle)
        v.addLayout(head)

        # Timeline + console
        split = QtWidgets.QSplitter()
        split.setOrientation(QtCore.Qt.Horizontal)

        # Left: steps list (timeline)
        left = QtWidgets.QWidget()
        lyl = QtWidgets.QVBoxLayout(left)
        lyl.setContentsMargins(8,8,8,8)
        self.step_list = QtWidgets.QListWidget()
        self.step_list.setAlternatingRowColors(True)
        for s in self.plan.steps:
            self.step_list.addItem(f"○ {s}")
        lyl.addWidget(QtWidgets.QLabel("Timeline"))
        lyl.addWidget(self.step_list)
        split.addWidget(left)

        # Right: console log with typer
        right = QtWidgets.QWidget()
        ryl = QtWidgets.QVBoxLayout(right)
        ryl.setContentsMargins(8,8,8,8)
        ryl.addWidget(QtWidgets.QLabel("Agent console"))
        self.console = QtWidgets.QTextEdit(readOnly=True)
        self.console.setStyleSheet("background:#0b1020; color:#e5e7eb; font-family:Consolas,Monaco,monospace;")
        ryl.addWidget(self.console)
        split.addWidget(right)
        split.setSizes([250, 570])

        v.addWidget(split)

        # Footer: actions
        footer = QtWidgets.QHBoxLayout()
        self.btn_sim = QtWidgets.QPushButton("Simulate")
        self.btn_run = QtWidgets.QPushButton("Run plan")
        self.btn_close = QtWidgets.QPushButton("Close")
        footer.addWidget(self.btn_sim)
        footer.addWidget(self.btn_run)
        footer.addStretch(1)
        footer.addWidget(self.btn_close)
        v.addLayout(footer)

        self.btn_close.clicked.connect(self.close)
        self.btn_sim.clicked.connect(self._simulate)
        self.btn_run.clicked.connect(self._run)

        # typer
        self.typer = _Typer(self.console, delay_ms=700, parent=self)

        # Hook agent signals -> UI
        self.agent.log.connect(lambda s: self.typer.add_lines(s))
        self.agent.step_started.connect(self._on_step_started)
        self.agent.step_finished.connect(self._on_step_finished)
        self.agent.errored.connect(lambda s: self.typer.add_lines(f"❌ {s}"))

        # Style list rows a bit
        self.step_list.setStyleSheet("""
            QListWidget::item { padding:8px; }
            QListWidget::item:selected { background:#e5e7eb; color:#111827; }
        """)

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
