"""Command line: evaluate runs, validate files against the schema, print the JSON schemas.
  maref evaluate runs.jsonl [--tasks tasks.json] [--json out.json] [--fail-on-fail]
  maref validate runs.jsonl [--tasks tasks.json]
  maref schema run|task
`runs` is a JSONL file (one run per line), a JSON array, or a directory of run .json files. Runs sharing a `set_id` are treated as repeats of one task (the consistency dimension needs them).
Exit status: 0 ok, 1 with --fail-on-fail when any run FAILs, 2 for invalid input."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from importlib import resources
from pathlib import Path

from .evaluate import evaluate_run, evaluate_set
from .schema import Run, SchemaError, TaskSpec
from .suite import summarize


def _load_json(path: Path):
    text = path.read_text(encoding="utf-8").strip()
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    return data if isinstance(data, list) else data.get("runs", [data])


def load_runs(src: str) -> list[Run]:
    p = Path(src)
    raw = [d for f in sorted(p.glob("*.json")) for d in _load_json(f)] if p.is_dir() else _load_json(p)
    out = []
    for i, d in enumerate(raw):
        try:
            out.append(Run.from_dict(d))
        except SchemaError as e:
            raise SchemaError(f"run #{i} ({d.get('run_id', '?')}): {e}") from e
    return out


def load_tasks(src: str | None) -> dict[str, TaskSpec]:
    if not src:
        return {}
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    items = data.values() if isinstance(data, dict) else data
    return {t["task_id"]: TaskSpec.from_dict(t) for t in items}


def evaluate_all(runs: list[Run], tasks: dict[str, TaskSpec]):
    groups = defaultdict(list)
    for r in runs:
        groups[r.set_id or r.run_id].append(r)
    results = {}
    for members in groups.values():
        task = tasks.get(members[0].task_id)
        res = evaluate_set(members, task) if len(members) > 1 else [evaluate_run(members[0], task)]
        for r, rr in zip(members, res, strict=True):
            results[r.run_id] = rr
    return [results[r.run_id] for r in runs]


def _print_summary(results, out=None):
    out = out or sys.stdout
    s = summarize(results)
    print(f"{s['n_runs']} runs: " + ", ".join(f"{k} {v}" for k, v in sorted(s["run_verdicts"].items())), file=out)
    for dim, v in s["dimensions"].items():
        rate = "n/a" if v["pass_rate"] is None else f"{v['pass_rate']:.0%} (95% CI {v['pass_rate_ci95'][0]:.0%}-{v['pass_rate_ci95'][1]:.0%})"
        cov = "n/a" if v["coverage"] is None else f"{v['coverage']:.0%}"
        print(f"  {dim:<28} pass {rate:<24} assessed {v['assessed']:>4}  NA {v['NA']:>4}  undetermined {v['UNDETERMINED']:>4}  coverage {cov}", file=out)
    if s["failure_codes"]:
        print("  failure codes: " + ", ".join(f"{k} {v}" for k, v in sorted(s["failure_codes"].items(), key=lambda kv: -kv[1])), file=out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="maref", description="Run-level (trajectory) evaluation of agent runs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluate", help="evaluate runs")
    e.add_argument("runs")
    e.add_argument("--tasks", help="optional task specifications (reference-aware mode); without it MAREF runs reference-free")
    e.add_argument("--json", dest="json_out", help="write full per-run results here")
    e.add_argument("--fail-on-fail", action="store_true", help="exit 1 if any run FAILs (CI gate)")
    v = sub.add_parser("validate", help="validate run/task files against the schema")
    v.add_argument("runs")
    v.add_argument("--tasks")
    s = sub.add_parser("schema", help="print a JSON schema")
    s.add_argument("which", choices=["run", "task"])
    a = ap.parse_args(argv)
    try:
        if a.cmd == "schema":
            print(resources.files("maref").joinpath("schemas", f"{a.which}.schema.json").read_text(encoding="utf-8"))
            return 0
        runs, tasks = load_runs(a.runs), load_tasks(a.tasks)
        if a.cmd == "validate":
            print(f"ok: {len(runs)} runs, {len(tasks)} task specs")
            return 0
        results = evaluate_all(runs, tasks)
    except (SchemaError, OSError, json.JSONDecodeError) as ex:
        print(f"invalid input: {ex}", file=sys.stderr)
        return 2
    _print_summary(results)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps([r.to_dict() for r in results], indent=1) + "\n", encoding="utf-8")
    return 1 if a.fail_on_fail and any(r.verdict == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
