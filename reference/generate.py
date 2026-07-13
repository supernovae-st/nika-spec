#!/usr/bin/env python3
"""Seeded workflow generator for the differential harness (W0 · v0 subset).

Emits small valid workflows in TODAY's grammar using only deterministic
building blocks: exec argv [true] / [false], depends_on edges, retry and
on_error armor. Every emitted file is (a) evaluable by the reference model
and (b) runnable by the real engine offline with zero providers.
Determinism: same seed → same bytes.
"""

from __future__ import annotations

import random


def generate(seed: int) -> str:
    rng = random.Random(seed)
    n = rng.randint(3, 9)
    lines = ["nika: v1", f"workflow: gen-{seed}", "tasks:"]
    for i in range(n):
        tid = f"t{i}"
        deps = sorted(rng.sample(range(i), k=min(i, rng.randint(0, 2)))) if i else []
        fails = rng.random() < 0.35
        lines.append(f"  - id: {tid}")
        if deps:
            lines.append(f"    depends_on: [{', '.join(f't{d}' for d in deps)}]")
        lines.append("    exec:")
        lines.append(f"      command: [\"{'false' if fails else 'true'}\"]")
        if fails:
            r = rng.random()
            if r < 0.20:
                lines.append("    retry:")
                lines.append(f"      max_attempts: {rng.randint(1, 2)}")
            armor = rng.random()
            if armor < 0.30:
                lines.append("    on_error:")
                lines.append('      recover: "fallback"')
            elif armor < 0.45:
                lines.append("    on_error:")
                lines.append("      skip: true")
            elif armor < 0.55:
                lines.append("    on_error:")
                lines.append("      fail_workflow: true")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys

    print(generate(int(sys.argv[1]) if len(sys.argv) > 1 else 0), end="")
