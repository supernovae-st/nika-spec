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
- the TRACE door · `nika trace verify <abs trace.ndjson> --json --color
  never` — one JSON report (`verify_version` 1) framed by its exit (0/2/5
  on stdout · 3 as `nika: ` + the document on stderr), bound to the staged
  journal path and to the process exit. A closed table of typed families
  maps it to clean · finding · incomplete · forged · refused; the witness
  finding and the cost-replay leg are read from its ordered `lines`. A torn
  chain, an unknown family or another version is UNSUPPORTED, never a
  guessed verdict; any other reply is invalid evidence, never forged by its
  exit alone. Item tables come from `nika trace outputs <same path> --json
  --color never` (`outputs_version` 2 · only `id` and `items` are read), the
  prologue from the same frozen journal bytes, which must not change while
  the commands run.

Verdicts per fixture: AGREE · DIVERGE (each difference named) ·
ENGINE-ERROR (crash / timeout / signal / no events / a journal changed under
measurement — counted loud, never folded into divergence) · FIXTURE-ERROR
(invalid expectation, before engine invocation) · UNSUPPORTED (a valid
contract or a well-framed reply this runner has no adapter for — never
agreement, and never hiding a divergence).
Exit 0 iff every fixture AGREEs.

    NIKA_BIN=/path/to/nika python3 scripts/runtime-differential.py
    NIKA_BIN=… python3 scripts/runtime-differential.py runtime/gates  # one area
