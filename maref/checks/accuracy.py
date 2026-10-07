"""D1 Task Accuracy. Needs a reference: with none declared the dimension is UNDETERMINED (never guessed, never 1.0)."""
from __future__ import annotations

import re

from ..schema import DimResult
from ..taxonomy import Conf, Dim, V


def check(run, task, cfg) -> DimResult:
    refs = task.reference_answers if task else []
    if not refs:
        return DimResult(Dim.ACCURACY.value, V.UNDETERMINED.value, Conf.DETERMINISTIC.value, note="no reference declared")
    text = run.final_answer or (str(run.structured.get("data")) if run.structured and run.structured.get("data") is not None else "")
    if not text:
        return DimResult(Dim.ACCURACY.value, V.UNDETERMINED.value, Conf.DETERMINISTIC.value, note="no answer to compare")
    if any(re.search(p, text) for p in refs):
        return DimResult(Dim.ACCURACY.value, V.PASS.value, Conf.DETERMINISTIC.value)
    return DimResult(Dim.ACCURACY.value, V.FAIL.value, Conf.DETERMINISTIC.value, [{"code": "WRONG_ANSWER", "detail": "answer matches no declared reference", "evidence": text[:160]}])
