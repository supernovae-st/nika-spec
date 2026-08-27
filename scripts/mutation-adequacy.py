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
fixture-parity sweep · trifecta on the realized-flow witness (conformance/envelope) · redteam on
`0/3 fixtures die as named`).

Extended 2026-07-30 (wave 2) beyond the conformance cores to every
remaining judge with a probeable death surface: the C2 value-authority
proof (reference/values_core.py · a permissive judge admits every negative
values fixture) · the dup-keys gate (its selftest lives inside its own
file · a judge answering ok-to-everything fails its own dup cases). The
served-grammar door probe left with the door itself (0.109.0 · the
released binary speaks the ratified grammar · nothing downcasts). NOT
probed here, by design: ssot-map --selftest and gen-type-corpus --mutate
discriminate tampers by construction (their selftests ARE mutation
probes) · estate.py is a byte-pinned mirror with its own mutation-proven
selftest upstream · deep_static/cross-ref/stdlib layers die through the
fixture corpus (runner all IS their death surface, re-proven every gate
run).

Extended 2026-08-27 (#291 wave): the canon-projectors gate — its judge and
selftest are one file (`--check`) and its judged surface is DATA, so the
mutation IS the appended shadow: a duplicate top-level key at canon.yaml's
EOF wins under yaml.safe_load exactly like a later def binds last. Three
probes re-plant the original drifts (the uncounted `raw` mode · a canon
namespace with no 05-errors table row · the « 15 error namespaces » prose
fossil); each shadow keeps the upstream count==len law green ON PURPOSE, so
a death proves the named cross-check and never the old law.

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

# The #291 canon-projectors shadows · DATA mutations (canon.yaml · a
# duplicate top-level key appended at EOF wins under yaml.safe_load — the
# YAML twin of the shadow def). Each shadow re-types the counts: block so
# the count==len self-check stays GREEN and the death lands on the named
# cross-check, never upstream.
_CANON_COUNTS = (
    "counts:\n  verbs: 4\n  namespaces: 5\n  builtins: 28\n  providers: 17\n"
    "  extract_modes: {extract_modes}\n  templates: 14\n"
    "  error_namespaces: {error_namespaces}\n  error_categories: 12\n"
    "  error_codes: 103\n  pillars: 5\n  lifecycle_product: 4\n"
    "  lifecycle_decision: 4\n  lifecycle_risk: 4\n  diamond_layers: 7\n"
    "  steal_pattern_tiers: 4\n  severity: 4\n  mcp_tools: 9\n"
    "  mcp_protocol_versions: 5\n"
)
_SHADOW_MODES_SANS_RAW = _CANON_COUNTS.format(extract_modes=9, error_namespaces=24) + (
    "extract_modes:\n  count: 9\n  reference: stdlib/extract-modes-v0.1.md\n"
    "  items: [article, feed, jq, links, markdown, metadata, selector, sitemap, text]\n"
)
_SHADOW_NS_SANS_AUTH = _CANON_COUNTS.format(extract_modes=10, error_namespaces=23) + (
    "error_namespaces:\n  count: 23\n  reference: spec/05-errors.md\n"
    "  items: [NIKA-AGENT, NIKA-ASSERT, NIKA-BUILTIN, NIKA-CANCEL, NIKA-COMP,\n"
    "          NIKA-DAG, NIKA-DEFAULT, NIKA-EXEC, NIKA-IMPL, NIKA-INFER,\n"
    "          NIKA-INVOKE, NIKA-LOCK, NIKA-MCP, NIKA-DECIDE, NIKA-DRIFT,\n"
    "          NIKA-PARSE, NIKA-PORT, NIKA-PROVIDER, NIKA-SEC, NIKA-TIMEOUT,\n"
    "          NIKA-TYPE, NIKA-VAR, NIKA-VALUES]\n"
)
_SHADOW_PILLAR_FOSSIL = (
    "pillars:\n  count: 5\n  immutable: true\n  reference: spec/00-overview.md\n"
    "  items:\n"
    '    - { order: 1, name: envelope,  semantic: "the nine-key envelope" }\n'
    '    - { order: 2, name: verbs,     semantic: "the 4 native execution models" }\n'
    '    - { order: 3, name: dag,       semantic: "task composition + control flow" }\n'
    '    - { order: 4, name: variables, semantic: "scope-bound state threading" }\n'
    '    - { order: 5, name: errors,    semantic: "the 15 error namespaces + handling contract" }\n'
)

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
    # The #291 canon-projectors ratchet · judge and selftest share one file
    # and the judged surface is DATA (canon.yaml · YAML last-wins) — the
    # shadow constants above. One probe per cross-check.
    (("scripts/canon-projectors.py", "--check"), "canon.yaml", _SHADOW_MODES_SANS_RAW),
    (("scripts/canon-projectors.py", "--check"), "canon.yaml", _SHADOW_NS_SANS_AUTH),
    (("scripts/canon-projectors.py", "--check"), "canon.yaml", _SHADOW_PILLAR_FOSSIL),
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
        # (Found live 2026-07-30: the served-grammar door's selftest — a
        # judge in no CI gate, retired with the door at 0.109.0 — sat
        # red-on-clean and its first DIES proved nothing.)
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