"""
from __future__ import annotations

import trace_media

import hashlib
import json
import math
import os
import pathlib
import re
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
    if claim in {"expected-approval.json", "expected-http.json",
                 "expected-compose.json", "expected-export.json"}:
        # A separate, fully validated observation contract never falls through
        # to run or verify. Load the pure validator only for these new doors.
        import importlib.util
        module_spec = importlib.util.spec_from_file_location(
            "nika_observation_contracts", pathlib.Path(__file__).with_name("observation_contracts.py"))
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        try:
            capability = module.validate(directory, claim)
        except (ValueError, TypeError, UnicodeError, OSError) as error:
            raise InvalidFixture(str(error)) from error
        raise UnsupportedFixture(f"{capability} requires a qualified command adapter")
    if claim in {"expected-resume.json", "expected-explain.json", "expected-energy.json"}:
        # A separate door is recognized only once its expectation is one well-formed
        # JSON object: malformed bytes stay FIXTURE-ERROR, never « unsupported ». The
        # rest of that door's contract is not validated by this adapter.
        try:
            value = strict_json((directory / claim).read_text(encoding="utf-8"))
        except (ValueError, UnicodeError, OSError) as error:
            raise InvalidFixture(f"{claim} is not one well-formed JSON document: {error}") from error
        if not isinstance(value, dict):
            raise InvalidFixture(f"{claim} must be a JSON object")
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
        unknown = set(expected) - {"verdict", "cost_replay", "prologue", "items", "harness_media", "note"}
        if unknown:
            raise ValueError(f"unknown trace assertion: {', '.join(sorted(unknown))}")
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
        if "harness_media" in expected:
            trace_media.validate_expected(expected["harness_media"])
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


# The trace door reads the reference engine's own JSON reports. One command
# yields one report, framed by its exit as the command dispatcher prints it: exit
# 0, 2 or 5 put the document on stdout; exit 3 puts `nika: ` and the document
# on stderr. Nothing is read from prose outside that document, and no other
# version or family inherits a known verdict.
ENV_PREFIX = "nika: "
VERIFY_VERSION = 1
OUTPUTS_VERSION = 2
LADDER_TIERS = {"ok", "sealed", "anchored", "replayed"}
FINISH_EXITS = {"broken": 2, "buried-seal": 2, "line-over-long": 2, "refused": 3,
                "unchained": 3, "empty": 3, "unreadable": 3}
# (attained tier, seal leg, anchor leg) → the exit of that ladder; any other
# combination is no report of a keyless, anchor-free, replay-free verify.
LADDER_ROWS = {
    ("ok", "unsealed", "not-present"): 0,
    ("sealed", "sealed", "not-present"): 0,
    ("anchored", "sealed", "anchored"): 0,
    ("ok", "forged", "not-present"): 2,
    ("sealed", "sealed", "gap"): 2,
    ("ok", "unattributable", "not-present"): 3,
}
SEAL_FIELDS = {"unsealed": {}, "sealed": {"key_id": str, "source": str},
               "forged": {"reason": str}, "unattributable": {"reason": str},
               "buried": {"line": int, "trailing": int}}
ANCHOR_FIELDS = {"not-present": {}, "required": {}, "gap": {"reason": str},
                 "anchored": {"log_index": str, "tree_size": str, "gen_time": str}}
REPLAY_FIELDS = {"not-asked": {}, "replayed": {}, "diverged": {"reason": str},
                 "not-attempted": {"reason": str}}
# The leg a line states by its marker, the most specific first; None marks a value no
# keyless, anchor-free, replay-free verify produces. A refusing leg must be stated.
LEG_MARKERS = (
    ("UNSEALED — ", "seal", "unsealed"), ("SEALED — ", "seal", "sealed"),
    ("SEAL FORGED — ", "seal", "forged"), ("SEAL UNATTRIBUTABLE — ", "seal", "unattributable"),
    ("SEAL BURIED — ", "seal", "buried"),
    ("ANCHORED — rekor index ", "anchor", "anchored"),
    ("ANCHORED — no sidecar", "anchor", "not-present"),
    ("ANCHOR FORGED — ", "anchor", "gap"), ("ANCHORED — ", "anchor", None),
    ("REPLAYED — the journal re-executes identically", "replay", "replayed"),
    ("REPLAYED — not attempted (pass --replay", "replay", "not-asked"),
    ("REPLAYED — not attempted: ", "replay", "not-attempted"),
    ("REPLAY DIVERGED — ", "replay", "diverged"), ("REPLAYED — ", "replay", None),
)
STATED_REFUSALS = {("seal", "forged"), ("seal", "unattributable"), ("anchor", "gap")}
# A headline line belongs to one report family; no report carries a second.
HEADLINES = ("OK — ", "INCOMPLETE — ", "BROKEN at line ", "TAMPERED — ")
BOUND_PHRASES = ("beyond the verifier's line bound", "over the journal bound")
WITNESS = "FINDING — the run exercised effects and carries zero permit_checked frames"
BROKEN = re.compile(r"BROKEN at line \d+ — ")
LINE_BOUND = re.compile(r"line \d+ is (\d+) bytes — beyond the verifier's line bound \((\d+) bytes\)")
FILE_BOUND = re.compile(r"(\d+) bytes — over the journal bound \((\d+) bytes · NEP-0012 law 1 · "
                        r"a file beyond it is not a run this engine produced\)")


class InvalidEvidence(ValueError):
    """An engine reply that is not one well-typed report of its family."""


class InvalidMeasurement(RuntimeError):
    """The journal changed while its commands ran: no observation is joined."""


def decoded(stream) -> str:
    """Commands return bytes; invalid UTF-8 is invalid evidence, never repaired."""
    if isinstance(stream, bytes):
        try:
            return stream.decode("utf-8")
        except UnicodeDecodeError as error:
            raise InvalidEvidence("output is not UTF-8") from error
    return stream or ""


def one_object(text: str) -> dict:
    """Exactly one strict JSON object, outer whitespace only."""
    try:
        document = strict_json(text)
    except ValueError as error:
        raise InvalidEvidence(f"not one JSON document ({error})") from error
    if not isinstance(document, dict):
        raise InvalidEvidence("the report is not a JSON object")
    return document


def framed_report(proc) -> dict:
    """The one document a command frames by its exit; no search, no prose fallback."""
    if proc.returncode < 0:
        raise RuntimeError(f"killed by signal {-proc.returncode}")
    stdout, stderr = decoded(proc.stdout), decoded(proc.stderr)
    if proc.returncode in (0, 2, 5):
        if stderr.strip():
            raise InvalidEvidence("stderr beside a stdout report")
        return one_object(stdout)
    if proc.returncode != 3:
        raise InvalidEvidence(f"exit {proc.returncode} frames no report")
    if stdout.strip():
        raise InvalidEvidence("stdout beside an ENV report")
    if not stderr.startswith(ENV_PREFIX):
        raise InvalidEvidence("an ENV report without its exact frame")
    return one_object(stderr[len(ENV_PREFIX):])


def verify_report(proc, trace: str) -> dict:
    """The verify document bound to this command: version, subject, exit, lines."""
    document = framed_report(proc)
    version = document.get("verify_version")
    if type(version) is not int:
        raise InvalidEvidence("verify_version is not an integer")
    if version != VERIFY_VERSION:
        raise UnsupportedFixture(f"verify_version {version} has no admitted adapter")
    if document.get("trace") != trace:
        raise InvalidEvidence("the report names another trace")
    if type(document.get("tier")) is not str or not document["tier"]:
        raise InvalidEvidence("tier is not a nonempty string")
    if type(document.get("exit")) is not int or document["exit"] != proc.returncode:
        raise InvalidEvidence("exit does not state the process exit")
    lines = document.get("lines")
    if not isinstance(lines, list) or any(type(line) is not str for line in lines):
        raise InvalidEvidence("lines is not a list of strings")
    return document


def physical(lines: list[str]) -> list[str]:
    """Every entry's own lines, in order: one entry may hold several."""
    return [row for entry in lines for row in entry.split("\n")]


