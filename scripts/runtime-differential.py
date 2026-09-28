#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""The behavioral tier's first command-level measure — both doors.

`tests/runtime/` reserved its fixtures "until the vertical slice lands";
the slice landed releases ago, and nobody had measured the tier by
command. This differential drives every fixture through the PUBLIC
surfaces (the binary boundary · never linkage):

- the RUN door · `nika run <input.nika> --json` (+ `--var k=v` from
  run.json `vars`, its `env` overlaid on the subprocess) — the NDJSON
  event stream projects onto expected-run.json: `workflow_state` from the
  terminal workflow_* event · per-task status from the task_* outcome
  `class` · `output` from outcome payload.value · `error_code` from
  payload.error.code · `events_include` membership with the dot↔underscore
  normalization (`task.started:<id>` ↔ kind task_started + task field).
  Each fixture runs in its own throwaway cwd (traces and fs effects stay
  out of the repo).
- the TRACE door · `nika trace verify <trace.ndjson>` — expected-verify
  verdicts map to measured surfaces: clean = rc 0 without a marker ·
  finding = rc 0 with `FINDING — ` · incomplete = rc 5 with
  `INCOMPLETE — ` · forged = rc 2 · refused = rc 2 with the decode-bound
  wording « beyond the verifier's » (rc 3 = unchained/missing input · no
  fixture expects it today).

Verdicts per fixture: AGREE · DIVERGE (each difference named) ·
ENGINE-ERROR (crash / no events — counted loud, never folded into
divergence) · FIXTURE-ERROR (invalid expectation, before engine invocation).
Exit 0 iff every fixture AGREEs.

    NIKA_BIN=/path/to/nika python3 scripts/runtime-differential.py
    NIKA_BIN=… python3 scripts/runtime-differential.py runtime/gates  # one area
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal

SPEC_ROOT = pathlib.Path(__file__).resolve().parent.parent
# Behavioral markers anywhere under tests/ include stdlib's run fixtures.
# Discover malformed neighbors too; static expected.json/lints stay separate.
RUNTIME = SPEC_ROOT / "conformance" / "tests"

TERMINAL_TASK_KINDS = {
    "task_completed", "task_failed", "task_skipped", "task_cancelled",
}
WORKFLOW_STATE = {
    "workflow_completed": "success",
    "workflow_failed": "failure",
    "workflow_cancelled": "cancelled",
}


def parse_events(stdout: str) -> list[dict]:
    # A pretty check/error document is a different public response shape.
    # Once reading NDJSON, no malformed line may disappear from the evidence.
    try:
        document = strict_json(stdout)
    except ValueError:
        document = None
    if isinstance(document, dict) and "kind" not in document:
        return []
    events = []
    diagnostics = 0
    for number, line in enumerate(stdout.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            event = strict_json(line)
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
            if "kind" not in event and set(event) & {"error", "clean"}:
                diagnostics += 1
                continue  # admission judges the complete diagnostic separately
            if not isinstance(event.get("kind"), str) or not event["kind"]:
                raise ValueError("event has no nonempty kind")
            events.append(event)
        except ValueError as error:
            raise ValueError(f"invalid engine JSON at line {number}: {error}") from error
    if diagnostics and events:
        raise ValueError("runtime events mixed with a separate pre-boot diagnostic")
    return events


def project(events: list[dict]) -> dict:
    """The event stream → the expected-run.json shape."""
    state = None
    tasks: dict[str, dict] = {}
    seen: set[str] = set()
    for e in events:
        kind = e.get("kind", "")
        fields = event_fields(e)
        task = fields.get("task", "")
        if not isinstance(task, str):
            raise ValueError("task identity must be a string")
        seen.add(f"{kind.replace('_', '.')}:{task}" if task else kind.replace("_", "."))
        if state is not None and kind.startswith("task_"):
            raise ValueError("task event follows workflow termination")
        if kind in WORKFLOW_STATE:
            if state is not None:
                raise ValueError("multiple workflow terminal events")
            state = WORKFLOW_STATE[kind]
        if kind in TERMINAL_TASK_KINDS:
            if not task or task in tasks:
                raise ValueError("missing task identity or repeated terminal event")
            outcome = fields.get("outcome")
            if not isinstance(outcome, str):
                raise ValueError("task outcome must be encoded JSON")
            out = strict_json(outcome)
            status = {"task_completed": "success", "task_failed": "failure",
                      "task_skipped": "skipped", "task_cancelled": "cancelled"}[kind]
            if not isinstance(out, dict) or out.get("class") != status:
                raise ValueError("task kind and outcome class disagree")
            payload = out.get("payload", {})
            if not isinstance(payload, dict):
                raise ValueError("task payload must be an object")
            error = payload.get("error") or {}
            if not isinstance(error, dict):
                raise ValueError("task error must be an object")
            if "attempts" in payload and (type(payload["attempts"]) is not int
                                          or payload["attempts"] < 0):
                raise ValueError("task attempts must be a nonnegative integer")
            tasks[task] = {
                "status": status,
                "output": payload.get("value"),
                "error_code": error.get("code"),
                "attempts": payload.get("attempts"),
            }
    return {"workflow_state": state, "tasks": tasks, "events": seen}


def judge_run(engine: str, d: pathlib.Path) -> list[str]:
    """Differences between the projected run and expected-run.json."""
    expected, run = load_run_contract(d)
    cmd = [engine, "run", str(d / "input.nika"), "--json"]
    # run.json carries the launch invocation: `vars` and `inputs` both land
    # on --var (the flag sets a workflow `inputs:` value) · `env` overlays
    # the subprocess. (The inputs key was authored ahead of the README —
    # found live: two regate fixtures failed VAR-001 because the harness
    # never threaded it, and the divergence was the harness's.)
    launch = {**(run.get("vars") or {}), **(run.get("inputs") or {})}
    for k, v in launch.items():
        cmd += ["--var", f"{k}={v if isinstance(v, str) else json_text(v)}"]
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (run.get("env") or {}).items()})
    with tempfile.TemporaryDirectory(prefix="nika-rt-") as scratch:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=180, cwd=scratch, env=env)
    try:
        events = parse_events(proc.stdout)
    except ValueError as error:
        return [f"invalid engine evidence: {error}"]
    if "admission" in expected:
        diffs = diff_admission(expected["admission"], proc, events)
        if expected["admission"]["accepted"]:
            diffs += diff_execution(expected, proc.returncode, events)
        return diffs
    if not events:
        # A run can refuse at its EMBEDDED CHECK before any event boots —
        # rc 2 with the check report (one pretty-printed object) on
        # stdout. That is a verdict, not a crash: name it as its own
        # difference so the fixture's runtime expectation reads against
        # the truth (the static gate fired first).
        try:
            report = strict_json(proc.stdout)
        except ValueError:
            report = None
        if proc.returncode == 2 and isinstance(report, dict):
            return [f"CHECK-REFUSED pre-boot (clean={report.get('clean')}) · "
                    "the embedded static gate fired before any runtime event"]
        if isinstance(report, dict) and isinstance(report.get("error"), dict):
            return [f"RUN-REFUSED pre-boot · {report['error'].get('code')} · "
                    "no runtime execution claim was observed"]
        raise RuntimeError(f"no events on stdout (rc={proc.returncode} · "
                           f"stderr: {proc.stderr.strip()[:140]!r})")
    return diff_execution(expected, proc.returncode, events)


