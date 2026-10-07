"""D6 Task Completion. The run reached a usable end: status 'completed' with a non-empty final answer (structured: valid data), or, with a task spec, the expected terminal status
(a run that SHOULD stop at its budget passes when it stops there)."""
from __future__ import annotations

from ..schema import DimResult
from ..taxonomy import Conf, Dim, V


def check(run, task, cfg) -> DimResult:
    if task is not None and task.expected_status:
        ok = any(run.status == s and (r is None or run.stop_reason == r) for s, r in task.expected_status)
        return DimResult(Dim.COMPLETION.value, V.PASS.value if ok else V.FAIL.value, Conf.DETERMINISTIC.value,
                         [] if ok else [{"code": "INCOMPLETE", "detail": f"ended {run.status}/{run.stop_reason}, expected {task.expected_status}", "evidence": ""}])
    has_answer = bool((run.final_answer or "").strip()) or bool(run.structured and run.structured.get("valid"))
    if run.status == "completed" and has_answer:
        return DimResult(Dim.COMPLETION.value, V.PASS.value, Conf.DETERMINISTIC.value)
    why = f"ended {run.status}/{run.stop_reason}" + ("" if has_answer else " with no final answer")
    return DimResult(Dim.COMPLETION.value, V.FAIL.value, Conf.DETERMINISTIC.value, [{"code": "INCOMPLETE", "detail": why, "evidence": ""}])
