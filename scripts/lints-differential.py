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
  eg*      egress advisory pair     → MEASURED (the same `hints[]` door ·
           kind egress · a prompt or system text holding a private key)
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
import tempfile

SPEC_ROOT = pathlib.Path(__file__).resolve().parent.parent
LINTS = SPEC_ROOT / "conformance" / "tests" / "lints"
# The measured lint families, by the `kind` each hint carries on the door.
LINT_KINDS = ("native-first", "egress")


def hints_pairs(report: dict) -> list[tuple[str, str]]:
    """(rule, task) pairs from a check report, report order kept.

    Only the lint families are lints (`native-first` and `egress` hints) —
    the surface also carries non-lint advisories (the F-P3 clock hint,
    cost/energy notes) that expected-lints.json never speaks, so harvesting
    every hint would fake divergences on clean fixtures (found live on first
    run · pinned by the selftest's clock-advisory tamper case). The rule id
    is the hint's `code`, else the prefix of its advice.
    """
    pairs: list[tuple[str, str]] = []
    for h in report.get("hints") or []:
        if not isinstance(h, dict) or h.get("kind") not in LINT_KINDS:
            continue
        rule = str(h.get("code") or str(h.get("advice", "")).split(" · ", 1)[0])
        pairs.append((rule, str(h.get("task", ""))))
    return pairs


def stage(fixture: pathlib.Path, into: pathlib.Path) -> pathlib.Path:
    """Copy a fixture directory (its side files included) and rename its
    `input.yaml` to the `input.nika` program file the engine reads."""
    staged = into / fixture.name
    shutil.copytree(fixture, staged)
    (staged / "input.yaml").rename(staged / "input.nika")
    return staged / "input.nika"


def report_hints(report: dict, name: str) -> list[tuple[str, str]]:
    """A parse-fatal report carries no lint surface at all, so it is no
    verdict: read as silence it would agree with every clean fixture."""
    if report.get("parse_fatal"):
        raise RuntimeError(f"the engine could not parse {name} · a parse-fatal "
                           "report is no lint verdict")
    return hints_pairs(report)


def engine_hints(engine: str, fixture: pathlib.Path) -> list[tuple[str, str]]:
    """`nika check --json` on the fixture staged as `input.nika`, in a
    throwaway directory: since the `.nika` hard cut the engine refuses
    `input.yaml` as a program (parse-fatal, no hints), and the throwaway
    cwd keeps an ancestor project file out of the measurement."""
    with tempfile.TemporaryDirectory(prefix="nika-lints-") as temp:
        workflow = stage(fixture, pathlib.Path(temp))
        proc = subprocess.run(
            [engine, "check", "--json", str(workflow)],
            capture_output=True, text=True, timeout=120, cwd=workflow.parent,
        )
    out = proc.stdout
    start = out.find("{")
    if start < 0:
        raise RuntimeError(f"no JSON from the engine on {fixture.name} · "
                           f"stderr: {proc.stderr.strip()[:160]!r}")
    return report_hints(json.loads(out[start:]), fixture.name)


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
    egress = {"hints": [
        {"kind": "egress", "code": "egress/001",
         "advice": "egress/001 · a `prompt:` or `system:` text holds a PEM private-key block",
         "task": "brief"},
    ]}
    checks.append(("an egress lint extracts (rule, task) through the same door",
                   hints_pairs(egress) == [("egress/001", "brief")]))
    checks.append(("an empty surface is silence", hints_pairs({}) == []))
    checks.append(("a malformed hint entry is skipped, never a crash",
                   hints_pairs({"hints": ["garbage", None]}) == []))
    try:
        report_hints({"parse_fatal": True, "clean": False, "findings": []}, "probe")
        refused = False
    except RuntimeError:
        refused = True
    checks.append(("a parse-fatal report is no verdict, never silence", refused))
    checks.append(("a parsed report still reads its hints",
                   report_hints(fire, "probe") == [("native-first/001", "crawl")]))
    with tempfile.TemporaryDirectory(prefix="nika-lints-selftest-") as temp:
        fixture = pathlib.Path(temp) / "fixture"
        (fixture / "prompts").mkdir(parents=True)
        (fixture / "input.yaml").write_text("nika: probe\n")
        (fixture / "prompts" / "side.md").write_text("side file\n")
        staged = stage(fixture, pathlib.Path(temp) / "staged")
        checks.append(("a fixture is staged as input.nika with its side files",
                       staged.name == "input.nika"
                       and staged.read_text() == "nika: probe\n"
                       and (staged.parent / "prompts" / "side.md").is_file()
                       and not (staged.parent / "input.yaml").exists()))
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
    measured = diverged = nodoor = errored = 0
    for d in dirs:
        expected = json.loads((d / "expected-lints.json").read_text())["lints"]
        exp_pairs = [(e["rule"], e["task"]) for e in expected]
        name = d.name
        if not (name.startswith(("nf", "eg")) or name.startswith("clean-")):
            nodoor += 1
            print(f"NODOOR    {name} · expects {exp_pairs or 'silence'} · "
                  "one-obvious-way has no command surface")
            continue
        try:
            got = engine_hints(engine, d)
        except RuntimeError as error:
            errored += 1
            print(f"ERROR     {name} · {error}")
            continue
        measured += 1
        if got == exp_pairs:
            print(f"AGREE     {name} · {exp_pairs or 'silent'}")
        else:
            diverged += 1
            print(f"DIVERGE   {name} · expected {exp_pairs} · got {got}")
    print(f"\nlints-differential · {measured} measured "
          f"({measured - diverged} agree · {diverged} diverge) · "
          f"{errored} engine-errors · "
          f"{nodoor} NO-DOOR (the one-obvious-way surface owe)")
    return 1 if diverged or errored else 0


if __name__ == "__main__":
    raise SystemExit(main())
