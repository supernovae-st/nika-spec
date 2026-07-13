#!/usr/bin/env python3
"""The executable reference model — readable semantics, v0 (W0 · Cedar method).

This file IS the readable semantics of the scheduling core: task admission,
the default gate, retry, recovery, skip, fail_workflow and cancellation.
The Rust engine is the performant implementation OF this semantics; the
differential runner (differential.py) proves the two agree on generated
workflows. v0 scope = the surface the generator emits (exec argv true/false,
depends_on edges, retry/on_error armor). Extensions land wave by wave:
typed edges + after (W2) · returns/decoders (W3) · outcome causes (W5) ·
callables + composition (W-COMP) · decision/abstention (W-DEC).

Determinism law: evaluation is a pure function of the parsed workflow —
no clocks, no randomness, no I/O.
"""

from __future__ import annotations

import yaml

SUCCESS, FAILURE, SKIPPED, CANCELLED = "success", "failure", "skipped", "cancelled"
TERMINAL = {SUCCESS, FAILURE, SKIPPED, CANCELLED}


class ModelError(Exception):
    """The reference model refuses what the checker would refuse."""


def parse(text: str) -> dict:
    """Parse the v0 subset. Refuses what it does not model (loudly)."""
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict) or doc.get("nika") != "v1":
        raise ModelError("envelope: nika: v1 required")
    raw_tasks = doc.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ModelError("tasks: non-empty list required (v0 models today's list form)")
    tasks, order = {}, []
    for t in raw_tasks:
        tid = t.get("id")
        if not tid or tid in tasks:
            raise ModelError(f"task id missing or duplicate: {tid!r}")
        exec_block = t.get("exec") or {}
        cmd = exec_block.get("command")
        if not isinstance(cmd, list) or not cmd:
            raise ModelError(f"{tid}: v0 models exec argv tasks only")
        on_error = t.get("on_error") or {}
        armor = None
        if "recover" in on_error:
            armor = ("recover", on_error["recover"])
        elif on_error.get("skip") is True:
            armor = ("skip", None)
        elif on_error.get("fail_workflow") is True:
            armor = ("fail_workflow", None)
        tasks[tid] = {
            "deps": list(t.get("depends_on") or []),
            "fails": cmd[0] == "false",
            "attempts": 1 + int((t.get("retry") or {}).get("max_attempts") or 0),
            "armor": armor,
        }
        order.append(tid)
    for tid, t in tasks.items():
        for d in t["deps"]:
            if d not in tasks:
                raise ModelError(f"{tid}: unknown dependency {d!r}")
    return {"tasks": tasks, "order": order}


def waves(model: dict) -> list[list[str]]:
    """Kahn levels over depends_on — the main precedence graph (v0: E_d∪E_c
    collapses to depends_on; W2 splits the roles)."""
    tasks, order = model["tasks"], model["order"]
    depth: dict[str, int] = {}

    def d(tid: str, seen: tuple = ()) -> int:
        if tid in seen:
            raise ModelError(f"cycle through {tid}")
        if tid not in depth:
            deps = tasks[tid]["deps"]
            depth[tid] = 0 if not deps else 1 + max(d(x, seen + (tid,)) for x in deps)
        return depth[tid]

    for tid in order:
        d(tid)
    out: list[list[str]] = [[] for _ in range(max(depth.values()) + 1)]
    for tid in order:  # source order inside a wave = presentation, kept for stability
        out[depth[tid]].append(tid)
    return out


def evaluate(model: dict) -> dict[str, dict]:
    """The scheduling semantics. Returns {task: {status, recovered, attempts}}.

    Laws modeled (each is a normative sentence the engine must agree with):
      GATE    a task runs iff ALL deps ∈ {success, skipped}; otherwise it is
              cancelled (dead-path elimination), transitively.
      RETRY   a failing task re-runs up to its attempt budget; a deterministic
              failure exhausts it.
      RECOVER on_error.recover settles the task SUCCESS carrying the recovery
              value (observed engine behavior: task_recovered then
              task_completed); the failure is recorded via recovered=True.
      SKIP    on_error.skip settles the task SKIPPED; downstream default
              gates treat skipped as passable.
      HALT    on_error.fail_workflow settles FAILURE and fails the RUN —
              but adds NO extra task cancellation at this scale: the
              differential proved (seeds 4/6/38 · 0.103.0) that independent
              branches still run to completion; only the failing task's own
              downstream cancels, via GATE like any failure. Whether unlaunched
              far waves abort on long sequential DAGs needs a dedicated
              witness — owned by the W5 outcome chapter.
      DEFAULT a failure without armor settles FAILURE; its downstream is
              cancelled by GATE.
    """
    tasks = model["tasks"]
    state: dict[str, dict] = {}
    for wave in waves(model):
        # settle the whole wave first (models concurrent dispatch)
        for tid in wave:
            t = tasks[tid]
            if any(state[d]["status"] not in (SUCCESS, SKIPPED) for d in t["deps"]):
                state[tid] = {"status": CANCELLED, "recovered": False, "attempts": 0}
                continue
            attempts = t["attempts"] if t["fails"] else 1
            if not t["fails"]:
                state[tid] = {"status": SUCCESS, "recovered": False, "attempts": 1}
                continue
            kind = t["armor"][0] if t["armor"] else None
            if kind == "recover":
                state[tid] = {"status": SUCCESS, "recovered": True, "attempts": attempts}
            elif kind == "skip":
                state[tid] = {"status": SKIPPED, "recovered": False, "attempts": attempts}
            else:
                # plain failure AND fail_workflow: task-level status is the
                # same; fail_workflow only forces the RUN outcome (see HALT)
                state[tid] = {"status": FAILURE, "recovered": False, "attempts": attempts}
    for tid in model["order"]:  # anything never reached (defensive)
        state.setdefault(tid, {"status": CANCELLED, "recovered": False, "attempts": 0})
    return state


def evaluate_text(text: str) -> dict[str, dict]:
    return evaluate(parse(text))
