"""Small statistics helpers (no dependencies). Every rate in a report is printed with its denominator and a Wilson 95% interval; with n this small the interval is the honest summary, not the point estimate."""
from __future__ import annotations

import math
import random


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fmt(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f}%, 95% CI {100 * lo:.0f}-{100 * hi:.0f}%)" if n else "0/0"


def bootstrap_diff(a: list[int], b: list[int], iters: int = 10000, seed: int = 20260101) -> tuple[float, float, float]:
    """Paired bootstrap of mean(a) - mean(b) over the same items. Returns (diff, lo, hi) for a 95% percentile interval."""
    assert len(a) == len(b) and a
    rng = random.Random(seed)
    n = len(a)
    base = sum(a) / n - sum(b) / n
    ds = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        ds.append(sum(a[i] for i in idx) / n - sum(b[i] for i in idx) / n)
    ds.sort()
    return base, ds[int(0.025 * iters)], ds[int(0.975 * iters) - 1]


def quantile(xs: list[float], q: float) -> float:
    s = sorted(xs)
    if not s:
        return 0.0
    i = min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))
    return s[i]
