#!/usr/bin/env python3
"""Seeded W2 workflow generator (DRAFT · joins the differential when a W2
engine exists — until then it feeds the model's own property tests).

Emits small valid workflows in the W2 grammar: task map · with bindings
(.output / .status / .error refs → value / terminal-observation /
failure-observation edges) · after predicates · when literals · exec argv
[true]/[false] · retry and on_error armor. No depends_on — W2 kills it.
Determinism: same seed → same bytes.
"""

from __future__ import annotations

import random

FIELDS = ["output", "output", "output", "status", "error"]  # value-biased mix
PREDICATES = ["succeeded", "failed", "skipped", "terminal"]


def generate(seed: int) -> str:
    rng = random.Random(seed)
    n = rng.randint(3, 9)
    lines = ["nika: v1", "workflow:", f"  id: gen-w2-{seed}", "tasks:"]
    for i in range(n):
        tid = f"t{i}"
        lines.append(f"  {tid}:")
        # incoming edges: producers only among earlier tasks (acyclic by construction)
        producers = sorted(rng.sample(range(i), k=min(i, rng.randint(0, 2)))) if i else []
        withs, afters = [], []
        for p in producers:
            if rng.random() < 0.65:
                field = rng.choice(FIELDS)
                withs.append((f"b{p}", f"${{{{ tasks.t{p}.{field} }}}}"))
            else:
                afters.append((f"t{p}", rng.choice(PREDICATES)))
        if withs:
            lines.append("    with:")
            for name, expr in withs:
                lines.append(f"      {name}: '{expr}'")
        if afters:
            lines.append("    after:")
            for producer, pred in afters:
                lines.append(f"      {producer}: {pred}")
        if rng.random() < 0.10:
            lines.append("    when: false")
        fails = rng.random() < 0.35
        lines.append("    exec:")
        lines.append(f"      command: [\"{'false' if fails else 'true'}\"]")
        if fails:
            if rng.random() < 0.20:
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
