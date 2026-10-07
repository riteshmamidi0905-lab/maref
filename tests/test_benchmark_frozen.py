import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_benchmark_files_match_the_freeze():
    fz = json.loads((ROOT / "benchmark" / "FREEZE.json").read_text())
    assert fz["n_files"] == len(fz["files"]) > 380
    for rel, digest in fz["files"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, f"{rel} changed after the benchmark freeze: a change needs MAREF-Bench v2"
    new = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "benchmark").rglob("*") if p.is_file() and p.suffix in (".json", ".py") and p.name != "FREEZE.json" and "__pycache__" not in p.parts)
    assert new == sorted(fz["files"]), "files were added to or removed from the frozen benchmark"
    assert hashlib.sha256(json.dumps(fz["files"], sort_keys=True).encode()).hexdigest() == fz["root_sha256"]