def headline_line(line: str) -> bool:
    return line.startswith(HEADLINES) or any(phrase in line for phrase in BOUND_PHRASES)


def stated_legs(lines: list[str]) -> list[tuple[str, str | None]]:
    """The leg each line states by its marker, in order; a line without one states none."""
    stated = []
    for line in lines:
        marker = next(((name, value) for prefix, name, value in LEG_MARKERS
                       if line.startswith(prefix)), None)
        if marker:
            stated.append(marker)
    return stated


def leg(document: dict, name: str, families: dict) -> str:
    """One typed ladder leg; an unrecognized value has no admitted reading."""
    value = document.get(name)
    if not isinstance(value, dict) or type(value.get("tier")) is not str:
        raise InvalidEvidence(f"{name} is not a typed leg")
    tier = value["tier"]
    if tier not in families:
        raise UnsupportedFixture(f"{name} tier {tier!r} has no admitted reading")
    for key, kind in families[tier].items():
        if type(value.get(key)) is not kind:
            raise InvalidEvidence(f"{name}.{key} is not a {kind.__name__}")
    return tier


def chain_headline(document: dict) -> str:
    """The chain's own headline, with the liveness only an incomplete one carries."""
    chain = document.get("chain")
    if not isinstance(chain, dict):
        raise InvalidEvidence("chain is not an object")
    events, head = chain.get("events"), chain.get("head")
    if type(events) is not int or events < 0 or type(head) is not str or not head:
        raise InvalidEvidence("chain events or head are mistyped")
    if type(chain.get("headline")) is not str or "liveness" not in chain:
        raise InvalidEvidence("chain headline or liveness is missing")
    headline, liveness = chain["headline"], chain["liveness"]
    if headline not in ("intact", "torn", "incomplete"):
        raise UnsupportedFixture(f"chain headline {headline!r} has no admitted reading")
    if headline != "incomplete":
        if liveness is not None:
            raise InvalidEvidence(f"an {headline} chain states a liveness")
    elif type(liveness) is not str:
        raise InvalidEvidence("an incomplete chain without its liveness")
    elif liveness not in ("alive", "dead", "unknown"):
        raise UnsupportedFixture(f"liveness {liveness!r} has no admitted reading")
    return headline


def ladder_reading(document: dict) -> tuple[str, str]:
    """A ladder report: its typed legs decide and its owned lines must agree."""
    headline = chain_headline(document)
    seal = leg(document, "seal", SEAL_FIELDS)
    anchor = leg(document, "anchor", ANCHOR_FIELDS)
    replay = leg(document, "replay", REPLAY_FIELDS)
    row = (document["tier"], seal, anchor)
    if replay != "not-asked" or row not in LADDER_ROWS:
        raise InvalidEvidence(f"tier {row[0]} · seal {seal} · anchor {anchor} · replay {replay} "
                              "is no report of this invocation")
    lines = physical(document["lines"])
    typed = {"seal": seal, "anchor": anchor, "replay": replay}
    stated = stated_legs(lines)
    if any(typed[name] != value for name, value in stated):
        raise InvalidEvidence("a line states a leg its typed field contradicts")
    if not ({(name, typed[name]) for name in typed} & STATED_REFUSALS) <= set(stated):
        raise InvalidEvidence("a refusing leg is not stated by its lines")
    if any(headline_line(line) for line in lines):
        raise InvalidEvidence("a ladder report carries a headline line")
    code, exit_code = LADDER_ROWS[row], document["exit"]
    if code:
        # A refusing leg keeps its own exit, whatever the lifecycle says.
        if exit_code != code:
            raise InvalidEvidence(f"a {seal} seal and {anchor} anchor at exit {exit_code}")
        return ("verdict", "forged") if code == 2 else ("observation", "unattributable")
    if headline == "incomplete":
        if row != ("ok", "unsealed", "not-present") or exit_code != 5:
            raise InvalidEvidence(f"an incomplete chain with a {seal} seal at exit {exit_code}")
        return "verdict", "incomplete"
    if exit_code:
        raise InvalidEvidence(f"an {headline} chain at exit {exit_code}")
    if headline == "torn":
        return "observation", "torn"
    findings = [line for line in lines if line.startswith("FINDING")]
    witnesses = [line for line in findings if line.startswith(WITNESS)]
    if len(witnesses) != len(findings):
        raise UnsupportedFixture("a finding family this adapter does not read")
    if len(witnesses) > 1:
        raise InvalidEvidence("a repeated witness finding")
    return "verdict", "finding" if witnesses else "clean"


