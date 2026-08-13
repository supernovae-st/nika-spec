# FINDINGS — reference-engine observations vs spec (conformance v0.1 polish, 2026-07-08, nika 0.97.0)

Non-blocking observations recorded while proving the corpus green. Neither is
asserted BY the corpus (headers were chosen so both engine behaviors conform);
both deserve an upstream look. The one asserted divergence stays
`errors/recover-task-ref-no-edge.nika.yaml` (spec 05 §recover await ·
supernovae-st/nika#291 · verdict DIVERGENT by design).

## F-1 · Unknown tool: check refuses without the spec wire code

`verbs/invoke-unknown-tool-reject.nika.yaml` — spec 05 §errors: `NIKA-INVOKE-001 |
unknown tool (unresolvable nika:/mcp: id) | validation_error`. `nika check` (0.97.0)
refuses correctly but reports only the TOOLS gate verdict
(`✖ TOOLS \`nika:nonexistent_builtin_xyzzy\` … is not a canonical builtin`) — the
INVOKE-001 wire code never appears on the check surface. Same convention across the
permits/secrets gates (spec-05 SEC-004-class refusals print `✖ PERMITS/SECRETS`
verdicts, no code). The corpus encodes this as the `check-reject (gate verdict)`
header class; an engine that additionally prints the wire code is equally
conformant. Upstream question: should check-time gate refusals surface the
canonical wire code (one-voice)?

> **Re-measured 2026-07-30 · nika 0.106.1 — EVOLVED, and the question
> sharpened.** The surface now emits a CODE (`NIKA-BUILTIN-001` in
> `check --json`, probed on the same unknown-`nika:*` shape) — the
> codeless half of this finding is closed. What remains is a family
> question: BUILTIN-001's registered condition is the *statically-checkable
> arg contract*, while 05 assigns *unknown tool* to `NIKA-INVOKE-001` —
> the engine speaks a neighbouring code. Same one-voice genre as the
> codeless-rungs owe (supernovae-st/nika#761); parked with it rather than
> filed separately.

## F-2 · Out-of-range index / missing map key → VAR-001 "unresolved reference" (whole expression as ref name)

Probed (lab `cel/c12-index-out-of-range`, `cel/c14-missing-map-key` — NOT in corpus):
`when: ${{ vars.xs[10] == 1 }}` on a 3-element list fails at RUN with
`NIKA-VAR-001 · unresolved template reference "vars.xs[10] == 1"` — likewise for a
missing map key. Two observations: (a) CEL standard semantics ("no such index" /
"no such key" eval error) read as a NIKA-VAR-006-class evaluation error, and the
spec does not enumerate the case — spec-clarification candidate; (b) the error
message reports the ENTIRE expression as the unresolved reference name —
message-quality issue. Because the normative code is ambiguous, c12 was swapped out
of the corpus for `cel/c15-string-method-type-mismatch` (spec 03 side-constraint 1
is explicit, engine fires exactly `NIKA-VAR-006`); index-out-of-range sits in the
v0.2 backlog pending the spec call.

> **Re-measured 2026-07-30 · nika 0.106.1 — STANDS unchanged.** The same
> probe (a `when:` indexing past a 3-element list) still fails at run as
> `NIKA-VAR-001 · unresolved template reference` with the whole
> expression as the reference name. Both halves of the finding hold; the
> v0.2 spec call stays owed.

## F-3 · Every binary-differential is dark: the corpus is ahead of the shipped engine

**Measured 2026-08-13 · `nika 0.108.0` (the shipped binary).** Both
differentials that run the real binary against this repo's corpus agree on
*nothing*, and it is one cause, not two ·

```
python3 reference/differential.py --seeds 120     →   0/120 agree
python3 scripts/oracle-differential.py --bin nika →   0/50 agree · 50 unexplained
```

Every divergence is the same line ·
`NIKA-PARSE-003 · invalid `nika:` version "<id>" — the value is exactly `v1``.
The shipped engine still requires the OLD envelope (`nika: v1`); the corpus,
the templates and `reference/generate.py` already carry the NEW identity form
(`nika: <workflow-id>`). The workflow is refused at parse, so every task reads
`engine=None` and the comparison has no subject.

**This is a cascade state, not a defect on either side.** The teaching surface
was migrated first, by design; the engine arm lands with the envelope window.
Both harnesses go green again on their own when it ships — no fixture and no
model needs a change here.

**What it costs while it lasts, and why it is written down.** Two proof
surfaces read GREEN in prose and BLACK in fact: `reference/README.md` published
`120/120 agree` beside the command until 2026-08-13. A differential that
compares nothing reports no divergence, so *the failure mode is silence* — it
cannot be distinguished from success by anyone who does not run it. Until the
engine arm lands, the proofs that hold are the ones with no binary in the
loop · `reference/selftest.py` (28 laws · 300 seeds) · `scripts/gen-gate-matrix.py
--check` · `scripts/lints-differential.py --selftest` (5/5) ·
`scripts/mutation-adequacy.py --check` (15/15 selftests die under a permissive
judge). All green at this commit.
