#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Relative-reference integrity for the governance surfaces.

The rot class this gates fired twice on 2026-07-19: a matrix row cited a
live number that drifted, and every row cites files by relative link — a
deleted workflow would leave the claim standing with nothing behind it.
This check makes the STRUCTURAL half impossible: every relative markdown
link in the governed set must resolve to a real file or directory.

Scope · the governance/meta surfaces (README · GLOSSARY · CONTRIBUTING ·
SECURITY · CONFORMANT_IMPLEMENTATIONS · CITATION-adjacent · governance/).
The spec chapters cross-link each other heavily and are corpus-gated
already; they can join later if the class ever fires there.

usage: python3 scripts/check-md-refs.py            # exit 0 clean · 1 broken
"""

from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent

SURFACES = sorted(
    [
        *HERE.glob("*.md"),
        *(HERE / "governance").glob("*.md"),
    ]
)

# [text](target) · capture the target · ignore images ! prefix is fine too
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def targets(text: str):
    for m in LINK.finditer(text):
        t = m.group(1)
        if t.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield t.split("#", 1)[0]


def main() -> int:
    broken: list[str] = []
    for md in SURFACES:
        text = md.read_text(encoding="utf-8")
        for t in targets(text):
            if not t:
                continue
            target = (md.parent / t).resolve()
            if not target.exists():
                broken.append(f"{md.relative_to(HERE)} → {t}")
    if broken:
        for b in broken:
            print(f"✗ dead ref · {b}", file=sys.stderr)
        return 1
    print(f"✓ md refs resolve · {len(SURFACES)} governed surfaces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
