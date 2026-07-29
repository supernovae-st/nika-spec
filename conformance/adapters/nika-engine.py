#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""The reference Rust engine, wrapped to speak the runner protocol.

The Bowtie harness pattern the protocol names
([../runner-protocol.md](../runner-protocol.md) §Third-party mode): the
engine's native `nika check --json` emits its own report contract (30
keys), not the suite's wire shape, so it wraps itself here rather than
teach the runner a second dialect.

    NIKA_BIN=/path/to/nika \\
      python3 conformance/runner.py run conformance/tests/deep/composition \\
        --engine "python3 conformance/adapters/nika-engine.py"

The contract: the workflow path arrives as the FINAL argument, and the
verdict JSON goes to stdout — `{"valid": bool, "errors": [...]}`.

## The mapping, and what it deliberately does NOT invent

`valid` ← the report's `clean` — the same boolean that drives the
engine's exit code. Advisory hints and cost/energy warnings neither
clear it nor set it.

`errors` ← every array `clean` is composed from, in report order:

| source | coded? | what it carries |
|---|---|---|
| `conformance[]` | yes | parse + validation violations (the `analyze` tier) |
| `findings[]` | yes | the gate rungs — composition · permits · policy · trifecta · schema · args · gates · writes |
| `model_findings[]` | **no** | the MODELS rung (`model` · `tasks` · `why`) |
| `skill_findings[]` | **no** | the SKILLS rung |

The last two are the honest limit of this adapter, and naming it is the
point: those rungs emit no spec CODE, so a fixture expecting one
(`{"namespace": "NIKA-PROVIDER"}`) cannot match them and FAILS LOUD.
Mapping the MODELS rung onto `NIKA-PROVIDER` would be a guess — the
spec's rule is *a literal `model:` must carry a canonical provider
prefix*, the rung's claim is *this provider does not resolve in THIS
binary*, and those are neighbouring claims, not the same one. They are
reported anyway, `detail` only: an `invalid` verdict with no reason
attached is the worst output a harness can print, and was this
adapter's first draft.

Two more deliberate absences:

- **no `category`**. The report carries `code` + `gate` + `kind`, never
  the spec's error CATEGORY, and the matching rule makes category
  advisory whenever a `code` is present. A fixture asserting a
  category-ONLY expectation is therefore out of reach by construction —
  loud, never a silent pass.
- **no derived `namespace`**. The matching rule already accepts an
  expected namespace when an emitted `code` starts with it, so deriving
  one would add a second, guessable spelling of the same fact
  (`NIKA-BUILTIN-DONE-001` splits two ways · a guess is wrong for one).

Exit 0 with a verdict on stdout · exit 3 when the engine emitted no JSON
(the runner turns silence into a LOUD `harness_error`, never a pass).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys


# Every array the engine's `clean` is composed from (see the docstring
# table). The last two are codeless by construction, and are reported
# with a `detail` only — an invalid verdict must never arrive reasonless.
VIOLATION_SOURCES = ("conformance", "findings", "model_findings", "skill_findings")


def _detail(f: dict) -> str:
    """The engine's human sentence, whichever key this rung uses."""
    for key in ("message", "detail", "why"):
        if f.get(key):
            return str(f[key])
    return json.dumps(f, sort_keys=True)


def verdict(report: dict) -> dict:
    """The report contract → the wire shape (see the module docstring)."""
    errors: list[dict] = []
    for key in VIOLATION_SOURCES:
        for f in report.get(key) or []:
            if not isinstance(f, dict):
                continue
            e: dict = {"detail": _detail(f)}
            if f.get("code"):
                e["code"] = f["code"]
            errors.append(e)
    return {"valid": bool(report.get("clean")), "errors": errors}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: nika-engine.py [--] <workflow-path>", file=sys.stderr)
        return 2
    path = argv[-1]
    engine = os.environ.get("NIKA_BIN") or shutil.which("nika") or "nika"
    try:
        proc = subprocess.run(
            [engine, "check", "--json", path],
            capture_output=True, text=True, timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"nika-engine adapter: {engine} · {e}", file=sys.stderr)
        return 3
    out = proc.stdout.strip()
    start = out.find("{")
    if start < 0:
        print(
            f"nika-engine adapter: no JSON on stdout · stderr: "
            f"{proc.stderr.strip()[:200]!r}",
            file=sys.stderr,
        )
        return 3
    try:
        report = json.loads(out[start:])
    except json.JSONDecodeError as e:
        print(f"nika-engine adapter: report is not JSON · {e}", file=sys.stderr)
        return 3
    print(json.dumps(verdict(report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
