#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""The map's generated island — SSOT.md §9 derives from estate.yaml.

SSOT.md is the map of where every fact lives, and until this projector the
map itself was the last hand-typed surface: its GATED table was prose, and
prose drifts (measured 2026-07-29: the map's own census disagreed with the
tree the same day it was written). The skeleton that is DERIVABLE — which
generated surfaces exist, which tool emits each, which gate refuses its
drift — now projects from estate.yaml between markers; every judgment
sentence around the island stays authored.

    python3 scripts/ssot-map-projector.py --write   # regenerate the island
    python3 scripts/ssot-map-projector.py --check   # re-emit · byte-compare · exit 5

Same contract as the sibling projectors (canon-projectors · showcase-
projector · llms-projector): --check re-emits in memory and byte-compares,
so a hand edit inside the markers makes CI red.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SPEC_ROOT = Path(__file__).resolve().parent.parent
SSOT_MD = SPEC_ROOT / "SSOT.md"
ESTATE = SPEC_ROOT / "estate.yaml"

OPEN = "<!-- estate:map -->"
CLOSE = "<!-- /estate:map -->"


def short_tool(tool: str) -> str:
    """The command's identity without its parenthetical lore."""
    return tool.split(" (")[0].strip()


def short_gate(gate: str) -> str:
    """The gate's refusing command, not its workflow coordinates."""
    tail = gate.split("→")[-1].strip() if "→" in gate else gate.strip()
    return tail.split(" (")[0].strip()


def render(estate: dict) -> str:
    """The island body — every line derived, nothing editorial."""
    lines: list[str] = [OPEN]
    lines.append("")
    lines.append("The rows below are DERIVED from `estate.yaml` — regenerate with")
    lines.append("`python3 scripts/ssot-map-projector.py --write`; a hand edit here is")
    lines.append("refused by `--check` (exit 5), the same contract every projection has.")
    lines.append("")
    lines.append("| generated surface | emitted by | drift refused by |")
    lines.append("|---|---|---|")
    rows = [
        f
        for f in estate.get("files", [])
        if f.get("class") == "generated" and f.get("derivation")
    ]
    for f in sorted(rows, key=lambda r: r["path"]):
        d = f["derivation"]
        lines.append(
            f"| `{f['path']}` | `{short_tool(d.get('tool', '?'))}` "
            f"| `{short_gate(d.get('gate', '?'))}` |"
        )
    s = estate.get("summary", {})
    by = s.get("by_class", {})
    lines.append("")
    lines.append(
        f"Provenance floor: {s.get('classified_files', '?')} tracked files classified · "
        f"authored {by.get('authored', '?')} · generated {by.get('generated', '?')} · "
        f"pinned-copy {by.get('pinned-copy', '?')} · testimonial {by.get('testimonial', '?')} "
        f"(estate schema {estate.get('estate_schema', '?')} · mode {estate.get('mode', '?')})."
    )
    lines.append("")
    lines.append(CLOSE)
    return "\n".join(lines)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--write", "--check"):
        print("ssot-map-projector · mode --write | --check", file=sys.stderr)
        return 2
    estate = yaml.safe_load(ESTATE.read_text())
    text = SSOT_MD.read_text()
    if OPEN not in text or CLOSE not in text:
        print(f"ssot-map-projector · markers missing in {SSOT_MD.name}", file=sys.stderr)
        return 2
    head, rest = text.split(OPEN, 1)
    _, tail = rest.split(CLOSE, 1)
    projected = head + render(estate) + tail
    if mode == "--write":
        SSOT_MD.write_text(projected)
        print(f"✓ wrote estate:map island · {SSOT_MD.name}")
        return 0
    if projected != text:
        print(
            "ssot-map-projector · DRIFT · SSOT.md estate:map island · run --write",
            file=sys.stderr,
        )
        return 5
    print("✓ SSOT.md estate:map island in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
