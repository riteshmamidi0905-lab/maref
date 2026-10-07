"""D4 Instruction Adherence. Format constraints stated in the objective (one word / one sentence / start with Yes or No), structured-output validity, and, with a task spec, declared constraints."""
from __future__ import annotations

import re

from ..schema import DimResult
from ..taxonomy import Conf, Dim, V
from ..text import sentences

ONE_WORD = re.compile(r"(?i)\b(?:answer|reply|respond)\s+with\s+(?:one|a single|1)\s+word\b|\bone[- ]word answer\b")
ONE_SENTENCE = re.compile(r"(?i)\b(?:in|with)\s+(?:one|a single|1)[- ]sentence\b|\bone[- ]sentence\b")
YES_NO = re.compile(r"(?i)\bstart (?:your answer )?with yes or no\b")


def check(run, task, cfg) -> DimResult:
    findings, applicable = [], False
    ans = (run.final_answer or "").strip()
    if run.structured is not None:
        applicable = True
        if not run.structured.get("valid"):
            findings.append({"code": "STRUCTURE_INVALID", "detail": f"structured output invalid after {run.structured.get('repairs')} repair(s)", "evidence": ans[:120]})
    if ans and run.structured is None:
        obj = run.objective
        if ONE_WORD.search(obj):
            applicable = True
            if len(re.findall(r"\w+", ans)) != 1:
                findings.append({"code": "FORMAT_VIOLATION", "detail": "asked for one word", "evidence": ans[:120]})
        if ONE_SENTENCE.search(obj):
            applicable = True
            if len(sentences(ans)) != 1:
                findings.append({"code": "FORMAT_VIOLATION", "detail": "asked for one sentence", "evidence": ans[:120]})
        if YES_NO.search(obj) or (task and task.constraints.get("yes_no_start")):
            applicable = True
            if not re.match(r"(?i)^\W*(yes|no)\b", ans):
                findings.append({"code": "FORMAT_VIOLATION", "detail": "asked to start with Yes or No", "evidence": ans[:120]})
        for p in (task.constraints.get("regex", []) if task else []):
            applicable = True
            if not re.search(p, ans):
                findings.append({"code": "FORMAT_VIOLATION", "detail": f"declared pattern {p} not met", "evidence": ans[:120]})
        for p in (task.constraints.get("not_regex", []) if task else []):
            applicable = True
            if re.search(p, ans):
                findings.append({"code": "FORMAT_VIOLATION", "detail": f"forbidden pattern {p} present", "evidence": ans[:120]})
    if not applicable:
        return DimResult(Dim.ADHERENCE.value, V.NA.value, Conf.HEURISTIC.value, note="no stated constraint to check")
    return DimResult(Dim.ADHERENCE.value, V.FAIL.value if findings else V.PASS.value, Conf.HEURISTIC.value, findings)
