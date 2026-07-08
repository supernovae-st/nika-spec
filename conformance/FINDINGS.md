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
