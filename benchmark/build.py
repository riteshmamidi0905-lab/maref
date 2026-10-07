"""Build MAREF-Bench v1 from ARB-1 run artifacts. Deterministic: the same inputs produce the same files. Usage:
  python benchmark/build.py --arb /path/to/agent-runtime-bench --tags pass1 sample11 sample12 sample13 sample14
Writes benchmark/data/{runs,tasks.json,references.json,labels.json,split.json,manifest.json}. The split is fixed by task id (-01/-02 = dev, -03/-04 = test), stratified by category, NOT by outcome."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import labels as L  # noqa: E402
import taskspecs  # noqa: E402

POLICY = {"forbidden_tools": ["delete_account"], "approval_required_tools": ["write_note"]}


def to_run(arb: dict, tag: str, summary: dict, task: dict) -> dict:
    effects = [{"type": "write_note", "args": n, "approved": True} for n in arb["effects"]["notes"]] + [{"type": "delete_account", "args": {"account_id": a}, "approved": None} for a in arb["effects"]["deletions"]]
    st = arb.get("structured")
    return {"schema": "maref-run/1", "run_id": f"{tag}:{arb['task_id']}", "task_id": arb["task_id"], "set_id": arb["task_id"], "objective": task.get("objective") or task.get("user"),
            "final_answer": arb.get("final_answer"), "status": arb["status"], "stop_reason": arb.get("stop_reason"),
            "tool_calls": [{"name": c["name"], "args": c["args"], "ok": bool(c.get("ok")), "output": c.get("output") or "", "error": c.get("error") or "", "failure": c.get("failure") or None} for c in arb["tool_calls"]],
            "effects": effects, "evidence": [], "policy": POLICY, "structured": ({k: st[k] for k in ("valid", "repairs", "first_try_valid")} | {"data": st.get("data")}) if st else None,
            "meta": {"source": "arb-1", "tag": tag, "category": arb["category"], "adversarial": arb["adversarial"], "model": summary["model"], "sampling": summary["sampling"], "latency_s": arb["latency_s"],
                     "usage": arb["usage"], "bench_git_sha": summary.get("bench_git_sha"), "runtime_commit": summary["runtime_commit"]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arb", required=True)
    ap.add_argument("--tags", nargs="+", required=True)
    a = ap.parse_args()
    arb_root = Path(a.arb)
    bench = json.loads((arb_root / "benchmark" / "tasks.json").read_text())
    tasks = {t["id"]: t for t in bench["tasks"]}
    data = HERE / "data"
    (data / "runs").mkdir(parents=True, exist_ok=True)
    by_task, labels, runs_index = {}, {}, []
    prov = {}
    for tag in a.tags:
        summary = json.loads((arb_root / "reports" / tag / "summary.json").read_text())
        prov[tag] = {"model": summary["model"], "sampling": summary["sampling"], "bench_git_sha": summary.get("bench_git_sha")}
        for p in sorted((arb_root / "reports" / tag / "runs").glob("*.json")):
            arb = json.loads(p.read_text())
            run = to_run(arb, tag, summary, tasks[arb["task_id"]])
            (data / "runs" / f"{tag}__{arb['task_id']}.json").write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
            lab = L.label(arb)
            lab["FM_ANY"] = int(not arb["grade"]["success"])
            labels[run["run_id"]] = lab
            by_task.setdefault(arb["task_id"], []).append(arb)
            runs_index.append(run["run_id"])
    sets = L.set_labels(by_task)
    for rid in labels:
        tid = rid.split(":")[1]
        labels[rid]["FM_INCONSISTENT"] = sets[tid]
    (data / "tasks.json").write_text(json.dumps(taskspecs.T, indent=1, ensure_ascii=False) + "\n")
    (data / "references.json").write_text(json.dumps(taskspecs.REFERENCES, indent=1, ensure_ascii=False) + "\n")
    split = {tid: ("dev" if int(tid[-2:]) <= 2 else "test") for tid in tasks}
    (data / "split.json").write_text(json.dumps({"rule": "task id suffix -01/-02 = dev, -03/-04 = test (stratified by category, independent of outcomes)", "tasks": split}, indent=1) + "\n")
    (data / "labels.json").write_text(json.dumps({"fm_doc": L.FM_DOC, "label_rules": "benchmark/labels.py", "labels": labels, "set_labels": sets}, indent=1) + "\n")
    counts = {fm: {"applicable_runs": sum(1 for v in labels.values() if v.get(fm) is not None), "present": sum(1 for v in labels.values() if v.get(fm) == 1)} for fm in L.FM + ["FM_ANY"]}
    arb_sha = subprocess.run(["git", "-C", str(arb_root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    (data / "manifest.json").write_text(json.dumps({"benchmark": "MAREF-Bench-real-v1", "source": "ARB-1 run artifacts", "arb_repo_head_at_build": arb_sha, "tags": a.tags, "provenance": prov, "n_runs": len(runs_index), "n_tasks": len(tasks),
                                                    "counts": counts}, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    print(len(runs_index), "runs")


if __name__ == "__main__":
    main()
