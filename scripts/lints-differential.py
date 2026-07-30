#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""The lints tier's first differential — measured through the only door.

The corpus (conformance/tests/lints/ · expected-lints.json · exact ordered
equality per runner-protocol.md) carries two rule families with OPPOSITE
public surfaces, and this measurement names the split rather than papering
it:

- `native-first/*` rides `nika check --json` — each firing rule arrives in
  `hints[]` as {kind: "native-first", advice: "native-first/NNN · …",
  task}. MEASURABLE by command today (the binary boundary honoured).
- `one-obvious-way/*` has NO command-level surface: the engine's
  `lints_one_obvious_way` suite walks this very corpus LINKED, in-repo —
  a single oracle proving the corpus from inside. A fixture expecting that
  family is NO-DOOR here: named and counted loud, never a silent pass or
  a fake fail. (First measured 2026-07-30 · the surface owe is the engine's,
  same genre as the codeless rungs.)

Fixture classes by directory prefix (the corpus naming is the family):
  nf*      native-first pair        → MEASURED (exact ordered rule+task)
  clean-*  global silence           → MEASURED AT THE DOOR (hints must be
           empty · the one-obvious-way half of that silence stays
           command-unverifiable until the door exists)
  else     one-obvious-way corpus   → NO-DOOR

Exit 0 iff zero MEASURED fixtures diverge (NO-DOOR never fails the run —
it is the measurement's finding, printed loud).

    NIKA_BIN=/path/to/nika python3 scripts/lints-differential.py
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

SPEC_ROOT = pathlib.Path(__file__).resolve().parent.parent
LINTS = SPEC_ROOT / "conformance" / "tests" / "lints"


def hints_pairs(report: dict) -> list[tuple[str, str]]:
    """(rule, task) pairs from a check report, report order kept.

    Only `kind: "native-first"` hints are lints — the surface also carries
    non-lint advisories (the F-P3 clock hint, cost/energy notes) that
    expected-lints.json never speaks, so harvesting every hint would fake
    divergences on clean fixtures (found live on first run · pinned by
    the selftest's clock-advisory tamper case).
    """
    pairs: list[tuple[str, str]] = []
    for h in report.get("hints") or []:
        if not isinstance(h, dict) or h.get("kind") != "native-first":
            continue
        rule = str(h.get("advice", "")).split(" · ", 1)[0]
        pairs.append((rule, str(h.get("task", ""))))
    return pairs


def engine_hints(engine: str, workflow: pathlib.Path) -> list[tuple[str, str]]:
    proc = subprocess.run(
        [engine, "check", "--json", str(workflow)],
        capture_output=True, text=True, timeout=120,
    )
    out = proc.stdout
    start = out.find("{")
    if start < 0:
        raise RuntimeError(f"no JSON from the engine on {workflow.name} · "
                           f"stderr: {proc.stderr.strip()[:160]!r}")
    return hints_pairs(json.loads(out[start:]))


def selftest() -> int:
    """The judge's own laws, offline — no engine, CI-runnable.

    A differential whose extraction lies reads as agreement forever, so
    the extraction is pinned: the kind filter (a non-lint advisory must
    contribute NOTHING · the fake-divergence class found live), the
    advice-prefix rule id, report order, and the empty surface.
    """
    checks: list[tuple[str, bool]] = []
    fire = {"hints": [
        {"kind": "native-first",
         "advice": "native-first/001 · `curl` is an HTTP fetch — …",
         "task": "crawl"},
    ]}
    checks.append(("a firing native-first hint extracts (rule, task)",
                   hints_pairs(fire) == [("native-first/001", "crawl")]))
    clock = {"hints": [
        {"kind": "clock",
         "advice": "1 task(s) declare `timeout:` against an undeclared clock …",
         "task": "-"},
    ]}
    checks.append(("a non-lint advisory (the F-P3 clock hint) contributes NOTHING",
                   hints_pairs(clock) == []))
    mixed = {"hints": [
        clock["hints"][0],
        {"kind": "native-first", "advice": "native-first/005 · `node` runs …",
         "task": "upload"},
        fire["hints"][0],
    ]}
    checks.append(("mixed surface keeps report order, lints only",
                   hints_pairs(mixed) == [("native-first/005", "upload"),
                                          ("native-first/001", "crawl")]))
    checks.append(("an empty surface is silence", hints_pairs({}) == []))
    checks.append(("a malformed hint entry is skipped, never a crash",
                   hints_pairs({"hints": ["garbage", None]}) == []))
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'}  {name}")
    print(f"lints-differential selftest · {len(checks) - len(bad)}/{len(checks)}")
    return 1 if bad else 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        return selftest()
    engine = os.environ.get("NIKA_BIN") or shutil.which("nika") or "nika"
    dirs = sorted(p for p in LINTS.iterdir() if (p / "expected-lints.json").exists())
    if not dirs:
        print(f"FAIL  {LINTS} · no lint fixtures found")
        return 1
    measured = diverged = nodoor = 0
    for d in dirs:
        expected = json.loads((d / "expected-lints.json").read_text())["lints"]
        exp_pairs = [(e["rule"], e["task"]) for e in expected]
        name = d.name
        if not (name.startswith("nf") or name.startswith("clean-")):
            nodoor += 1
            print(f"NODOOR    {name} · expects {exp_pairs or 'silence'} · "
                  "one-obvious-way has no command surface")
            continue
        got = engine_hints(engine, d / "input.yaml")
        measured += 1
        if got == exp_pairs:
            print(f"AGREE     {name} · {exp_pairs or 'silent'}")
        else:
            diverged += 1
            print(f"DIVERGE   {name} · expected {exp_pairs} · got {got}")
    print(f"\nlints-differential · {measured} measured "
          f"({measured - diverged} agree · {diverged} diverge) · "
          f"{nodoor} NO-DOOR (the one-obvious-way surface owe)")
    return 1 if diverged else 0


if __name__ == "__main__":
    raise SystemExit(main())
