# NEP-0015 · Preview-commit: the effect request is hashed at judgment and recomputed at the sink

- **NEP**: 0015 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle · 0008 the egress projection · 0009 the effective path identity · 0010 the run declaration · 0011 the run lifecycle · 0012 the receipt as untrusted input · 0013 the approval ticket · 0014 the thin-laws lot 3a)
- **Title**: Preview-commit — every effectful step carries the digest of its judged request, the executor recomputes it on the exact bytes it fires, and one bit of divergence is a refusal
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-29

## Abstract

An effectful step (`exec` · `invoke`) is judged twice today — statically
at check and against the permit boundary at dispatch — but what is judged
is the program and the globs, never the rendered request. The arguments
are rendered after judgment, against a scope that carries upstream task
outputs, and nothing binds the approved plan to the fired syscall. This
NEP closes that window: every effect request is serialized canonically
and hashed at resolution (PREVIEW), and the executor — the only
component that reaches the sink — recomputes the digest on the exact
bytes it is about to fire (COMMIT). Any divergence, down to one bit of
rendered argv, is fail-closed with a `divergence` finding at the receipt
(`NIKA-SEC-011`). Judged = executed descends from the run to the action.

## Motivation

A workflow's scope is not neutral: it carries the outputs of upstream
tasks — fetched pages, tool results, model generations — which are
attacker-influenceable data. When `${{ }}` interpolation renders an
`exec` argv or an `invoke` payload against that scope, the bytes that
reach the sink can differ from anything a human or a static pass ever
judged. This is the time-of-check/time-of-use gap at the scale of the
action, and it is the load-bearing observation of SecureClaw
([arXiv:2606.09549](https://arxiv.org/abs/2606.09549) · measured:
0/2000 attack success on ASB, 4/629 on AgentDojo, 25/25 adversarial
bypass attempts refused), transposed from its gateway setting into the
engine's dispatch. The contract system's fourth invariant — judged =
executed = attested — held at the run level; this NEP makes it hold at
the level of the individual effect.

## Specification

The law (MUST):

1. **The effect request ρ.** Every effectful step materializes, at
   resolution time, its canonical request
   `ρ = (verb, task_id, attempt, intent, inputs, ctx)` where `intent` is
   the rendered argv (`exec`) or the rendered tool + arguments
   (`invoke`), and `ctx` binds the judgment context: the plan's semantic
   hash (spec 15), the lock digest, the permits digest (the boundary as
   judged), the tool pin digest (`invoke` · the TOFU pin), the sandbox
   spec digest (`exec`), the approval class, and the run id with the
   attempt counter (freshness, anti-replay intra- and inter-run).
2. **Preview.** At the point the request is resolved, the engine
   computes `preview_digest = blake3("effect-preview" ‖ JCS(ρ))` — a
   domain-separated digest over the RFC 8785 canonical serialization.
3. **Commit.** The dispatch layer — the only code that reaches the
   sinks — recomputes `commit_digest` over the exact bytes it is about
   to fire, before the syscall. COMMIT if and only if
   `commit_digest == preview_digest`. Otherwise the step refuses
   fail-closed (`NIKA-SEC-011` · `security_error`) and the receipt
   carries `divergence: {preview, commit}` as a finding.
4. **Attestation is additive.** The digests ride the terminal frames of
   the trace as additive fields — no trace-format bump, no change to
   any green workflow's receipt shape beyond the new fields.
5. **Deny-aware recovery.** A refusal renders a fixed template — the
   coarse action class, the reason code, a safe continuation hint — from
   a family closed by this specification. No refusal ever embeds
   dereferenced content, and no model-generated text ever enters the
   refusal.

The binding covers the two effectful verbs only. `infer` and `agent`
are not sinks — they mutate no external state; their bound is the run
certificate (call counts · cost), not a request digest.

## Rationale

- **Equality of bytes, never a judge.** The binding is a digest
  comparison — deterministic, sub-millisecond, implementable by any
  second engine from JCS + a hash + the receipt shape. The impossibility
  result on LLM-audited action pipelines
  ([arXiv:2605.17634](https://arxiv.org/abs/2605.17634)) is honored by
  construction: no model sits between preview and commit.
- **Recompute at the sink, not upstream.** Only the executor sees the
  exact bytes that will fire (post-interpolation, post-encoding). Any
  comparison point earlier in the pipeline re-opens the window.
- **Digest, not HMAC, inside one process.** SecureClaw needs a keyed
  binding because its preview crosses a trust boundary (an untrusted
  runtime between gateway and executor). Inside one engine process the
  domain-separated digest over the canonical pre-image suffices; a keyed
  or signed artefact enters only when the preview leaves the process
  (a human-approval UI riding NEP-0013's ticket chain · a remote policy
  engine) — see Deferred.
- **Digests at the receipt, not values.** The request's inputs rise to
  the receipt as digests by default, so equality is provable without
  disclosure — the disclosure-class law (F-O10) decides what is salted,
  redacted, or plain, and the preview digest is the honest unit of
  proof either way.

## Backwards Compatibility

Fully additive. Green workflows gain two digest fields on terminal
frames and nothing else. The only new refusal fires when the request
mutates between resolution and dispatch — which was always either a
bug or an attack; no honest workflow depends on it. `infer`/`agent`
steps are untouched.

## Reference Implementation

- The engine lane (`feat/f-p6-preview-commit`): the canonical request
  materialization, the preview digest at resolution, the recompute at
  both dispatch fire points (`exec` spawn · `invoke` run), the
  fail-closed divergence refusal (`NIKA-SEC-011`) with its receipt
  finding, the additive digest fields on terminal frames, and the
  fixtures — the honest step green end to end, the one-bit argv mutation
  refused, the zero-argument tool whose context alone mutates refused.

## Deferred

- The signed preview artefact for previews that cross a trust boundary
  (the human-approval rendering of NEP-0013 · a remote policy engine):
  the digest then rides the ticket's signature chain.
- The canon `LAW-*` mint for the preview-commit relation (the
  divergence code rides `law_ids: []` until the freeze batch names the
  law).
- Multiparty preview (a plan previewed on one machine, committed on
  another) — rides F-P7's attested channel.

## Rejected alternatives

- **An LLM judge between preview and commit** — the binding is equality
  of bytes; a model layer is not a boundary (the impossibility anchor).
- **Binding `infer`/`agent` as effect commits** — they are not sinks;
  the certificate already bounds them; a digest there buys nothing and
  bends the semantics.
- **Intra-process HMAC (`k_bind`)** — no second party exists inside the
  engine; false cryptographic solemnity. The domain-separated blake3
  discipline (`proof/ir.rs`) already owns this.
- **Re-hashing the source YAML** — the digest binds the rendered
  canonical request, never the source text: identity is semantic
  (spec 15), and two textually different sources of one plan must
  preview identically.
- **Refusal without recovery** — a bare deny kills utility (SecureClaw
  measures the recovery path as the difference between 70% and 86%
  task utility at 0% attack success); the recovery is templates, never
  a model rewriting the request to make it pass.

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
