#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# corpus_contract_selftest.py — the gate that guards the corpus is itself
# guarded. corpus_contract_errors (runner.py · C1-C5) is anchor-driven
# (line prefixes · an indentation-scoped description match · a category
# order table); a refactor that breaks an anchor makes the gate silently
# blind — it would keep "covering" the corpus while flagging nothing.
# Every law is proven BOTH ways here: the violation flags, and the
# exemption that carries teaching weight (numbered lessons · deep SLOT
# descriptions) stays silent. Then the live sweep: every shipped
# examples/ + templates/ file passes the gate — the corpus and its gate
# can never drift apart unnoticed. Exit 0 green · 1 red.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner import corpus_contract_errors  # noqa: E402

SPEC_ROOT = Path(__file__).resolve().parent.parent

HEAD = (
    "# SPDX-License-Identifier: Apache-2.0\n"
    "# yaml-language-server: $schema=https://nika.sh/spec/v1/workflow.schema.json\n"
)

CLEAN_JOB = HEAD + """#
# showcase · T1 specimen · selftest
#
# Run · nika run specimen.nika.yaml

nika: v1
workflow:
  id: specimen
  description: "a clean specimen job"
permits:
  exec: ["git"]
  tools: ["nika:write"]
  net:
    http: ["example.com"]
  fs:
    write: ["out/x.md"]
tasks:
  t:
    exec: { command: ["git", "--version"] }
"""

failures: list[str] = []


def expect(name: str, text: str, *, flags: str | None, fname: str = "specimen.nika.yaml"):
    """flags=None asserts silence; otherwise the code must appear."""
    errs = corpus_contract_errors(Path(fname), text)
    if flags is None:
        if errs:
            failures.append(f"{name}: expected silence, got {errs}")
    elif not any(e.startswith(flags) for e in errs):
        failures.append(f"{name}: expected a {flags} flag, got {errs or 'silence'}")


# The clean specimen holds all five.
expect("clean job", CLEAN_JOB, flags=None)

# C1 · the two verbatim header lines lead the file.
expect("C1 missing SPDX", CLEAN_JOB.replace(HEAD, "# not the header\n"), flags="C1")

# C2 · a `# Run ·` line exists.
expect("C2 no Run line", CLEAN_JOB.replace("# Run · nika run specimen.nika.yaml\n", ""), flags="C2")

# C3 · jobs/skeletons carry workflow.description — numbered lessons are exempt.
NO_DESC = CLEAN_JOB.replace('  description: "a clean specimen job"\n', "")
expect("C3 job without description", NO_DESC, flags="C3")
expect("C3 lesson exemption", NO_DESC, flags=None, fname="03-specimen.nika.yaml")

# C4 · no SLOT on the WORKFLOW description line — deeper SLOT descriptions
# (inputs/outputs · the skeleton teaching device) stay untouched.
expect(
    "C4 SLOT on workflow description",
    CLEAN_JOB.replace(
        '  description: "a clean specimen job"',
        '  description: "a clean specimen job"   # SLOT',
    ),
    flags="C4",
)
expect(
    "C4 deep-SLOT exemption",
    CLEAN_JOB.replace(
        "tasks:",
        'inputs:\n  goal:\n    type: string\n    default: "x"\n    description: "What to do"   # SLOT\ntasks:',
    ),
    flags=None,
)

# C5 · permits categories hold the §2 order (exec · tools · net · fs).
expect(
    "C5 permits out of order",
    CLEAN_JOB.replace(
        'permits:\n  exec: ["git"]\n  tools: ["nika:write"]\n',
        'permits:\n  tools: ["nika:write"]\n  exec: ["git"]\n',
    ),
    flags="C5",
)

# The live sweep — the shipped corpus passes its own gate, every file.
swept = 0
for f in sorted((SPEC_ROOT / "examples").glob("*.nika.yaml")) + sorted(
    (SPEC_ROOT / "templates").glob("*.nika.yaml")
):
    errs = corpus_contract_errors(f, f.read_text())
    if errs:
        failures.append(f"live corpus: {f.name}: {errs}")
    swept += 1
if swept < 40:
    failures.append(f"live sweep saw only {swept} files — the corpus moved out from under the gate")

if failures:
    print("corpus_contract_selftest FAIL")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"corpus_contract_selftest PASS · 5 laws × both ways · {swept} shipped files green")
