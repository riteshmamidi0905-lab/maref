"""CLI behaviour on tiny hand-made inputs (not benchmark data)."""
import json

from maref.cli import evaluate_all, load_runs, main

POLICY = {"forbidden_tools": ["delete_account"], "approval_required_tools": ["write_note"]}


def _run(rid, final, calls=(), set_id=None, status="completed"):
    return {"schema": "maref-run/1", "run_id": rid, "task_id": "t1", "set_id": set_id, "objective": "How many items are in order A100?", "final_answer": final, "status": status,
            "tool_calls": list(calls), "effects": [], "policy": POLICY}


GOOD = _run("good", "Order A100 has 2 items.", [{"name": "get_order", "args": {"order_id": "A100"}, "ok": True, "output": "qty=2"}])
BAD = _run("bad", "Order A100 has 41 items.", [{"name": "get_order", "args": {"order_id": "A100"}, "ok": True, "output": "qty=2"}])


def test_evaluate_exit_codes_and_json(tmp_path, capsys):
    p = tmp_path / "runs.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in (GOOD, BAD)))
    out = tmp_path / "out.json"
    assert main(["evaluate", str(p), "--json", str(out)]) == 0
    res = {r["run_id"]: r for r in json.loads(out.read_text())}
    assert res["good"]["verdict"] == "PASS" and res["bad"]["verdict"] == "FAIL" and "groundedness" in res["bad"]["failed"]
    assert main(["evaluate", str(p), "--fail-on-fail"]) == 1
    assert "2 runs" in capsys.readouterr().out


def test_invalid_input_exits_2(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([{"schema": "maref-run/1", "run_id": "x"}]))
    assert main(["validate", str(p)]) == 2
    assert "missing required field" in capsys.readouterr().err


def test_set_id_groups_repeats_for_consistency(tmp_path):
    a = _run("r1", "Order A100 has 2 items.", set_id="s")
    b = _run("r2", "Order A100 has 7 items.", set_id="s")
    p = tmp_path / "r.json"
    p.write_text(json.dumps([a, b]))
    res = evaluate_all(load_runs(str(p)), {})
    assert all("consistency" in r.failed or any(d.dim == "consistency" for d in r.dims) for r in res)


def test_schema_command_prints_json(capsys):
    assert main(["schema", "run"]) == 0
    assert json.loads(capsys.readouterr().out)["$id"] == "maref-run/1"
