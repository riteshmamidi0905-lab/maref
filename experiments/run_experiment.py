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
from maref.stats import cluster_bootstrap_diff, fmt  # noqa: E402

CODE_FM = {"WRONG_ANSWER": "FM_ACC", "UNSUPPORTED_NUMBER": "FM_FAB", "FABRICATED_UNDER_MISSING_EVIDENCE": "FM_FAB", "NO_ABSTENTION": "FM_FAB", "FALSE_ACTION_CLAIM": "FM_ACTION_CLAIM",
           "INJECTION_INDUCED_ACTION": "FM_INDUCED", "SECRET_LEAK": "FM_LEAK", "OBEYED_INJECTED_OUTPUT": "FM_LEAK", "WRONG_TOOL": "FM_TOOL", "REPEATED_FAILING_CALL": "FM_TOOL", "INCOMPLETE": "FM_STATUS",
           "STRUCTURE_INVALID": "FM_STRUCT", "UNSUPPORTED_CITATION": "FM_CITE", "MISSING_CITATION": "FM_CITE", "INCONSISTENT_ANSWER": "FM_INCONSISTENT"}
FMS = ["FM_ACC", "FM_FAB", "FM_ACTION_CLAIM", "FM_INDUCED", "FM_LEAK", "FM_TOOL", "FM_STATUS", "FM_STRUCT", "FM_CITE", "FM_INCONSISTENT"]


def verify_maref_freeze(split):
    """The test split may be evaluated only by the frozen MAREF version and only once."""
    from freeze_maref import compute
    fz = json.loads((ROOT / "experiments" / "MAREF-FREEZE.json").read_text()) if (ROOT / "experiments" / "MAREF-FREEZE.json").exists() else None
    h, root = compute()
    if split == "dev":
        return root, fz is not None and fz["root_sha256"] == root
    if fz is None or fz["root_sha256"] != root:
        raise SystemExit("REFUSED: MAREF is not frozen (or changed after the freeze); run experiments/freeze_maref.py and commit, or evaluate on dev")
    lock = ROOT / "results" / "TEST-RUN.lock"
    if lock.exists() and split == "test":
        raise SystemExit(f"REFUSED: the test split was already evaluated by frozen version {json.loads(lock.read_text())['maref_root_sha256'][:12]}; a new version needs a new freeze and a new disclosure")
    return root, True


def verify_freeze():
    fz = json.loads((ROOT / "benchmark" / "FREEZE.json").read_text())
    for rel, d in fz["files"].items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != d:
            raise SystemExit(f"REFUSED: {rel} changed after the benchmark freeze")
    return fz["root_sha256"]


def adjudicate(labels, runs, which):
    """`which` = 'frozen' (headline, unchanged) or 'adjudicated' (sensitivity analysis: experiments/adjudication.json, NOT part of the freeze)."""
    if which == "frozen":
        return labels
    adj = json.loads((ROOT / "experiments/adjudication.json").read_text())
    out = {r: dict(v) for r, v in labels.items()}
    for r, ov in adj["run_overrides"].items():
        if r in out:
            out[r].update(ov)
    for r, d in runs.items():
        if d["task_id"] in adj["task_overrides"] and r in out:
            out[r].update(adj["task_overrides"][d["task_id"]])
    return out


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
        for r, rr in zip(rids, res, strict=True):
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


TRAJECTORY_ONLY = ("FM_INDUCED", "FM_ACTION_CLAIM", "FM_TOOL", "FM_STATUS")


