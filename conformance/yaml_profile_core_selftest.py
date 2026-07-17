#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference YAML-profile judge (R11 · D-2026-07-17-N5) —
every law branch inline, the ruled caps cross-checked against their
canon/grammar.yaml declaration, and the fixtures-parity sweep over
conformance/yaml-profile/ (the executable half of the fixture-parity
closure gate: a negative that stops refusing, or a positive that stops
admitting, turns THIS red — an orphaned fixture is never silent)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from yaml_profile_core import (  # noqa: E402
    DEPTH_CAP, DOCUMENT_CAP, SCALAR_CAP, TEACHING, judge_file, profile_errors)

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def codes(src) -> list[str]:
    return [e["code"] for e in profile_errors(src)]


WF = "nika: v1\nworkflow: { id: p }\ntasks: { t: { exec: { command: [echo, hi] } } }\n"

# ── the three R11 point-1 interdictions ────────────────────────────────
law("a clean minimal workflow admits", codes(WF) == [])
law("anchor refuses EVEN unreferenced (R11 point 3) → 001",
    codes("a: &x 1\nb: 2\n") == ["NIKA-YAML-001"])
law("anchor + alias → 001 then 002 (document order · never expanded)",
    codes("a: &x 1\nb: *x\n") == ["NIKA-YAML-001", "NIKA-YAML-002"])
law("alias refuses at the EVENT, before composition → exactly 002",
    codes("b: *ghost\n") == ["NIKA-YAML-002"])
law("merge key (inline map · no anchor needed) → exactly 003",
    codes("t:\n  <<: { a: 1 }\n") == ["NIKA-YAML-003"])

# ── duplicate + non-string keys · custom tags · non-finite floats ──────
law("duplicate mapping key → 004", codes("a: 1\na: 2\n") == ["NIKA-YAML-004"])
law("same key in DIFFERENT maps is legal", codes("a: { k: 1 }\nb: { k: 2 }\n") == [])
law("custom tag → 006", codes("a: !secret hi\n") == ["NIKA-YAML-006"])
law("explicit CORE tag (!!str) is legal", codes("a: !!str 5\n") == [])
law("plain int key → 007", codes("123: x\n") == ["NIKA-YAML-007"])
law("QUOTED numeric key is a string key (legal)", codes('"123": x\n') == [])
law("complex (collection) key → 007", codes("? [a]\n: x\n") == ["NIKA-YAML-007"])
law(".nan → 008", codes("a: .nan\n") == ["NIKA-YAML-008"])
law("-.inf → 008", codes("a: -.inf\n") == ["NIKA-YAML-008"])
law("the plain string 'nan' is legal (only the float forms refuse)",
    codes("a: nan\n") == [])
law("a finite float is legal", codes("a: 3.14\n") == [])

# ── the ruled caps · exact frontiers (D-2026-07-17-N5) ─────────────────
law("scalar of exactly 65 536 bytes is LEGAL (cap frontier)",
    codes("a: " + "x" * SCALAR_CAP + "\n") == [])
law("scalar of 65 537 bytes → 005 (gap P5 closed)",
    codes("a: " + "x" * (SCALAR_CAP + 1) + "\n") == ["NIKA-YAML-005"])


def nested(levels: int) -> str:
    out = []
    for i in range(1, levels):
        out.append("  " * (i - 1) + f"n{i}:")
    out.append("  " * (levels - 1) + "leaf: 1")
    return "\n".join(out) + "\n"


law("nesting of exactly 64 levels is LEGAL (cap frontier)",
    codes(nested(DEPTH_CAP)) == [])
law("nesting of 65 levels → 009 (reported once)",
    codes(nested(DEPTH_CAP + 1)) == ["NIKA-YAML-009"])
law("document of exactly 1 MiB is LEGAL (cap frontier)",
    codes(b"#" * (DOCUMENT_CAP - len(b"\na: 1\n")) + b"\na: 1\n") == [])
law("document of 1 MiB + 1 refuses NET — nothing else judged past the boundary",
    codes(b"#" * (DOCUMENT_CAP - len(b"\na: &x *y\n") + 1) + b"\na: &x *y\n")
    == ["NIKA-YAML-010"])

# ── unicode contract (one code · two branches) ─────────────────────────
law("BOM → 011", codes("﻿a: 1\n".encode()) == ["NIKA-YAML-011"])
law("non-NFC source → 011", codes(b"a: cafe\xcc\x81\n") == ["NIKA-YAML-011"])
law("the same text in NFC is legal", codes("a: café\n") == [])

