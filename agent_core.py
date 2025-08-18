# agent_core.py
from PyQt5 import QtCore

class AgentPlan:
    def __init__(self, name: str, steps: list[str]):
        self.name = name
        self.steps = list(steps or [])

class Agent(QtCore.QObject):
    # Log & lifecycle
    log = QtCore.pyqtSignal(str)
    step_started = QtCore.pyqtSignal(str)
    step_finished = QtCore.pyqtSignal(str, str)
    errored = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions = {}

    def register(self, name: str, func):
        """Register an action callable(agent, ctx) -> (ctx, info_str)"""
        self._actions[str(name)] = func

    # Optional convenience for bulk registering
    def register_many(self, mapping: dict[str, callable]):
        self._actions.update(mapping or {})

    def run_step(self, name: str, ctx: dict):
        name = str(name)
        fn = self._actions.get(name)
        if not fn:
            raise RuntimeError(f"Agent action '{name}' not registered")
        self.step_started.emit(name)
        self.log.emit(f"▶ Running action: {name}")
        res_ctx, info = fn(self, dict(ctx or {}))
        info_str = str(info or "").strip()
        if info_str:
            self.log.emit(info_str)
        self.step_finished.emit(name, info_str)
        return dict(res_ctx or {})

    def run_plan(self, plan: AgentPlan, ctx: dict):
        """Run all steps synchronously, emitting signals along the way."""
        ctx = dict(ctx or {})
        try:
            self.log.emit(f"🧭 Plan '{plan.name}' started")
            for step in plan.steps:
                ctx = self.run_step(step, ctx)
            self.log.emit(f"✅ Plan '{plan.name}' complete")
            return ctx
        except Exception as e:
            msg = f"Agent failed in step '{step}': {e}"
            self.errored.emit(msg)
            raise
