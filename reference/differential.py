#!/usr/bin/env python3
"""Differential runner — the reference model vs the real engine (Cedar method).

For each seed: generate a workflow → evaluate it in the readable model →
run it with the real binary (offline, exec-only) → compare per-task terminal
statuses (+ the recovered flag). Any divergence prints the workflow and both
verdicts: either the model misstates the semantics (fix the model — the
sentence was wrong) or the engine drifted (file it — the ledger owns it).

usage: python3 reference/differential.py --seeds 50 [--bin nika] [--start 0]
exit:  0 all seeds agree · 1 divergences (listed)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate import generate  # noqa: E402
from semantics import evaluate_text  # noqa: E402

TERMINAL_KINDS = {
    "task_completed": "success",
    "task_failed": "failure",
    "task_skipped": "skipped",
    "task_cancelled": "cancelled",
}


def run_engine(binary: str, text: str) -> dict[str, dict]:
    with tempfile.NamedTemporaryFile("w", suffix=".nika.yaml", delete=False) as f:
        f.write(text)
        path = f.name
    proc = subprocess.run(
        [binary, "run", path, "--json"],
        capture_output=True, text=True, timeout=120,
    )
    state: dict[str, dict] = {}
    recovered: set[str] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = ev.get("kind", "")
        fields = {f["key"]: f["value"] for f in ev.get("fields", [])}
        task = fields.get("task")
        if not task:
            continue
        if kind == "task_recovered":
            recovered.add(task)
        status = TERMINAL_KINDS.get(kind)
        if status:
            state[task] = {"status": status, "recovered": task in recovered}
    Path(path).unlink(missing_ok=True)
    return state


def compare(model: dict, engine: dict) -> list[str]:
    diffs = []
    for tid in sorted(set(model) | set(engine)):
        m, e = model.get(tid), engine.get(tid)
        m_view = (m["status"], m["recovered"]) if m else None
        e_view = (e["status"], e["recovered"]) if e else None
        if m_view != e_view:
            diffs.append(f"  {tid}: model={m_view} engine={e_view}")
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--bin", default="nika")
    args = ap.parse_args()
    bad = 0
    for seed in range(args.start, args.start + args.seeds):
        text = generate(seed)
        model = {k: {"status": v["status"], "recovered": v["recovered"]}
                 for k, v in evaluate_text(text).items()}
        engine = run_engine(args.bin, text)
        diffs = compare(model, engine)
        if diffs:
            bad += 1
            print(f"DIVERGENT seed={seed}")
            print("\n".join(diffs))
            print("--- workflow ---")
            print(text)
    total = args.seeds
    print(f"differential: {total - bad}/{total} seeds agree · bin={args.bin}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
