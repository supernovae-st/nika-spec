# NEP-0002 · Lethal-trifecta detection with a Rule-of-Two human gate

- **NEP**: 0002 (0001 is the reserved `nika: v1` language surface)
- **Title**: Make the lethal trifecta a static check with a required human gate
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-19
- **Amended**: v2.0 · 2026-07-20 (realized-flow judgment · agent whitelist
  refinement · the infer/agent integrity inversion)

## Abstract

Add a static check that fires when a workflow's declared capability boundary
grants all three legs of the lethal trifecta · private-data access, untrusted-
content ingress, and external egress · without a human gate on the egress path.
It makes the trifecta decidable from the `permits:` block alone and enforces the
Rule of Two (at most two of the three unattended) as a check, not a guideline.

## Motivation

The lethal trifecta (Willison) and the Agents Rule of Two (Meta) are the two
dominant 2026 heuristics for agent safety, but today they live in prose and
human vigilance. Because a Nika workflow declares its private reads (`fs.read`),
its untrusted-content tools (`tools:` / `nika:fetch`) and its egress (`net.http`
/ workspace-escaping `fs.write` / `exec`) explicitly and up front, the
composition is a decidable property of a file a human already reviews. No other
runtime can compute it, precisely because no other runtime carries the
capability boundary as authored source. This is a security feature and the
sharpest one-line statement of the language's thesis: the trifecta becomes a
check.

## Specification

Legs, read off the declared boundary:

- **① private-data**: `permits.fs.read` is non-empty. (v2 refinement: a
  sensitivity classification over read paths; v1 treats any declared read as ①.)
- **② untrusted ingress (amended v2.0)**: the boundary grants an ingress-capable
  tool AND the task graph **realizes** untrusted content — a `nika:fetch`
  builtin **invoked** (a glob like `nika:*` covers the grant), an `mcp:*` tool
  invoked (server-provided content is untrusted by construction; the catalog
  `content_trust` mark is the follow-on refinement, absent = untrusted), or an
  `agent:` whose `tools:` whitelist admits an ingress-capable tool (a browsing
  agent's final message is attacker-influenced even with a statically clean
  prompt). First-party LOCAL builtins (`nika:read` · `nika:write` · …) are NOT
  ingress: a private read is ①'s domain, a write ③'s. Untrusted content
  **propagates** through `with:` bindings, `for_each` items, `tasks.*.output`
  reads, and `on_error.recover` reads; **`infer:`/`agent:` outputs carry it when
  their prompt sees it** — the integrity direction, where the "model output is
  not a verbatim echo" carve-out (confidentiality-only) does not apply: a
  summary of an attacker's page carries the attacker's payload. An `exec:` task
  is content-tainted when it has a tainted data ancestor OR (`fs.read` non-empty
  ∧ a tainted task **capable of writing** — an fs-write builtin or another exec —
  ran earlier in the run order): the filesystem-mediated flow a static argv scan
  cannot see. (v1.1 note: the coarse any-grant reading flagged the spec's own
  permits-fit fixture `deep/014-permits-fit-valid` — `tools: [nika:read,
  nika:write]` declares no ingress.)
- **③ external egress**: `permits.net.http` is non-empty, OR a `permits.fs.write`
  glob escapes the declared workspace, OR `permits.exec` is enabled.

Rule (amended v2.0): if ①∧②∧③ hold, the check emits **`NIKA-SEC-009`** for
every **egress-capable task whose effect surface the untrusted content reaches**
(a realized flow · the finding names its witness `source → sink`), UNLESS a
blocking `invoke: nika:prompt` human gate (no `default:` arg) dominates it
(Rule of Two: with a gate, the third leg is a human decision, not an autonomous
capability). An `agent:` task is egress-capable iff its whitelist admits an
egress-effecting tool (per the one effect table; `mcp:*` fail-closed) — a
pure-compute whitelist is not egress. (SEC-008 is reserved by the AUTH plane —
`canon/laws/authority.yaml` FINDING-AUTH-02 allocates `NIKA-AUTH-001..005` +
`NIKA-SEC-008` — so the trifecta takes the next free id. One gate mitigates
every task it dominates; the gate runs once per run.)