def diff_execution(expected: dict, code: int, events: list[dict]) -> list[str]:
    try:
        got = project(events)
    except ValueError as error:
        return [f"invalid engine evidence: {error}"]
    return diff_run(expected, got) + diff_run_completion(code, events)


def diff_run(expected: dict, got: dict) -> list[str]:
    """The judge, pure: every difference named (selftest-pinned)."""
    diffs: list[str] = []
    want_state = expected.get("workflow_state")
    if want_state is not None and got["workflow_state"] != want_state:
        diffs.append(f"workflow_state: want {want_state} · got {got['workflow_state']}")
    for tid, want in (expected.get("tasks") or {}).items():
        have = got["tasks"].get(tid)
        if have is None:
            diffs.append(f"task {tid}: no terminal event")
            continue
        if "status" in want and have["status"] != want["status"]:
            diffs.append(f"task {tid}.status: want {want['status']} · got {have['status']}")
        if "output" in want and not json_equal(have["output"], want["output"]):
            diffs.append(f"task {tid}.output: want {want['output']!r} · "
                         f"got {str(have['output'])[:80]!r}")
        text = have["output"] if isinstance(have["output"], str) else json_text(have["output"])
        if "output_contains" in want and want["output_contains"] not in text:
            diffs.append(f"task {tid}.output missing substring {want['output_contains']!r}")
        if "error_code" in want and have["error_code"] != want["error_code"]:
            diffs.append(f"task {tid}.error_code: want {want['error_code']} · "
                         f"got {have['error_code']}")
        if "attempts" in want and (type(have["attempts"]) is not int
                                   or have["attempts"] != want["attempts"]):
            diffs.append(f"task {tid}.attempts: want {want['attempts']} · "
                         f"got {have['attempts']}")
    for ev in expected.get("events_include") or []:
        if ev not in got["events"]:
            diffs.append(f"events_include missing {ev}")
    return diffs


def trace_verdict(rc: int, out: str) -> str:
    """The verify exit-map, pure — measured again on 0.119.0:
    forged rides rc 2 · a decode-bound refusal (17 §refused · the walk
    never ran) rides rc 2 too and only its « beyond the verifier's »
    wording discriminates · finding exits 0 like clean; incomplete has its
    own exit 5 since ADR-129, as required by spec 17 (selftest-pinned)."""
    if rc == 2:
        return "refused" if "beyond the verifier's" in out else "forged"
    if rc == 5 and "INCOMPLETE — " in out:
        return "incomplete"
    if rc == 0:
        if "INCOMPLETE — " in out:
            return "invalid-incomplete-exit=0"
        return "finding" if "FINDING — " in out else "clean"
    return f"rc={rc}"


def diff_prologue(expected: dict, events: list[dict]) -> list[str]:
    """Assert boot facts separately from chain integrity; never infer origins."""
    if not expected:
        return []
    if not events or events[0].get("kind") != "workflow_started":
        return ["prologue: missing initial workflow_started"]
    fields = events[0].get("fields", [])
    if not isinstance(fields, list):
        return ["prologue: malformed fields"]
    values: dict[str, object] = {}
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get("key"), str):
            return ["prologue: malformed field"]
        key = field["key"]
        if key in values:
            return [f"prologue: duplicate field {key}"]
        values[key] = field.get("value")
    diffs = [f"prologue: missing field {key}"
             for key in expected.get("present", []) if key not in values]
    diffs += [f"prologue: unexpected field {key}"
              for key in expected.get("absent", []) if key in values]
    if "input_origins" in expected:
        raw = values.get("inputs")
        try:
            if not isinstance(raw, str):
                raise ValueError("inputs must be a JSON string")
            pairs = json.loads(raw, object_pairs_hook=list)
            if not isinstance(pairs, list) or any(
                not isinstance(pair, tuple) or len(pair) != 2
                or not all(isinstance(value, str) for value in pair)
                for pair in pairs
            ):
                raise ValueError("origins must be a string map")
            origins = dict(pairs)
            if len(origins) != len(pairs) or not raw.lstrip().startswith("{"):
                raise ValueError("origins must be an object with unique keys")
        except (ValueError, TypeError):
            diffs.append("prologue.input_origins: missing or malformed map")
        else:
            if origins != expected["input_origins"]:
                diffs.append(f"prologue.input_origins: want {expected['input_origins']!r} · got {origins!r}")
    return diffs


def unique_object(pairs: list[tuple]) -> dict:
    """Neither evidence nor expectations may overwrite a repeated field."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key}")
        result[key] = value
    return result


class InvalidFixture(ValueError):
    """An expectation cannot be evaluated as a conformance claim."""


class UnsupportedFixture(ValueError):
    """A valid contract needs an adapter this command runner does not provide."""


def strict_json(raw: str):
    def reject_constant(value):
        raise ValueError(f"non-JSON numeric constant {value}")
    return json.loads(raw, object_pairs_hook=unique_object, parse_float=finite_float,
                      parse_constant=reject_constant)


def json_equal(left, right) -> bool:
    """JSON kinds are distinct; numbers compare exactly, objects without key order."""
    numbers = (int, float, Decimal)
    if type(left) in numbers and type(right) in numbers:
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_equal(v, right[k]) for k, v in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left == right


def json_text(value) -> str:
    """Stable compact JSON without converting exact decimal values to binary floats."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + json_text(value[k])
                               for k in sorted(value)) + "}"
    if isinstance(value, list):
        return "[" + ",".join(map(json_text, value)) + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def event_fields(event: dict) -> dict:
    fields = event.get("fields", [])
    if not isinstance(fields, list):
        raise ValueError("event fields must be an array")
    pairs = []
    for field in fields:
        if (not isinstance(field, dict) or not isinstance(field.get("key"), str)
                or not field["key"] or "value" not in field):
            raise ValueError("malformed event field")
        pairs.append((field["key"], field["value"]))
    return unique_object(pairs)


