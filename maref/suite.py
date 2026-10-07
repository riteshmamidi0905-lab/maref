"""Suite-level reporting: per-dimension verdict counts, pass rate among assessed runs with a Wilson interval, coverage (assessed / applicable), failure-code counts, run verdicts."""
from __future__ import annotations

from collections import Counter, defaultdict

from .stats import wilson


def summarize(results) -> dict:
    per = defaultdict(Counter)
    codes = Counter()
    verdicts = Counter(r.verdict for r in results)
    for r in results:
        for d in r.dims:
            per[d.dim][d.verdict] += 1
            for f in d.findings:
                if f.get("severity", "fail") == "fail":
                    codes[f["code"]] += 1
    dims = {}
    for dim, c in per.items():
        assessed = c["PASS"] + c["FAIL"]
        applicable = assessed + c["UNDETERMINED"]
        lo, hi = wilson(c["PASS"], assessed) if assessed else (0.0, 1.0)
        dims[dim] = {"PASS": c["PASS"], "FAIL": c["FAIL"], "NA": c["NA"], "UNDETERMINED": c["UNDETERMINED"], "assessed": assessed, "pass_rate": (c["PASS"] / assessed) if assessed else None,
                     "pass_rate_ci95": [round(lo, 3), round(hi, 3)] if assessed else None, "coverage": (assessed / applicable) if applicable else None}
    return {"n_runs": len(results), "run_verdicts": dict(verdicts), "dimensions": dims, "failure_codes": dict(codes)}