Severity: a finding at check time (exit code 2 · CI-gating). The only escape is
the human gate task · never a suppression flag · so the enforced invariant is
structural. The check reads only the static `permits:` block and the DAG: no
model call, no runtime state, fully reproducible (consistent with the rest of
the check ladder).

## Conformance test

New fixtures under `conformance/security/`, each with its expected verdict, join
the Core suite: `trifecta-complete-refuse` (all three legs, no gate → the
diagnostic) · `trifecta-gated-pass` (a gate dominates the egress path → clean) ·
three `two-of-three-pass` cases (drop each leg → clean) ·
`gate-present-not-dominating-refuse` (a gate that does not guard the egress path
→ the diagnostic). v2.0 adds: `trifecta-granted-not-invoked-pass` (the grant
realizes nothing → clean) · `trifecta-flow-through-infer-refuse` (a model
summary carries the payload) · `trifecta-recovery-read-refuse` ·
`trifecta-exec-opacity-refuse` (the file-mediated channel) ·
`trifecta-parallel-clean-egress-pass` · `trifecta-pure-agent-pass` ·
`trifecta-ingress-agent-refuse` · `trifecta-gate-once-dominates-pass`. A
Standards Track NEP does not leave Discussion without these.

## Compatibility impact

None for workflows that already grant at most two of the three legs unattended,
or that already gate egress · surfaces checked: `permits.{fs,net,exec,tools}`,
the `nika:prompt` gate, the DAG dominance relation. The change is a NEW finding
on workflows that were already granting all three legs with no human in the
loop; those were the workflows the heuristic warns about.

**v2.0**: v2.0 findings are a strict subset of v1.1 findings — every v2.0
finding is a realized flow v1.1 already flagged. No previously-refused workflow
needs changes; workflows flagged under v1.1 solely by granted-but-never-invoked
ingress (or by egress tasks no untrusted content reaches) become clean.
Previously-passing workflows are unaffected in both directions (a gate that
dominated still dominates; a narrowed permit still drops a leg).

## Migration plan

Additive: no existing valid workflow changes shape. A workflow newly flagged
adds one `invoke: nika:prompt` gate on the egress path (or narrows a permit to
drop a leg). `nika check` teaches the fix in the finding.

## Rejected alternatives

- **A denylist of dangerous tool/host combinations** · rejected. The CVE record
  (e.g. a command denylist bypassed by obfuscation) is exactly why the boundary
  is computed over the GRANTED set (an allowlist) instead of enumerating bad
  ones. The trifecta check is an allowlist-native property.
- **A learned / heuristic risk score** · rejected. The point is total
  interpretability: the finding must be explainable by pointing at three lines
  of the file. A score is neither reproducible nor reviewable.
- **A warning instead of an error** · rejected as the default. The "compile
  error" framing is the contribution; a warning is ignorable and does not enforce
  the Rule of Two. (Open for Discussion: an opt-in `--warn` mode for adoption.)
- **Read-path sensitivity as a ① refinement** (v2.0) · rejected: classifying
  `fs.read` globs (ordinary vs. sensitive) is a false-negative factory —
  `./data/**` IS private in every threat model that matters, and a
  "non-sensitive" verdict tells an attacker exactly which directory to target.
- **Sandbox-dependent exec refinement** (v2.0) · rejected: an `exec:` allowlist
  is egress on every platform; a static check whose verdict depends on the host
  OS is not a check, it is a horoscope (the NEP's own reproducibility clause).
- **Informed gate placement** (the gate must sit between source and sink) ·
  deferred with a trigger condition: consent-before-fetch is still consent;
  when a runtime prompt UX renders the pending egress payload, placement
  becomes enforceable value.
- **Private-read taint (the dual lattice)** · deferred: the exec-opacity hole
  makes sink-level ① unsound-to-honest; boundary-level ① is the right static
  grain. Revisit with v2.0 field data.
- **Exec stdout as an ingress source** · rejected: operator-program output;
  arming ② on it makes every exec pipeline trifecta-armed.
