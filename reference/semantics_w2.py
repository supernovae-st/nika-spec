#!/usr/bin/env python3
"""The W2 reference model DRAFT — typed edges + after + when (Cedar method).

STATUS · DRAFT, written INSIDE the W1 window to pipeline W2 (law §0.10: the
model exists BEFORE the runtime — the Rust engine of W2 will be written
against this file and differential-tested). It merges only when the W2
window opens; until then it binds nothing.

Sources (locked rulings only — nothing here is invented):
  · mega-plan §W2 (2026-07-13-nika-v1-refonte-2060-mega-plan.md)
  · G11 edge roles: e = (producer, consumer, role, predicate)
  · gate algebra v2: default gate over E_d∪E_c = ALL ∈ {success, skipped} ·
    after predicates {succeeded|failed|skipped|terminal} · when = business
    condition POST-gate (the always-pattern migrates to after: {t: terminal})
  · depends_on DIES in W2 (data → with · data-less control → after)
  · when namespaces: {inputs, config, with, item, index} — tasks.* illegal

The v0/W1 laws (GATE RETRY RECOVER SKIP HALT DEFAULT) are inherited from
semantics.py verbatim — this file only replaces HOW a task's admission gate
is computed (per-edge predicates instead of the single depends_on set).

OPEN WITNESSES (questions this model exposes for the W2 window — each needs
an operator ruling or an engine-differential answer before W2 ships):
  W2-Q1  depends_on ≡ after:{t: succeeded} is FALSE on a skipped producer:
         the old gate passes on skipped, the new predicate cancels. The W2
         codemod is "equivalence-or-stop" — this is a STOP unless the
         mapping targets the default value-edge law or a passed-predicate.
         (selftest_w2.py::test_migration_gap_depends_on_vs_after proves it.)
  W2-Q2  is CANCELLED ∈ terminal for after:{t: terminal}? This model says
         yes (TERMINAL = the four settled states) — needs a witness against
         the W2 engine + the G12 outcome table.
  W2-Q3  a VALUE edge from a SKIPPED producer passes the default gate but
         the value is absent (#75-D5 partial-output law, owed W5) — the
         model passes the gate and says nothing about the value.

Determinism law: evaluation is a pure function of the parsed workflow —
no clocks, no randomness, no I/O.
"""

from __future__ import annotations

import re

import yaml

SUCCESS, FAILURE, SKIPPED, CANCELLED = "success", "failure", "skipped", "cancelled"
TERMINAL = {SUCCESS, FAILURE, SKIPPED, CANCELLED}

# --- edge roles (G11) -------------------------------------------------------
VALUE, TERMINAL_OBS, FAILURE_OBS, CONTROL = (
    "value",
    "terminal-observation",
    "failure-observation",
    "control",
)

# pass-set per role/predicate: the producer states that let the edge admit
# its consumer once the producer settles. Anything else = dead path.
PASS_VALUE = {SUCCESS, SKIPPED}  # gate algebra v2 default (W2-Q3 for the value itself)
PASS_TERMINAL_OBS = set(TERMINAL)  # any settled state observable (W2-Q2 for cancelled)
PASS_FAILURE_OBS = {FAILURE}  # a recovered producer settles SUCCESS — edge dies
AFTER_PREDICATES = {
    "succeeded": {SUCCESS},
    "failed": {FAILURE},
    "skipped": {SKIPPED},
    "terminal": set(TERMINAL),
}

REF = re.compile(r"\$\{\{\s*tasks\.([A-Za-z0-9_-]+)\.(output|status|error|duration_ms)[^}]*\}\}")


class ModelError(Exception):
    """The reference model refuses what the checker would refuse."""


def _edges_of_binding(consumer: str, expr: str) -> list[tuple[str, str, str, frozenset]]:
    """One with-binding expression → N static edges (an expression with N refs
    creates N edges — the graph is what CAN be required)."""
    out = []
    for producer, field in REF.findall(str(expr)):
        if field == "output":
            out.append((producer, consumer, VALUE, frozenset(PASS_VALUE)))
        elif field in ("status", "duration_ms"):
            out.append((producer, consumer, TERMINAL_OBS, frozenset(PASS_TERMINAL_OBS)))
        else:  # error
            out.append((producer, consumer, FAILURE_OBS, frozenset(PASS_FAILURE_OBS)))
    return out