def diff_run_completion(code: int, events: list[dict]) -> list[str]:
    """A command claim includes its unique boot, terminal settlement and process exit."""
    starts = [i for i, e in enumerate(events) if e["kind"] == "workflow_started"]
    terminal = [e for e in events if e["kind"] in WORKFLOW_STATE]
    settlements = [i for i, e in enumerate(events) if e["kind"] == "run_settled"]
    diffs = []
    if starts != [0]:
        diffs.append("run: missing or repeated initial workflow_started")
    if len(terminal) != 1:
        diffs.append("run: missing or repeated workflow terminal event")
    if len(settlements) != 1 or settlements != [len(events) - 1]:
        diffs.append("run: missing, repeated or non-final run_settled")
    if len(terminal) == 1:
        state = WORKFLOW_STATE[terminal[0]["kind"]]
        status = {"success": "succeeded", "failure": "failed", "cancelled": "cancelled"}[state]
        if len(settlements) == 1 and events[settlements[0]].get("status") != status:
            diffs.append("run: settlement status contradicts workflow terminal")
        expected_code = {"success": 0, "failure": 1, "cancelled": 130}[state]
        if code != expected_code:
            diffs.append(f"run exit: want {expected_code} for {state} · got {code}")
    return diffs


def fixture_door(directory: pathlib.Path) -> str:
    """Validate owned fixture layout before dispatch; never pick one of two claims."""
    names = {p.name for p in directory.iterdir()}
    claims = {n for n in names if n.startswith("expected-") and n != "expected-lints.json"}
    if len(claims) != 1:
        raise InvalidFixture("fixture requires exactly one behavioral expectation")
    claim = claims.pop()
    if claim in {"expected-resume.json", "expected-explain.json", "expected-energy.json"}:
        raise UnsupportedFixture(f"{claim} requires a separate command adapter")
    required = {"expected-run.json": "input.nika", "expected-verify.json": "trace.ndjson"}
    if claim not in required:
        raise InvalidFixture(f"unknown behavioral expectation {claim}")
    if not (directory / required[claim]).is_file():
        raise InvalidFixture(f"missing {required[claim]}")
    return "run" if claim == "expected-run.json" else "trace"


def load_run_contract(directory: pathlib.Path) -> tuple[dict, dict]:
    """Validate every run assertion and invocation before calling the engine."""
    if fixture_door(directory) != "run":
        raise InvalidFixture("run door requires expected-run.json")
    def reject_constant(value):
        raise ValueError(f"non-JSON numeric constant {value}")

    def read(name):
        value = json.loads((directory / name).read_text(encoding="utf-8"),
                           object_pairs_hook=unique_object, parse_float=finite_float,
                           parse_constant=reject_constant)
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
        return value

    def keys(value, allowed, label):
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object")
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unknown {label} keys: {', '.join(sorted(unknown))}")

    def words(value, label):
        if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
            raise ValueError(f"{label} must be an array of nonempty strings")

    try:
        expected = read("expected-run.json")
        run = read("run.json") if (directory / "run.json").exists() else {}
        keys(expected, {"workflow_state", "tasks", "events_include", "admission", "receipt", "note"},
             "run assertion")
        keys(run, {"vars", "inputs", "env", "access", "harness_attestations"}, "run invocation")
        if not set(expected) - {"note"}:
            raise ValueError("run expectation has no assertions")
        if "workflow_state" in expected and expected["workflow_state"] not in {
            "success", "failure", "cancelled",
        }:
            raise ValueError("unknown workflow_state")
        tasks = expected.get("tasks", {})
        if not isinstance(tasks, dict) or ("tasks" in expected and not tasks):
            raise ValueError("tasks must be a nonempty object")
        for task, wanted in tasks.items():
            if not task:
                raise ValueError("empty task identity")
            keys(wanted, {"status", "output", "output_contains", "error_code", "attempts"}, "task assertion")
            if wanted.get("status") not in {"success", "failure", "skipped", "cancelled"}:
                raise ValueError("missing or unknown task status")
            for key in ("output_contains", "error_code"):
                if key in wanted and not isinstance(wanted[key], str):
                    raise ValueError(f"{key} must be a string")
            if "attempts" in wanted and (type(wanted["attempts"]) is not int or wanted["attempts"] < 0):
                raise ValueError("attempts must be a nonnegative integer")
        if "events_include" in expected:
            words(expected["events_include"], "events_include")
        if "admission" in expected:
            admission = expected["admission"]
            keys(admission, {"accepted", "error_code", "witness_contains"}, "admission")
            if type(admission.get("accepted")) is not bool:
                raise ValueError("admission.accepted must be boolean")
            if admission["accepted"]:
                if set(admission) != {"accepted"}:
                    raise ValueError("accepted admission cannot assert a refusal")
            else:
                if not isinstance(admission.get("error_code"), str) or not admission["error_code"]:
                    raise ValueError("refused admission needs an error_code")
                words(admission.get("witness_contains", []), "admission.witness_contains")
                if set(expected) & {"workflow_state", "tasks", "events_include"}:
                    raise ValueError("refused admission cannot assert execution")
        for key in ("vars", "inputs", "env"):
            if key in run and (not isinstance(run[key], dict) or any(not k for k in run[key])):
                raise ValueError(f"{key} must be an object with nonempty names")
        if any(not isinstance(v, str) for v in run.get("env", {}).values()):
            raise ValueError("env values must be strings")
        for key in set(run.get("vars", {})) & set(run.get("inputs", {})):
            if not json_equal(run["vars"][key], run["inputs"][key]):
                raise ValueError(f"vars and inputs disagree for {key}")
    except (ValueError, TypeError, UnicodeError, OSError) as error:
        raise InvalidFixture(str(error)) from error
    unsupported = set(run) & {"access", "harness_attestations"}
    if "receipt" in expected:
        unsupported.add("receipt")
    if unsupported:
        raise UnsupportedFixture("injected harness/receipt adapter required: " + ", ".join(sorted(unsupported)))
    return expected, run