def finish_reading(document: dict, trace: str) -> tuple[str, str]:
    """A non-ladder report: its family, its exit and its own headline line."""
    tier, exit_code = document["tier"], document["exit"]
    if any(name in document for name in ("chain", "seal", "anchor", "replay")):
        raise InvalidEvidence(f"a {tier} report carries a ladder claim")
    if exit_code != FINISH_EXITS[tier]:
        raise InvalidEvidence(f"a {tier} report at exit {exit_code}")
    first, *rest = physical(document["lines"]) or [""]
    if any(headline_line(line) for line in rest):
        raise InvalidEvidence(f"a {tier} report carries a second headline")
    # A finish family states no ladder leg, a buried seal only its own.
    if stated_legs([first, *rest]) != ([("seal", "buried")] if tier == "buried-seal" else []):
        raise InvalidEvidence(f"a {tier} report states a ladder leg it does not carry")
    if tier == "broken" and BROKEN.match(first):
        return "verdict", "forged"
    if tier == "buried-seal" and first.startswith("TAMPERED — "):
        return "verdict", "forged"
    bound = LINE_BOUND.fullmatch(first)
    if tier == "line-over-long" and bound and int(bound[1]) > int(bound[2]):
        return "verdict", "refused"
    if tier == "refused":
        # The decode bound is the exact total-file report; a key refusal is not.
        size = FILE_BOUND.fullmatch(first[len(trace) + 2:]) \
            if first.startswith(trace + ": ") and not rest else None
        if size and int(size[1]) > int(size[2]):
            return "verdict", "refused"
        return "observation", "refused without the file-bound report"
    if tier in ("unchained", "empty", "unreadable"):
        return "observation", tier
    raise InvalidEvidence(f"a {tier} report without its own headline line")


def verify_reading(document: dict, trace: str) -> tuple[str, str]:
    """A verdict from one admitted family, or a named observation no fixture claims."""
    tier = document["tier"]
    if tier in LADDER_TIERS:
        return ladder_reading(document)
    if tier in FINISH_EXITS:
        return finish_reading(document, trace)
    raise UnsupportedFixture(f"verify tier {tier!r} has no admitted reading")


def cost_replay_verdict(lines: list[str]) -> str:
    """The report's own budget leg: one marker, its continuation in the same entry."""
    markers = [(rows, index) for rows in (entry.split("\n") for entry in lines)
               for index, row in enumerate(rows) if row.startswith("COST-REPLAY — ")]
    if len(markers) != 1:
        return "missing-or-ambiguous"
    rows, index = markers[0]
    marker, following = rows[index], rows[index + 1:index + 2]
    if marker.startswith("COST-REPLAY — unrecorded · "):
        return "unrecorded"
    if marker.startswith("COST-REPLAY — REFUSED · "):
        return "refused"
    phrase = "  the budget verdict re-judged from the journaled dollars"
    if marker.startswith("COST-REPLAY — the pinned pricing table is this engine's (") \
            and following and (following[0] == phrase or following[0].startswith(phrase + " (")):
        return "replayed"
    return "unrecognized"


def journal_prologue(raw: bytes, expected: dict) -> list[str]:
    """Read only the initial nonempty event of the frozen bytes; other laws stay engine-owned."""
    try:
        first = next((line for line in raw.split(b"\n") if line.strip()), b"")
        event = json.loads(first.decode("utf-8"), object_pairs_hook=unique_object,
                           parse_float=finite_float)
        if not isinstance(event, dict):
            raise ValueError("initial event must be an object")
    except ValueError as error:
        return [f"prologue: cannot read initial event ({error})"]
    return diff_prologue(expected, [event])


