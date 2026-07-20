#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# grammar_door_selftest.py — binary-free proof of the served-grammar door.
#   1 · a golden pair covering every transform (envelope · inputs+const
#       merge · task map→list · after: folds · edge synthesis · ref rewrite)
#   2 · idempotence (W2 in → byte-identical out)
#   3 · the STOP-list refuses loudly (config: · exotic workflow child ·
#       flow-bodied task key)
#   4 · a pack sweep · every examples/ + templates/ file downcasts without
#       refusal and sheds every wnew-only construct
# The binary-backed proof (each downcast passes `nika check` · one runs
# end-to-end) lives with the consumers: the docs gate (oracle-sweep) and
# the release train. Exit 0 green · 1 red.

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grammar_door import DoorRefusal, downcast_w2  # noqa: E402

SPEC_ROOT = Path(__file__).resolve().parent.parent

GOLDEN_IN = """\
nika: v1
workflow:
  id: golden
  description: "the full-construct golden"

inputs:
  text:
    type: string

const:
  target: 899

secrets:
  hook:
    source: env
    key: HOOK_URL

tasks:
  fetch:
    invoke:
      tool: "nika:fetch"
      args: { url: "${{ const.target }}" }
  judge:  # keeps its comment
    infer:
      prompt: "judge ${{ inputs.text }} against ${{ tasks.fetch.output }}"
  record:
    after:
      judge: terminal
    invoke:
      tool: "nika:notify"
      args: { note: "${{ tasks.judge.output }}" }
"""

GOLDEN_OUT = """\
nika: v1
workflow: golden
description: "the full-construct golden"

vars:
  text:
    type: string
  target: 899

secrets:
  hook:
    source: env
    key: HOOK_URL

tasks:
  - id: fetch
    invoke:
      tool: "nika:fetch"
      args: { url: "${{ vars.target }}" }
  - id: judge  # keeps its comment
    depends_on: [fetch]
    infer:
      prompt: "judge ${{ vars.text }} against ${{ tasks.fetch.output }}"
  - id: record
    depends_on: [judge]
    invoke:
      tool: "nika:notify"
      args: { note: "${{ tasks.judge.output }}" }
"""


def fail(msg: str) -> None:
    print(f"grammar-door selftest ✗ {msg}")
    sys.exit(1)


def main() -> int:
    got = downcast_w2(GOLDEN_IN, "golden")
    if got != GOLDEN_OUT:
        import difflib

        diff = "\n".join(difflib.unified_diff(
            GOLDEN_OUT.splitlines(), got.splitlines(), "want", "got", lineterm=""))
        fail(f"golden mismatch\n{diff}")

    if downcast_w2(got, "golden@2") != got:
        fail("not idempotent on its own output")

    for bad, why in (
        ("nika: v1\nworkflow: x\nconfig:\n  a: 1\ntasks:\n  t:\n    exec:\n      run: 'true'\n",
         "config: must refuse"),
        ("nika: v1\nworkflow:\n  id: x\n  version: 2\ntasks:\n  t:\n    exec:\n      run: 'true'\n",
         "workflow child beyond id/description must refuse"),
        ("nika: v1\nworkflow: x\ntasks:\n  t: { exec: { run: 'true' } }\n",
         "flow-bodied task key must refuse"),
    ):
        try:
            downcast_w2(bad, "stop")
            fail(why)
        except DoorRefusal:
            pass

    pack = (
        sorted((SPEC_ROOT / "examples").glob("*.nika.yaml"))
        + sorted((SPEC_ROOT / "examples" / "showcase").glob("*.nika.yaml"))
        + sorted((SPEC_ROOT / "templates").glob("*.nika.yaml"))
    )
    if len(pack) < 30:
        fail(f"pack sweep found only {len(pack)} files — layout moved?")
    for f in pack:
        text = f.read_text()
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("nika:"):
                text = "\n".join(lines[i:]).rstrip() + "\n"
                break
        try:
            w2 = downcast_w2(text, f.name)
        except DoorRefusal as e:
            fail(f"pack refusal · {e}")
        if re.search(r"^(inputs|const|config):", w2, re.M):
            fail(f"{f.name} · wnew value block survived the door")
        if not re.search(r"^workflow: \S", w2, re.M):
            fail(f"{f.name} · workflow did not collapse to a scalar")
        if re.search(r"^    after:", w2, re.M):
            fail(f"{f.name} · task-level after: survived the door")
        if downcast_w2(w2, f.name + "@2") != w2:
            fail(f"{f.name} · not idempotent")

    print(f"grammar-door selftest ✓ golden + stop-list + {len(pack)} pack files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
