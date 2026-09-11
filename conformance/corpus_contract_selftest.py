#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# corpus_contract_selftest.py — the gate that guards the corpus is itself
# guarded. corpus_contract_errors (runner.py · C1 · C2 · C5) is
# anchor-driven (line prefixes · a category order table); a refactor that
# breaks an anchor makes the gate silently blind — it would keep
# "covering" the corpus while flagging nothing. Every law is proven BOTH
# ways here: the violation flags, and the clean specimen stays silent.
# Then the live sweep: every shipped examples/ + templates/ file passes
# the gate — the corpus and its gate can never drift apart unnoticed.
# Exit 0 green · 1 red.
#
# C3/C4 retired with `workflow.description` (the envelope nuke · the
# scalar `workflow:` carries no prose). Their ids are NOT reused.

import sys
import contextlib
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner import corpus_contract_errors  # noqa: E402
import runner  # noqa: E402

SPEC_ROOT = Path(__file__).resolve().parent.parent

HEAD = (
    # REUSE-IgnoreStart — the string teaches the header, not the file
    "# SPDX-License-Identifier: Apache-2.0\n"
    # REUSE-IgnoreEnd
    "# yaml-language-server: $schema=https://nika.sh/spec/v1/workflow.schema.json\n"
)

CLEAN_JOB = HEAD + """#
# showcase · T1 specimen · selftest
#
# Run · nika run specimen.nika.yaml

nika: specimen
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


# The clean specimen holds all three.
expect("clean job", CLEAN_JOB, flags=None)

# C1 · the two verbatim header lines lead the file.
expect("C1 missing SPDX", CLEAN_JOB.replace(HEAD, "# not the header\n"), flags="C1")

# C2 · a `# Run ·` line exists.
expect("C2 no Run line", CLEAN_JOB.replace("# Run · nika run specimen.nika.yaml\n", ""), flags="C2")

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

# The all command must not silently stop checking the template shelf when
# its directory disappears. Stub only unrelated fixture suites: real
# corpus validation proves both the missing shelf and the restored one.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for relative in ("examples", "examples/snippets"):
        directory = root / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "specimen.nika.yaml").write_text(CLEAN_JOB)
    witness = root / runner.WITNESS_RED[0]
    witness.parent.mkdir(parents=True)
    witness.write_bytes((SPEC_ROOT / runner.WITNESS_RED[0]).read_bytes())
    with patch.object(runner, "SPEC_ROOT", root), patch.object(runner, "run_fixtures", return_value=0):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            missing_rc = runner.main(["runner.py", "all"])
        if missing_rc != 1 or "no *.nika.yaml found" not in output.getvalue():
            failures.append("all accepted a missing template shelf")
        (root / "templates").mkdir()
        (root / "templates/specimen.nika.yaml").write_text(CLEAN_JOB)
        negative = root / "templates/specimen.negative.yaml"
        negative.write_text("nika: specimen-negative\ntasks: {}\n")
        with contextlib.redirect_stdout(io.StringIO()):
            restored_rc = runner.main(["runner.py", "all"])
        if restored_rc != 0:
            failures.append("all refused the restored valid template shelf")
        negative.write_text(CLEAN_JOB)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            accepted_rc = runner.main(["runner.py", "all"])
        if accepted_rc != 1 or "FAIL  specimen.negative.yaml" not in output.getvalue():
            failures.append("all accepted a negative template that became valid")
        negative.unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            absent_rc = runner.main(["runner.py", "all"])
        if absent_rc != 1 or "no *.negative.yaml found" not in output.getvalue():
            failures.append("all accepted an empty negative-template corpus")

if failures:
    print("corpus_contract_selftest FAIL")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"corpus_contract_selftest PASS · 3 laws × both ways · mandatory template shelf and refusals · {swept} shipped files green")
