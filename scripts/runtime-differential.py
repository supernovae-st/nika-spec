#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""The behavioral tier's first command-level measure — both doors.

`tests/runtime/` reserved its fixtures "until the vertical slice lands";
the slice landed releases ago, and nobody had measured the tier by
command. This differential drives every fixture through the PUBLIC
surfaces (the binary boundary · never linkage):

- the RUN door · `nika run <input.nika.yaml> --json` (+ `--var k=v` from
  run.json `vars`, its `env` overlaid on the subprocess) — the NDJSON
  event stream projects onto expected-run.json: `workflow_state` from the
  terminal workflow_* event · per-task status from the task_* outcome
  `class` · `output` from outcome payload.value · `error_code` from
  payload.error.code · `events_include` membership with the dot↔underscore
  normalization (`task.started:<id>` ↔ kind task_started + task field).
  Each fixture runs in its own throwaway cwd (traces and fs effects stay
  out of the repo).
- the TRACE door · `nika trace verify <trace.ndjson>` — expected-verify
  verdicts map to measured surfaces: clean = rc 0 without the
  `FINDING — ` marker · finding = rc 0 with it · forged = rc 2 ·
  (rc 3 = unchained/missing input · no fixture expects it today).

Verdicts per fixture: AGREE · DIVERGE (each difference named) ·
ENGINE-ERROR (crash / no events — counted loud, never folded into
divergence). Exit 0 iff every fixture AGREEs.

    NIKA_BIN=/path/to/nika python3 scripts/runtime-differential.py
    NIKA_BIN=… python3 scripts/runtime-differential.py runtime/gates  # one area
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

SPEC_ROOT = pathlib.Path(__file__).resolve().parent.parent
# The behavioral universe is discovered by FILE SHAPE anywhere under
# tests/ (expected-run.json / expected-verify.json triples) — that is
# how tests/stdlib/behavioral/ joins the same sweep as tests/runtime/
# while the static tiers (expected.json) stay invisible to it.
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
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def project(events: list[dict]) -> dict:
    """The event stream → the expected-run.json shape."""
    state = None
    tasks: dict[str, dict] = {}
    seen: set[str] = set()
    for e in events:
        kind = e.get("kind", "")
        fields = {f["key"]: f["value"] for f in e.get("fields", [])
                  if isinstance(f, dict) and "key" in f}
        task = str(fields.get("task", ""))
        seen.add(f"{kind.replace('_', '.')}:{task}" if task else kind.replace("_", "."))
        if kind in WORKFLOW_STATE:
            state = WORKFLOW_STATE[kind]
        if kind in TERMINAL_TASK_KINDS and task:
            outcome = fields.get("outcome")
            out: dict = {}
            if isinstance(outcome, str):
                try:
                    out = json.loads(outcome)
                except json.JSONDecodeError:
                    out = {}
            payload = out.get("payload") or {}
            tasks[task] = {
                "status": out.get("class") or kind.removeprefix("task_"),
                "output": payload.get("value"),
                "error_code": (payload.get("error") or {}).get("code"),
            }
    return {"workflow_state": state, "tasks": tasks, "events": seen}


