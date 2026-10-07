"""D5 Consistency (set-level): runs of the same task should reach the same decision. Compared on facts, not wording: the decision class (answered / abstained / no answer), the set of numbers, the set of
cited ids, and the terminal status. Tool-sequence differences are reported as an info finding by default (a calculator is optional) and fail only with cfg.strict_tool_consistency."""
from __future__ import annotations

from ..schema import DimResult
from ..taxonomy import Conf, Dim, V
from ..text import ABSTAIN, ids, numbers


def signature(run) -> tuple:
    ans = (run.final_answer or "").strip()
    cls = "none" if not ans else ("abstain" if ABSTAIN.search(ans) else "answer")
    return (cls, tuple(sorted(set(round(n, 3) for n in numbers(ans)))), tuple(sorted(set(ids(ans)))), run.status)


def _compatible(a: tuple, b: tuple) -> bool:
    """Two signatures conflict only if the decision class or status differ, or their number sets / citation sets are not nested: extra grounded detail in one answer is not a contradiction (dev finding, docs/DEV-LOG.md)."""
    (ca, na, ia, sa), (cb, nb, ib, sb) = a, b
    return ca == cb and sa == sb and (set(na) <= set(nb) or set(nb) <= set(na)) and (set(ia) <= set(ib) or set(ib) <= set(ia))


def check_set(runs, cfg) -> DimResult:
    if len(runs) < 2:
        return DimResult(Dim.CONSISTENCY.value, V.NA.value, Conf.DETERMINISTIC.value, note="needs at least two runs of the same task")
    sigs = {signature(r) for r in runs}
    tools = {tuple(c.name for c in r.tool_calls) for r in runs}
    findings = []
    conflicts = [(a, b) for i, a in enumerate(sorted(sigs, key=str)) for b in sorted(sigs, key=str)[i + 1:] if not _compatible(a, b)]
    if conflicts:
        findings.append({"code": "INCONSISTENT_ANSWER", "detail": f"{len(conflicts)} conflicting pair(s) among {len(sigs)} distinct (decision, numbers, citations, status) signatures over {len(runs)} runs", "evidence": [str(c) for c in conflicts[:3]]})
    if len(tools) > 1:
        f = {"code": "INCONSISTENT_TOOL_USE", "detail": f"{len(tools)} distinct tool sequences", "evidence": sorted(map(str, tools))[:4], "severity": "fail" if cfg.strict_tool_consistency else "info"}
        findings.append(f)
    failing = [f for f in findings if f.get("severity", "fail") == "fail"]
    return DimResult(Dim.CONSISTENCY.value, V.FAIL.value if failing else V.PASS.value, Conf.HEURISTIC.value, findings)
