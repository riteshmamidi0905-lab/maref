"""Evaluate runs. `evaluate_run` for one run; `evaluate_set` for the runs of one task (adds the set-level consistency dimension to each). Deterministic: the same input gives the same output."""
from __future__ import annotations

from .checks import abstention, accuracy, action, adherence, completion, consistency, groundedness, safety
from .gates import Config, aggregate
from .schema import Run, RunResult, TaskSpec

CHECKS = [accuracy, groundedness, abstention, adherence, completion, action, safety]


def evaluate_run(run: Run, task: TaskSpec | None = None, cfg: Config | None = None, extra=None) -> RunResult:
    cfg = cfg or Config()
    dims = [m.check(run, task, cfg) for m in CHECKS]
    dims += list(extra or [])
    return aggregate(run.run_id, run.task_id, dims, cfg, "reference-aware" if task else "reference-free")


def evaluate_set(runs: list[Run], task: TaskSpec | None = None, cfg: Config | None = None) -> list[RunResult]:
    cfg = cfg or Config()
    cons = consistency.check_set(runs, cfg)
    return [evaluate_run(r, task, cfg, extra=[cons]) for r in runs]
