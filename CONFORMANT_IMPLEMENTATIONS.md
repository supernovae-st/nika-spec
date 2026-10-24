# Conformant implementations

> Registry of engines that pass the [conformance suite](conformance/runner-protocol.md).
> A row is added (or upgraded) only with a verifiable run of the suite at a
> pinned spec commit · per [spec/07-conformance.md](spec/07-conformance.md)
> §Claiming conformance. The claim string is « **Nika v1 Conformant —
> <Level> (spec <commit>)** » · one form everywhere.
> SPDX-License-Identifier: Apache-2.0

| Implementation | Language | Core | Runtime | Stdlib | Spec commit | Verified |
|---|---|---|---|---|---|---|
| [nika](https://github.com/supernovae-st/nika) (reference engine · **0.123.0**, the maintained reference release) | Rust | ⚠️ **247/248** core fixtures by command (`NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep **414/421**: core 247/248 · deep 50/50 · stdlib 100/106 · values 10/10 · types 4/4 · gates 3/3). The one core red: `core/envelope/055-secret-source-vault-withdrawn-refused`, a `source: vault` secret the engine still admits after 01 withdrew it | **124/124 measured agree** · 0 diverge · 0 engine errors (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run, trace and access doors); 46 of the 170 behavioral fixtures are UNSUPPORTED by this runner (no qualified adapter yet), named and never counted as passes | ⚠️ static surface **100/106**: `stdlib/001` and `stdlib/providers/001 · 002 · 006` (a bare `NIKA-PROVIDER` with no category), `stdlib/hash/002 · 003` (the `key` and `op` arguments of `nika:hash` refused with `NIKA-BUILTIN-001`) · lints **7/7** at the only door + 25 NO-DOOR (`NIKA_BIN=… python3 scripts/lints-differential.py`) | `6390b08` | 2026-10-24 |
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.106.1 · superseded by the row above) | Rust | ✅ **131/131** core fixtures — BY COMMAND, never linkage (the Bowtie adapter · `NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep 213/217, every remaining divergence a NAMED engine owe: the codeless rungs [nika#761](https://github.com/supernovae-st/nika/issues/761)) | ✅ **56/56** behavioral fixtures by command (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run + trace doors) | ✅ static surface 28/32 (the 4 reds are the [#761](https://github.com/supernovae-st/nika/issues/761) codeless MODELS rung) · lints 4/4 at the only door + 25 NO-DOOR ([#763](https://github.com/supernovae-st/nika/issues/763)) · behavioral half pending | `63a6295` | 2026-07-30 |

The 0.123.0 row was replayed with the released binary (`nika 0.123.0
(0bfde3765)`) on `main` at `7937fc9`, whose conformance tree is
byte-identical to `6390b08`, the commit engine 0.123.0 embeds (its
`SPEC_PIN`). It earns
no level claim at that commit: Core has one red, and the Runtime and
Stdlib v0.1 levels include Core ([07 §Level 2](spec/07-conformance.md#level-2--runtime-conformance)).
Every red is named above, and the behavior this runner measures agrees.

`conformance/run.sh nika` over its 106-file corpus at `6390b08` (macOS
arm64) gives 90 PASS · 10 DRIFT · 0 DIVERGENT · 6 BUG. Seven DRIFTs come
from the macOS exec sandbox refusing the confined process (`NIKA-SEC-001`
where the file expects `NIKA-EXEC-001`). Four files are refused by the
reference oracle as well, so their headers lag the spec:
`dag/foreach-fail-fast-false`, `dag/foreach-fail-fast-true`,
`verbs/timeout-per-iteration` and `envelope/trifecta-human-gate-dominates`
(repaired after the pin). Five remain divergences to triage:
`dag/foreach-empty-skips`, `dag/when-false-skips`,
`envelope/permits-empty-default-deny`, `envelope/sec-exec-blocklist-rm-rf`
and `verbs/agent-injection-contained`.

## How to be listed

1. Run the suite against your engine: `conformance/run.sh <your-engine>`
   scores every corpus file against the intent its `# Expected:` header
   declares, or `python3 conformance/runner.py run conformance/tests/<level>
   --engine "<adapter>"` drives the declarative fixtures through a small
   adapter (see the [runner protocol](conformance/runner-protocol.md)
   §Third-party mode). There is no built-in `conformance` subcommand to
   call on an engine.
2. Open a PR on [supernovae-st/nika-spec](https://github.com/supernovae-st/nika-spec)
   adding a row · include the spec commit you ran against and a reproducible
   command or CI link.
3. Levels are claimed independently · `Core` alone is a valid claim.

---

🦋 *The suite is the contract · machine-checkable forever.*
