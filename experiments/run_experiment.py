"""Run MAREF (reference-free and reference-aware) and the baselines on MAREF-Bench v1 and write the results.
  python experiments/run_experiment.py --split dev  --out results/dev     (allowed while developing)
  python experiments/run_experiment.py --split test --out results/test    (the final, single evaluation of a frozen MAREF version)
Refuses to run if the benchmark differs from benchmark/FREEZE.json."""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import baselines  # noqa: E402

from maref.evaluate import evaluate_run, evaluate_set  # noqa: E402
from maref.schema import Run, TaskSpec  # noqa: E402
from maref.stats import bootstrap_diff, fmt, wilson  # noqa: E402

CODE_FM = {"WRONG_ANSWER": "FM_ACC", "UNSUPPORTED_NUMBER": "FM_FAB", "FABRICATED_UNDER_MISSING_EVIDENCE": "FM_FAB", "NO_ABSTENTION": "FM_FAB", "FALSE_ACTION_CLAIM": "FM_ACTION_CLAIM",
           "INJECTION_INDUCED_ACTION": "FM_INDUCED", "SECRET_LEAK": "FM_LEAK", "OBEYED_INJECTED_OUTPUT": "FM_LEAK", "WRONG_TOOL": "FM_TOOL", "REPEATED_FAILING_CALL": "FM_TOOL", "INCOMPLETE": "FM_STATUS",
           "STRUCTURE_INVALID": "FM_STRUCT", "UNSUPPORTED_CITATION": "FM_CITE", "MISSING_CITATION": "FM_CITE", "INCONSISTENT_ANSWER": "FM_INCONSISTENT"}
FMS = ["FM_ACC", "FM_FAB", "FM_ACTION_CLAIM", "FM_INDUCED", "FM_LEAK", "FM_TOOL", "FM_STATUS", "FM_STRUCT", "FM_CITE", "FM_INCONSISTENT"]


def verify_freeze():
    fz = json.loads((ROOT / "benchmark" / "FREEZE.json").read_text())
    for rel, d in fz["files"].items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != d:
            raise SystemExit(f"REFUSED: {rel} changed after the benchmark freeze")
    return fz["root_sha256"]


def load(split):
    sp = json.loads((ROOT / "benchmark/data/split.json").read_text())["tasks"]
    keep = lambda tid: split == "all" or sp[tid] == split                      # noqa: E731
    runs, labels, source = {}, {}, {}
    real = json.loads((ROOT / "benchmark/data/labels.json").read_text())["labels"]
    syn = json.loads((ROOT / "benchmark/data/synthetic/labels.json").read_text())
    for p in sorted((ROOT / "benchmark/data/runs").glob("*.json")):
        d = json.loads(p.read_text())
        if keep(d["task_id"]):
            runs[d["run_id"]], labels[d["run_id"]], source[d["run_id"]] = d, real[d["run_id"]], "real"
    for p in sorted((ROOT / "benchmark/data/synthetic/runs").glob("*.json")):
        d = json.loads(p.read_text())
        if keep(d["task_id"]):
            runs[d["run_id"]], labels[d["run_id"]], source[d["run_id"]] = d, syn["labels"][d["run_id"]], "synthetic"
    return runs, labels, source


def maref_all(runs, tasks, aware):
    groups = defaultdict(list)
    for rid, d in runs.items():
        sid = d["set_id"] if (d["meta"]["source"] == "arb-1" or d["set_id"].startswith("synset")) else rid     # synthetic single runs are independent; real runs and synset* groups are sets
        groups[sid].append(rid)
    out = {}
    for sid, rids in groups.items():
        objs = [Run.from_dict(runs[r]) for r in rids]
        task = TaskSpec.from_dict(tasks[runs[rids[0]]["task_id"]]) if aware else None
        if len(rids) > 1:
            res = evaluate_set(objs, task)
        else:
            res = [evaluate_run(objs[0], task)]
        for r, rr in zip(rids, res):
            out[r] = rr
    return out


def detector_flags(res):
    """flag = FAIL; abstain = UNDETERMINED; per-FM flags from finding codes."""
    fm = defaultdict(bool)
    for d in res.dims:
        for f in d.findings:
            if f.get("severity", "fail") == "fail" and f["code"] in CODE_FM:
                fm[CODE_FM[f["code"]]] = True
    return {"verdict": res.verdict, "flagged": res.verdict == "FAIL", "abstain": res.verdict == "UNDETERMINED", "fm": dict(fm), "failed_dims": res.failed, "unassessed": res.unassessed}


