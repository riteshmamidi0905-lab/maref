"""The public wording in docs/CLAIM.md (and README/EVALUATION) is checked against the recorded test-split results, so the claim cannot drift from the data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = json.loads((ROOT / "results" / "test" / "results.json").read_text())
CLAIM = (ROOT / "docs" / "CLAIM.md").read_text()
EVAL = (ROOT / "docs" / "EVALUATION.md").read_text()
README = (ROOT / "README.md").read_text()


def _cell(src, det, key):
    return RES["by_source"][src]["detectors"][det][key].split(" (")[0]


def test_card_numbers_are_the_recorded_numbers():
    assert _cell("all", "MAREF-RA", "recall") == "33/33"
    assert _cell("all", "MAREF-RA", "false_alarm") == "36/154"
    assert _cell("all", "MAREF-RA", "agreement_with_labels") == "151/187"
    for text in (CLAIM, EVAL, README):
        assert "33/33" in text and "36/154" in text and "151/187" in text


def test_pre_registered_comparison_against_llmeval_gates_is_quoted_exactly():
    p, r = RES["paired"]["all: MAREF-RA vs B2-llmeval-gates"], RES["paired"]["real: MAREF-RA vs B2-llmeval-gates"]
    assert (round(p["agreement_diff"], 3), [round(x, 3) for x in p["ci95"]]) == (0.257, [0.097, 0.419])
    assert (round(r["agreement_diff"], 3), [round(x, 3) for x in r["ci95"]]) == (0.292, [0.092, 0.492])
    assert (RES["by_source"]["real"]["detectors"]["MAREF-RA"]["FP"], RES["by_source"]["real"]["detectors"]["B2-llmeval-gates"]["FP"]) == (30, 65)
    assert "+0.257" in CLAIM and "[0.097, 0.419]" in CLAIM and "+0.292" in CLAIM and "[0.092, 0.492]" in CLAIM and "30/112" in CLAIM and "65/112" in CLAIM


def test_stronger_baselines_are_not_shown_better_and_agreements_are_quoted():
    assert [_cell("all", d, "agreement_with_labels") for d in ("B0-always-pass", "B4-llmeval-tuned", "B3-judge")] == ["154/187", "158/187", "166/187"]
    for d in ("B0-always-pass", "B4-llmeval-tuned", "B3-judge"):
        lo, hi = RES["paired"][f"all: MAREF-RA vs {d}"]["ci95"]
        assert lo < 0 < hi, "the claim says every interval includes zero"
    assert "154/187" in CLAIM and "158/187" in CLAIM and "166/187" in CLAIM


def test_verdict_is_preserved_verbatim_and_criterion_3_failed_as_described():
    dd = RES["distinctness_decision"]
    assert dd["verdict"] == "MIXED: agreement and false alarms hold, no trajectory-only failure mode qualifies"
    assert dd["criterion_1_agreement_ci_lower_bound_above_0"]["holds"] and dd["criterion_2_real_false_alarm_not_higher_than_llmeval"]["holds"] and not dd["criterion_3_trajectory_only_mode"]["holds"]
    modes = {m["fm"]: m for m in dd["criterion_3_trajectory_only_mode"]["modes"]}
    assert modes["FM_ACTION_CLAIM"]["positives"] == 5 and modes["FM_ACTION_CLAIM"]["maref_ra_recall"] == "5/5" and modes["FM_ACTION_CLAIM"]["b2_recall"] == "4/5"
    assert not any(m["qualifies"] for m in modes.values())
    assert dd["verdict"] in CLAIM and dd["verdict"] in EVAL


def test_the_primary_label_is_the_headline_and_secondary_labels_are_labelled_as_sensitivity():
    assert RES["labels"] == "frozen"
    assert "not independent validation" in CLAIM.lower() and "not independent validation" in EVAL.lower() and "not independent validation" in README.lower()
    assert "sensitivity" in CLAIM.lower() and "sensitivity analyses (not the headline" in EVAL.lower()
    for item in ("known before MAREF-Bench", "tuned on the dev split", "test-split answers had been read", "v1.1", "run once and is now spent", "lexicon blind spots", "no independent human"):
        assert item.lower() in CLAIM.lower(), item
