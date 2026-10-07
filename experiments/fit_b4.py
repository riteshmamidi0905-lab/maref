"""Baseline B4: llmeval with thresholds FITTED ON THE DEV SPLIT (a fairness check: MAREF's heuristics were tuned on dev, so the output-level baseline gets a comparable tuning budget).
The rule is 'flag a run if any chosen llmeval criterion scores below its threshold'. Greedy coordinate ascent over (criterion, threshold) pairs maximises agreement with the FROZEN FM_ANY label on the dev split only;
a pair is added only if it improves dev agreement by at least one run. Writes experiments/b4_thresholds.json; the test split never enters this file's inputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import baselines  # noqa: E402
from run_experiment import load  # noqa: E402

GRID = [round(0.1 * i, 1) for i in range(1, 11)]


def main():
    runs, labels, _ = load("dev")
    refs = baselines.load_references(ROOT / "benchmark")
    ev = baselines.make_evaluator()
    crit = {rid: baselines.score(ev, d, refs.get(d["task_id"], ""))["criteria"] for rid, d in runs.items()}
    names = sorted(next(iter(crit.values())))
    y = {rid: bool(labels[rid]["FM_ANY"]) for rid in runs}

    def agreement(rule):
        return sum(any(crit[r][c] < t for c, t in rule.items()) == y[r] for r in runs)
    rule, best = {}, agreement({})
    while True:
        cand = None
        for c in names:
            for t in GRID:
                trial = {**rule, c: t}
                a = agreement(trial)
                if a > best and (cand is None or a > cand[0]):
                    cand = (a, c, t)
        if cand is None:
            break
        best, rule = cand[0], {**rule, cand[1]: cand[2]}
    out = {"fitted_on": "dev split only", "n_dev_runs": len(runs), "dev_agreement": f"{best}/{len(runs)}", "rule": "flag if any listed criterion score < its threshold", "thresholds": rule}
    (ROOT / "experiments" / "b4_thresholds.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
