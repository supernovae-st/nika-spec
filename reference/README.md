# The executable reference model

The readable semantics of the scheduling core, verified against the real
engine by differential testing (the Cedar method: model → proofs on the
model → production implementation → differential random testing).

- **`semantics.py`** — the model (W2 « the flow »). Each law is a normative
  sentence (GATE-v2 per-edge pass-sets · WHEN post-gate · RETRY · RECOVER ·
  SKIP · DEFAULT); evaluation is a pure function of the parsed
  workflow. Edge roles: value · terminal-observation · failure-observation ·
  control (after predicates · terminal includes cancelled).
- **`generate.py`** — seeded generator of small valid W2 workflows built
  from deterministic blocks only (`exec` argv `true`/`false`, `with:`
  bindings, `after:` predicates, retry/on_error armor). Same seed → same
  bytes.
- **`differential.py`** — runs every seed through the model AND the real
  binary (offline, zero providers) and compares per-task terminal statuses
  plus the recovered flag. A divergence means either the model's sentence
  is wrong (fix the sentence) or the engine drifted (ledger it).

```
python3 reference/differential.py --seeds 120        # 120/120 agree @ 0.109.0 (2026-08-19 · the nine-key envelope)
python3 reference/differential.py --seeds 1 --start 38   # inspect one seed
```

> **Re-measured 2026-08-19 · `120/120` on 0.109.0** (the release that speaks
> the nine-key envelope · a local build of the release code, engine commit
> `9f7042827` inside the `v0.109.0` tag). Two things had to move, and only
> one of them was the engine. On 2026-08-13 the reading was `0/120`
> against the shipped `nika 0.108.0`, which still required the old
> version-marker envelope while `generate.py` already emitted the
> `nika: <id>` identity form: every generated workflow was refused at
> parse and every task read `engine=None` — the harness was AHEAD of the
> shipped engine. With 0.109.0 that wall fell and a second one showed
> behind it: the generator declared no `permits:` block, and an absent
> boundary on an effectful file is zero authority (`NIKA-AUTH-006`), so
> every run refused at its embedded check before the first event. The
> generator now declares the three programs it uses (`echo` · `true` ·
> `false`), and the differential is a current reading again. The binary-
> free proofs stayed green throughout: `reference/selftest.py` (28 laws ·
> 300 seeds) and `scripts/gen-gate-matrix.py --check`.

First catch (2026-07-13, the day the harness was born): the model's HALT
law assumed the workflow-failure arm of `on_error` (then spelled
`fail_workflow`, removed 2026-08-11 · an unrecovered failure IS the
default) cancels every unsettled task; seeds 4/6/38 proved the engine
lets independent branches run to completion — the law was rewritten from
the evidence, and the long-DAG abort question now has a named witness
owed to the outcome chapter.

v0 scope = today's grammar subset the generator emits. Extensions land
wave by wave (typed edges · returns/decoders · outcome causes · callables
and composition · decision/abstention), each with its own generator blocks
and differential gate before the corresponding breaking window opens.

## W2 draft (pipelined inside the W1 window · merges when W2 opens)

`semantics_w2.py` + `selftest_w2.py` model the W2 delta from the LOCKED
rulings only (G11 edge roles · gate algebra v2 · after predicates · when
post-gate · depends_on dies): 25 self-tests green without any binary.
Three named witnesses are exposed for the W2 window — W2-Q1 the
depends_on ≢ after:succeeded migration gap on a skipped producer (the
codemod's equivalence-or-stop STOP case), W2-Q2 cancelled ∈ terminal,
W2-Q3 the skipped-producer value absence (#75-D5). The differential
runner joins once a W2 engine exists — the model leads (law §0.10).
