#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Adequacy-by-mutation: every conformance selftest must be able to FAIL.

A suite that cannot fail proves nothing. Each `conformance/*_core.py` judge
carries laws its `*_selftest.py` claims to assert — this probe breaks each
judge with ONE minimal mutation (its primary verdict goes PERMISSIVE: refuses
nothing, accepts everything) and demands the selftest DIE. A selftest that
survives its judge's death is decorative — the probe exits non-zero and names
it. First run 2026-07-30: 10/10 die, every death on a named law (composition
on the cross-file laws · type on `open ⋢ closed rides assignable` · decision
on bucket-edge ordering · gateway on the on_absent closed set · outcome on
the unknown-class refusal · proof on `semantically-different IRs → different
semantic hash` · projection on the env_value leak · yaml-profile on the
fixture-parity sweep · trifecta on the release-radar witness · redteam on
`0/3 fixtures die as named`).

Mutations run in a throwaway detached git worktree of HEAD — the working
tree is never touched, and the worktree is removed on every exit path.
Probes judge HEAD: commit (or at least stage nothing you fear) before
trusting a run. The shadow def appended at a module's end wins over the
original (later def binds last), and Python's late binding makes internal
callers see it too — no signature surgery, one appended line pair per probe.

    python3 scripts/mutation-adequacy.py        # exit 0 iff 10/10 die

Runs on demand (repo QA), deliberately NOT part of `runner.py all`: the
gate proves fixtures against the oracle; this proves the oracle's own
selftests can lose. Companion: conformance/runner-protocol.md (the suite
contract) · the selftests themselves (the laws).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (selftest, judged file, permissive shadow appended at the judge's EOF)
PROBES = [
    ("composition_core_selftest.py", "composition_core.py",
     "def composition_errors(*a, **k):\n    return []\n"),
    ("type_core_selftest.py", "type_core.py",
     "def assignable(*a, **k):\n    return True\n"),
    ("decision_core_selftest.py", "decision_core.py",
     "def validate_bundle(*a, **k):\n    return None\n"),
    ("gateway_core_selftest.py", "gateway_core.py",
     "def validate_bundle(*a, **k):\n    return None\n"),
    ("outcome_core_selftest.py", "outcome_core.py",
     "def validate_outcome(*a, **k):\n    return None\n"),
    ("proof_core_selftest.py", "proof_core.py",
     "def semantic_hash(*a, **k):\n    return '0' * 64\n"),
    ("projection_core_selftest.py", "projection_core.py",
     "def validate(*a, **k):\n    return None\n"),
    ("yaml_profile_core_selftest.py", "yaml_profile_core.py",
     "def profile_errors(*a, **k):\n    return []\n"),
    ("trifecta_core_selftest.py", "trifecta_core.py",
     "def trifecta_errors(*a, **k):\n    return []\n"),
    # redteam's judge is the reference pipeline itself: a permissive
    # validate_text means every seeded attack "PASSED SILENTLY".
    ("redteam_core_selftest.py", "runner.py",
     "def validate_text(*a, **k):\n    return {'valid': True, 'errors': []}\n"),
]


def _git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True)


def probe_all(worktree: Path) -> int:
    conf = worktree / "conformance"
    survivors: list[tuple[str, str]] = []
    for selftest, judged, shadow in PROBES:
        # A renamed selftest must fail as a HARNESS error, never count as a
        # death: python's "no such file" rc would fake a DIES forever.
        missing = [p for p in (conf / selftest, conf / judged) if not p.exists()]
        if missing:
            raise FileNotFoundError(f"probe table stale: {missing[0]}")
        rel = f"conformance/{judged}"
        _git("-C", str(worktree), "checkout", "--", rel)
        target = conf / judged
        target.write_text(target.read_text() + "\n\n" + shadow)
        proc = subprocess.run(
            [sys.executable, str(conf / selftest)],
            capture_output=True, text=True, timeout=300,
        )
        _git("-C", str(worktree), "checkout", "--", rel)
        died = proc.returncode != 0
        tail = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
        mark = "DIES    " if died else "SURVIVES"
        print(f"{mark} rc={proc.returncode} · {selftest} ⟵ permissive {judged} · {tail[:110]}")
        if not died:
            survivors.append((selftest, judged))
    print()
    if survivors:
        print(f"DECORATIVE ({len(survivors)}) — a selftest that cannot fail proves nothing:")
        for s, j in survivors:
            print(f"  {s} survived a permissive {j}")
        return 1
    print(f"{len(PROBES)}/{len(PROBES)} selftests die when their judge goes permissive — the harness is real.")
    return 0


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="nika-mutation-adequacy-"))
    worktree = tmp / "wt"
    _git("-C", str(REPO), "worktree", "add", "--detach", str(worktree), "HEAD")
    try:
        return probe_all(worktree)
    finally:
        subprocess.run(
            ["git", "-C", str(REPO), "worktree", "remove", "--force", str(worktree)],
            capture_output=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
