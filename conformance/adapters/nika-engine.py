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

## The fixture context, staged · never the caller's

The engine reads its project from the working directory, not from the
workflow path: `.nika/mcp_servers.json`, an ancestor `nika.yaml`, HOME.
So the adapter never hands the engine the caller's world. Per call:

1. the input path and the engine binary resolve first (`NIKA_BIN`, else
   `nika` on the caller's PATH), to absolute paths;
2. a private scratch gets `project/` and `home/`. The input's EXACT bytes
   become `project/input.nika` (the engine requires the `.nika` suffix;
   `input.yaml` stays the canonical fixture and is never rewritten), and
   the hash is verified;
3. every other regular file of the fixture's OWN directory is copied
   byte-exact to the same relative path: composition children, skills,
   and a declared `.nika/mcp_servers.json` registry. `expected.json` is
   the verdict, never an input, and is not copied. A symlink, a special
   file, a missing file or a fixture-authored `nika.yaml` is never
   invented, followed or overwritten: the call is a harness error;
4. an EMPTY `project/nika.yaml` closes the upward project search;
5. the binary runs `check --json <absolute project/input.nika>` with
   cwd=project and an explicit environment (scratch HOME and TMPDIR,
   `NIKA_KEYCHAIN=off`, the default PATH). No caller variable, no
   provider key, no project/config override is inherited;
6. only the owned scratch is removed afterwards.

This is a harness boundary, not an OS sandbox: a HOME and a cwd do not
confine a process.

Exit 0 with a verdict on stdout · exit 3 when the engine emitted no JSON,
timed out, or the fixture context could not be staged (the runner turns
silence into a LOUD `harness_error`, never a pass).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_REGISTRY = _REPO / "canon" / "diagnostics" / "registry.yaml"
_CANON = _REPO / "canon.yaml"

CHECK_TIMEOUT_S = 120
# The verdict is the fixture's answer, never one of its inputs.
NOT_STAGED = {"expected.json"}
# A fixture directory is small; a larger tree means the input is not in one.
MAX_FILES, MAX_BYTES = 256, 8 * 1024 * 1024


class StageError(Exception):
    """The fixture context cannot be staged as declared."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stage(source: Path, project: Path) -> None:
    """Copy the fixture's own directory into `project` (module docstring)."""
    fixture = source.parent
    if (fixture / "nika.yaml").exists() or (
            (fixture / "input.nika").exists() and source.name != "input.nika"):
        raise StageError("the fixture authors its own nika.yaml or input.nika · "
                         "the staged project would overwrite it")
    count = size = 0
    for root, dirs, names in os.walk(fixture, followlinks=False):
        for name in dirs + names:
            p = Path(root) / name
            mode = p.lstat().st_mode
            if stat.S_ISDIR(mode):
                continue
            if not stat.S_ISREG(mode):
                raise StageError(f"not a regular file: {p}")
            if p == source or (Path(root) == fixture and name in NOT_STAGED):
                continue
            count, size = count + 1, size + p.lstat().st_size
            if count > MAX_FILES or size > MAX_BYTES:
                raise StageError(f"{fixture} is not a fixture directory (too large)")
            dest = project / p.relative_to(fixture)
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = p.read_bytes()
            dest.write_bytes(data)
            if _sha(dest.read_bytes()) != _sha(data):
                raise StageError(f"copy mismatch: {p}")
    data = source.read_bytes()
    staged = project / "input.nika"
    staged.write_bytes(data)
    if _sha(staged.read_bytes()) != _sha(data):
        raise StageError("staged input bytes differ from the fixture")
    (project / "nika.yaml").write_bytes(b"")


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
    source = Path(argv[-1]).resolve()
    found = os.environ.get("NIKA_BIN") or shutil.which("nika")
    if not found or not source.is_file() or Path(argv[-1]).is_symlink():
        print(f"nika-engine adapter: engine {found!r} or input {source} not found",
              file=sys.stderr)
        return 3
    engine = os.path.abspath(found)
    scratch = Path(tempfile.mkdtemp(prefix="nika-engine-adapter-")).resolve()
    try:
        project, home, tmp = scratch / "project", scratch / "home", scratch / "tmp"
        for d in (project, home, tmp):
            d.mkdir()
        try:
            stage(source, project)
        except (StageError, OSError) as e:
            print(f"nika-engine adapter: cannot stage {source} · {e}", file=sys.stderr)
            return 3
        env = {"HOME": str(home), "TMPDIR": str(tmp), "PATH": os.defpath,
               "NIKA_KEYCHAIN": "off"}
        try:
            proc = subprocess.run(
                [engine, "check", "--json", str(project / "input.nika")],
                cwd=project, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=CHECK_TIMEOUT_S,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"nika-engine adapter: {engine} · {e}", file=sys.stderr)
            return 3
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
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
