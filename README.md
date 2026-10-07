# MAREF: Multi-Dimensional Agent Reliability Evaluation Framework

> ## Research prototype · pre-registered verdict: MIXED
> MAREF evaluates **runs of an agent** (objective, tool calls and results, side effects, final answer, how the run ended). **It is not an agent.** This repository is an evaluation prototype with a pre-registered, same-author evaluation. **This is not independent validation.**
>
> On the held-out test split (reference-aware mode, frozen primary labels, 187 runs): **`33/33` labelled failures detected · `36/154` clean runs flagged · `151/187` overall agreement.**
> The three results, in full (canonical wording and numbers: [`docs/CLAIM.md`](docs/CLAIM.md); statistics: [`docs/EVALUATION.md`](docs/EVALUATION.md)):
> 1. **Against llmeval as shipped, the pre-registered comparison was passed.** Agreement vs llmeval hard gates: pooled **+0.257**, 95% [0.097, 0.419]; real runs **+0.292**, 95% [0.092, 0.492]. Real clean-run false alarms: **30/112 (~27%)** vs **65/112 (~58%)**.
> 2. **Against stronger baselines, better overall agreement was not established.** MAREF **151/187** vs always-pass 154/187, dev-fitted llmeval 158/187, local 4B judge 166/187; every paired interval includes zero.
> 3. **Trajectory-specific advantage was not established.** The third pre-registered criterion failed: no trajectory-only failure mode had at least 5 positives **and** MAREF recall ≥ 80% **and** llmeval-gates recall ≤ 50%.
>
> Verdict, verbatim from the frozen decision function: `MIXED: agreement and false alarms hold, no trajectory-only failure mode qualifies`.
> **The test split has been used once and is spent.** MAREF v0.1.0 was frozen first; a lock file refuses a second evaluation. Any change to MAREF needs newly written tasks.
> **Same-author, not independent:** one AI author wrote the ARB tasks and oracles, the benchmark, the checkers, the baselines and the analysis; no human labelled or reviewed anything; ARB results were known before the benchmark was built; MAREF was tuned on the dev split; some test answers had been read during ARB analysis; benchmark v1.1 declaration corrections followed the initial dev work; the oracle and MAREF share lexicon blind spots. Full account: [`docs/INDEPENDENCE.md`](docs/INDEPENDENCE.md).