def diff_admission(expected: dict, proc, events: list[dict]) -> list[str]:
    """Admission refusal is a structured diagnostic before every workflow/task event."""
    execution = [e for e in events if e["kind"].replace(".", "_").startswith(("workflow_", "task_"))]
    if expected["accepted"]:
        return [] if any(e["kind"].replace(".", "_") == "workflow_started" for e in execution) else [
            "admission: accepted run has no workflow_started"
        ]
    diffs = []
    if proc.returncode == 0:
        diffs.append("admission: refusal exited zero")
    if execution:
        diffs.append("admission: execution events preceded or accompanied refusal")
    try:
        document = strict_json(proc.stdout)
        error = document["error"]
        if not isinstance(error, dict):
            raise ValueError("error must be an object")
    except (ValueError, KeyError, TypeError):
        return diffs + ["admission: missing or ambiguous structured error"]
    if error.get("code") != expected["error_code"]:
        diffs.append(f"admission.error_code: want {expected['error_code']} · got {error.get('code')}")
    message = error.get("message")
    for witness in expected.get("witness_contains", []):
        if not isinstance(message, str) or witness not in message:
            diffs.append(f"admission: missing witness {witness!r}")
    return diffs


def finite_float(raw: str) -> Decimal:
    """JSON exponent syntax must not overflow into a non-finite expectation."""
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    return Decimal(raw)


def validate_prologue(expected: object) -> None:
    """Validate the shape of every documented boot assertion before any effect."""
    if not isinstance(expected, dict):
        raise ValueError("prologue must be an object")
    unknown = set(expected) - {"present", "absent", "input_origins"}
    if unknown:
        raise ValueError(f"unknown prologue assertion: {', '.join(sorted(unknown))}")
    for key in ("present", "absent"):
        fields = expected.get(key, [])
        if not isinstance(fields, list) or any(
            not isinstance(field, str) or not field for field in fields
        ):
            raise ValueError(f"prologue.{key} must be an array of nonempty field names")
        if len(set(fields)) != len(fields):
            raise ValueError(f"prologue.{key} repeats a field")
    if set(expected.get("present", [])) & set(expected.get("absent", [])):
        raise ValueError("a prologue field cannot be both present and absent")
    if "input_origins" in expected:
        origins = expected["input_origins"]
        if not isinstance(origins, dict) or any(
            not key or not isinstance(value, str) or not value
            for key, value in origins.items()
        ):
            raise ValueError("prologue.input_origins must map input names to channel names")


def trace_expectation(raw: str) -> dict:
    """Reject ambiguous fixture bytes before invoking any engine command."""
    def reject_constant(value: str):
        raise ValueError(f"non-JSON numeric constant {value}")
    try:
        expected = json.loads(raw, object_pairs_hook=unique_object,
                              parse_constant=reject_constant, parse_float=finite_float)
        if not isinstance(expected, dict):
            raise ValueError("expectation must be an object")
        verdict = expected.get("verdict")
        if not isinstance(verdict, str) or verdict not in {
            "clean", "finding", "incomplete", "forged", "refused",
        }:
            raise ValueError("missing or unknown trace verdict")
        if "cost_replay" in expected:
            replay = expected["cost_replay"]
            if not isinstance(replay, str) or replay not in {
                "replayed", "refused", "unrecorded",
            }:
                raise ValueError("unknown cost_replay claim")
        if "prologue" in expected:
            validate_prologue(expected["prologue"])
        if "items" in expected:
            items = expected["items"]
            if not isinstance(items, dict) or not items:
                raise ValueError("items must be a nonempty task map")
            for task, rows in items.items():
                if not task:
                    raise ValueError("item task identity must be nonempty")
                if rows is not None and not isinstance(rows, list):
                    raise ValueError("item expectation must be an array or null")
        return expected
    except (ValueError, TypeError) as error:
        raise InvalidFixture(str(error)) from error


def load_trace_expectation(path: pathlib.Path) -> dict:
    """Decode failures belong to the fixture, never to an uninvoked engine."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (UnicodeError, OSError) as error:
        raise InvalidFixture(f"cannot read UTF-8 expectation: {error}") from error
    return trace_expectation(raw)


def cost_replay_verdict(out: str, stderr: str = "") -> str:
    """Read the public verify report's separate budget leg, never the journal pin."""
    # A stream boundary is not a continuation of an unterminated line or
    # of a report in the other stream. Preserve each report's own context.
    markers = []
    for stream in (out, stderr):
        lines = stream.splitlines()
        markers += [(line, lines[index + 1:index + 2])
                    for index, line in enumerate(lines)
                    if line.startswith("COST-REPLAY — ")]
    if len(markers) != 1:
        return "missing-or-ambiguous"
    marker, following = markers[0]
    if marker.startswith("COST-REPLAY — unrecorded · "):
        return "unrecorded"
    if marker.startswith("COST-REPLAY — REFUSED · "):
        return "refused"
    phrase = "  the budget verdict re-judged from the journaled dollars"
    if marker.startswith("COST-REPLAY — the pinned pricing table is this engine's (") \
            and following and (following[0] == phrase or following[0].startswith(phrase + " (")):
        return "replayed"
    return "unrecognized"


def journal_prologue(path: pathlib.Path, expected: dict) -> list[str]:
    """Read only the initial nonempty event; other trace laws stay engine-owned."""
    try:
        with path.open("rb") as journal:
            raw = next((line for line in journal if line.strip()), b"")
        event = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                           parse_float=finite_float)
        if not isinstance(event, dict):
            raise ValueError("initial event must be an object")
    except (ValueError, UnicodeError, OSError) as error:
        return [f"prologue: cannot read initial event ({error})"]
    return diff_prologue(expected, [event])


