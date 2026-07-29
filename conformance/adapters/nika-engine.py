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

`category` ← the diagnostics registry, by code — ONE truth, never a
guess. The report itself carries `code` + `gate` + `kind`, never the
spec's error CATEGORY; the registry
(`canon/diagnostics/registry.yaml`) records each imported code's
category as the greppable `category: <c>` fragment of its `notes:`
(the C0 canon-flip audit trail), and a value is admitted only when
`canon.yaml`'s closed `error_categories` set knows it. The registry's
`cause:` field is deliberately NOT read — it carries the category
verbatim only until the table-13 runtime cause mapping mints (registry
`$comment`), then diverges. A code the registry does not cover stays
category-less (today: the 11 kernel-born NIKA-YAML rows + the 2
NIKA-AGENT seeds carry no fragment) — absent, loud on a category-only
fixture, never invented. Codeless rungs get no category either. An
unreadable registry degrades the same way, with a warning on stderr:
categories vanish, verdicts and codes stay — fail-closed, since a
missing category can only turn a match into a LOUD mismatch.

One more deliberate absence:

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
import re
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_REGISTRY = _REPO / "canon" / "diagnostics" / "registry.yaml"
_CANON = _REPO / "canon.yaml"


# Every array the engine's `clean` is composed from (see the docstring
# table). The last two are codeless by construction, and are reported
# with a `detail` only — an invalid verdict must never arrive reasonless.
VIOLATION_SOURCES = ("conformance", "findings", "model_findings", "skill_findings")


def load_categories() -> dict[str, str]:
    """code → spec category, from the diagnostics registry (see docstring).

    The greppable `category: <c>` fragment of each row's `notes:` is the
    carrier; `canon.yaml`'s closed `error_categories` set is the gate. A
    row without the fragment contributes nothing — absent stays absent.
    """
    import yaml  # the suite's own dependency (conformance/requirements.txt)

    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    closed = set(
        yaml.load(_CANON.read_text(), Loader=loader)["error_categories"]["items"]
    )
    registry = yaml.load(_REGISTRY.read_text(), Loader=loader)
    categories: dict[str, str] = {}
    for row in registry.get("diagnostics") or []:
        m = re.search(r"category:\s*([a-z_]+)", row.get("notes") or "")
        if m and m.group(1) in closed:
            categories[row["id"]] = m.group(1)
    return categories


def _detail(f: dict) -> str:
    """The engine's human sentence, whichever key this rung uses."""
    for key in ("message", "detail", "why"):
        if f.get(key):
            return str(f[key])
    return json.dumps(f, sort_keys=True)


def verdict(report: dict, categories: dict[str, str] | None = None) -> dict:
    """The report contract → the wire shape (see the module docstring)."""
    errors: list[dict] = []
    for key in VIOLATION_SOURCES:
        for f in report.get(key) or []:
            if not isinstance(f, dict):
                continue
            e: dict = {"detail": _detail(f)}
            if f.get("code"):
                e["code"] = f["code"]
                category = (categories or {}).get(f["code"])
                if category:
                    e["category"] = category
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
    try:
        categories = load_categories()
    except Exception as e:  # degrade, never crash: absence is fail-closed
        print(f"nika-engine adapter: registry unreadable · {e}", file=sys.stderr)
        categories = {}
    print(json.dumps(verdict(report, categories)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
