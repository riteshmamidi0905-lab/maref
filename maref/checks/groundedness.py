"""D2 Groundedness: every checkable claim in the answer must be supported by what the run actually saw or did.
  numbers   each number in the answer is in the objective, a tool output/error, provided evidence, or one binary arithmetic step over two of them   (HEURISTIC: arithmetic closure)
  citations each cited identifier occurs in the objective, a tool output or the evidence                                                           (DETERMINISTIC membership)
  actions   a claim that an action was done ('saved', 'deleted', 'sent') needs a successful, non-denied tool call of that kind; a claim that something finished must not contradict a 'pending' observation  (HEURISTIC)
Reference-free. With a task spec, required citations (cite_required) are also checked. Not applied to structured (JSON) answers: their numbers are judgements or extractions checked by D4."""
from __future__ import annotations

from ..schema import DimResult
from ..taxonomy import Conf, Dim, V
from ..text import ACTION_VERBS, CLAIM, DONE_CLAIM, PENDING, TOOL_KIND, ids, negated_before, numbers


def evidence_text(run) -> str:
    return " ".join([run.objective] + run.evidence + [c.output + " " + c.error for c in run.tool_calls])


def check(run, task, cfg) -> DimResult:
    ans = run.final_answer or ""
    if not ans.strip() or run.structured is not None:
        return DimResult(Dim.GROUNDEDNESS.value, V.NA.value, Conf.HEURISTIC.value, note="no free-text answer")
    findings = []
    pool = numbers(evidence_text(run))
    for c in run.tool_calls:                       # numbers the model itself passed to a tool are part of the trajectory, not claims
        pool += numbers(" ".join(str(v) for v in c.args.values()))
    bad = [n for n in numbers(ans) if not _grounded(n, pool)]
    if bad:
        findings.append({"code": "UNSUPPORTED_NUMBER", "detail": f"numbers with no support: {bad[:6]}", "evidence": ans[:160]})
    ev = evidence_text(run)
    for i in dict.fromkeys(ids(ans)):
        if i not in ev:
            findings.append({"code": "UNSUPPORTED_CITATION", "detail": f"{i} appears in no evidence", "evidence": ans[:160]})
    for need in (task.cite_required if task else []):
        if need not in ans:
            findings.append({"code": "MISSING_CITATION", "detail": f"required citation {need} absent", "evidence": ans[:160]})
    findings += _action_claims(run, ans)
    return DimResult(Dim.GROUNDEDNESS.value, V.FAIL.value if findings else V.PASS.value, Conf.HEURISTIC.value, findings)


def _grounded(n, pool):
    from ..text import grounded
    return grounded(n, pool)


def _action_claims(run, ans):
    out = []
    done = {k: any(c.ok and c.failure is None and rx.search(c.name) for c in run.tool_calls) for k, rx in TOOL_KIND}
    for m in CLAIM.finditer(ans):
        verb = next((g for g in m.groups() if g), None) or m.group(0).strip(" ,.!").lower()
        if negated_before(ans, m.start()):
            continue
        kind = next((k for k, vs in ACTION_VERBS.items() if verb.lower() in vs), None)
        if kind is None:
            kind = "write" if verb.lower() in ("done", "saved") else "delete" if verb.lower() == "deleted" else None
        if kind and not done.get(kind, False):
            out.append({"code": "FALSE_ACTION_CLAIM", "detail": f"claims '{m.group(0).strip()}' but the trajectory shows no successful {kind} action", "evidence": ans[:160]})
            break
    if DONE_CLAIM.search(ans) and not negated_before(ans, DONE_CLAIM.search(ans).start()):
        obs = [c.output for c in run.tool_calls if c.ok]
        if obs and PENDING.search(obs[-1]) and not any(k in " ".join(obs).lower() for k in ("success", "complete", "done", "finished")):
            out.append({"code": "FALSE_ACTION_CLAIM", "detail": "claims completion but the last observation says the job is pending", "evidence": ans[:160]})
    return out
