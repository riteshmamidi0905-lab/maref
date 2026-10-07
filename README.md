# MAREF: Multi-Dimensional Agent Reliability Evaluation Framework

A small, dependency-free Python library that evaluates **a run of an agent** (objective, tool calls and results, side effects, final answer, how it ended), not just the final text.
Each of eight dimensions returns `PASS`, `FAIL`, `NA` (does not apply) or `UNDETERMINED` (applies, but the information to decide is missing); a failure on any gated dimension fails the run; a score is reported but never gates.
Every failure carries a code from a fixed taxonomy, the evidence, and a confidence class (`deterministic` / `heuristic` / `judge`).

> **Status: research prototype with a mixed result, evaluated on one small model and a benchmark written by the same AI assistant that wrote the checkers. No human annotation. Read `docs/SPEC.md` (what it is and is not) and `docs/EVALUATION.md` (what was measured, with intervals and negative results) before quoting anything.**

## Why it exists, and what is not new
`llmeval` scores an output string. `ai-agent-from-scratch` has a small run-level evaluator. MAREF is neither "the first agent evaluator" nor a better *output* scorer. It adds, specifically: applicability-aware verdicts (never a silent 1.0), hard-gate veto aggregation,
a failure taxonomy, reference-free provenance for injected actions, separate control-level and model-level safety findings, set-level consistency, reference-free vs reference-aware modes, and uncertainty reporting. Details and the pre-registered test for "is it distinct from llmeval?" are in `docs/SPEC.md`.

## Use
```bash
pip install -e '.[dev]'
maref evaluate runs.jsonl --tasks tasks.json --json out.json --fail-on-fail     # reference-aware; omit --tasks for reference-free
maref validate runs.jsonl                                                       # schema check
maref schema run                                                                # JSON Schema of a run
```
```python
from maref.evaluate import evaluate_run
from maref.schema import Run
result = evaluate_run(Run.from_dict(run_dict))      # reference-free
print(result.verdict, result.failed, result.unassessed)
```
Schemas: `maref/schemas/{run,task}.schema.json` (`maref-run/1`, `maref-task/1`). Runs sharing a `set_id` are treated as repeats of one task for the consistency dimension.

## Dimensions
`task_accuracy`, `groundedness`, `hallucination_resistance`, `instruction_adherence`, `consistency` (set-level), `task_completion`, `action_correctness`, `policy_and_injection_safety`. Definitions, applicability and confidence classes: `docs/SPEC.md` section 3.

## Benchmark (MAREF-Bench v1, frozen before any checker was written)
240 real runs (the frozen ARB-1 agent benchmark, 48 tasks, run once greedily and four times sampled with `qwen3-4b-instruct-2507` Q4_K_M inside the frozen `ai-agent-from-scratch` runtime) and 142 controlled synthetic runs for failure modes the real model never produced.
Labels for real runs come mechanically from ARB's oracles; synthetic labels from construction. Dev/test split by task id; the test split is evaluated **once** by a frozen MAREF version (`experiments/freeze_maref.py`, enforced by `experiments/run_experiment.py`).
`docs/BENCHMARK.md` lists construction, label rules, the audit, the disclosed label noise, and every limit. `docs/DEV-LOG.md` lists every change made after looking at the dev split.

```bash
python benchmark/build.py --arb ../agent-runtime-bench --tags pass1 sample11 sample12 sample13 sample14   # rebuild (deterministic)
python experiments/run_experiment.py --split dev --out results/dev                                            # allowed while developing
python experiments/run_experiment.py --split test --out results/test --judge results/judge/judge_verdicts.json  # once, frozen version only
pytest -q                                                                                                     # 28 tests
```

## Result of the one-time test evaluation (read `docs/EVALUATION.md`)
On the held-out test split (187 runs, 24 task clusters) the frozen v0.1.0 flagged **every** failing run (33/33) and **23%** of clean runs (36/154; 27% on real runs, concentrated in six tasks whose five runs were all flagged).
It beats llmeval's shipped defaults on run-level agreement, but **not** an always-pass baseline, a dev-fitted llmeval, or a 4B judge. On dev it looked better (93% agreement, 7% false alarms) because the heuristics were tuned there. Pre-registered distinctness verdict: **MIXED**.
Root causes of the false alarms (a lexicon decision class, numbered-list markers read as numbers, a repeated-failing-call rule that ignores a requested retry) are documented; fixes were deliberately **not** made, because the test split can only be used once.

## Honest limits (short list; the long one is in the docs)
One author for tasks, oracles, labels, checkers and analysis. One small quantised model. The real model produced **zero** fabrications, false action claims, wrong-tool, status or structure failures, so recall for those modes is measured on synthetic runs only.
Lexicon-based checks share vocabulary blind spots with the lexicon-based oracles they are compared with (documented: "failure"/"restricted"). A judge baseline is a 4B local model, not a strong judge.