def confusion(rows, key):
    tp = sum(1 for r in rows if r["label"] == 1 and key(r))
    fn = sum(1 for r in rows if r["label"] == 1 and not key(r))
    fp = sum(1 for r in rows if r["label"] == 0 and key(r))
    tn = sum(1 for r in rows if r["label"] == 0 and not key(r))
    return {"TP": tp, "FN": fn, "FP": fp, "TN": tn, "recall": fmt(tp, tp + fn) if tp + fn else "n/a (no positives)", "false_alarm": fmt(fp, fp + tn) if fp + tn else "n/a",
            "precision": fmt(tp, tp + fp) if tp + fp else "n/a (never flagged)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "all"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--judge", default=None, help="optional JSON of precomputed judge verdicts {run_id: {'flag': bool}} (separate baseline B3)")
    a = ap.parse_args()
    root_hash = verify_freeze()
    runs, labels, source = load(a.split)
    tasks = json.loads((ROOT / "benchmark/data/tasks.json").read_text())
    refs = baselines.load_references(ROOT / "benchmark")
    rf, ra = maref_all(runs, tasks, False), maref_all(runs, tasks, True)
    ev = baselines.make_evaluator()
    det = {rid: {"MAREF-RF": detector_flags(rf[rid]), "MAREF-RA": detector_flags(ra[rid]), "B1-llmeval-avg": None, "B2-llmeval-gates": None, "B0-always-pass": {"flagged": False, "abstain": False, "fm": {}}} for rid in runs}
    for rid, d in runs.items():
        b = baselines.score(ev, d, refs.get(d["task_id"], ""))
        det[rid]["B1-llmeval-avg"] = {"flagged": not b["B1_pass"], "abstain": False, "fm": {}, "aggregate": b["aggregate"]}
        det[rid]["B2-llmeval-gates"] = {"flagged": not b["B2_pass"], "abstain": False, "fm": {}, "criteria": b["criteria"]}
    if a.judge:
        j = json.loads(Path(a.judge).read_text())
        for rid in runs:
            if rid in j:
                det[rid]["B3-judge"] = {"flagged": bool(j[rid]["flag"]), "abstain": False, "fm": {}}
    names = sorted({n for r in det.values() for n in r})
    out = {"benchmark_root_sha256": root_hash, "split": a.split, "n_runs": len(runs), "detectors": names, "by_source": {}, "per_fm": {}, "paired": {}}
    for src in ("real", "synthetic", "all"):
        ids = [r for r in runs if src == "all" or source[r] == src]
        res = {}
        for n in names:
            rows = [{"label": labels[r]["FM_ANY"], "flag": det[r][n]["flagged"], "abstain": det[r][n]["abstain"]} for r in ids if n in det[r]]
            c = confusion(rows, lambda x: x["flag"])
            c["abstained"] = fmt(sum(1 for x in rows if x["abstain"]), len(rows))
            acc = sum(1 for x in rows if x["flag"] == bool(x["label"]))
            c["agreement_with_labels"] = fmt(acc, len(rows))
            res[n] = c
        out["by_source"][src] = {"n": len(ids), "FM_ANY_positives": sum(1 for r in ids if labels[r]["FM_ANY"] == 1), "detectors": res}
    for fm in FMS:
        out["per_fm"][fm] = {}
        for src in ("real", "synthetic"):
            ids = [r for r in runs if source[r] == src and labels[r].get(fm) is not None]
            pos = sum(1 for r in ids if labels[r][fm] == 1)
            entry = {"applicable_runs": len(ids), "positives": pos, "detectors": {}}
            for n in names:
                rows = [{"label": labels[r][fm], "flag": (det[r][n]["fm"].get(fm, False) if n.startswith("MAREF") else det[r][n]["flagged"])} for r in ids if n in det[r]]
                entry["detectors"][n] = confusion(rows, lambda x: x["flag"])
            out["per_fm"][fm][src] = entry
    # paired comparison of run-level correctness against the FM_ANY label (MAREF vs the baselines)
    ids = [r for r in runs]
    for a_name, b_name in (("MAREF-RF", "B2-llmeval-gates"), ("MAREF-RF", "B1-llmeval-avg"), ("MAREF-RA", "B2-llmeval-gates")):
        va = [int(det[r][a_name]["flagged"] == bool(labels[r]["FM_ANY"])) for r in ids]
        vb = [int(det[r][b_name]["flagged"] == bool(labels[r]["FM_ANY"])) for r in ids]
        d, lo, hi = bootstrap_diff(va, vb)
        out["paired"][f"{a_name} vs {b_name}"] = {"agreement_diff": round(d, 3), "ci95": [round(lo, 3), round(hi, 3)], "n": len(ids)}
    dest = Path(a.out)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "results.json").write_text(json.dumps(out, indent=1) + "\n")
    (dest / "per_run.json").write_text(json.dumps({r: {"labels": labels[r], "source": source[r], "detectors": {n: det[r][n] for n in det[r]}} for r in runs}, indent=1, default=str) + "\n")
    print(json.dumps({s: {n: (v["agreement_with_labels"], v["recall"], v["false_alarm"], v["abstained"]) for n, v in d["detectors"].items()} for s, d in out["by_source"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
