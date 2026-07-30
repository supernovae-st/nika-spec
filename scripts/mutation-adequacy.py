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

Extended 2026-07-30 (wave 2) beyond the conformance cores to every
remaining judge with a probeable death surface: the served-grammar door
(scripts/grammar_door.py · a silenced _refuse melts the STOP-list) · the
C2 value-authority proof (reference/values_core.py · a permissive judge
admits every negative values fixture) · the dup-keys gate (its selftest
lives inside its own file · a judge answering ok-to-everything fails its
own dup cases). NOT probed here, by design: ssot-map --selftest and
gen-type-corpus --mutate discriminate tampers by construction (their
selftests ARE mutation probes) · estate.py is a byte-pinned mirror with
its own mutation-proven selftest upstream · deep_static/cross-ref/stdlib
layers die through the fixture corpus (runner all IS their death
surface, re-proven every gate run).

Mutations run in a throwaway detached git worktree of HEAD — the working
tree is never touched, and the worktree is removed on every exit path.
Probes judge HEAD: commit (or at least stage nothing you fear) before
trusting a run. The shadow def appended at a module's end wins over the
original (later def binds last), and Python's late binding makes internal
callers see it too — no signature surgery, one appended line pair per probe.

    python3 scripts/mutation-adequacy.py        # exit 0 iff every probe dies

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

# (selftest invocation, judged file, permissive shadow appended at the
# judge's EOF). Paths are repo-relative; a tuple invocation carries args
# (a selftest living INSIDE its judge runs as `<judge> --selftest`).
PROBES = [
    ("conformance/composition_core_selftest.py", "conformance/composition_core.py",
     "def composition_errors(*a, **k):\n    return []\n"),
    ("conformance/type_core_selftest.py", "conformance/type_core.py",
     "def assignable(*a, **k):\n    return True\n"),
    ("conformance/decision_core_selftest.py", "conformance/decision_core.py",
     "def validate_bundle(*a, **k):\n    return None\n"),
    ("conformance/gateway_core_selftest.py", "conformance/gateway_core.py",
     "def validate_bundle(*a, **k):\n    return None\n"),
    ("conformance/outcome_core_selftest.py", "conformance/outcome_core.py",
     "def validate_outcome(*a, **k):\n    return None\n"),
    ("conformance/proof_core_selftest.py", "conformance/proof_core.py",
     "def semantic_hash(*a, **k):\n    return '0' * 64\n"),
    ("conformance/projection_core_selftest.py", "conformance/projection_core.py",
     "def validate(*a, **k):\n    return None\n"),
    ("conformance/yaml_profile_core_selftest.py", "conformance/yaml_profile_core.py",
     "def profile_errors(*a, **k):\n    return []\n"),
    ("conformance/trifecta_core_selftest.py", "conformance/trifecta_core.py",
     "def trifecta_errors(*a, **k):\n    return []\n"),
    # redteam's judge is the reference pipeline itself: a permissive
    # validate_text means every seeded attack "PASSED SILENTLY".
    ("conformance/redteam_core_selftest.py", "conformance/runner.py",
     "def validate_text(*a, **k):\n    return {'valid': True, 'errors': []}\n"),
    # The served-grammar door: a _refuse that stops raising melts the
    # STOP-list — the selftest's refusal leg must catch it.
    ("scripts/grammar_door_selftest.py", "scripts/grammar_door.py",
     "def _refuse(*a, **k):\n    return None\n"),
    # The C2 value-authority proof judges conformance/values/** through
    # values_core: a permissive judge admits every negative fixture.
    ("conformance/values_proof.py", "reference/values_core.py",
     "def values_core_errors(*a, **k):\n    return []\n"),
    # The dup-keys gate self-tests inside its own file — where an
    # appended shadow is DEAD CODE (sys.exit(main()) runs first), so the
    # mutation is a surgical replacement: the dup arm goes permissive.
    # (Found live: the shadow form "survived" here and the survivor was
    # the PROBE, not the selftest — a same-file judge needs replace.)
    (("scripts/check-yaml-dup-keys.py", "--selftest"),
     "scripts/check-yaml-dup-keys.py",
     ("replace",
      '    except DupKey as e:\n        return "dup", str(e)\n',
      '    except DupKey:\n        return "ok", None\n')),
    # The differential judges (self-executing files · replace mode): a
    # lints extractor whose kind filter melts harvests non-lint
    # advisories — the clock-tamper case must catch it.
    (("scripts/lints-differential.py", "--selftest"),
     "scripts/lints-differential.py",
     ("replace",
      '        if not isinstance(h, dict) or h.get("kind") != "native-first":\n',
      '        if not isinstance(h, dict):\n')),
    # A runtime judge that never diffs reads every tamper as agreement —
    # the flipped-status and typed-value cases must die.
    (("scripts/runtime-differential.py", "--selftest"),
     "scripts/runtime-differential.py",
     ("replace",
      '    diffs: list[str] = []\n    want_state = expected.get("workflow_state")\n',
      '    diffs: list[str] = []\n    return diffs\n    want_state = expected.get("workflow_state")\n')),
]


def _git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True)


def probe_all(worktree: Path) -> int:
    survivors: list[tuple[str, str]] = []
    for selftest, judged, shadow in PROBES:
        cmd = (selftest,) if isinstance(selftest, str) else tuple(selftest)
        label = " ".join(cmd)
        # A renamed selftest must fail as a HARNESS error, never count as a
        # death: python's "no such file" rc would fake a DIES forever.
        missing = [p for p in (worktree / cmd[0], worktree / judged)
                   if not p.exists()]
        if missing:
            raise FileNotFoundError(f"probe table stale: {missing[0]}")
        _git("-C", str(worktree), "checkout", "--", judged)
        # Baseline gate: a selftest RED before any mutation makes its
        # death meaningless — the probe would report DIES on a corpse.
        # (Found live: grammar_door_selftest sat red-on-clean — it is in
        # no CI gate — and its first DIES proved nothing.)
        clean = subprocess.run(
            [sys.executable, str(worktree / cmd[0]), *cmd[1:]],
            capture_output=True, text=True, timeout=300,
        )
        if clean.returncode != 0:
            tail = (clean.stdout.strip().splitlines() or ["(no output)"])[-1]
            raise RuntimeError(
                f"{label} is RED before mutation (rc={clean.returncode}) — "
                f"fix the selftest first · {tail[:110]}")
        target = worktree / judged
        if isinstance(shadow, tuple):
            # ("replace", old, new) · for judges that EXECUTE on import or
            # carry their own __main__ (an appended shadow is dead code
            # there — sys.exit runs before it binds). The old text must
            # exist: a drifted judge fails as a harness error, never as a
            # silent no-op mutation.
            _, old, new = shadow
            text = target.read_text()
            if old not in text:
                raise ValueError(f"probe table stale: replace target absent in {judged}")
            target.write_text(text.replace(old, new, 1))
        else:
            target.write_text(target.read_text() + "\n\n" + shadow)
        proc = subprocess.run(
            [sys.executable, str(worktree / cmd[0]), *cmd[1:]],
            capture_output=True, text=True, timeout=300,
        )
        _git("-C", str(worktree), "checkout", "--", judged)
        died = proc.returncode != 0
        tail = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
        mark = "DIES    " if died else "SURVIVES"
        print(f"{mark} rc={proc.returncode} · {label} ⟵ permissive {judged} · {tail[:110]}")
        if not died:
            survivors.append((label, judged))
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
