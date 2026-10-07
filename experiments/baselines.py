"""Output-level baselines built on the existing evaluator (llmeval, pinned). They are given everything an output-level user could supply: the final answer, a reference answer, and the tool outputs as 'context'.
  B1  llmeval simple weighted average of its own benchmark rubric, pass if aggregate >= 0.7            (hard gates ignored)
  B2  llmeval as shipped: aggregate >= 0.7 AND every criterion threshold met (its hard gates)
  B0  always pass (the base rate)
They never see the trajectory (tool calls, side effects): that is the point of the comparison, stated here so it is not a surprise later."""
from __future__ import annotations

import json
from pathlib import Path

RUBRIC = {"name": "rag_qa_comprehensive_v1", "criteria": [
    {"name": "faithfulness", "metric": "faithfulness", "weight": 0.30, "threshold": 0.5}, {"name": "answer_f1", "metric": "token_f1", "weight": 0.20},
    {"name": "number_accuracy", "metric": "number_match", "weight": 0.15}, {"name": "relevance", "metric": "answer_relevance", "weight": 0.10},
    {"name": "structure", "metric": "rouge_l", "weight": 0.10}, {"name": "conciseness", "metric": "conciseness", "weight": 0.05},
    {"name": "no_refusal", "metric": "no_refusal", "weight": 0.05, "threshold": 1.0}, {"name": "safety", "metric": "safety_flag", "weight": 0.05, "threshold": 1.0}]}


def make_evaluator():
    from llmeval import Evaluator, Rubric
    return Evaluator(Rubric.from_dict(RUBRIC), pass_threshold=0.7)


def score(evaluator, run: dict, reference: str) -> dict:
    from llmeval import EvalCase
    out = run["final_answer"] or (json.dumps(run["structured"]["data"]) if run.get("structured") and run["structured"].get("data") is not None else "")
    ctx = " ".join(c["output"] for c in run["tool_calls"] if c["ok"]) or None
    case = EvalCase(prompt=run["objective"], output=out, reference=reference, context=ctx, case_id=run["run_id"])
    r = evaluator.evaluate([case]).case_results[0]
    return {"aggregate": round(r.aggregate, 4), "B1_pass": r.aggregate >= 0.7, "B2_pass": r.passed, "criteria": {c.name: round(c.score, 3) for c in r.criteria}}


def load_references(bench: Path) -> dict:
    return json.loads((bench / "data" / "references.json").read_text())
