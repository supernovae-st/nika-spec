# Conformance corpus v0.1

Prove an engine implements **`nika: v1`** without reading the reference
implementation: run every workflow here through YOUR engine and match each
file's **declared intent**. 95 files across the 5 pillars —
`envelope/` (28) · `variables/` (19) · `verbs/` (17) · `errors/` (17) ·
`dag/` (14) — all runnable offline (`mock/*` models only · no keys · no
network · deterministic).

```sh
conformance/run.sh /path/to/your-engine   # PASS / DRIFT / BUG / DIVERGENT
```

The reference runner is intentionally small POSIX sh — the CONTRACT is the
header grammar below, not the runner; re-implement it in anything.

## Headers — the intent grammar

Every file's first comment block declares its outcome. The `# Expected:`
line is normative for the file; other comments are context.

| header | meaning |
|---|---|
| `# Expected: NIKA-XXX-NNN at CHECK.` | negative · the static check MUST refuse with that code |
| `# Expected: NIKA-XXX-NNN at RUN.` | negative · check passes, the run MUST fail with that code |
| `# Expected: NIKA-XXX-NNN (check or run).` | negative · either stage may catch it (a stricter check is conformant) |
| `# Expected: check-reject (gate verdict).` | negative · the static check MUST refuse (nonzero exit) — no specific wire code required. Used for the permits/secrets/tools boundary gates, which report a human verdict (`✖ PERMITS …` / `✖ SECRETS …` / `✖ TOOLS …`) rather than a NIKA code. An engine that additionally surfaces a wire code (e.g. `NIKA-SEC-004` per spec 05) is equally conformant. |
| `# Expected: exit 0 — …` | positive · the workflow completes clean (includes the *recovered* class: an internal error recovered via `on_error` — workflow-level success) |

Runner contract beyond headers: create `out/<family>/` sink dirs before the
loop (files write only under `./out/` · `run.sh` does this) and export the
corpus's single env secret `FAKE_API_KEY_FOR_TEST` (any dummy value — used by
`envelope/secrets-infer-egress-sanctioned` per spec 01 §secrets `source: env`).

Verdicts: **PASS** (outcome matches intent) · **DRIFT** (failed as declared
but with a different code — a code-mapping bug) · **BUG** (outcome
contradicts intent) · **DIVERGENT** (below).

## The divergence policy (honesty by construction)

This corpus asserts the **spec**, never the reference implementation. When
the reference engine itself diverges from the normative spec text, the case
is still IN the corpus, marked `DIVERGENCE` in its header, and reports
`DIVERGENT` — visible pressure, never a silent green.

v0.1 carries one: `errors/recover-task-ref-no-edge.nika.yaml` — spec 05
§recover requires awaiting a no-edge referent's terminal state; the
reference engine currently raises `NIKA-VAR-001`
([supernovae-st/nika#291](https://github.com/supernovae-st/nika/issues/291)).
An engine that follows the spec turns this file green — and is MORE
conformant than the reference on that row.

## Scope + coverage

`coverage-matrix.tsv` maps pillar × error-namespace × stage to the covering
file — empty cells are the honest v0.2 backlog (notably: no mock
`NIKA-INFER` exemplar yet · `NIKA-AGENT` run-fail needs a mock port ·
self-contained file-builtin positives).

Curated 2026-07-08 from the reference engine's private e2e lab (475
workflows → 95 by per-cell best-file selection; provider-locked,
network-dependent, and fixture-coupled files excluded). Apache-2.0, like
the spec.