# ── pass-throughs + teachings ──────────────────────────────────────────
law("unparseable YAML is NIKA-PARSE-001, never a profile code (R11 point 4)",
    codes("a: [\n") == ["NIKA-PARSE-001"])
law("every emitted refusal carries the REGISTRY teaching (one voice)",
    all(e["teaching"] == TEACHING[e["code"]]
        for e in profile_errors("a: &x 1\nb: *x\n<<: { c: .nan }\n")))
law("the 11 profile teachings are loaded from canon/diagnostics/registry.yaml",
    sum(1 for k in TEACHING if k.startswith("NIKA-YAML-")) == 11
    and all(TEACHING[f"NIKA-YAML-{i:03d}"] for i in range(1, 12)))

# ── the caps match their canon/grammar.yaml declaration ────────────────
_GRAMMAR = yaml.safe_load(
    (Path(__file__).parent.parent / "canon" / "grammar.yaml").read_text(encoding="utf-8"))
_SHAPES = {f"{row['id']}.{f['name']}": f.get("value_shape", "")
           for row in _GRAMMAR["grammar"] for f in row.get("fields", [])}


def _declared(shape_key: str) -> int:
    m = re.search(r"_(\d+)_", _SHAPES.get(shape_key, "") + "_")
    return int(m.group(1)) if m else -1


law("SCALAR_CAP == the yaml_scalar_cap registry declaration (D-2026-07-17-N5)",
    _declared("yaml_scalar_cap.size_over_cap") == SCALAR_CAP)
law("DEPTH_CAP == the yaml_document_caps depth declaration",
    _declared("yaml_document_caps.depth_over_cap") == DEPTH_CAP)
law("DOCUMENT_CAP == the yaml_document_caps size declaration",
    _declared("yaml_document_caps.size_over_cap") == DOCUMENT_CAP)
law("the unicode contract declares refuse-BOM + require-NFC",
    _SHAPES.get("yaml_unicode_contract.non_nfc_or_bom_disposition") == "refuse_bom_require_nfc")

# ── fixtures-parity sweep (closure gate: fixture-parity) ───────────────
FIXTURES = Path(__file__).parent / "yaml-profile"
EXPECTED = re.compile(r"#\s*Expected:\s*(NIKA-[A-Z]+-\d{3}) at CHECK\.")

invalid = sorted((FIXTURES / "invalid").glob("*.nika.yaml"))
valid = sorted((FIXTURES / "valid").glob("*.nika.yaml"))
law("at least 11 negative fixtures exist (one per profile condition)", len(invalid) >= 11)
law("at least 3 positive fixtures exist", len(valid) >= 3)

for p in invalid:
    header = p.read_bytes().decode("utf-8").lstrip("﻿")
    m = EXPECTED.search(header)
    got = [e["code"] for e in judge_file(p)]
    law(f"invalid/{p.name} refuses with exactly [{m.group(1) if m else '??'}]",
        m is not None and got == [m.group(1)])
for p in valid:
    law(f"valid/{p.name} admits", judge_file(p) == [])

# the at-limit positives really sit AT the caps (a lazy fixture cannot pass)
def _max_depth(p: Path) -> int:
    d = mx = 0
    for e in yaml.parse(p.read_text(encoding="utf-8")):
        if isinstance(e, (yaml.events.MappingStartEvent, yaml.events.SequenceStartEvent)):
            d += 1
            mx = max(mx, d)
        elif isinstance(e, (yaml.events.MappingEndEvent, yaml.events.SequenceEndEvent)):
            d -= 1
    return mx


def _max_scalar(p: Path) -> int:
    return max(len(e.value.encode("utf-8")) for e in yaml.parse(p.read_text(encoding="utf-8"))
               if isinstance(e, yaml.events.ScalarEvent))


law("valid/depth-at-cap sits EXACTLY at 64 levels",
    _max_depth(FIXTURES / "valid" / "depth-at-cap.nika.yaml") == DEPTH_CAP)
law("valid/scalar-at-cap carries EXACTLY a 65 536-byte scalar",
    _max_scalar(FIXTURES / "valid" / "scalar-at-cap.nika.yaml") == SCALAR_CAP)
law("invalid/document-over-cap is EXACTLY cap+1 bytes (the minimal illegal document)",
    (FIXTURES / "invalid" / "document-over-cap.nika.yaml").stat().st_size == DOCUMENT_CAP + 1)

bad = [n for n, ok in CHECKS if not ok]
print(f"yaml-profile-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
