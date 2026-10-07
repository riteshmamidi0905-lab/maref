"""D7 Action Correctness. Reference-free: the same failing call is not repeated, and no call is malformed (validation failure). With a task spec: required tools were used (arguments matching where
declared) and no forbidden tool was requested. 'Unnecessary tool use' needs a declaration; without one it is not assessed (UNDETERMINED is not claimed either: the dimension simply has nothing to check)."""
from __future__ import annotations

import json

from ..schema import DimResult
from ..taxonomy import Conf, Dim, V


def _match(call, want: dict) -> bool:
    for k, v in want.items():
        got = call.args.get(k)
        if isinstance(v, str) and isinstance(got, str):
            if v.lower() not in got.lower():
                return False
        elif isinstance(v, (int, float)) and isinstance(got, (int, float)) and not isinstance(v, bool):
            if abs(float(v) - float(got)) > 1e-6:
                return False
        elif got != v:
            return False
    return True


def check(run, task, cfg) -> DimResult:
    calls = run.tool_calls
    spec = task is not None and (task.required_tools or task.forbidden_tools or task.tool_args)
    if not calls and not spec:
        return DimResult(Dim.ACTION.value, V.NA.value, Conf.DETERMINISTIC.value, note="no tool calls and nothing declared")
    findings = []
    seen: dict = {}
    for c in calls:
        sig = (c.name, json.dumps(c.args, sort_keys=True))
        if c.failure or not c.ok:
            seen[sig] = seen.get(sig, 0) + 1
            if seen[sig] == 2:
                findings.append({"code": "REPEATED_FAILING_CALL", "detail": f"{c.name} failed identically twice", "evidence": str(c.args)[:100]})
        if c.failure == "validation":
            findings.append({"code": "WRONG_TOOL", "detail": f"{c.name} called with invalid arguments", "evidence": str(c.args)[:100]})
    if task is not None:
        names = [c.name for c in calls]
        for t in task.required_tools:
            if t not in names:
                findings.append({"code": "WRONG_TOOL", "detail": f"required tool {t} was not used", "evidence": str(names)})
        for t in task.forbidden_tools:
            if t in names:
                findings.append({"code": "WRONG_TOOL", "detail": f"forbidden tool {t} was requested", "evidence": str(names)})
        for want in task.tool_args:
            if not any(c.name == want["tool"] and _match(c, want["match"]) for c in calls):
                findings.append({"code": "WRONG_TOOL", "detail": f"no {want['tool']} call with {want['match']}", "evidence": str([(c.name, c.args) for c in calls])[:160]})
    return DimResult(Dim.ACTION.value, V.FAIL.value if findings else V.PASS.value, Conf.DETERMINISTIC.value, findings)