def parse(text: str) -> dict:
    """Parse the W2 subset the generator emits. Refuses what it does not
    model (loudly) — and refuses the W1 forms W2 kills."""
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict) or doc.get("nika") != "v1":
        raise ModelError("envelope: nika: v1 required")
    raw_tasks = doc.get("tasks")
    if not isinstance(raw_tasks, dict) or not raw_tasks:
        raise ModelError("tasks: non-empty map required (W1 · the key IS the identity)")
    tasks, order, edges = {}, [], []
    for tid, t in raw_tasks.items():
        if not tid or not isinstance(t, dict):
            raise ModelError(f"task {tid!r}: body must be a mapping")
        if "depends_on" in t:
            raise ModelError(f"{tid}: depends_on is dead in W2 (data → with · control → after)")
        exec_block = t.get("exec") or {}
        cmd = exec_block.get("command")
        if not isinstance(cmd, list) or not cmd:
            raise ModelError(f"{tid}: this model covers exec argv tasks only")
        # E_d — with bindings, one edge per ref, role per field (G11)
        for _name, expr in (t.get("with") or {}).items():
            edges.extend(_edges_of_binding(tid, expr))
        # E_c — after predicates (control · state, no data)
        for producer, pred in (t.get("after") or {}).items():
            if pred not in AFTER_PREDICATES:
                raise ModelError(f"{tid}: after predicate {pred!r} ∉ {sorted(AFTER_PREDICATES)}")
            edges.append((producer, tid, CONTROL, frozenset(AFTER_PREDICATES[pred])))
        # when — business condition POST-gate · local namespaces only.
        # The generator emits literal booleans; a tasks.* ref in when is illegal.
        when = t.get("when", True)
        if isinstance(when, str) and REF.search(when):
            raise ModelError(f"{tid}: when must be local (tasks.* is illegal in when)")
        on_error = t.get("on_error") or {}
        armor = None
        if "recover" in on_error:
            armor = ("recover", on_error["recover"])
        elif on_error.get("skip") is True:
            armor = ("skip", None)
        elif on_error.get("fail_workflow") is True:
            armor = ("fail_workflow", None)
        tasks[tid] = {
            "fails": cmd[0] == "false",
            "when": bool(when),
            "attempts": 1 + int((t.get("retry") or {}).get("max_attempts") or 0),
            "armor": armor,
        }
        order.append(tid)
    for producer, consumer, _role, _ok in edges:
        if producer not in tasks:
            raise ModelError(f"{consumer}: unknown task {producer!r} referenced")  # DAG-002 heir
    return {"tasks": tasks, "order": order, "edges": edges}


def waves(model: dict) -> list[list[str]]:
    """Kahn levels over G_p = E_d ∪ E_c (roles do not change precedence —
    every edge orders execution; predicates only gate admission)."""
    order = model["order"]
    preds: dict[str, set] = {tid: set() for tid in order}
    for producer, consumer, _role, _ok in model["edges"]:
        preds[consumer].add(producer)
    depth: dict[str, int] = {}

    def d(tid: str, seen: tuple = ()) -> int:
        if tid in seen:
            raise ModelError(f"cycle through {tid}")  # DAG-004 unchanged
        if tid not in depth:
            depth[tid] = 0 if not preds[tid] else 1 + max(d(x, seen + (tid,)) for x in preds[tid])
        return depth[tid]

    for tid in order:
        d(tid)
    out: list[list[str]] = [[] for _ in range(max(depth.values()) + 1)]
    for tid in order:  # source order inside a wave = presentation, kept for stability
        out[depth[tid]].append(tid)
    return out


def evaluate(model: dict) -> dict[str, dict]:
    """The W2 scheduling semantics. Returns {task: {status, recovered, attempts}}.

    Laws (delta vs v0 — everything else inherited verbatim):
      GATE-v2  a task runs iff EVERY incoming edge's producer settled INSIDE
               that edge's pass-set (per-edge predicates · G11); any settled
               producer outside a pass-set cancels the consumer (dead-path
               elimination), transitively.
      WHEN     evaluated POST-gate: gate passes + when is false → SKIPPED
               (not cancelled) — downstream default gates treat it as
               passable, exactly like on_error.skip.
      RETRY / RECOVER / SKIP / HALT / DEFAULT — identical to semantics.py
               (HALT: fail_workflow fails the RUN, independent branches
               still complete — the 120/120 differential law of W0).
    """
    tasks = model["tasks"]
    incoming: dict[str, list] = {tid: [] for tid in model["order"]}
    for producer, consumer, role, ok in model["edges"]:
        incoming[consumer].append((producer, role, ok))
    state: dict[str, dict] = {}
    for wave in waves(model):
        for tid in wave:
            t = tasks[tid]
            if any(state[p]["status"] not in ok for p, _role, ok in incoming[tid]):
                state[tid] = {"status": CANCELLED, "recovered": False, "attempts": 0}
                continue
            if not t["when"]:
                state[tid] = {"status": SKIPPED, "recovered": False, "attempts": 0}
                continue
            if not t["fails"]:
                state[tid] = {"status": SUCCESS, "recovered": False, "attempts": 1}
                continue
            attempts = t["attempts"]
            kind = t["armor"][0] if t["armor"] else None
            if kind == "recover":
                state[tid] = {"status": SUCCESS, "recovered": True, "attempts": attempts}
            elif kind == "skip":
                state[tid] = {"status": SKIPPED, "recovered": False, "attempts": attempts}
            else:
                state[tid] = {"status": FAILURE, "recovered": False, "attempts": attempts}
    for tid in model["order"]:  # anything never reached (defensive)
        state.setdefault(tid, {"status": CANCELLED, "recovered": False, "attempts": 0})
    return state


def evaluate_text(text: str) -> dict[str, dict]:
    return evaluate(parse(text))
