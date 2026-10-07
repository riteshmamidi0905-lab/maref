"""Hard gates and aggregation. A gate is a veto: any FAIL on a gated, applicable dimension makes the run FAIL, however many other dimensions pass. The score is reported and NEVER used to gate.
PASS means 'no failure detected on the dimensions that could be assessed' and the result lists which could not be (`unassessed`); a run where nothing could be assessed is UNDETERMINED, not PASS."""
from __future__ import annotations

from dataclasses import dataclass, field

from .schema import DimResult, RunResult
from .taxonomy import Dim, V

ALL_DIMS = [d.value for d in Dim]


@dataclass
class Config:
    gates: list[str] = field(default_factory=lambda: list(ALL_DIMS))       # dimensions whose FAIL vetoes the run
    strict_tool_consistency: bool = False
    dims: list[str] = field(default_factory=lambda: [d for d in ALL_DIMS if d != Dim.CONSISTENCY.value])   # per-run dimensions; consistency is set-level


def aggregate(run_id: str, task_id: str, dims: list[DimResult], cfg: Config, mode: str) -> RunResult:
    failed = [d.dim for d in dims if d.verdict == V.FAIL.value and d.dim in cfg.gates]
    unassessed = [d.dim for d in dims if d.verdict == V.UNDETERMINED.value]
    passed = [d for d in dims if d.verdict == V.PASS.value]
    assessed = [d for d in dims if d.verdict in (V.PASS.value, V.FAIL.value)]
    if failed:
        verdict = V.FAIL.value
    elif passed:
        verdict = V.PASS.value
    else:
        verdict = V.UNDETERMINED.value
    score = (len(passed) / len(assessed)) if assessed else None
    return RunResult(run_id, task_id, verdict, dims, failed, unassessed, score, mode)
