"""Hash-lock the benchmark: python benchmark/freeze.py  -> benchmark/FREEZE.json. tests/test_benchmark_frozen.py fails if any locked file changes; experiments refuse to run on a changed benchmark."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def files():
    out = [p for p in HERE.rglob("*") if p.is_file() and p.name not in ("FREEZE.json",) and "__pycache__" not in p.parts and p.suffix in (".json", ".py")]
    return sorted(out)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    fz = {rel: digest(p) for p in files() for rel in [str(p.relative_to(ROOT))]}
    root = hashlib.sha256(json.dumps(fz, sort_keys=True).encode()).hexdigest()
    (HERE / "FREEZE.json").write_text(json.dumps({"benchmark": "MAREF-Bench v1", "frozen_before": "any MAREF checker was written or run", "root_sha256": root, "n_files": len(fz), "files": fz}, indent=1) + "\n")
    print(root, len(fz), "files")


if __name__ == "__main__":
    main()