def diff_items(expected: dict, raw: str) -> list[str]:
    """Judge the engine's item projection, not a second local page fold."""
    try:
        document = strict_json(raw)
        tasks = document.get("tasks") if isinstance(document, dict) else None
        if not isinstance(tasks, list):
            raise ValueError("missing task array")
        by_id = {}
        for task in tasks:
            if not isinstance(task, dict) or not isinstance(task.get("id"), str):
                raise ValueError("malformed task")
            if task["id"] in by_id:
                raise ValueError("duplicate task identity")
            by_id[task["id"]] = task
    except (ValueError, TypeError) as error:
        return [f"items: malformed engine projection ({error})"]
    diffs = []
    for task_id, wanted in expected.items():
        if task_id not in by_id:
            diffs.append(f"items {task_id}: task absent")
            continue
        actual = by_id[task_id].get("items")
        # JSON equality keeps true distinct from 1 and a numeric index from
        # its string spelling; array order and every row field are asserted.
        if not json_equal(actual, wanted):
            diffs.append(f"items {task_id}: projection differs from expected table")
    return diffs


def judge_trace(engine: str, d: pathlib.Path) -> list[str]:
    """Differences between the verify verdict and expected-verify.json."""
    if fixture_door(d) != "trace":
        raise InvalidFixture("trace door requires expected-verify.json")
    expected = load_trace_expectation(d / "expected-verify.json")
    want = expected["verdict"]
    proc = subprocess.run(
        [engine, "trace", "verify", str(d / "trace.ndjson"), "--color", "never"],
        capture_output=True, text=True, timeout=120,
    )
    got = trace_verdict(proc.returncode, "\n".join((proc.stdout, proc.stderr)))
    diffs = [] if got == want else [f"verdict: want {want} · got {got}"]
    if "cost_replay" in expected:
        replay = cost_replay_verdict(proc.stdout, proc.stderr)
        if replay != expected["cost_replay"]:
            diffs.append(f"cost_replay: want {expected['cost_replay']} · got {replay}")
    if expected.get("prologue"):
        # This is a semantic assertion over recorded bytes, not a second
        # integrity verifier. The engine's verdict above remains mandatory.
        diffs += journal_prologue(d / "trace.ndjson", expected["prologue"])
    if "items" in expected:
        projection = subprocess.run(
            [engine, "trace", "outputs", str(d / "trace.ndjson"), "--json", "--color", "never"],
            capture_output=True, text=True, timeout=120,
        )
        if projection.returncode:
            diffs.append(f"items: trace outputs exited {projection.returncode}")
        else:
            diffs += diff_items(expected["items"], projection.stdout)
    return diffs


def _ev(kind: str, **fields: object) -> str:
    return json.dumps({"kind": kind,
                       "fields": [{"key": k, "value": v} for k, v in fields.items()]})


