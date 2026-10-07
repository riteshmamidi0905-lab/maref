"""The experiment machinery: cluster bootstrap, label adjudication, the pre-registered decision rule, and the one-time test lock."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT))
import run_experiment as X  # noqa: E402

from maref.stats import cluster_bootstrap_diff  # noqa: E402


def test_cluster_bootstrap_is_wider_than_item_bootstrap_for_correlated_items():
    from maref.stats import bootstrap_diff
    a = [1] * 20 + [0] * 20
    b = [0] * 20 + [1] * 20
    clusters = ["x"] * 20 + ["y"] * 20          # perfectly correlated within a cluster
    d1, lo1, hi1 = bootstrap_diff(a, b)
    d2, lo2, hi2 = cluster_bootstrap_diff(a, b, clusters)
    assert d1 == d2 == 0.0 and (hi2 - lo2) > (hi1 - lo1)


def test_adjudication_changes_only_the_listed_labels():
    runs = {"pass1:ARB-TF-02": {"task_id": "ARB-TF-02"}, "pass1:ARB-MT-01": {"task_id": "ARB-MT-01"}}
    labels = {"pass1:ARB-TF-02": {"FM_ANY": 1, "FM_INCONSISTENT": 1}, "pass1:ARB-MT-01": {"FM_ANY": 1, "FM_INDUCED": 1, "FM_INCONSISTENT": 0}}
    frozen = X.adjudicate(labels, runs, "frozen")
    adj = X.adjudicate(labels, runs, "adjudicated")
    assert frozen == labels
    assert adj["pass1:ARB-TF-02"] == {"FM_ANY": 0, "FM_INCONSISTENT": 0}
    assert adj["pass1:ARB-MT-01"] == labels["pass1:ARB-MT-01"]
    assert labels["pass1:ARB-TF-02"]["FM_ANY"] == 1, "the input must not be mutated"


def test_test_split_refuses_without_a_matching_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(X, "ROOT", tmp_path)
    (tmp_path / "experiments").mkdir()
    (tmp_path / "results").mkdir()
    sys.modules.pop("freeze_maref", None)
    import freeze_maref
    monkeypatch.setattr(freeze_maref, "ROOT", tmp_path)
    monkeypatch.setattr(freeze_maref, "files", lambda: [])
    with pytest.raises(SystemExit, match="not frozen"):
        X.verify_maref_freeze("test")
    root, ok = X.verify_maref_freeze("dev")
    assert ok is False
