"""Typed evaluation schema. A RUN is the unit of evaluation (not a single output): the objective, the trajectory, every tool call with its result, the observed side effects, the final answer and how the
run ended. A TASKSPEC is OPTIONAL reference information (expected answer, constraints, required/forbidden tools, canaries, expected terminal status): with it MAREF runs 'reference-aware'; without it,
'reference-free', and any dimension that needs a reference says UNDETERMINED instead of guessing. Plain dataclasses + JSON (schema/run.schema.json, schema/task.schema.json); no dependencies."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

RUN_SCHEMA = "maref-run/1"
TASK_SCHEMA = "maref-task/1"
STATUSES = ("completed", "stopped", "failed", "escalated")


class SchemaError(ValueError):
    pass


def _req(d: dict, key: str, typ):
    if key not in d:
        raise SchemaError(f"missing required field '{key}'")
    if not isinstance(d[key], typ):
        raise SchemaError(f"field '{key}' must be {typ}, got {type(d[key]).__name__}")
    return d[key]


@dataclass
class ToolCall:
    name: str
    args: dict
    ok: bool
    output: str = ""
    error: str = ""
    failure: str | None = None        # 'denied' | 'tool_error' | 'validation' | 'injection_blocked' | ... | None
    id: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> ToolCall:
        return cls(_req(d, "name", str), _req(d, "args", dict), bool(_req(d, "ok", (bool, type(None))) or False), d.get("output") or "", d.get("error") or "", d.get("failure") or None, d.get("id") or "")


@dataclass
class Effect:
    type: str                          # e.g. 'write_note', 'delete_account'
    args: dict = field(default_factory=dict)
    approved: bool | None = None       # True/False if an approval decision was recorded for it, None if none was

    @classmethod
    def from_dict(cls, d: dict) -> Effect:
        return cls(_req(d, "type", str), d.get("args") or {}, d.get("approved"))


@dataclass
class Run:
    run_id: str
    task_id: str
    objective: str
    status: str
    final_answer: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    effects: list[Effect] = field(default_factory=list)
    stop_reason: str | None = None
    set_id: str | None = None          # runs of the same task share a set_id (consistency is a set-level dimension)
    evidence: list[str] = field(default_factory=list)       # context documents given to the model besides tool outputs
    policy: dict = field(default_factory=dict)              # operator policy: {'forbidden_tools': [...], 'approval_required_tools': [...]}
    structured: dict | None = None                          # {'valid': bool, 'repairs': int, 'first_try_valid': bool}
    meta: dict = field(default_factory=dict)                # model, sampling, latency, usage: carried, never scored
    schema: str = RUN_SCHEMA

    @classmethod
    def from_dict(cls, d: dict) -> Run:
        if d.get("schema") != RUN_SCHEMA:
            raise SchemaError(f"unsupported schema {d.get('schema')!r}")
        status = _req(d, "status", str)
        if status not in STATUSES:
            raise SchemaError(f"status must be one of {STATUSES}")
        return cls(_req(d, "run_id", str), _req(d, "task_id", str), _req(d, "objective", str), status, d.get("final_answer"), [ToolCall.from_dict(x) for x in d.get("tool_calls", [])],
                   [Effect.from_dict(x) for x in d.get("effects", [])], d.get("stop_reason"), d.get("set_id"), list(d.get("evidence") or []), d.get("policy") or {}, d.get("structured"), d.get("meta") or {})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskSpec:
    """Everything optional. Absent means 'not declared', never 'false'."""
    task_id: str
    answerable: bool | None = None
    reference_answers: list[str] = field(default_factory=list)        # regexes; any match = correct
    constraints: dict = field(default_factory=dict)                   # {'regex': [], 'not_regex': [], 'must_include': [], 'must_not_include': []}
    required_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    tool_args: list[dict] = field(default_factory=list)               # [{'tool': 'convert_units', 'match': {'value': 42}}]
    canaries: list[str] = field(default_factory=list)                 # strings that must never appear in the answer
    cite_required: list[str] = field(default_factory=list)
    expected_status: list[list] = field(default_factory=list)         # [['completed', None]] or [['stopped', 'step_limit']]
    forbidden_outputs: list[str] = field(default_factory=list)        # regexes the answer must not match (an injected instruction's requested output)
    schema: str = TASK_SCHEMA

    @classmethod
    def from_dict(cls, d: dict) -> TaskSpec:
        if d.get("schema") != TASK_SCHEMA:
            raise SchemaError(f"unsupported schema {d.get('schema')!r}")
        return cls(_req(d, "task_id", str), d.get("answerable"), list(d.get("reference_answers") or []), d.get("constraints") or {}, list(d.get("required_tools") or []), list(d.get("forbidden_tools") or []),
                   list(d.get("tool_args") or []), list(d.get("canaries") or []), list(d.get("cite_required") or []), list(d.get("expected_status") or []), list(d.get("forbidden_outputs") or []))

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DimResult:
    dim: str
    verdict: str                       # PASS | FAIL | NA | UNDETERMINED
    confidence: str                    # deterministic | heuristic | judge
    findings: list[dict] = field(default_factory=list)       # [{'code': 'UNSUPPORTED_NUMBER', 'detail': ..., 'evidence': ...}]
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunResult:
    run_id: str
    task_id: str
    verdict: str                       # PASS | FAIL | UNDETERMINED
    dims: list[DimResult]
    failed: list[str] = field(default_factory=list)
    unassessed: list[str] = field(default_factory=list)       # applicable dimensions that could not be decided
    score: float | None = None         # fraction of assessed dimensions that passed; REPORTED, NEVER USED TO GATE
    mode: str = "reference-free"

    def to_dict(self) -> dict:
        return asdict(self)
