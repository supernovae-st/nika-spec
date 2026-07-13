# The executable reference model

The readable semantics of the scheduling core, verified against the real
engine by differential testing (the Cedar method: model → proofs on the
model → production implementation → differential random testing).

- **`semantics.py`** — the model. Each law is a normative sentence
  (GATE · RETRY · RECOVER · SKIP · HALT · DEFAULT); evaluation is a pure
  function of the parsed workflow.
- **`generate.py`** — seeded generator of small valid workflows built from
  deterministic blocks only (`exec` argv `true`/`false`, `depends_on`,
  retry/on_error armor). Same seed → same bytes.
- **`differential.py`** — runs every seed through the model AND the real
  binary (offline, zero providers) and compares per-task terminal statuses
  plus the recovered flag. A divergence means either the model's sentence
  is wrong (fix the sentence) or the engine drifted (ledger it).

```
python3 reference/differential.py --seeds 120        # 120/120 agree @ 0.103.0
python3 reference/differential.py --seeds 1 --start 38   # inspect one seed
```

First catch (2026-07-13, the day the harness was born): the model's HALT
law assumed `fail_workflow` cancels every unsettled task; seeds 4/6/38
proved the engine lets independent branches run to completion — the law
was rewritten from the evidence, and the long-DAG abort question now has
a named witness owed to the outcome chapter.

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
