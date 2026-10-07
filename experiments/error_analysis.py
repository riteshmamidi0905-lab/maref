"""List every disagreement between a detector and the labels (false alarms and misses) with the findings that caused it, from a results directory written by run_experiment.py. Read-only.
  python experiments/error_analysis.py results/test [--detector MAREF-RA] [--labels frozen|adjudicated]"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--detector", default="MAREF-RA")
    ap.add_argument("--labels", default="frozen", choices=["frozen", "adjudicated", "anyset"])
    a = ap.parse_args()
    per = json.loads((Path(a.results_dir) / "per_run.json").read_text())
    key = {"frozen": "labels", "adjudicated": "labels_adjudicated", "anyset": "labels_anyset"}[a.labels]
    rows = []
    for rid, v in sorted(per.items()):
        d = v["detectors"].get(a.detector)
        if d is None:
            continue
        lab = bool(v[key]["FM_ANY"])
        if d["flagged"] != lab:
            fms = sorted(k for k, x in v[key].items() if x == 1 and k != "FM_ANY")
            rows.append((("MISS" if lab else "FALSE ALARM"), rid, v["source"], fms, sorted(k for k, x in d.get("fm", {}).items() if x), d.get("failed_dims", []), d.get("unassessed", [])))
    print(f"{a.detector} vs {a.labels} labels: {len(rows)} disagreements ({sum(1 for r in rows if r[0] == 'MISS')} misses, {sum(1 for r in rows if r[0] != 'MISS')} false alarms)")
    for kind, rid, src, fms, flagged_fm, fdims, un in rows:
        print(f"  {kind:11} {rid:34} {src:9} labelled {fms or '-'}  MAREF flagged {flagged_fm or '-'}  failed dims {fdims or '-'}")


if __name__ == "__main__":
    main()
