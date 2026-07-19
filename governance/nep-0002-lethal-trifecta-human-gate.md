# NEP-0002 · Lethal-trifecta detection with a Rule-of-Two human gate

- **NEP**: 0002 (0001 is the reserved `nika: v1` language surface)
- **Title**: Make the lethal trifecta a static check with a required human gate
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-19

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
- **② untrusted ingress**: the task graph can pull untrusted content into
  context · a `nika:fetch` builtin, or a tool present in `permits.tools`. (v2:
  per-tool trust marks from the catalog; v1 treats any fetch/tool as ②.)
- **③ external egress**: `permits.net.http` is non-empty, OR a `permits.fs.write`
  glob escapes the declared workspace, OR `permits.exec` is enabled.

Rule: if ①∧②∧③ hold for a path through the DAG, the check emits a new diagnostic
(proposed `NIKA-SEC-008`, next free in the NIKA-SEC family · final id minted at
acceptance) with the message "lethal trifecta complete · human gate required",
UNLESS a blocking `invoke: nika:prompt` human gate dominates every egress-capable
task on that path (Rule of Two: with a gate, the third leg is a human decision,
not an autonomous capability).

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
→ the diagnostic). A Standards Track NEP does not leave Discussion without these.

## Compatibility impact

None for workflows that already grant at most two of the three legs unattended,
or that already gate egress · surfaces checked: `permits.{fs,net,exec,tools}`,
the `nika:prompt` gate, the DAG dominance relation. The change is a NEW finding
on workflows that were already granting all three legs with no human in the
loop; those were the workflows the heuristic warns about.

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