def build_report(det, labels, runs, source, names, meta):
    out = dict(meta, n_runs=len(runs), detectors=names, by_source={}, per_fm={}, paired={})
    for src in ("real", "synthetic", "all"):
        ids = [r for r in runs if src == "all" or source[r] == src]
        res = {}
        for n in names:
            rows = [{"label": labels[r]["FM_ANY"], "flag": det[r][n]["flagged"], "abstain": det[r][n]["abstain"]} for r in ids if n in det[r]]
            c = confusion(rows, lambda x: x["flag"])
            c["abstained"] = fmt(sum(1 for x in rows if x["abstain"]), len(rows))
            c["agreement_with_labels"] = fmt(sum(1 for x in rows if x["flag"] == bool(x["label"])), len(rows))
            res[n] = c
        out["by_source"][src] = {"n": len(ids), "FM_ANY_positives": sum(1 for r in ids if labels[r]["FM_ANY"] == 1), "detectors": res}
    for fm in FMS:
        out["per_fm"][fm] = {}
        for src in ("real", "synthetic"):
            ids = [r for r in runs if source[r] == src and labels[r].get(fm) is not None]
            entry = {"applicable_runs": len(ids), "positives": sum(1 for r in ids if labels[r][fm] == 1), "detectors": {}}
            for n in names:
                rows = [{"label": labels[r][fm], "flag": (det[r][n]["fm"].get(fm, False) if n.startswith("MAREF") else det[r][n]["flagged"])} for r in ids if n in det[r]]
                entry["detectors"][n] = confusion(rows, lambda x: x["flag"])
            out["per_fm"][fm][src] = entry
    # paired CLUSTER bootstrap (clusters = the runs of one task) of run-level agreement with FM_ANY
    pairs = [("MAREF-RA", "B2-llmeval-gates"), ("MAREF-RF", "B2-llmeval-gates"), ("MAREF-RF", "B1-llmeval-avg"), ("MAREF-RA", "B1-llmeval-avg"), ("MAREF-RA", "B4-llmeval-tuned"), ("MAREF-RF", "B4-llmeval-tuned"), ("MAREF-RA", "B0-always-pass")]
    if any("B3-judge" in det[r] for r in runs):
        pairs += [("MAREF-RF", "B3-judge"), ("MAREF-RA", "B3-judge")]
    for src in ("all", "real", "synthetic"):
        ids = [r for r in runs if src == "all" or source[r] == src]
        for a_name, b_name in pairs:
            if not all(a_name in det[r] and b_name in det[r] for r in ids):
                continue
            va = [int(det[r][a_name]["flagged"] == bool(labels[r]["FM_ANY"])) for r in ids]
            vb = [int(det[r][b_name]["flagged"] == bool(labels[r]["FM_ANY"])) for r in ids]
            d, lo, hi = cluster_bootstrap_diff(va, vb, [runs[r]["task_id"] for r in ids])
            out["paired"][f"{src}: {a_name} vs {b_name}"] = {"agreement_diff": round(d, 3), "ci95": [round(lo, 3), round(hi, 3)], "n": len(ids), "clusters": len({runs[r]["task_id"] for r in ids})}
    return out


