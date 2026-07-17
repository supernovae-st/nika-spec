#!/usr/bin/env python3
"""The reference model — typed edges + after + when (Cedar method).

STATUS · NORMATIVE since the W2 window opened (law §0.10: the model exists
BEFORE the runtime — the Rust engine implements THIS file and is
differential-tested against it). The pre-W2 model (depends_on grammar)
lives in git history only.

Sources (locked rulings only — nothing here is invented):
  · mega-plan §W2 (2026-07-13-nika-v1-refonte-2060-mega-plan.md)
  · G11 edge roles: e = (producer, consumer, role, predicate)
  · gate algebra v2: default gate over E_d∪E_c = ALL ∈ {success, skipped} ·
    after predicates {success|failure|skipped|terminal} · when = business
    condition POST-gate (the always-pattern migrates to after: {t: terminal})
  · depends_on DIES in W2 (data → with · data-less control → after)
  · when namespaces: {inputs, config, with, item, index} — tasks.* illegal

The v0/W1 laws (GATE RETRY RECOVER SKIP HALT DEFAULT) are inherited from
semantics.py verbatim — this file only replaces HOW a task's admission gate
is computed (per-edge predicates instead of the single depends_on set).

WITNESS LEDGER (resolved at the 2026-07-14 window · fixtures on spec#91):
  W2-Q1  RESOLVED AS THE STOP CLASS · depends_on ≡ after:{t: success} is
         FALSE on a skipped producer (old gate passed · success cancels ·
         a value binding still passes). The codemod is equivalence-or-stop:
         this exact divergence is what the STOP diagnostic prints.
  W2-Q2  RESOLVED · cancelled ∈ terminal (binary witnesses w2q2* · the
         after:{t: terminal} edge admits past a CANCELLED producer).
  W2-Q3  OWED W5 · a VALUE edge from a SKIPPED producer passes the default
         gate but the value is defined-null (#75-D5 partial-output law) —
         the model passes the gate and says nothing about the value.
  W2-P1  PRECISION (this window · from the skip-preserves-error fixture) ·
         PASS_FAILURE_OBS = {failure, skipped}: a skip may carry a
         preserved error (on_error.skip · 05); pass-sets stay context-free.

Determinism law: evaluation is a pure function of the parsed workflow —
no clocks, no randomness, no I/O.
"""

from __future__ import annotations

import json
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "conformance"))
from type_core import parse_type as tc_parse  # noqa: E402
from type_core import fits as tc_fits  # noqa: E402

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
PASS_TERMINAL_OBS = set(TERMINAL)  # any settled state observable (cancelled included · W2-Q2 resolved)
# {failure, skipped}: a skip may carry a PRESERVED error (on_error.skip · 05
# §Fields) — the pass-set stays context-free and the decision-skip read is
# defined-null. A recovered producer settles SUCCESS — the edge still dies.
PASS_FAILURE_OBS = {FAILURE, SKIPPED}
AFTER_PREDICATES = {
    "success": {SUCCESS},
    "failure": {FAILURE},
    "skipped": {SKIPPED},
    "terminal": set(TERMINAL),
}

REF = re.compile(r"\$\{\{\s*tasks\.([A-Za-z0-9_-]+)\.(output|status|cause|error|duration_ms)[^}]*\}\}")


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
        # W3 · decode + returns over `echo <payload>` (the differential's
        # typed slice): decode json parses argv[1] · a returns contract is
        # judged by the reference type core (fit ⊑ · NIKA-TYPE-101 class).
        decode_fails = False
        fit_fails = False
        if exec_block.get("decode") == "json" and cmd[0] == "echo":
            payload = cmd[1] if len(cmd) > 1 else ""
            try:
                decoded = json.loads(payload)
            except (ValueError, TypeError):
                decode_fails = True
                decoded = None
            ret = t.get("returns")
            if not decode_fails and ret is not None:
                names = set(doc.get("types") or {})
                rt = tc_parse(ret, names, f"{tid}.returns")
                if not tc_fits(decoded, rt, {}):
                    fit_fails = True
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
            "fails": cmd[0] == "false" or decode_fails or fit_fails,
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