def outputs_tasks(proc, trace: str) -> dict:
    """The version-2 task projection bound to this journal, by unique task identity."""
    if proc.returncode < 0:
        raise RuntimeError(f"trace outputs killed by signal {-proc.returncode}")
    if proc.returncode:
        raise InvalidEvidence(f"trace outputs exited {proc.returncode}")
    stdout, stderr = decoded(proc.stdout), decoded(proc.stderr)
    if stderr.strip():
        raise InvalidEvidence("stderr beside the projection")
    document = one_object(stdout)
    version = document.get("outputs_version")
    if type(version) is not int:
        raise InvalidEvidence("outputs_version is not an integer")
    if version != OUTPUTS_VERSION:
        raise UnsupportedFixture(f"outputs_version {version} has no admitted item adapter")
    if document.get("trace") != trace:
        raise InvalidEvidence("the projection names another trace")
    tasks = document.get("tasks")
    if not isinstance(tasks, list):
        raise InvalidEvidence("missing task array")
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or type(task.get("id")) is not str or not task["id"]:
            raise InvalidEvidence("malformed task")
        if task["id"] in by_id:
            raise InvalidEvidence("duplicate task identity")
        by_id[task["id"]] = task
    return by_id


def diff_items(expected: dict, by_id: dict) -> list[str]:
    """Judge the engine's item projection, not a second local page fold."""
    diffs = []
    for task_id, wanted in expected.items():
        if task_id not in by_id or "items" not in by_id[task_id]:
            diffs.append(f"items {task_id}: task or item table absent")
        # JSON equality keeps true distinct from 1 and a numeric index from
        # its string spelling; array order and every row field are asserted.
        elif not json_equal(by_id[task_id]["items"], wanted):
            diffs.append(f"items {task_id}: projection differs from expected table")
    return diffs