def selftest() -> int:
    """The judge's own laws, offline — no engine, CI-runnable. The day's
    live lessons pinned as permanent tampers: exact value means TYPE
    included ('2' is not 2) · a pretty-printed check report is not an
    event stream · finding exits 0 like clean."""
    checks: list[tuple[str, bool]] = []
    stream = "\n".join([
        _ev("workflow_started", workflow="w"),
        _ev("task_completed", task="a",
            outcome=json.dumps({"cause": "normal", "class": "success",
                                "payload": {"value": 2, "attempts": 1}})),
        _ev("task_skipped", task="b",
            outcome=json.dumps({"cause": "error_skip", "class": "skipped",
                                "payload": {"error": {"code": "NIKA-X-001"}}})),
        _ev("workflow_completed", workflow="w"),
    ])
    got = project(parse_events(stream))
    checks.append(("projection · state + typed value + error code",
                   got["workflow_state"] == "success"
                   and got["tasks"]["a"]["output"] == 2
                   and got["tasks"]["b"]["error_code"] == "NIKA-X-001"))
    checks.append(("projection · events normalize dot-for-underscore",
                   "task.completed:a" in got["events"]))
    agree = {"workflow_state": "success",
             "tasks": {"a": {"status": "success", "output": 2},
                       "b": {"status": "skipped", "error_code": "NIKA-X-001"}},
             "events_include": ["task.completed:a"]}
    checks.append(("agreement yields zero diffs", diff_run(agree, got) == []))
    checks.append(("a flipped status is named",
                   any("a.status" in d for d in diff_run(
                       {"tasks": {"a": {"status": "failure"}}}, got))))
    checks.append(("exact value means TYPE included ('2' is not 2)",
                   any("a.output" in d for d in diff_run(
                       {"tasks": {"a": {"output": "2"}}}, got))))
    checks.append(("a missing expected event is named",
                   any("events_include" in d for d in diff_run(
                       {"events_include": ["task.started:zzz"]}, got))))
    checks.append(("a wrong attempts count is named (retry observability)",
                   any("a.attempts" in d for d in diff_run(
                       {"tasks": {"a": {"attempts": 3}}}, got))))
    checks.append(("a task with no terminal event is named",
                   any("no terminal event" in d for d in diff_run(
                       {"tasks": {"ghost": {"status": "success"}}}, got))))
    checks.append(("a pretty-printed check report is NOT an event stream",
                   parse_events('{\n  "analysis": {}\n}') == []))
    checks.append(("trace exit-map · clean / finding / forged / other",
                   trace_verdict(0, "OK — chain intact") == "clean"
                   and trace_verdict(0, "FINDING — witness absent") == "finding"
                   and trace_verdict(2, "BROKEN at line 4 — recorded chain") == "forged"
                   and trace_verdict(3, "") == "rc=3"))
    # Fixture 004 now requires exit 5 (spec 17); historical exit 0 no longer
    # discharges that law. Decode-bound refusals retain their exit 2 class.
    checks.append(("trace exit-map · incomplete requires its own exit 5",
                   trace_verdict(5, "INCOMPLETE — 9 events · chain intact") == "incomplete"
                   and trace_verdict(0, "INCOMPLETE — 9 events · chain intact") != "incomplete"
                   and trace_verdict(5, "") != "incomplete"))
    checks.append(("trace exit-map · a bound refusal rides rc 2 behind its wording",
                   trace_verdict(2, "line 2 is 1048890 bytes — beyond the verifier's "
                                    "line bound (1048576 bytes)") == "refused"))
    boot_want = {"present": ["inputs"], "absent": ["seed"],
                 "input_origins": {"supplied": "api-caller", "defaulted": "file"}}
    def boot(origins):
        return parse_events(_ev("workflow_started", inputs=origins))
    origin_map = json.dumps(boot_want["input_origins"])
    checks.append(("API and file origins remain distinct",
                   diff_prologue(boot_want, boot(origin_map)) == []))
    for wrong in ("cli-operator", "ci-context", "env", "file"):
        substituted = json.dumps({"supplied": wrong, "defaulted": "file"})
        checks.append((f"API origin cannot become {wrong}",
                       bool(diff_prologue(boot_want, boot(substituted)))))
    for name, raw in [("absent", None), ("invalid JSON", "{"),
                      ("array", "[]"), ("null", "null"),
                      ("wrong value type", '{"supplied": true}'),
                      ("duplicate input", '{"supplied":"file","supplied":"api-caller","defaulted":"file"}'),
                      ("missing input", '{"supplied":"api-caller"}'),
                      ("extra input", '{"supplied":"api-caller","defaulted":"file","extra":"file"}')]:
        checks.append((f"origin assertion refuses {name}",
                       bool(diff_prologue(boot_want, boot(raw)))))
    doubled = boot(origin_map)
    doubled[0]["fields"].append({"key": "inputs", "value": origin_map})
    checks.append(("duplicate boot field is not silently overwritten",
                   bool(diff_prologue(boot_want, doubled))))
    checks.append(("missing boot is not guessed from later events",
                   bool(diff_prologue(boot_want, parse_events(_ev("task_started"))))))
    checks.append(("absent boot claim is enforced",
                   bool(diff_prologue(boot_want, parse_events(
                       _ev("workflow_started", inputs=origin_map, seed=0))))))
    rows = [{"index": 0, "item": "a", "status": "failed"},
            {"index": 1, "item": "b", "status": "cancelled"},
            {"index": 2, "item": "c", "status": "never_started"}]
    def item_document(value):
        return json.dumps({"tasks": [{"id": "fan", "items": value}]})
    checks.append(("exact item projection preserves cancelled versus never_started",
                   diff_items({"fan": rows}, item_document(rows)) == []))
    checks.append(("incomplete item table remains unrecorded",
                   diff_items({"fan": None}, item_document(None)) == []))
    for label, value in [
        ("cancelled relabelled never_started", [rows[0], {**rows[1], "status": "never_started"}, rows[2]]),
        ("false completion of missing pages", []),
        ("lost item", rows[:-1]),
        ("reordered items", list(reversed(rows))),
        ("boolean index", [rows[0], {**rows[1], "index": True}, rows[2]]),
        ("string index", [{**rows[0], "index": "0"}, *rows[1:]]),
    ]:
        checks.append((f"item assertion refuses {label}",
                       bool(diff_items({"fan": rows}, item_document(value)))))
    checks.append(("a complete table cannot stand in for an incomplete one",
                   bool(diff_items({"fan": None}, item_document(rows)))))
    for raw in ('{}', '[]', '{', '{"tasks":[]}',
                '{"tasks":[{"id":"fan"},{"id":"fan"}]}',
                '{"tasks":[{"id":"fan","items":null,"items":[]}]}'):
        checks.append(("malformed or absent item projection fails",
                       bool(diff_items({"fan": rows}, raw))))
    # Exercise the fixture-loading boundary as well as the pure comparator.
    # Ambiguous expectations cannot become agreement by dropping assertions.
    from unittest.mock import patch
    invalid_expectations = [
        ("duplicate verdict", '{"verdict":"forged","verdict":"clean"}'),
        ("duplicate items field", '{"verdict":"clean","items":{"fan":[]},"items":{"fan":null}}'),
        ("duplicate task expectation", '{"verdict":"clean","items":{"fan":[],"fan":null}}'),
        ("empty item task map", '{"verdict":"clean","items":{}}'),
        ("empty task identity", '{"verdict":"clean","items":{"":null}}'),
        ("item scalar", '{"verdict":"clean","items":{"fan":0}}'),
        ("non-finite expectation", '{"verdict":"clean","items":{"fan":[{"index":NaN}]}}'),
        ("overflowing JSON float", '{"verdict":"clean","note":1e999}'),
        ("negative overflowing JSON float", '{"verdict":"clean","items":{"fan":[-1e999]}}'),
        ("undecodable expectation", b'{"verdict":"clean","note":"\xff"}'),
        ("numeric cost replay", '{"verdict":"clean","cost_replay":5}'),
        ("unknown cost replay", '{"verdict":"clean","cost_replay":"unknown"}'),
        ("null cost replay", '{"verdict":"clean","cost_replay":null}'),
        ("scalar prologue", '{"verdict":"clean","prologue":5}'),
        ("null prologue", '{"verdict":"clean","prologue":null}'),
        ("string present fields", '{"verdict":"clean","prologue":{"present":"seed"}}'),
        ("non-string absent field", '{"verdict":"clean","prologue":{"absent":[5]}}'),
        ("empty field name", '{"verdict":"clean","prologue":{"present":[""]}}'),
        ("contradictory fields", '{"verdict":"clean","prologue":{"present":["seed"],"absent":["seed"]}}'),
        ("scalar input origins", '{"verdict":"clean","prologue":{"input_origins":5}}'),
        ("non-string input origin", '{"verdict":"clean","prologue":{"input_origins":{"x":false}}}'),
        ("misspelled origins", '{"verdict":"clean","prologue":{"input-origins":{"x":"env"}}}'),
        ("misspelled absence", '{"verdict":"clean","prologue":{"absnet":["inputs"]}}'),
        ("singular origin", '{"verdict":"clean","prologue":{"input_origin":{"x":"env"}}}'),
        ("capitalized presence", '{"verdict":"clean","prologue":{"Present":["seed"]}}'),
    ]
    for label, raw in invalid_expectations:
        with tempfile.TemporaryDirectory(prefix="nika-rt-selftest-") as scratch:
            fixture = pathlib.Path(scratch)
            # These tests double the process; the required input still exists.
            (fixture / "input.nika").write_text("nika: judge-selftest\n")
            (fixture / "trace.ndjson").write_text("")
            (fixture / "expected-verify.json").write_bytes(
                raw if isinstance(raw, bytes) else raw.encode("utf-8"))
            with patch("subprocess.run") as invoke:
                invoke.side_effect = [
                    subprocess.CompletedProcess([], 0, "OK — chain intact", ""),
                    subprocess.CompletedProcess([], 0, item_document(None), ""),
                ]
                rejected = False
                try:
                    judge_trace("unused-engine", fixture)
                except InvalidFixture:
                    rejected = True
                except (ValueError, TypeError, AttributeError, OSError):
                    pass  # A fixture failure must keep its own classification.
                checks.append((f"fixture refuses {label} before engine invocation",
                               rejected and invoke.call_count == 0))
    for name, expected in [
        ("verdict only", {"verdict": "clean"}),
        ("empty complete table", {"verdict": "clean", "items": {"fan": []}}),
        ("unrecorded table", {"verdict": "clean", "items": {"fan": None}}),
        ("ordered typed rows", {"verdict": "clean", "items": {"fan": rows}}),
        ("prologue assertions", {"verdict": "clean", "prologue": boot_want}),
        ("empty origin map", {"verdict": "clean", "prologue": {"input_origins": {}}}),
        ("finite fractional value", {"verdict": "clean", "note": 1.25}),
    ]:
        checks.append((f"fixture accepts {name}",
                       trace_expectation(json.dumps(expected)) == expected))
    replay_lines = {
        "unrecorded": "COST-REPLAY — unrecorded · the boot frame pins no pricing table",
        "refused": "COST-REPLAY — REFUSED · the pinned pricing table is not this engine's",
        "replayed": "COST-REPLAY — the pinned pricing table is this engine's (known pin)\n"
                    "  the budget verdict re-judged from the journaled dollars",
    }
    for wanted in replay_lines:
        for actual, line in replay_lines.items():
            with tempfile.TemporaryDirectory(prefix="nika-cost-selftest-") as scratch:
                fixture = pathlib.Path(scratch)
                # These tests double the process; the required input still exists.
                (fixture / "input.nika").write_text("nika: judge-selftest\n")
                (fixture / "trace.ndjson").write_text("")
                (fixture / "expected-verify.json").write_text(json.dumps(
                    {"verdict": "clean", "cost_replay": wanted}))
                with patch("subprocess.run") as invoke:
                    invoke.return_value = subprocess.CompletedProcess(
                        [], 0, "OK — chain intact\n" + line, "")
                    diffs = judge_trace("unused-engine", fixture)
                    checks.append((f"cost replay {wanted} compared with {actual}",
                                   bool(diffs) == (wanted != actual)
                                   and invoke.call_count == 1))
    for label, line in [
        ("missing", ""),
        ("unknown", "COST-REPLAY — unknown"),
        ("unjudged pin", "COST-REPLAY — the pinned pricing table is this engine's"),
        ("conflicting", replay_lines["replayed"] + "\n" + replay_lines["refused"]),
    ]:
        with tempfile.TemporaryDirectory(prefix="nika-cost-selftest-") as scratch:
            fixture = pathlib.Path(scratch)
            # These tests double the process; the required input still exists.
            (fixture / "input.nika").write_text("nika: judge-selftest\n")
            (fixture / "trace.ndjson").write_text("")
            (fixture / "expected-verify.json").write_text(
                '{"verdict":"clean","cost_replay":"replayed"}')
            with patch("subprocess.run") as invoke:
                invoke.return_value = subprocess.CompletedProcess(
                    [], 0, "OK — chain intact\n" + line, "")
                checks.append((f"cost replay refuses {label} evidence",
                               bool(judge_trace("unused-engine", fixture))))
    # Each semantic claim keeps its own reading failure; a malformed boot
    # does not turn a completed engine command into an engine crash.
    for label, raw, agrees in [
        ("leading blank", b"\n  \n" + _ev("workflow_started", seed=7).encode(), True),
        ("truncated first row", b'{"kind":', False),
        ("non-UTF-8 first row", b'\xff', False),
        ("empty journal", b'', False),
        ("scalar boot", b'5\n', False),
        ("array boot", b'[]\n', False),
        ("duplicate boot key", b'{"kind":"task_started","kind":"workflow_started","fields":[{"key":"seed","value":7}]}', False),
    ]:
        with tempfile.TemporaryDirectory(prefix="nika-prologue-selftest-") as scratch:
            fixture = pathlib.Path(scratch)
            # These tests double the process; the required input still exists.
            (fixture / "input.nika").write_text("nika: judge-selftest\n")
            (fixture / "trace.ndjson").write_text("")
            (fixture / "expected-verify.json").write_text(
                '{"verdict":"clean","prologue":{"present":["seed"]}}')
            (fixture / "trace.ndjson").write_bytes(raw)
            with patch("subprocess.run") as invoke:
                invoke.return_value = subprocess.CompletedProcess([], 0, "OK — chain intact\n", "")
                try:
                    differences = judge_trace("unused-engine", fixture)
                    held = (not differences) == agrees and invoke.call_count == 1
                except (ValueError, TypeError, AttributeError, UnicodeError):
                    held = False
                checks.append((f"journal prologue reads {label} without misattribution", held))
    known = replay_lines["replayed"].splitlines()[0]
    phrase = "  the budget verdict re-judged from the journaled dollars"
    for label, stdout, stderr, wanted, agrees in [
        ("unrelated warning", known + "\n", "warning: " + phrase, "replayed", False),
        ("unrelated following section", known + "\nOTHER\n" + phrase, "", "replayed", False),
        ("phrase in other stream", known + "\n", phrase, "replayed", False),
        ("unterminated conflicting reports", replay_lines["unrecorded"], replay_lines["refused"], "unrecorded", False),
        ("stderr report after unterminated stdout", "OK — chain intact", replay_lines["unrecorded"], "unrecorded", True),
    ]:
        with tempfile.TemporaryDirectory(prefix="nika-stream-selftest-") as scratch:
            fixture = pathlib.Path(scratch)
            # These tests double the process; the required input still exists.
            (fixture / "input.nika").write_text("nika: judge-selftest\n")
            (fixture / "trace.ndjson").write_text("")
            (fixture / "expected-verify.json").write_text(json.dumps(
                {"verdict": "clean", "cost_replay": wanted}))
            with patch("subprocess.run") as invoke:
                invoke.return_value = subprocess.CompletedProcess([], 0, stdout, stderr)
                checks.append((f"cost report keeps {label} boundaries",
                               (not judge_trace("unused-engine", fixture)) == agrees))
    checks.append(("compact check reports and errors are not events",
                   parse_events('{"clean":false}\n{"error":{"code":"NIKA-1708"}}') == []))
    admission = {"admission": {"accepted": False, "error_code": "NIKA-1708",
                               "witness_contains": ["ticket"]}}
    diagnostic = json.dumps({"error": {"code": "NIKA-1708", "message": "missing ticket"}})
    for label, code, stdout, agrees in [
        ("exact refusal", 3, diagnostic, True),
        ("zero exit", 0, diagnostic, False),
        ("wrong code", 3, diagnostic.replace("1708", "1709"), False),
        ("missing witness", 3, diagnostic.replace("ticket", "other"), False),
        ("missing diagnostic", 3, "", False),
        ("duplicate error", 3, '{"error":{},"error":{"code":"NIKA-1708","message":"ticket"}}', False),
        ("boot before refusal", 3, _ev("workflow_started") + "\n" + diagnostic, False),
        ("task before refusal", 3, _ev("task_started", task="a") + "\n" + diagnostic, False),
    ]:
        with tempfile.TemporaryDirectory(prefix="nika-admission-selftest-") as scratch:
            fixture = pathlib.Path(scratch)
            # These tests double the process; the required input still exists.
            (fixture / "input.nika").write_text("nika: judge-selftest\n")
            (fixture / "trace.ndjson").write_text("")
            (fixture / "expected-run.json").write_text(json.dumps(admission))
            with patch("subprocess.run") as invoke:
                invoke.return_value = subprocess.CompletedProcess([], code, stdout, "")
                checks.append((f"admission judges {label}",
                               (not judge_run("unused-engine", fixture)) == agrees))
    valid_run = '{"workflow_state":"success","tasks":{"a":{"status":"success"}}}'
    for label, expectation, invocation, error_type in [
        ("misspelled assertion", '{"workflow_stat":"success"}', '{}', InvalidFixture),
        ("empty assertions", '{"note":"not a test"}', '{}', InvalidFixture),
        ("duplicate verdict", '{"workflow_state":"success","workflow_state":"failure"}', '{}', InvalidFixture),
        ("unknown task assertion", '{"tasks":{"a":{"status":"success","outpt":0}}}', '{}', InvalidFixture),
        ("boolean attempts", '{"tasks":{"a":{"status":"success","attempts":true}}}', '{}', InvalidFixture),
        ("NaN", '{"tasks":{"a":{"status":"success","output":NaN}}}', '{}', InvalidFixture),
        ("overflow", '{"tasks":{"a":{"status":"success","output":1e999}}}', '{}', InvalidFixture),
        ("non-UTF8", b'{"note":"\xff"}', '{}', InvalidFixture),
        ("string admission", '{"admission":{"accepted":"false"}}', '{}', InvalidFixture),
        ("unknown admission claim", '{"admission":{"accepted":false,"error_code":"x","witness":[]}}', '{}', InvalidFixture),
        ("unknown invocation", valid_run, '{"var":{"x":1}}', InvalidFixture),
        ("duplicate input", valid_run, '{"vars":{"x":1,"x":2}}', InvalidFixture),
        ("conflicting input sources", valid_run, '{"vars":{"x":1},"inputs":{"x":true}}', InvalidFixture),
        ("null env", valid_run, '{"env":null}', InvalidFixture),
        ("injected harness", '{"admission":{"accepted":true}}', '{"harness_attestations":{}}', UnsupportedFixture),
        ("access seat", valid_run, '{"access":"codex"}', UnsupportedFixture),
        ("receipt", '{"admission":{"accepted":true},"receipt":{"tokens":null}}', '{}', UnsupportedFixture),
    ]:
        with tempfile.TemporaryDirectory(prefix="nika-run-contract-selftest-") as scratch:
            fixture = pathlib.Path(scratch)
            # These tests double the process; the required input still exists.
            (fixture / "input.nika").write_text("nika: judge-selftest\n")
            (fixture / "trace.ndjson").write_text("")
            (fixture / "expected-run.json").write_bytes(
                expectation if isinstance(expectation, bytes) else expectation.encode())
            (fixture / "run.json").write_text(invocation)
            with patch("subprocess.run") as invoke:
                rejected = False
                try:
                    judge_run("unused-engine", fixture)
                except error_type:
                    rejected = True
                checks.append((f"run fixture classifies {label} before any engine call",
                               rejected and not invoke.called))
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'}  {name}")
    print(f"runtime-differential selftest · {len(checks) - len(bad)}/{len(checks)}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--selftest":
        return selftest()
    engine = os.environ.get("NIKA_BIN") or shutil.which("nika") or "nika"
    root = RUNTIME
    if len(argv) > 1:
        root = SPEC_ROOT / "conformance" / "tests" / argv[1].removeprefix("conformance/tests/")
    markers = {"input.nika", "run.json", "trace.ndjson"}
    dirs = sorted({p.parent for p in root.rglob("*") if p.is_file() and (
        p.name in markers or (p.name.startswith("expected-") and p.name != "expected-lints.json"))})
    if not dirs:
        print(f"FAIL  {root} · no runtime fixtures found")
        return 1
    agree = diverged = errors = fixture_errors = unsupported = 0
    for d in dirs:
        rel = d.relative_to(RUNTIME)
        try:
            diffs = (judge_run(engine, d) if fixture_door(d) == "run"
                     else judge_trace(engine, d))
        except UnsupportedFixture as e:
            unsupported += 1
            print(f"UNSUPPORTED  {rel} · {e}")
            continue
        except InvalidFixture as e:
            fixture_errors += 1
            print(f"FIXTURE-ERROR  {rel} · {e}")
            continue
        except Exception as e:  # engine crash / timeout / no events — loud
            errors += 1
            print(f"ENGINE-ERROR  {rel} · {e}")
            continue
        if diffs:
            diverged += 1
            print(f"DIVERGE   {rel}")
            for x in diffs:
                print(f"          · {x}")
        else:
            agree += 1
            print(f"AGREE     {rel}")
    print(f"\nruntime-differential · {agree + diverged + errors + fixture_errors + unsupported} fixtures · "
          f"{agree} agree · {diverged} diverge · {errors} engine-errors · "
          f"{fixture_errors} fixture-errors · {unsupported} unsupported")
    return 1 if (diverged or errors or fixture_errors or unsupported) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
