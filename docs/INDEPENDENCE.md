# Independence, contamination and AI authorship (full disclosure)

## Who did what
Everything in this repository and in the benchmark it is measured on was written by **one AI assistant (Claude, Sonnet 5.5) working for the repository owner**, in one continuous working session, with the owner setting the scope and the rules and reviewing nothing line by line. Specifically the same author wrote:
the ARB-1 tasks, oracles, control checks and harness (`agent-runtime-bench`); the MAREF-Bench label rules, the 142 synthetic runs and their labels; the MAREF checkers, taxonomy, lexicons and statistics; the baseline configurations (llmeval rubric, thresholds, the dev-fitted B4, the judge prompt);
the label adjudication; and this write-up. **No human independently labelled, reviewed or audited any run, label, rule or result.** Every number here is a number about *this author's* notion of failure on *this author's* tasks.

## What was done to limit self-confirmation (and what each measure does not do)
| Measure | What it protects against | What it does not protect against |
|---|---|---|
| Benchmark (runs, labels, split, synthetic runs) frozen and hash-locked **before** any MAREF checker was written (`8295a60`); a test fails if any frozen file changes | tuning labels or data to the checkers | the author's mental model of failure shaping both; the v1.1 declaration corrections (task specs only; disclosed) |
| Dev/test split by task id, independent of outcomes; checkers adjusted **only** on dev (`docs/DEV-LOG.md`); test split run **once** by a frozen MAREF version (hash of every source file, enforced by `experiments/run_experiment.py`, lock file) | overfitting to the evaluation set | the author had *read* the final answers of the failed real runs of both splits while writing up ARB-1, before the test evaluation (see below) |
| Real-run labels derived mechanically from ARB oracle code that MAREF does not import | labels that merely echo MAREF's own rules | both are one author's lexicons: **shared blind spots are documented** ("failure", "restricted") |
| Synthetic runs for failure modes the real model never produced, labelled by construction, written before the checkers | reporting recall on zero positives | construction labels are the author's intent; "bad" scripts resemble what the author expected checkers to catch |
| Baselines: llmeval pinned at `99e6121` (simple average, hard gates), a **dev-fitted** llmeval (B4) for tuning parity, a judge-only baseline with a frozen prompt | comparing against a strawman | the judge is a 4B local model (the same model that produced the real runs: self-judging bias is possible); llmeval was designed for output strings, not runs |
| Pre-registered distinctness rule (`docs/SPEC.md` section 8, hashed into the MAREF freeze) | choosing the conclusion after seeing results | the rule itself was written by the author who had seen the dev results |
| Paired **cluster** bootstrap (runs of one task resampled together), Wilson intervals, per-failure-mode counts with zero-positive modes labelled "no real positives" | pseudo-replication, over-confident intervals | 24 task clusters per split; intervals are still wide |
| Results reported against both the frozen labels (headline) and an adjudicated set; negative results kept | hiding label noise | the adjudication is the same author's reading |

## Specific contamination events (all of them)
1. **ARB-1 results seen before MAREF-Bench was built.** I knew the greedy pass (43/48 and which tasks failed) when I designed the benchmark and the synthetic runs. The label rules and split are defined over task identity and oracle check names, not outcomes, but the choice of which failure modes the synthetic runs cover was informed by knowing the real model's failures.
2. **Dev-split inspection and changes.** Three dev iterations changed MAREF after I looked at dev errors (`docs/DEV-LOG.md`): the first clean-run false-alarm rate was 74%, and fixes included exempting the numbers 0 and 1 (trading recall for fewer false alarms), restricting the injection-provenance rule to instruction-like sentences, and nesting tolerance in the consistency check.
3. **Benchmark v1.1.** After the first dev runs I corrected my own reference-aware task declarations (not runs, labels, split or references) for **all** tasks, not only dev ones, and re-froze. The v1 freeze commit stays in history.
4. **Reading test-split answers.** While writing the ARB-1 results I read every failed real run's final answer, including those of test-split tasks (ARB-MT-03 and ARB-PI-03 are test tasks). This revealed four oracle false negatives (TF-02 ×3, RF-01 ×1; all in the **dev** split) and led to `experiments/adjudication.json`, written before the test evaluation. MAREF's lexicons were **not** changed in response (that would have been tuning on a phrasing).
5. **The same blind spot in two checkers.** MAREF's decline vocabulary lacks the same words as ARB's oracle lexicon. The agreement of the two on those runs is shared error.

## What would make this evidence stronger (not done)
A person who did not write any of it labels a random sample (suggest 60 runs, stratified by task category and detector outcome) blind to MAREF's output and to the oracle result; compare their labels with the frozen ones and with MAREF; fix the benchmark if they disagree with the oracle; only then evaluate on a second, newly written task set with a second model. Until then MAREF is a **prototype with a reproducible, honestly caveated evaluation**, not a validated evaluator.
