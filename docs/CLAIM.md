# MAREF: the claim, stated precisely

**Research prototype · pre-registered distinctness verdict: MIXED.**
This file is the canonical wording for any public statement about MAREF's measured result. It exists because "MAREF did not beat llmeval" is **wrong** and "MAREF beat llmeval" is **incomplete**: the pre-registered comparison against llmeval as shipped was passed, the comparison against stronger baselines was not, and the trajectory-specific criterion failed. All three are results; none may be dropped.

All numbers: the held-out **test split** of MAREF-Bench v1, evaluated **once** by the frozen MAREF v0.1.0 (`experiments/MAREF-FREEZE.json`, root `d5f1d12c…a817`), **reference-aware** mode, **frozen primary labels** (`FM_ANY`), 187 runs (120 real runs of one small model, 67 controlled synthetic runs), 24 task clusters. Source: `results/test/results.json`, rendered in `docs/EVALUATION.md`.

## Compact presentation (the card as shown on the portfolio)
> **MAREF · Research prototype · MIXED**
> `33/33` labelled failures detected · `36/154` clean runs flagged · `151/187` overall agreement
> Pre-registered advantage vs shipped llmeval gates; no demonstrated advantage over stronger baselines or for trajectory-specific failures.
> [Full evaluation →]

The card links to the complete evaluation (`docs/EVALUATION.md`). **`33/33` must never be shown without the false-alarm (`36/154`) and agreement (`151/187`) figures beside it.** Each figure is the MAREF reference-aware, frozen-primary-label, pooled test-split number (187 runs).

## 1. Against llmeval as shipped: the pre-registered comparison was passed
MAREF reference-aware had **significantly higher run-level agreement** with the frozen labels than **llmeval hard gates**, under the pre-registered paired **cluster** bootstrap (all runs of a task resampled together):

| | difference in agreement (MAREF-RA − llmeval hard gates) | 95% interval |
|---|---|---|
| pooled (187 runs) | **+0.257** | [0.097, 0.419] |
| real runs only (120) | **+0.292** | [0.092, 0.492] |

Its **false-alarm rate on clean real runs was lower**: MAREF **30/112 (~27%)** against shipped llmeval hard gates **65/112 (~58%)**. (Criteria 1 and 2 of the pre-registered rule, `docs/SPEC.md` section 8: both pass.)
For completeness, llmeval's other shipped aggregation (simple average, B1) is also below MAREF: +0.214, 95% [0.058, 0.370] pooled. It is reported, not part of the rule.

## 2. Against stronger baselines: better overall agreement was not established
| detector (frozen primary labels, pooled 187 runs) | agreement | MAREF-RA minus it | 95% interval |
|---|---|---|---|
| MAREF reference-aware | **151/187** | n/a | n/a |
| always pass (base rate) | 154/187 | −0.016 | [−0.158, 0.119] |
| llmeval with thresholds fitted on dev | 158/187 | −0.037 | [−0.181, 0.104] |
| local 4B judge (frozen prompt) | 166/187 | −0.080 | [−0.206, 0.053] |

Every interval includes zero, so MAREF is **not shown to be better** than any of them on overall agreement; the point estimates are slightly negative (on the 120 real runs alone −0.15 to −0.18, again with intervals including zero). MAREF's recall was the highest of all detectors (33/33 failing runs, 8/8 real), but with 36/154 clean runs flagged (23%) its overall agreement was 151/187, and its false-alarm rate was higher than that of the always-pass (0%), dev-fitted llmeval (4%) and judge (8%) baselines, which is why its agreement did not improve on theirs.

## 3. Trajectory-specific distinctness: the third pre-registered criterion failed
Criterion 3 required a trajectory-only failure mode (`FM_INDUCED`, `FM_ACTION_CLAIM`, `FM_TOOL`, `FM_STATUS`) with **all** of: at least 5 positives in the test split; MAREF recall ≥ 80%; llmeval-gates recall ≤ 50%. **None qualified:**

| mode | positives (real / synthetic) | MAREF-RA recall | llmeval-gates recall | fails because |
|---|---|---|---|---|
| `FM_INDUCED` | 0 (0 / 0) | 0/0 | 0/0 | no positives |
| `FM_ACTION_CLAIM` | 5 (0 / 5) | 5/5 | 4/5 (80%) | llmeval recall above 50% |
| `FM_TOOL` | 2 (0 / 2) | 2/2 | 2/2 | fewer than 5 positives |
| `FM_STATUS` | 1 (0 / 1) | 1/1 | 1/1 | fewer than 5 positives |

So an empirical advantage specific to trajectory-visible failures **was not established**; the test split contains no real positives for any of the four modes.
(On the dev split, where MAREF was tuned, it detected 10/10 real `FM_INDUCED` runs against llmeval gates' 5/10. That is a tuned-split observation, not part of the pre-registered result.)

## 4. The verdict, preserved exactly
The frozen decision function (`experiments/run_experiment.py`, `decision()`) returned, unmodified:

**`MIXED: agreement and false alarms hold, no trajectory-only failure mode qualifies`**

in plain words: **MIXED — agreement and false-alarm criteria passed; trajectory-only empirical advantage was not established.**
Disclosure about the rule itself: the prose of `docs/SPEC.md` section 8 spelled out three outcomes (all criteria hold; criterion 1 or 2 fails; only criterion 3 holds on synthetic runs). The outcome "criteria 1 and 2 hold, criterion 3 fails" is named `MIXED` only in the frozen `decision()` code, which was committed before the test run. Nothing about it was chosen after the result.

## 5. Primary labels are the headline; everything else is a sensitivity analysis
* The headline is always the **frozen primary label** (`FM_ANY`: the ARB oracle failed, or a synthetic script injected a failure).
* The **secondary definition** (also counting members of inconsistent sets; declared **after** the dev results were seen) and the **adjudicated labels** (same-author corrections to four oracle false negatives; all four runs are dev tasks, so they change **nothing** on the test split) may appear **only** as clearly labelled sensitivity analyses, never in place of the numbers above.
* "Clean run" in `36/154` means a run whose frozen primary label is 0; that label ignores set-level inconsistency (see `docs/SPEC.md`).

## 6. Independence disclosure (travels with every statement of the result)
**This is not independent validation.**
* The same AI author created the ARB tasks and oracles, the MAREF benchmark (labels, synthetic runs, split), the MAREF checkers, the baselines and the analysis.
* There was **no independent human labelling or review** of any task, label, rule or result.
* The ARB aggregate results were **known before MAREF-Bench was constructed**.
* MAREF was **tuned on the dev split** (three iterations; `docs/DEV-LOG.md`).
* **Some test-split answers had been read** during the ARB analysis, before the test evaluation.
* **Benchmark v1.1 declaration corrections** were made after the initial dev work (task declarations only; disclosed; re-frozen).
* The test split was **run once and is now spent**; any change to MAREF needs new tasks.
* **Shared lexicon blind spots** exist between the ARB oracle and MAREF's own checkers (same author, same vocabulary; e.g. "failure", "restricted"), so their agreement is weaker evidence than it looks.
Full account: `docs/INDEPENDENCE.md`.

## 7. Wording rules
* Say: "research prototype", "MIXED", "pre-registered", "frozen primary labels", "same-author benchmark", "one small model".
* Do **not** say: "validated", "independently validated", "outperforms llmeval" (unqualified), "does not beat llmeval", "better than baselines", "production-ready", or quote a secondary or adjudicated number as the headline.
* Always give the denominators and link the full evaluation. Never quote `33/33` (or "perfect recall") without the `36/154` clean-run false alarms and the `151/187` agreement beside it.
