"""Render a results directory (written by run_experiment.py) into a markdown evaluation report, so no number in the document is transcribed by hand.
  python experiments/render_evaluation.py results/test > docs/EVALUATION-test.md"""
import json
import sys
from pathlib import Path

DET_ORDER = ["MAREF-RA", "MAREF-RF", "B3-judge", "B4-llmeval-tuned", "B2-llmeval-gates", "B1-llmeval-avg", "B0-always-pass"]
LABELS = {"MAREF-RA": "MAREF reference-aware", "MAREF-RF": "MAREF reference-free", "B3-judge": "B3 judge-only (4B local model)", "B4-llmeval-tuned": "B4 llmeval, thresholds fitted on dev",
          "B2-llmeval-gates": "B2 llmeval hard gates (as shipped)", "B1-llmeval-avg": "B1 llmeval simple average", "B0-always-pass": "B0 always pass (base rate)"}
SHORT = {"MAREF-RA": "MAREF-RA", "MAREF-RF": "MAREF-RF", "B3-judge": "B3 judge", "B4-llmeval-tuned": "B4 tuned llmeval", "B2-llmeval-gates": "B2 llmeval gates", "B1-llmeval-avg": "B1 llmeval avg", "B0-always-pass": "B0 always pass"}
VARIANTS = [("results.json", "Frozen labels, primary definition `FM_ANY` (the headline; the pre-registered decision uses this one)"),
            ("results-adjudicated.json", "Adjudicated labels, primary definition (sensitivity analysis; same author; not independent)"),
            ("results-anyset.json", "Frozen labels, secondary definition `FM_ANY` or member of an inconsistent set (declared after dev results were seen; exploratory)"),
            ("results-adjudicated-anyset.json", "Adjudicated labels, secondary definition (exploratory)")]


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def short(s):
    return s.split(" (")[0] if isinstance(s, str) else s


def render(d: Path) -> str:
    out = []
    for fname, title in VARIANTS:
        p = d / fname
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        dets = [n for n in DET_ORDER if n in r["detectors"]]
        out.append(f"## {title}\n")
        if fname == "results.json":
            out.append(f"Split `{r['split']}`, {r['n_runs']} runs. Benchmark root `{r['benchmark_root_sha256'][:12]}`, MAREF root `{r['maref_root_sha256'][:12]}` (frozen: {r['maref_frozen']}).\n")
        for src in ("real", "synthetic", "all"):
            b = r["by_source"][src]
            out.append(f"**{src}** runs: n = {b['n']}, failing (label) = {b['FM_ANY_positives']}.\n")
            out.append(table(["detector", "agreement with labels", "recall (flags failing runs)", "false-alarm rate (flags clean runs)", "precision", "abstained"],
                             [[LABELS[n], b["detectors"][n]["agreement_with_labels"], b["detectors"][n]["recall"], b["detectors"][n]["false_alarm"], b["detectors"][n]["precision"], b["detectors"][n]["abstained"]] for n in dets]) + "\n")
        if fname == "results.json":
            out.append("### Per failure mode (a mode is flagged by MAREF through its own finding codes; the baselines can only flag the whole run)\n")
            rows = []
            for fm, srcs in r["per_fm"].items():
                for src, e in srcs.items():
                    if e["applicable_runs"] == 0:
                        continue
                    cells = []
                    for n in dets:
                        c = e["detectors"][n]
                        cells.append(f"{c['TP']}/{e['positives']}" + (f" (FP {c['FP']})" if c["FP"] else ""))
                    rows.append([fm, src, e["applicable_runs"], e["positives"] if e["positives"] else "**0 (no positives)**"] + cells)
            out.append(table(["mode", "source", "applicable runs", "positives"] + [SHORT[n] for n in dets], rows) + "\n")
            out.append("Cells are true positives / positives, with false positives in brackets. A mode with no positives cannot have a recall: it is not reported as 100%.\n")
        out.append("### Paired cluster-bootstrap difference in run-level agreement with the labels (a vs b; positive = a agrees more often)\n")
        out.append(table(["comparison", "difference", "95% interval", "runs", "task clusters"], [[k, v["agreement_diff"], v["ci95"], v["n"], v["clusters"]] for k, v in r["paired"].items()]) + "\n")
        if "distinctness_decision" in r:
            dd = r["distinctness_decision"]
            out.append("### Pre-registered distinctness decision (docs/SPEC.md section 8)\n")
            c1, c2, c3 = dd["criterion_1_agreement_ci_lower_bound_above_0"], dd["criterion_2_real_false_alarm_not_higher_than_llmeval"], dd["criterion_3_trajectory_only_mode"]
            out.append(f"1. Agreement interval above zero on pooled and on real runs: **{c1['holds']}** (pooled {c1['all']['agreement_diff'] if c1['all'] else 'n/a'} {c1['all']['ci95'] if c1['all'] else ''}; real {c1['real']['agreement_diff'] if c1['real'] else 'n/a'} {c1['real']['ci95'] if c1['real'] else ''}).")
            out.append(f"2. MAREF-RA real false-alarm rate not higher than llmeval-with-gates: **{c2['holds']}** (MAREF {c2['maref_ra']}, llmeval {c2['b2']}).")
            out.append(f"3. A trajectory-only mode with at least 5 positives, MAREF recall at least 80% and llmeval recall at most 50%: **{c3['holds']}**.\n")
            out.append(table(["mode", "positives (real / synthetic)", "MAREF-RA recall", "llmeval-gates recall", "qualifies"], [[w["fm"], f"{w['positives']} ({w['positives_by_source']['real']} / {w['positives_by_source']['synthetic']})", w["maref_ra_recall"], w["b2_recall"], w["qualifies"]] for w in c3["modes"]]) + "\n")
            out.append(f"**Verdict: {dd['verdict']}.**\n")
    return "\n".join(out)


if __name__ == "__main__":
    print(render(Path(sys.argv[1])))