## Where it sits
```
AI Agent Runtime   (ai-agent-from-scratch, pinned, unmodified)
      ↓ exercised by
Agent Runtime Benchmark (ARB-1: 48 tasks, runs a real local model)
      ↓ produces trajectories that are evaluated by
MAREF   (this repository: run-level evaluation of those trajectories)
```
* The agent runtime: [`ai-agent-from-scratch`](https://github.com/riteshmamidi0905-lab/ai-agent-from-scratch) (commit `231b186`).
* The benchmark and the real-model runs: [`agent-runtime-bench`](https://github.com/riteshmamidi0905-lab/agent-runtime-bench) (ARB-1 frozen at `e7b8e12`).
* The output-level evaluator MAREF is compared with: [`llm-eval-framework`](https://github.com/riteshmamidi0905-lab/llm-eval-framework) (pinned at `99e6121`).

## What it does, and what is not new
A small, dependency-free Python library. Eight dimensions each return `PASS`, `FAIL`, `NA` (does not apply) or `UNDETERMINED` (applies, but the information needed is missing); a failure on any gated dimension fails the run; a score is reported but never gates. Every failure carries a code from a fixed taxonomy, its evidence and a confidence class (`deterministic` / `heuristic` / `judge`).
Dimensions: `task_accuracy`, `groundedness`, `hallucination_resistance`, `instruction_adherence`, `consistency` (set-level), `task_completion`, `action_correctness`, `policy_and_injection_safety` ([`docs/SPEC.md`](docs/SPEC.md) section 3).
It is not "the first agent evaluator" (the runtime has a small run-level evaluator of its own) and not a better *output* scorer than llmeval. What it adds: applicability-aware verdicts (never a silent 1.0), hard-gate veto aggregation, a failure taxonomy, reference-free provenance for injected actions, a control-level / model-level split of safety findings, set-level consistency, reference-free vs reference-aware modes, and uncertainty reporting.

## Known weaknesses of this version (all from the held-out test split)
* **False alarms:** 36/154 clean runs (23%) pooled, 30/112 (27%) on real runs, concentrated in six of 24 tasks (all five runs of each). Causes: a lexicon-based decision class, numbered-list markers read as unsupported numbers, a repeated-failing-call rule that ignores a requested retry, a sentence-count heuristic.
* **Dev numbers were optimistic:** 93% agreement and 7% false alarms on dev, where it was tuned, vs 81% and 23% on test.
* **Seven of ten failure modes have no real positives in the test split;** recall for them rests on synthetic runs written by the same author.
* **One small model** (Qwen3-4B-Instruct-2507, Q4_K_M) and **48 author-written tasks**.
Fixes were deliberately not made after seeing the test results; see `docs/EVALUATION.md` section 3.

## Frozen artefacts (verify them)
| Artefact | Value |
|---|---|
| MAREF v0.1.0 root hash (every library, experiment, spec and baseline file) | `d5f1d12cd0020ca4619e616d27e0eb55837d04fb97c030791cab840e5639a817` (`experiments/MAREF-FREEZE.json`, commit `2dac231`) |
| MAREF-Bench v1.1 root hash (393 files: runs, labels, split, references, specs) | `effb7f4c971c23f1afd58ba67eb1b784f47a75d7ef84ed3b0a4dcc4730ac5843` (`benchmark/FREEZE.json`; v1 frozen at `8295a60`, declaration-only v1.1 re-freeze at `f761862`) |
| `docs/SPEC.md` (the pre-registered decision rule) | sha256 `97b2c7142c3e861d5f15fa84bfb4ddb678bdc2fad5cc662d2aeae4dfc543b386` |
| Judge-only baseline prompt | sha256 `4f00d42f0953a3d6a00e3bde4733e2596801ac43db4e66c451e06ee856a4ad93` (`experiments/JUDGE-FREEZE.json`) |
| Test-split evaluation | commit `a8c1208`; lock `results/TEST-RUN.lock` (names the frozen root above) |

```bash
python -c "import json,sys; sys.path.insert(0,'experiments'); from freeze_maref import compute; print('freeze intact:', compute()[1]==json.load(open('experiments/MAREF-FREEZE.json'))['root_sha256'])"
```

## Reproduce
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev,baselines]'          # baselines installs llmeval pinned at 99e6121; the core library has no dependencies
pytest -q                                   # 35 tests: unit tests, benchmark freeze, JSON-Schema validation of all 382 runs, experiment guards, claim-drift tests
ruff check .
# re-derive every reported figure from the committed outputs (read-only; no model, no re-evaluation):
python experiments/render_evaluation.py results/test      # all tables in docs/EVALUATION.md
python experiments/error_analysis.py results/test         # every disagreement with its findings
# the dev split may be evaluated freely (it reproduces results/dev-final):
python experiments/run_experiment.py --split dev --out /tmp/maref-dev
# the test split cannot be run again: this refuses because of the lock file
python experiments/run_experiment.py --split test --out /tmp/maref-test --judge results/judge/judge_verdicts.json
```
Running the test split again would not be new evidence (it is spent) and the guard refuses unless the freeze and the lock allow it.
Rebuilding the benchmark from the ARB run artefacts (optional): `python benchmark/build.py --arb ../agent-runtime-bench --tags pass1 sample11 sample12 sample13 sample14` with `agent-runtime-bench` checked out at the commit named in `benchmark/data/manifest.json`.
The judge baseline needs a local `llama-server` serving the weights recorded in `experiments/JUDGE-FREEZE.json` (`python experiments/judge.py ...`); its 382 verdicts are committed in `results/judge/`.

## Use
```bash
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

## Benchmark
MAREF-Bench v1: 240 real runs (the frozen ARB-1 benchmark, 48 tasks, run once greedily and four times sampled with a small local model inside the pinned runtime) and 142 controlled synthetic runs for failure modes the real model never produced. Labels for real runs come mechanically from ARB's oracles, synthetic labels from construction; dev/test split by task id. Construction, label rules, the audit, label noise found after the freeze (four oracle false negatives) and every limit: [`docs/BENCHMARK.md`](docs/BENCHMARK.md). Every change made after looking at the dev split: [`docs/DEV-LOG.md`](docs/DEV-LOG.md).

## Documents
[`docs/CLAIM.md`](docs/CLAIM.md) canonical claim and wording rules · [`docs/EVALUATION.md`](docs/EVALUATION.md) full test-split evaluation · [`docs/SPEC.md`](docs/SPEC.md) specification and pre-registered rule (frozen) · [`docs/INDEPENDENCE.md`](docs/INDEPENDENCE.md) authorship, contamination and what would make the evidence stronger · [`docs/BENCHMARK.md`](docs/BENCHMARK.md) · [`docs/DEV-LOG.md`](docs/DEV-LOG.md).

## License
MIT (see `LICENSE`).
