"""Freeze the MAREF version that will be evaluated on the test split: sha256 of every source file of the library, the experiment code, the judge prompt freeze and the adjudication file, plus the benchmark root hash.
  python experiments/freeze_maref.py            # writes experiments/MAREF-FREEZE.json
`run_experiment.py --split test` refuses to run unless every hash matches AND no test run has been recorded (results/TEST-RUN.lock), so the test split is evaluated exactly once per frozen version."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def files():
    fs = sorted(p for p in (ROOT / "maref").rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".json"))
    fs += [ROOT / "experiments" / n for n in ("baselines.py", "run_experiment.py", "fit_b4.py", "b4_thresholds.json", "judge.py", "JUDGE-FREEZE.json")] + [ROOT / "experiments" / "adjudication.json", ROOT / "benchmark" / "FREEZE.json", ROOT / "pyproject.toml", ROOT / "docs" / "SPEC.md"]
    return [f for f in fs if f.exists()]


def compute():
    h = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files()}
    root = hashlib.sha256(json.dumps(h, sort_keys=True).encode()).hexdigest()
    return h, root


if __name__ == "__main__":
    h, root = compute()
    (ROOT / "experiments" / "MAREF-FREEZE.json").write_text(json.dumps({"version": "0.1.0", "root_sha256": root, "files": h}, indent=1) + "\n")
    print("frozen", root)