def judge_trace(engine: str, d: pathlib.Path) -> list[str]:
    """Differences between the engine's JSON reports and expected-verify.json."""
    if fixture_door(d) != "trace":
        raise InvalidFixture("trace door requires expected-verify.json")
    expected = load_trace_expectation(d / "expected-verify.json")
    try:
        journal = (d / "trace.ndjson").resolve(strict=True)
        frozen = journal.read_bytes()
    except OSError as error:
        raise InvalidFixture(f"cannot stage trace.ndjson: {error}") from error
    # One canonical path and one byte image serve every command and the prologue.
    trace, digest, want = str(journal), hashlib.sha256(frozen).hexdigest(), expected["verdict"]
    diffs, unsupported, admitted = [], [], None
    proc = subprocess.run([engine, "trace", "verify", trace, "--json", "--color", "never"],
                          capture_output=True, timeout=120)
    try:
        report = verify_report(proc, trace)
        kind, got = verify_reading(report, trace)
        admitted = report
    except InvalidEvidence as error:
        diffs.append(f"verify: invalid evidence ({error})")
    except UnsupportedFixture as error:
        unsupported.append(f"verify: {error}")
    else:
        if kind == "observation" and got == "torn" and want in ("clean", "finding", "incomplete"):
            unsupported.append(f"verify: a torn chain attests no lifecycle end for {want}")
        elif got != want:
            diffs.append(f"verdict: want {want} · got {got}")
    if "cost_replay" in expected and admitted is not None:
        replay = cost_replay_verdict(admitted["lines"])
        if replay != expected["cost_replay"]:
            diffs.append(f"cost_replay: want {expected['cost_replay']} · got {replay}")
    if expected.get("prologue"):
        # This is a semantic assertion over recorded bytes, not a second
        # integrity verifier. The engine's verdict above remains mandatory.
        diffs += journal_prologue(frozen, expected["prologue"])
    if "harness_media" in expected:
        diffs += trace_media.compare_journal(frozen, expected["harness_media"], strict_json, json_equal)
    if "items" in expected:
        projection = subprocess.run(
            [engine, "trace", "outputs", trace, "--json", "--color", "never"],
            capture_output=True, timeout=120,
        )
        try:
            diffs += diff_items(expected["items"], outputs_tasks(projection, trace))
        except InvalidEvidence as error:
            diffs.append(f"items: invalid evidence ({error})")
        except UnsupportedFixture as error:
            unsupported.append(f"items: {error}")
    try:
        after = hashlib.sha256(journal.read_bytes()).hexdigest()
    except OSError as error:
        raise InvalidMeasurement(f"trace.ndjson unreadable after its commands: {error}") from error
    if after != digest:
        raise InvalidMeasurement("trace.ndjson changed while its commands ran")
    if diffs:
        return diffs + [f"unsupported · {note}" for note in unsupported]
    if unsupported:
        raise UnsupportedFixture("; ".join(unsupported))
    return []


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
    # The trace door's JSON reports (verify v1): a closed table of positive
    # families; framing, types, subject, exit and owned lines must agree.
    trace = "/fixtures/case/trace.ndjson"
    def ladder(lines=(), code=0, headline="intact", liveness=None, tier="ok",
               seal=None, anchor=None, path=trace, **extra):
        return json.dumps({"verify_version": 1, "trace": path, "tier": tier, "exit": code,
                           "chain": {"events": 9, "head": "0123abcd", "headline": headline,
                                     "liveness": liveness},
                           "seal": seal or {"tier": "unsealed"},
                           "anchor": anchor or {"tier": "not-present"},
                           "replay": {"tier": "not-asked"}, "lines": list(lines), **extra})
    def finish(tier, code, lines, **extra):
        return json.dumps({"verify_version": 1, "trace": trace, "tier": tier, "exit": code,
                           "lines": lines, **extra})
    def verdict_of(code, stdout, stderr=""):
        try:
            report = verify_report(subprocess.CompletedProcess([], code, stdout, stderr), trace)
            return ":".join(verify_reading(report, trace))
        except InvalidEvidence:
            return "invalid"
        except UnsupportedFixture:
            return "unsupported"
    witness = WITNESS + ": the\n  permit witness is absent"
    forged = {"tier": "forged", "reason": "the signature does not verify"}
    broken = ["BROKEN at line 4 — recorded chain a · computed b"]
    file_bound = (f"{trace}: 268435457 bytes — over the journal bound (268435456 bytes · "
                  "NEP-0012 law 1 · a file beyond it is not a run this engine produced)")
    for label, code, stdout, stderr, wanted in [
        ("an intact unsealed ladder is clean", 0, ladder(), "", "verdict:clean"),
        ("one witness finding is a finding", 0, ladder([witness]), "", "verdict:finding"),
        ("incomplete has its exit 5 and a liveness", 5,
         ladder(code=5, headline="incomplete", liveness="dead"), "", "verdict:incomplete"),
        ("a forged seal leg is forged", 2, ladder(["SEAL FORGED — bad"], 2, seal=forged), "",
         "verdict:forged"),
        ("a broken chain is forged", 2, finish("broken", 2, broken), "", "verdict:forged"),
        ("an append after the seal is forged", 2,
         finish("buried-seal", 2, ["TAMPERED — 9 events · chain intact · head 0123abcd",
                                   "SEAL BURIED — the journal carries a run_sealed frame"]),
         "", "verdict:forged"),
        ("the line bound is refused", 2,
         finish("line-over-long", 2,
                ["line 2 is 1048890 bytes — beyond the verifier's line bound (1048576 bytes)"]),
         "", "verdict:refused"),
        ("the file bound is refused in its ENV frame", 3, "",
         "nika: " + finish("refused", 3, [file_bound]), "verdict:refused"),
        ("a key refusal is not the decode bound", 3, "",
         "nika: " + finish("refused", 3, ["no trusted key: the keyring is unreadable"]),
         "observation:refused without the file-bound report"),
        ("a torn chain is its own observation", 0, ladder(headline="torn"), "",
         "observation:torn"),
        ("an empty exit 2 is no forgery", 2, "", "", "invalid"),
        ("an arbitrary exit 2 is no forgery", 2, "error: unexpected argument", "", "invalid"),
        ("prose is no report", 0, "OK — 9 events · chain intact · head 0123abcd", "", "invalid"),
        ("a stdout report at exit 3 is the wrong frame", 3, finish("refused", 3, [file_bound]),
         "", "invalid"),
        ("a warning beside the report is no single report", 0, ladder(), "warning: x",
         "invalid"),
        ("two documents are no single report", 0, ladder() + ladder(), "", "invalid"),
        ("another verify_version is unsupported", 0, ladder(verify_version=2), "",
         "unsupported"),
        ("a boolean version is no version", 0, ladder(verify_version=True), "", "invalid"),
        ("another journal is another subject", 0, ladder(path="/elsewhere/trace.ndjson"), "",
         "invalid"),
        ("the stated exit is the process exit", 0, ladder(code=2), "", "invalid"),
        ("an intact chain cannot exit 5", 5, ladder(code=5), "", "invalid"),
        ("an incomplete chain cannot exit 0", 0,
         ladder(headline="incomplete", liveness="dead"), "", "invalid"),
        ("a forged leg cannot exit 0", 0, ladder(["SEAL FORGED — bad"], seal=forged), "",
         "invalid"),
        ("a refusing line contradicts a clean ladder", 0, ladder(["SEAL FORGED — bad"]), "",
         "invalid"),
        ("a positive leg line contradicts its typed leg", 0,
         ladder(["SEALED — the run_sealed signature verifies · key k1 (trusted)"]), "", "invalid"),
        ("a broken report states no ladder leg", 2,
         finish("broken", 2, broken + ["ANCHOR FORGED — contradictory diagnostic"]), "",
         "invalid"),
        ("a headline line contradicts a ladder", 0,
         ladder(["OK — 9 events · chain intact · head 0123abcd"]), "", "invalid"),
        ("a replay result needs --replay", 0, ladder(replay={"tier": "replayed"}), "",
         "invalid"),
        ("an unknown verify tier is unsupported", 3, "", "nika: " + finish("unknown", 3, ["?"]),
         "unsupported"),
        ("an unknown finding family is unsupported", 0, ladder(["FINDING — a new law"]), "",
         "unsupported"),
        ("a repeated witness is no finding", 0, ladder([witness, witness]), "", "invalid"),
        ("a finish report cannot carry a ladder", 2, finish("broken", 2, broken, chain={}), "",
         "invalid"),
    ]:
        checks.append((f"verify JSON · {label}", verdict_of(code, stdout, stderr) == wanted))
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
    def item_document(value, version=2, path=trace):
        return json.dumps({"outputs_version": version, "trace": path, "state": "completed",
                           "liveness": None,
                           "tasks": [{"id": "fan", "status": "ok", "cause": "normal",
                                      "error_code": None, "recovered_from": None,
                                      "items": value}]})
    def items_diff(wanted, raw, code=0, stderr=""):
        try:
            return diff_items(wanted, outputs_tasks(
                subprocess.CompletedProcess([], code, raw, stderr), trace))
        except InvalidEvidence as error:
            return [f"invalid: {error}"]
        except UnsupportedFixture as error:
            return [f"unsupported: {error}"]
    checks.append(("exact item projection preserves cancelled versus never_started",
                   items_diff({"fan": rows}, item_document(rows)) == []))
    checks.append(("incomplete item table remains unrecorded",
                   items_diff({"fan": None}, item_document(None)) == []))
    for label, value in [
        ("cancelled relabelled never_started", [rows[0], {**rows[1], "status": "never_started"}, rows[2]]),
        ("false completion of missing pages", []),
        ("lost item", rows[:-1]),
        ("reordered items", list(reversed(rows))),
        ("boolean index", [rows[0], {**rows[1], "index": True}, rows[2]]),
        ("string index", [{**rows[0], "index": "0"}, *rows[1:]]),
    ]:
        checks.append((f"item assertion refuses {label}",
                       bool(items_diff({"fan": rows}, item_document(value)))))
    checks.append(("a complete table cannot stand in for an incomplete one",
                   bool(items_diff({"fan": None}, item_document(rows)))))
    head = '{"outputs_version":2,"trace":' + json.dumps(trace) + ','
    for raw in ('{}', '[]', '{', head + '"tasks":[]}',
                head + '"tasks":[{"id":"fan","items":null},{"id":"fan","items":null}]}',
                head + '"tasks":[{"id":"fan","items":null,"items":[]}]}',
                head + '"tasks":[{"id":"fan"}]}'):
        checks.append(("malformed, absent or field-less item projection fails",
                       bool(items_diff({"fan": None}, raw))))
    checks.append(("outputs version 1 is unsupported, never read as version 2",
                   items_diff({"fan": rows}, item_document(rows, version=1))[0]
                   .startswith("unsupported")))
    for label, raw, code, stderr in [
        ("a boolean version", item_document(rows, version=True), 0, ""),
        ("a string version", item_document(rows, version="2"), 0, ""),
        ("another journal", item_document(rows, path="/elsewhere/trace.ndjson"), 0, ""),
        ("a nonzero exit", item_document(rows), 3, ""),
        ("a warning beside it", item_document(rows), 0, "warning: x"),
    ]:
        outcome = items_diff({"fan": rows}, raw, code, stderr)
        checks.append((f"item projection refuses {label}",
                       bool(outcome) and outcome[0].startswith("invalid")))
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
                    "  the budget verdict re-judged from the journaled dollars (re-pricing)",
    }
    known, phrase = replay_lines["replayed"].split("\n")
    for wanted, line in replay_lines.items():
        checks.append((f"cost replay reads {wanted} from its own entry",
                       cost_replay_verdict(["UNSEALED — no run_sealed frame", line]) == wanted))
    for label, lines in [
        ("missing", []),
        ("unknown", ["COST-REPLAY — unknown"]),
        ("unjudged pin", [known]),
        ("conflicting", [replay_lines["replayed"], replay_lines["refused"]]),
        ("continuation in another entry", [known, phrase]),
        ("blank before the continuation", [known + "\n\n" + phrase]),
        ("reordered continuation", [phrase + "\n" + known]),
        ("indented marker", ["  " + replay_lines["unrecorded"]]),
    ]:
        checks.append((f"cost replay refuses {label} evidence",
                       cost_replay_verdict(lines) not in replay_lines))
    def staged(scratch, expected, journal=b"{}\n"):
        fixture = pathlib.Path(scratch)
        (fixture / "trace.ndjson").write_bytes(journal)
        (fixture / "expected-verify.json").write_text(json.dumps(expected))
        return fixture, str((fixture / "trace.ndjson").resolve())
    for wanted in replay_lines:
        for actual, line in replay_lines.items():
            with tempfile.TemporaryDirectory(prefix="nika-cost-selftest-") as scratch:
                fixture, path = staged(scratch, {"verdict": "clean", "cost_replay": wanted})
                with patch("subprocess.run") as invoke:
                    invoke.return_value = subprocess.CompletedProcess(
                        [], 0, ladder([line], path=path), "")
                    diffs = judge_trace("unused-engine", fixture)
                    checks.append((f"cost replay {wanted} compared with {actual}",
                                   bool(diffs) == (wanted != actual)
                                   and invoke.call_count == 1))
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
            fixture, path = staged(
                scratch, {"verdict": "clean", "prologue": {"present": ["seed"]}}, raw)
            with patch("subprocess.run") as invoke:
                invoke.return_value = subprocess.CompletedProcess([], 0, ladder(path=path), "")
                try:
                    differences = judge_trace("unused-engine", fixture)
                    held = (not differences) == agrees and invoke.call_count == 1
                except (ValueError, TypeError, AttributeError, UnicodeError):
                    held = False
                checks.append((f"journal prologue reads {label} without misattribution", held))
    # One fixture, one class: an unsupported reading never agrees nor hides a
    # divergence, a journal changed under measurement joins nothing, and the
    # commands are exactly the two JSON doors on one canonical path.
    def judged(expected, *replies, mutate=None):
        with tempfile.TemporaryDirectory(prefix="nika-door-selftest-") as scratch:
            fixture, path = staged(scratch, expected)
            answers = iter(replies)
            def double(argv, **kwargs):
                if mutate is not None:
                    (fixture / "trace.ndjson").write_bytes(mutate)
                return subprocess.CompletedProcess(argv, 0, next(answers)(path), "")
            with patch("subprocess.run", side_effect=double) as invoke:
                try:
                    outcome = "DIVERGE" if judge_trace("engine", fixture) else "AGREE"
                except UnsupportedFixture:
                    outcome = "UNSUPPORTED"
                except InvalidMeasurement:
                    outcome = "INVALID-MEASUREMENT"
                return outcome, [call.args[0] for call in invoke.call_args_list], path
    clean = lambda path: ladder(path=path)
    torn = lambda path: ladder(headline="torn", path=path)
    version_1 = lambda path: item_document(rows, version=1, path=path)
    version_2 = lambda path: item_document(rows, path=path)
    outcome, calls, path = judged({"verdict": "clean", "items": {"fan": rows}}, clean, version_2)
    checks.append(("the doors are exactly verify --json and outputs --json on one path",
                   outcome == "AGREE" and calls == [
                       ["engine", "trace", "verify", path, "--json", "--color", "never"],
                       ["engine", "trace", "outputs", path, "--json", "--color", "never"]]))
    checks.append(("no item claim issues no projection command",
                   judged({"verdict": "clean"}, clean)[1][1:] == []))
    checks.append(("a torn chain cannot discharge clean",
                   judged({"verdict": "clean"}, torn)[0] == "UNSUPPORTED"))
    checks.append(("a torn chain still diverges from forged",
                   judged({"verdict": "forged"}, torn)[0] == "DIVERGE"))
    checks.append(("version-1 items are unsupported, never agreement",
                   judged({"verdict": "clean", "items": {"fan": rows}}, clean, version_1)[0]
                   == "UNSUPPORTED"))
    checks.append(("an unsupported door never hides a divergence",
                   judged({"verdict": "forged", "items": {"fan": rows}}, clean, version_1)[0]
                   == "DIVERGE"))
    checks.append(("a journal changed under measurement joins nothing",
                   judged({"verdict": "clean"}, clean, mutate=b"{}\n{}\n")[0]
                   == "INVALID-MEASUREMENT"))
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
    markers = {"input.nika", "draft.nika", "run.json", "trace.ndjson"}
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
