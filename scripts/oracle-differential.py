#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""The two oracles of one law, diffed over the whole corpus.

Two independent implementations judge every Nika file: the engine
(`nika check` · Rust · AGPL) and this repo's reference runner (python ·
Apache-2.0). Same laws, zero shared code — which is the point, and the
risk: on 2026-07-29 they diverged on `ceo-monday-brief` (a bound authored
`./x` read as an escape by the reference and as in-bound by the engine),
and the corpus rode red on main while every engine gate stayed green.
An agreement nobody measures is a hope.

This is the sqllogictest move: run BOTH oracles over every corpus file
and refuse any verdict divergence that no ledger row explains.

    NIKA_BIN=/path/to/nika python3 scripts/oracle-differential.py
    python3 scripts/oracle-differential.py --bin /path/to/nika

Exit 0 · every file gets the same verdict from both oracles (or the
         divergence is covered by a ledger row below)
Exit 2 · environment (no engine binary)
Exit 4 · an unexplained divergence — the next b131a08 caught before main

The ledger: tolerated (file, reason) rows for KNOWN skew — e.g. a corpus
written for grammar the released binary does not carry yet. Every row is
a debt with a name; an empty ledger is the healthy state.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

SPEC_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPEC_ROOT / "conformance"))

import yaml  # noqa: E402
from runner import load_canon, load_schema, validate_workflow  # noqa: E402

# (filename, engine_ok, reference_ok, reason) — tolerated divergences,
# DIRECTIONAL: a row forgives exactly ONE (engine, reference) verdict
# pair. Any other combination stays unexplained — the portal never
# narrows (every file still runs through BOTH oracles) and a skew that
# changes shape must re-fail. Keep it EMPTY unless a skew has a name; a
# row here is a debt, not a dispensation.
LEDGER: list[tuple[str, bool, bool, str]] = [
    (
        "release-radar.nika.yaml",
        False,  # engine · REFUSES (NIKA-SEC-009 · the lethal trifecta)
        True,  # reference · GREEN (trifecta rule not implemented yet)
        "the deliberately-red witness: engine refuses NIKA-SEC-009 (lethal "
        "trifecta over an honest boundary) while the python reference reads "
        "it GREEN — SEC-009 is not implemented reference-side yet. DEBT: "
        "the trifecta rule lands in the reference, this row dies. Any OTHER "
        "verdict pair on this file is a NEW skew and fails.",
    ),
    # The six policy-skew rows (corpus ahead of the engine grammar ·
    # NEP-0014) died 2026-07-29 night exactly as written: the lot-3b PR
    # (#753) merged, an engine built from main parses `policy:`, and the
    # re-run read 48/49 agree with zero unexplained.
]


def engine_verdict(bin_path: str, f: pathlib.Path) -> tuple[bool, str]:
    """(passes, last line) from `nika check --native-strict` · rc is the law.

    rc 2 is the CLI refusing the INVOCATION, not the file — the probe must
    never read its own broken flag as 49 engine failures (it did, on its
    first run: an unknown flag returned rc 2 with an empty tail and the
    differential reported the whole corpus divergent)."""
    p = subprocess.run(
        [bin_path, "check", str(f), "--native-strict"],
        capture_output=True, text=True, cwd=SPEC_ROOT, timeout=120,
    )
    if p.returncode == 2 and "unexpected argument" in (p.stderr or ""):
        raise SystemExit(f"oracle-differential · broken probe invocation: {p.stderr.strip()[:120]}")
    tail = (p.stdout.strip().splitlines() or [""])[-1]
    return p.returncode == 0, tail


def reference_verdict(f: pathlib.Path, validator, canon) -> tuple[bool, str]:
    doc = yaml.safe_load(f.read_text())
    if not isinstance(doc, dict):
        return False, "unparseable envelope"
    # base_dir is the FILE's directory — the composition door resolves its
    # child relative to the caller, exactly as the CI suite invokes it
    # (runner.py: base_dir=inp.parent). Rooting it at the repo made the
    # probe report a false COMP-001 on the composition lesson — the second
    # broken-probe class this script caught in itself on day one.
    v = validate_workflow(doc, validator, canon=canon, base_dir=f.parent)
    errs = v.get("errors") or []
    head = errs[0].get("code") or errs[0].get("namespace") if errs else ""
    return bool(v.get("valid")), head or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default=os.environ.get("NIKA_BIN", ""))
    args = ap.parse_args()
    if not args.bin or not pathlib.Path(args.bin).exists():
        print("oracle-differential · no engine binary (NIKA_BIN or --bin)", file=sys.stderr)
        return 2
    validator, canon = load_schema(), load_canon()
    files = sorted(
        list((SPEC_ROOT / "examples").glob("*.nika.yaml"))
        + list((SPEC_ROOT / "templates").glob("*.nika.yaml"))
    )
    ledger = {name: (e, r, why) for name, e, r, why in LEDGER}
    agree = 0
    unexplained: list[str] = []
    for f in files:
        e_ok, e_tail = engine_verdict(args.bin, f)
        r_ok, r_head = reference_verdict(f, validator, canon)
        if e_ok == r_ok:
            agree += 1
            continue
        row = ledger.get(f.name)
        if row is not None and (e_ok, r_ok) == (row[0], row[1]):
            print(f"LEDGER {f.name} · engine={'pass' if e_ok else 'fail'} · "
                  f"reference={'pass' if r_ok else 'fail'} · {row[2]}")
            continue
        unexplained.append(f.name)
        print(f"DIVERGE {f.name} · engine={'pass' if e_ok else 'fail'} "
              f"({e_tail[:80]}) · reference={'pass' if r_ok else 'fail'} ({r_head})")
    print(f"\noracle-differential · {agree}/{len(files)} agree · "
          f"{len(unexplained)} unexplained · ledger {len(LEDGER)}")
    return 4 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main())
