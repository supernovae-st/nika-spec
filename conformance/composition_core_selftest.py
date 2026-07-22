#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the composition lane — the static laws of spec 14 on
inline docs (no fixture dir · single-doc law + reader laws via a temp
tree), pinned executable beside the runner."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from composition_core import composition_errors  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def codes(doc, base=None) -> set[str]:
    return {e["code"] for e in composition_errors(doc, base)}


def call(target, args=None, returns=None, permits=None):
    task = {"invoke": {"workflow": target}}
    if args is not None:
        task["invoke"]["args"] = args
    if returns is not None:
        task["returns"] = returns
    doc = {"nika": "v1", "workflow": {"id": "p"}, "tasks": {"call": task}}
    if permits is not None:
        doc["permits"] = permits
    return doc


# ── COMP-001 · single-doc, no reader needed ─────────────────────────────
law("templated target → COMP-001", "NIKA-COMP-001" in codes(call("./sub-${{ inputs.x }}.yaml")))
law("unpinned registry → COMP-001", "NIKA-COMP-001" in codes(call("registry:acme/audit")))
law("pinned registry → clean (single doc)", not codes(call("registry:acme/audit@1.0.0")))
law("a bare tool: invoke is not composition", not codes(
    {"nika": "v1", "workflow": {"id": "p"},
     "tasks": {"t": {"invoke": {"tool": "nika:read", "args": {"path": "x"}}}}}))

# ── the reader laws via a temp tree ─────────────────────────────────────
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    # the child DECLARES its own boundary (NEP-0003 law 6 · a child that
    # touches the world declares it, in its own file)
    (base / "child.nika.yaml").write_text(
        "nika: v1\nworkflow: { id: c }\npermits: { exec: [echo] }\n"
        "inputs: { url: { type: string, required: true } }\n"
        "tasks: { fetch: { exec: { command: [echo, hi] } } }\n"
        "outputs: { report: { value: \"x\", type: string } }\n")
    law("missing required child input → COMP-004",
        "NIKA-COMP-004" in codes(call("./child.nika.yaml"), base))
    law("arg type misfit → COMP-004",
        "NIKA-COMP-004" in codes(call("./child.nika.yaml", args={"url": 42}), base))
    law("outputs vs returns misfit → COMP-004",
        "NIKA-COMP-004" in codes(
            call("./child.nika.yaml", args={"url": "u"},
                 returns={"object": {"report": "integer"}}), base))
    law("child exec vs parent net-only → COMP-002",
        "NIKA-COMP-002" in codes(
            call("./child.nika.yaml", args={"url": "u"},
                 permits={"net": {"http": ["api.example.com"]}}), base))
    law("valid composition → clean (parent grants ∩ child declares)",
        not codes(call("./child.nika.yaml", args={"url": "u"},
                       returns={"object": {"report": "string"}},
                       permits={"exec": ["echo"]}), base))
    # NEP-0003 · the zero wall, both directions
    (base / "bare-child.nika.yaml").write_text(
        "nika: v1\nworkflow: { id: bc }\n"
        "tasks: { run: { exec: { command: [echo, hi] } } }\n")
    law("absent parent block = zero wall → COMP-002 (NEP-0003 law 5)",
        "NIKA-COMP-002" in codes(call("./child.nika.yaml"), base))
    law("child without block under permitted parent → COMP-002 (law 6)",
        "NIKA-COMP-002" in codes(
            call("./bare-child.nika.yaml", permits={"exec": ["echo"]}), base))
    (base / "pure-child.nika.yaml").write_text(
        "nika: v1\nworkflow: { id: pc }\n"
        "tasks: { think: { infer: { prompt: pure } } }\n")
    law("pure child under absent parent → clean",
        not codes(call("./pure-child.nika.yaml"), base))

    # self-launch + cycle
    (base / "self.nika.yaml").write_text(
        "nika: v1\nworkflow: { id: s }\ntasks: { c: { invoke: { workflow: ./self.nika.yaml } } }\n")
    law("self-launch → COMP-003",
        "NIKA-COMP-003" in codes(call("./self.nika.yaml"), base))
    (base / "a.nika.yaml").write_text(
        "nika: v1\nworkflow: { id: a }\ntasks: { c: { invoke: { workflow: ./bb.nika.yaml } } }\n")
    (base / "bb.nika.yaml").write_text(
        "nika: v1\nworkflow: { id: b }\ntasks: { c: { invoke: { workflow: ./a.nika.yaml } } }\n")
    law("two-file cycle → COMP-003",
        "NIKA-COMP-003" in codes(call("./a.nika.yaml"), base))

# ── no base_dir → only the single-doc law runs (never crashes) ──────────
law("no reader → cross-file laws silent (COMP-001 still fires)",
    codes(call("./child.nika.yaml"), None) == set()
    and "NIKA-COMP-001" in codes(call("./x-${{y}}.yaml"), None))

bad = [n for n, ok in CHECKS if not ok]
print(f"composition-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
