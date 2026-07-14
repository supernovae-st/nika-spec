#!/usr/bin/env python3
"""Self-tests + witnesses for the W2 reference model DRAFT.

Runs with stdlib + pyyaml only — no engine binary required (the W2 engine
does not exist yet; the differential runner joins when it does). Two kinds
of tests live here:
  · LAWS      — properties the model must hold (determinism · gate
                soundness · dead-path transitivity · v0 equivalence on the
                value-edge-only fragment)
  · WITNESSES — divergences the model EXPOSES for the W2 window rulings
                (they assert the divergence EXISTS — deleting one of these
                tests requires the ruling that resolves it)

usage: python3 reference/selftest_w2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import semantics as w2  # noqa: E402

PASS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS
    if not cond:
        print(f"✗ {name} {detail}")
        raise SystemExit(1)
    PASS += 1
    print(f"✓ {name}")


def wf(tasks: str) -> str:
    return f"nika: v1\nworkflow:\n  id: selftest\ntasks:\n{tasks}"


T = "    exec: {command: [\"true\"]}"
F = "    exec: {command: [\"false\"]}"


def status(text: str, tid: str) -> str:
    return w2.evaluate_text(text)[tid]["status"]


# --- LAWS --------------------------------------------------------------------

# determinism: same input, same output — twice
t = wf(f"  a:\n{T}\n  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}")
check("determinism", w2.evaluate_text(t) == w2.evaluate_text(t))

# value edge admits on success
check("value-edge · success admits", status(t, "b") == "success")

# value edge cancels downstream of a plain failure (dead-path)
t = wf(f"  a:\n{F}\n  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}")
check("value-edge · failure cancels", status(t, "b") == "cancelled")

# dead-path is transitive through value chains
t = wf(
    f"  a:\n{F}\n"
    f"  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}\n"
    f"  c:\n    with: {{x: '${{{{ tasks.b.output }}}}'}}\n{T}"
)
check("dead-path · transitive", status(t, "c") == "cancelled")

# after:{failed} — runs ONLY on failure · cancelled on success (both directions)
t = wf(f"  a:\n{F}\n  handle:\n    after: {{a: failed}}\n{T}")
check("after failed · failure admits", status(t, "handle") == "success")
t = wf(f"  a:\n{T}\n  handle:\n    after: {{a: failed}}\n{T}")
check("after failed · success cancels", status(t, "handle") == "cancelled")

# after:{terminal} — the always-pattern (runs on success AND on failure)
for body, want in ((T, "success"), (F, "failure")):
    t = wf(f"  a:\n{body}\n  always:\n    after: {{a: terminal}}\n{T}")
    check(f"after terminal · runs past {want}", status(t, "always") == "success")

# failure-observation: .error consumer dies on success, runs on failure,
# and DIES on a RECOVERED producer (recover settles SUCCESS — the failure
# is swallowed; the edge sees success ∉ {failure})
t = wf(f"  a:\n{T}\n  err:\n    with: {{e: '${{{{ tasks.a.error }}}}'}}\n{T}")
check("failure-obs · success cancels", status(t, "err") == "cancelled")
t = wf(f"  a:\n{F}\n  err:\n    with: {{e: '${{{{ tasks.a.error }}}}'}}\n{T}")
check("failure-obs · failure admits", status(t, "err") == "success")
t = wf(
    f"  a:\n{F}\n    on_error: {{recover: fallback}}\n"
    f"  err:\n    with: {{e: '${{{{ tasks.a.error }}}}'}}\n{T}"
)
check("failure-obs · recovered producer cancels the .error edge", status(t, "err") == "cancelled")

# terminal-observation: .status consumer runs whatever the producer did
for body in (T, F):
    t = wf(f"  a:\n{body}\n  obs:\n    with: {{s: '${{{{ tasks.a.status }}}}'}}\n{T}")
    check("terminal-obs · settled admits", status(t, "obs") == "success")

# when=false POST-gate → SKIPPED (not cancelled) · downstream value edge passes
t = wf(f"  a:\n    when: false\n{T}\n  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}")
r = w2.evaluate_text(t)
check("when false · skipped not cancelled", r["a"]["status"] == "skipped")
check("when false · skipped passes the default value gate (W2-Q3)", r["b"]["status"] == "success")

# one expression, two refs → two edges, BOTH must hold
t = wf(
    f"  a:\n{T}\n  b:\n{F}\n"
    f"  c:\n    with: {{x: '${{{{ tasks.a.output }}}} and ${{{{ tasks.b.output }}}}'}}\n{T}"
)
check("N refs = N edges · one dead edge cancels", status(t, "c") == "cancelled")

# refusals: depends_on is dead · unknown ref · cycle · tasks.* in when
for name, bad in (
    ("depends_on refused", f"  a:\n{T}\n  b:\n    depends_on: [a]\n{T}"),
    ("unknown ref refused", f"  b:\n    with: {{x: '${{{{ tasks.ghost.output }}}}'}}\n{T}"),
    (
        "cycle refused",
        f"  a:\n    with: {{x: '${{{{ tasks.b.output }}}}'}}\n{T}\n"
        f"  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}",
    ),
    ("tasks.* in when refused", f"  a:\n{T}\n  b:\n    when: '${{{{ tasks.a.status }}}}'\n{T}"),
):
    try:
        w2.evaluate_text(wf(bad))
        check(name, False, "(accepted!)")
    except w2.ModelError:
        check(name, True)

# W1-equivalence on the value-edge-only fragment: with-.output chains behave
# exactly like the dead depends_on gate ({success, skipped} passable). The
# expected column IS the W1 model's answer (semantics.py pre-W2 · git is the
# archive) — the fragment the codemod migrates mechanically.
CASES = [
    ("chain-ok", T, "success"),
    ("chain-fail", F, "cancelled"),
    (
        "chain-skip",
        F + "\n    on_error: {skip: true}",
        "success",
    ),
]
for name, a_body, want_b in CASES:
    w2_t = wf(f"  a:\n{a_body}\n  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}")
    got_w2 = status(w2_t, "b")
    check(f"w1-equivalence · {name}", got_w2 == want_b, f"w2={got_w2} want={want_b}")

# --- WITNESSES (open questions for the W2 window · deleting one requires
# --- the ruling that resolves it) ---------------------------------------------

# W2-Q1 · THE MIGRATION GAP (RESOLVED as the codemod STOP class): the dead
# depends_on gate on a skipped producer passed ({success, skipped}); the
# succeeded predicate cancels there while a value binding still passes.
# The two W2 spellings the codemod offers at the STOP diverge exactly here.
skip_a = F + "\n    on_error: {skip: true}"
strict = wf(f"  a:\n{skip_a}\n  b:\n    after: {{a: succeeded}}\n{T}")
value = wf(f"  a:\n{skip_a}\n  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}")
check(
    "W2-Q1 witness · succeeded cancels where the value edge passes (skip)",
    status(strict, "b") == "cancelled" and status(value, "b") == "success",
    f"strict={status(strict, 'b')} value={status(value, 'b')}",
)

# failure-observation admits on SKIPPED (a skip may carry a preserved error ·
# on_error.skip · 05 §Fields) — the pass-set is context-free {failure, skipped}:
# a decision-skip's error is defined-null, the read stays total.
t = wf(f"  a:\n{skip_a}\n  route:\n    with: {{e: '${{{{ tasks.a.error }}}}'}}\n{T}")
check("failure-obs · armor-skip admits (preserved error readable)", status(t, "route") == "success")
t = wf(f"  a:\n    when: false\n{T}\n  route:\n    with: {{e: '${{{{ tasks.a.error }}}}'}}\n{T}")
check("failure-obs · decision-skip admits (reads defined-null)", status(t, "route") == "success")

# W2-Q2 · RESOLVED (binary witnesses 2026-07-14 · w2q2* fixtures on spec#91):
# cancelled ∈ terminal — after:{t: terminal} admits past a CANCELLED producer.
t = wf(
    f"  a:\n{F}\n"
    f"  b:\n    with: {{x: '${{{{ tasks.a.output }}}}'}}\n{T}\n"
    f"  cleanup:\n    after: {{b: terminal}}\n{T}"
)
check("W2-Q2 witness · terminal admits past cancelled (model's answer)", status(t, "cleanup") == "success")

# --- PROPERTIES over generated workflows (seeded · no binary needed) ----------
# gate soundness + cancel witness + determinism, over 300 random W2 DAGs.

import generate  # noqa: E402

SEEDS = 300
for seed in range(SEEDS):
    text = generate.generate(seed)
    model = w2.parse(text)
    r1, r2 = w2.evaluate(model), w2.evaluate(model)
    assert r1 == r2, f"seed {seed}: non-deterministic"
    incoming = {tid: [] for tid in model["order"]}
    for producer, consumer, _role, ok in model["edges"]:
        incoming[consumer].append((producer, ok))
    for tid, res in r1.items():
        held = [r1[p]["status"] in ok for p, ok in incoming[tid]]
        if res["status"] == "cancelled":
            # CANCEL-WITNESS: a cancelled task names at least one dead edge
            assert not all(held), f"seed {seed}: {tid} cancelled with every edge held"
        else:
            # GATE-SOUNDNESS: a task that settled any other way passed every edge
            assert all(held), f"seed {seed}: {tid} ran with a dead edge"
        if res["status"] == "skipped" and res["attempts"] == 0:
            # when=false settles POST-gate: the gate must have passed
            assert all(held), f"seed {seed}: {tid} when-skipped without a passing gate"
check(f"properties · {SEEDS} seeds: gate-soundness + cancel-witness + determinism", True)

print(f"\nALL {PASS} GREEN — laws hold · W2-Q1/Q2 resolved · W2-Q3 owed W5 (semantics.py header)")