def judge_run(engine: str, d: pathlib.Path) -> list[str]:
    """Differences between the projected run and expected-run.json."""
    expected = json.loads((d / "expected-run.json").read_text())
    run = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    cmd = [engine, "run", str(d / "input.nika.yaml"), "--json"]
    # run.json carries the launch invocation: `vars` and `inputs` both land
    # on --var (the flag sets a workflow `inputs:` value) · `env` overlays
    # the subprocess. (The inputs key was authored ahead of the README —
    # found live: two regate fixtures failed VAR-001 because the harness
    # never threaded it, and the divergence was the harness's.)
    launch = {**(run.get("vars") or {}), **(run.get("inputs") or {})}
    for k, v in launch.items():
        cmd += ["--var", f"{k}={v if isinstance(v, str) else json.dumps(v)}"]
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (run.get("env") or {}).items()})
    with tempfile.TemporaryDirectory(prefix="nika-rt-") as scratch:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=180, cwd=scratch, env=env)
    events = parse_events(proc.stdout)
    if not events:
        # A run can refuse at its EMBEDDED CHECK before any event boots —
        # rc 2 with the check report (one pretty-printed object) on
        # stdout. That is a verdict, not a crash: name it as its own
        # difference so the fixture's runtime expectation reads against
        # the truth (the static gate fired first).
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            report = None
        if proc.returncode == 2 and isinstance(report, dict):
            return [f"CHECK-REFUSED pre-boot (clean={report.get('clean')}) · "
                    "the embedded static gate fired before any runtime event"]
        raise RuntimeError(f"no events on stdout (rc={proc.returncode} · "
                           f"stderr: {proc.stderr.strip()[:140]!r})")
    return diff_run(expected, project(events))


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
        if "output" in want and have["output"] != want["output"]:
            diffs.append(f"task {tid}.output: want {want['output']!r} · "
                         f"got {str(have['output'])[:80]!r}")
        if "output_contains" in want and want["output_contains"] not in str(have["output"]):
            diffs.append(f"task {tid}.output missing substring {want['output_contains']!r}")
        if "error_code" in want and have["error_code"] != want["error_code"]:
            diffs.append(f"task {tid}.error_code: want {want['error_code']} · "
                         f"got {have['error_code']}")
    for ev in expected.get("events_include") or []:
        if ev not in got["events"]:
            diffs.append(f"events_include missing {ev}")
    return diffs


def trace_verdict(rc: int, out: str) -> str:
    """The verify exit-map, pure — MEASURED, never assumed: forged rides
    rc 2 · finding exits 0 like clean and only the `FINDING — ` marker
    discriminates (selftest-pinned)."""
    if rc == 2:
        return "forged"
    if rc == 0:
        return "finding" if "FINDING — " in out else "clean"
    return f"rc={rc}"


def judge_trace(engine: str, d: pathlib.Path) -> list[str]:
    """Differences between the verify verdict and expected-verify.json."""
    want = json.loads((d / "expected-verify.json").read_text())["verdict"]
    proc = subprocess.run(
        [engine, "trace", "verify", str(d / "trace.ndjson"), "--color", "never"],
        capture_output=True, text=True, timeout=120,
    )
    got = trace_verdict(proc.returncode, proc.stdout + proc.stderr)
    return [] if got == want else [f"verdict: want {want} · got {got}"]


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
                                "payload": {"value": 2}})),
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
    checks.append(("a task with no terminal event is named",
                   any("no terminal event" in d for d in diff_run(
                       {"tasks": {"ghost": {"status": "success"}}}, got))))
    checks.append(("a pretty-printed check report is NOT an event stream",
                   parse_events('{\n  "analysis": {}\n}') == []))
    checks.append(("trace exit-map · clean / finding / forged / other",
                   trace_verdict(0, "OK — chain intact") == "clean"
                   and trace_verdict(0, "FINDING — witness absent") == "finding"
                   and trace_verdict(2, "") == "forged"
                   and trace_verdict(3, "") == "rc=3"))
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
    dirs = sorted(p for p in root.rglob("*")
                  if p.is_dir() and ((p / "expected-run.json").exists()
                                     or (p / "expected-verify.json").exists()))
    if not dirs:
        print(f"FAIL  {root} · no runtime fixtures found")
        return 1
    agree = diverged = errors = 0
    for d in dirs:
        rel = d.relative_to(RUNTIME)
        try:
            diffs = (judge_run(engine, d) if (d / "expected-run.json").exists()
                     else judge_trace(engine, d))
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
    print(f"\nruntime-differential · {agree + diverged + errors} fixtures · "
          f"{agree} agree · {diverged} diverge · {errors} engine-errors")
    return 1 if (diverged or errors) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