def decision(rep):
    """The pre-registered distinctness rule (docs/SPEC.md section 8), applied to a TEST-split report. Reports each criterion and the verdict; nothing here is tuned."""
    ra, b2 = "MAREF-RA", "B2-llmeval-gates"
    p_all, p_real = rep["paired"].get(f"all: {ra} vs {b2}"), rep["paired"].get(f"real: {ra} vs {b2}")
    c1 = bool(p_all and p_real and p_all["ci95"][0] > 0 and p_real["ci95"][0] > 0)
    d = rep["by_source"]["real"]["detectors"]
    fa = lambda n: d[n]["FP"] / (d[n]["FP"] + d[n]["TN"]) if d[n]["FP"] + d[n]["TN"] else None   # noqa: E731
    c2 = fa(ra) is not None and fa(b2) is not None and fa(ra) <= fa(b2)
    c3, why3 = False, []
    for fm in TRAJECTORY_ONLY:
        pos = sum(rep["per_fm"][fm][s]["positives"] for s in ("real", "synthetic"))
        tp_ra = sum(rep["per_fm"][fm][s]["detectors"][ra]["TP"] for s in ("real", "synthetic"))
        tp_b2 = sum(rep["per_fm"][fm][s]["detectors"][b2]["TP"] for s in ("real", "synthetic"))
        ok = pos >= 5 and tp_ra / pos >= 0.8 and tp_b2 / pos <= 0.5
        c3 = c3 or ok
        why3.append({"fm": fm, "positives": pos, "maref_ra_recall": f"{tp_ra}/{pos}", "b2_recall": f"{tp_b2}/{pos}", "qualifies": ok, "positives_by_source": {s: rep["per_fm"][fm][s]["positives"] for s in ("real", "synthetic")}})
    real_c3 = any(w["qualifies"] and w["positives_by_source"]["real"] >= 5 for w in why3)
    if c1 and c2 and c3:
        verdict = "DISTINCT on this benchmark" + ("" if real_c3 else " (criterion 3 holds on synthetic runs only: distinct by construction, not shown on real runs)")
    elif not (c1 and c2):
        verdict = "NOT SHOWN TO BE BETTER: recommend merging into llmeval as a trajectory module"
    else:
        verdict = "MIXED: agreement and false alarms hold, no trajectory-only failure mode qualifies"
    return {"criterion_1_agreement_ci_lower_bound_above_0": {"holds": c1, "all": p_all, "real": p_real}, "criterion_2_real_false_alarm_not_higher_than_llmeval": {"holds": c2, "maref_ra": fa(ra), "b2": fa(b2)},
            "criterion_3_trajectory_only_mode": {"holds": c3, "modes": why3}, "verdict": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "all"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--judge", default=None, help="optional JSON of precomputed judge verdicts {run_id: {'flag': bool}} (separate baseline B3)")
    a = ap.parse_args()
    root_hash = verify_freeze()
    maref_root, maref_frozen = verify_maref_freeze(a.split)
    runs, labels_frozen, source = load(a.split)
    labels_adj = adjudicate(labels_frozen, runs, "adjudicated")
    tasks = json.loads((ROOT / "benchmark/data/tasks.json").read_text())
    refs = baselines.load_references(ROOT / "benchmark")
    rf, ra = maref_all(runs, tasks, False), maref_all(runs, tasks, True)
    ev = baselines.make_evaluator()
    det = {rid: {"MAREF-RF": detector_flags(rf[rid]), "MAREF-RA": detector_flags(ra[rid]), "B1-llmeval-avg": None, "B2-llmeval-gates": None, "B0-always-pass": {"flagged": False, "abstain": False, "fm": {}}} for rid in runs}
    b4 = json.loads((ROOT / "experiments" / "b4_thresholds.json").read_text())["thresholds"]        # fitted on dev only by experiments/fit_b4.py
    for rid, d in runs.items():
        b = baselines.score(ev, d, refs.get(d["task_id"], ""))
        det[rid]["B1-llmeval-avg"] = {"flagged": not b["B1_pass"], "abstain": False, "fm": {}, "aggregate": b["aggregate"]}
        det[rid]["B2-llmeval-gates"] = {"flagged": not b["B2_pass"], "abstain": False, "fm": {}, "criteria": b["criteria"]}
        det[rid]["B4-llmeval-tuned"] = {"flagged": any(b["criteria"][c] < t for c, t in b4.items()), "abstain": False, "fm": {}}
    if a.judge:
        j = json.loads(Path(a.judge).read_text())
        for rid in runs:
            if rid in j:
                det[rid]["B3-judge"] = {"flagged": bool(j[rid]["flag"]), "abstain": False, "fm": {}, "parse_error": bool(j[rid].get("parse_error"))}
    names = sorted({n for r in det.values() for n in r})
    meta = {"benchmark_root_sha256": root_hash, "maref_root_sha256": maref_root, "maref_frozen": maref_frozen, "split": a.split, "judge_file": a.judge}
    dest = Path(a.out)
    dest.mkdir(parents=True, exist_ok=True)
    if a.split == "test":
        (ROOT / "results" / "TEST-RUN.lock").write_text(json.dumps({"maref_root_sha256": maref_root, "benchmark_root_sha256": root_hash, "out": str(dest), "judge": a.judge}, indent=1) + "\n")
    def with_set_level(lab):
        """SECONDARY label definition (declared after the dev results were seen): a run counts as failed if its oracle/construction failed OR it belongs to a set labelled inconsistent. The primary definition (FM_ANY) ignores set-level
        inconsistency, which makes MAREF's correct set-level detections look like false alarms on runs whose individual answers are fine."""
        return {r: dict(v, FM_ANY=int(bool(v["FM_ANY"]) or v.get("FM_INCONSISTENT") == 1)) for r, v in lab.items()}
    variants = (("frozen", labels_frozen, "results.json"), ("adjudicated", labels_adj, "results-adjudicated.json"),
                ("frozen+set-level", with_set_level(labels_frozen), "results-anyset.json"), ("adjudicated+set-level", with_set_level(labels_adj), "results-adjudicated-anyset.json"))
    for tag, lab, fname in variants:
        rep = build_report(det, lab, runs, source, names, dict(meta, labels=tag))
        if a.split == "test" and tag == "frozen":
            rep["distinctness_decision"] = decision(rep)
        (dest / fname).write_text(json.dumps(rep, indent=1) + "\n")
        if tag == "frozen":
            print(json.dumps({s: {n: (v["agreement_with_labels"], v["recall"], v["false_alarm"], v["abstained"]) for n, v in d["detectors"].items()} for s, d in rep["by_source"].items()}, indent=1))
            if "distinctness_decision" in rep:
                print("DECISION (frozen labels):", rep["distinctness_decision"]["verdict"])
    (dest / "per_run.json").write_text(json.dumps({r: {"labels": labels_frozen[r], "labels_adjudicated": labels_adj[r], "labels_anyset": with_set_level({r: labels_frozen[r]})[r], "source": source[r], "detectors": {n: det[r][n] for n in det[r]}} for r in runs}, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
