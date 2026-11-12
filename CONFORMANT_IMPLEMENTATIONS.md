# Conformant implementations

> Registry of engines that pass the [conformance suite](conformance/runner-protocol.md).
> A row is added (or upgraded) only with a verifiable run of the suite at a
> pinned spec commit · per [spec/07-conformance.md](spec/07-conformance.md)
> §Claiming conformance. The claim string is « **Nika v1 Conformant —
> <Level> (spec <commit>)** » · one form everywhere.
> SPDX-License-Identifier: Apache-2.0

| Implementation | Language | Core | Runtime | Stdlib | Spec commit | Verified |
|---|---|---|---|---|---|---|
| [nika](https://github.com/supernovae-st/nika) (reference engine · **0.124.4**, the current release) | Rust | ⚠️ **277/278** core fixtures by command (`NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep **453/460**: core 277/278 · deep 50/50 · stdlib 109/115 · values 10/10 · types 4/4 · gates 3/3). The one core red: `core/envelope/055-secret-source-vault-withdrawn-refused`, a `source: vault` secret the engine still admits after 01 withdrew it | ⚠️ **126/135 measured agree** · 9 diverge · 0 engine errors (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run, trace and access doors). All nine are `runtime/access-harness` fixtures on staged routes. `003 · 004 · 006 · 013 · 020` run an `agent:` task on the scripted codex-acp seat. The engine runs an agent task on that seat only in its measured asking mode, `read-only`, which the fixtures' route world cannot offer, so it refuses with `NIKA-1805` before the first prompt (0.124.3 gives the same five; `020` declares no service tier and meets the same refusal). `018 · 019 · 022` declare a service tier the staged session offers. The engine applies a tier on that seat only at the release where it measured the seat's speed control, codex-acp 1.13.1; the scripted seat answers as release 0.16.2, so it refuses with `NIKA-1805` before the first prompt. `027` declares a tier on the `openai` API route and expects `NIKA-1800` at admission; the engine refuses the staged plain-HTTP endpoint earlier, at its unknown-cost admission, with no code. 46 of the 181 behavioral fixtures are UNSUPPORTED by this runner (no qualified adapter yet), named and never counted as passes | ⚠️ static surface **109/115**: `stdlib/001` and `stdlib/providers/001 · 002 · 006` (a bare `NIKA-PROVIDER` code with no number, which the runner's matching rule cannot match to the expected namespace; 006 is also refused with `NIKA-AUTH-006`: its agent names `nika:read`, which no `permits.tools` grants), `stdlib/hash/002 · 003` (the signing arguments of `nika:hash`, spec-ahead of this engine, refused with `NIKA-BUILTIN-001`: `key` and `op` in 002, `op`, `public_key` and `signature` in 003; 002 is also refused with `NIKA-SEC-006`: its secret key reaches `nika:hash` with no `egress:` sanction, which [01 §egress](spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification) refuses, so that cause is the fixture's) · lints **7/7** at the only door + 25 NO-DOOR (`NIKA_BIN=… python3 scripts/lints-differential.py`) | `66dbdd6` | 2026-11-12 |
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.124.3 · superseded by the row above) | Rust | ⚠️ **277/278** core fixtures by command (`NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep **453/460**: core 277/278 · deep 50/50 · stdlib 109/115 · values 10/10 · types 4/4 · gates 3/3). The one core red: `core/envelope/055-secret-source-vault-withdrawn-refused`, a `source: vault` secret the engine still admits after 01 withdrew it | ⚠️ **126/135 measured agree** · 9 diverge · 0 engine errors (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run, trace and access doors). All nine are `runtime/access-harness` fixtures on staged routes. `003 · 004 · 006 · 013 · 020` run an `agent:` task on the scripted codex-acp seat. The engine runs an agent task on that seat only in its measured asking mode, `read-only`, which the fixtures' route world cannot offer, so it refuses with `NIKA-1805` before the first prompt (0.124.2 gives the same five; `020` declares no service tier and meets the same refusal). `018 · 019 · 022` declare a service tier the staged session offers. The engine applies a tier on that seat only at the release where it measured the seat's speed control, codex-acp 1.13.1; the scripted seat answers as release 0.16.2, so it refuses with `NIKA-1805` before the first prompt. `027` declares a tier on the `openai` API route and expects `NIKA-1800` at admission; the engine refuses the staged plain-HTTP endpoint earlier, at its unknown-cost admission, with no code. 46 of the 181 behavioral fixtures are UNSUPPORTED by this runner (no qualified adapter yet), named and never counted as passes | ⚠️ static surface **109/115**: `stdlib/001` and `stdlib/providers/001 · 002 · 006` (a bare `NIKA-PROVIDER` code with no number, which the runner's matching rule cannot match to the expected namespace; 006 is also refused with `NIKA-AUTH-006`: its agent names `nika:read`, which no `permits.tools` grants), `stdlib/hash/002 · 003` (the signing arguments of `nika:hash`, spec-ahead of this engine, refused with `NIKA-BUILTIN-001`: `key` and `op` in 002, `op`, `public_key` and `signature` in 003; 002 is also refused with `NIKA-SEC-006`: its secret key reaches `nika:hash` with no `egress:` sanction, which [01 §egress](spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification) refuses, so that cause is the fixture's) · lints **7/7** at the only door + 25 NO-DOOR (`NIKA_BIN=… python3 scripts/lints-differential.py`) | `5a579bc` | 2026-11-10 |
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.124.2 · superseded by the row above) | Rust | ⚠️ **277/278** core fixtures by command (`NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep **453/460**: core 277/278 · deep 50/50 · stdlib 109/115 · values 10/10 · types 4/4 · gates 3/3). The one core red: `core/envelope/055-secret-source-vault-withdrawn-refused`, a `source: vault` secret the engine still admits after 01 withdrew it | ⚠️ **126/135 measured agree** · 9 diverge · 0 engine errors (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run, trace and access doors). All nine are `runtime/access-harness` fixtures on staged routes. `003 · 004 · 006 · 013 · 020` run an `agent:` task on the scripted codex-acp seat. The engine runs an agent task on that seat only in its measured asking mode, `read-only`, which the fixtures' route world cannot offer, so it refuses with `NIKA-1805` before the first prompt (0.124.1 gives the same first four; `020` declares no service tier and meets the same refusal). `018 · 019 · 022` declare a service tier the staged session offers. The engine applies a tier on that seat only at the release where it measured the seat's speed control, codex-acp 1.13.1; the scripted seat answers as release 0.16.2, so it refuses with `NIKA-1805` before the first prompt. `027` declares a tier on the `openai` API route and expects `NIKA-1800` at admission; the engine refuses the staged plain-HTTP endpoint earlier, at its unknown-cost admission, with no code. 46 of the 181 behavioral fixtures are UNSUPPORTED by this runner (no qualified adapter yet), named and never counted as passes | ⚠️ static surface **109/115**: `stdlib/001` and `stdlib/providers/001 · 002 · 006` (a bare `NIKA-PROVIDER` code with no number, which the runner's matching rule cannot match to the expected namespace; 006 is also refused with `NIKA-AUTH-006`: its agent names `nika:read`, which no `permits.tools` grants), `stdlib/hash/002 · 003` (the signing arguments of `nika:hash`, spec-ahead of this engine, refused with `NIKA-BUILTIN-001`: `key` and `op` in 002, `op`, `public_key` and `signature` in 003; 002 is also refused with `NIKA-SEC-006`: its secret key reaches `nika:hash` with no `egress:` sanction, which [01 §egress](spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification) refuses, so that cause is the fixture's) · lints **7/7** at the only door + 25 NO-DOOR (`NIKA_BIN=… python3 scripts/lints-differential.py`) | `b4c692f` | 2026-11-10 |
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.124.1 · superseded by the row above) | Rust | ⚠️ **267/268** core fixtures by command (`NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep **443/450**: core 267/268 · deep 50/50 · stdlib 109/115 · values 10/10 · types 4/4 · gates 3/3). The one core red: `core/envelope/055-secret-source-vault-withdrawn-refused`, a `source: vault` secret the engine still admits after 01 withdrew it | ⚠️ **121/125 measured agree** · 4 diverge · 0 engine errors (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run, trace and access doors). The 4 that diverge, `runtime/access-harness/003 · 004 · 006 · 013`, run an `agent:` task on the scripted codex-acp seat. The engine runs an agent task on that seat only in its measured asking mode, `read-only`, which the fixtures' route world cannot offer, so it refuses with `NIKA-1805` before the first prompt (0.124.0 gives the same four). 46 of the 171 behavioral fixtures are UNSUPPORTED by this runner (no qualified adapter yet), named and never counted as passes | ⚠️ static surface **109/115**: `stdlib/001` and `stdlib/providers/001 · 002 · 006` (a bare `NIKA-PROVIDER` code with no number, which the runner's matching rule cannot match to the expected namespace; 006 is also refused with `NIKA-AUTH-006`: its agent names `nika:read`, which no `permits.tools` grants), `stdlib/hash/002 · 003` (the signing arguments of `nika:hash`, spec-ahead of this engine, refused with `NIKA-BUILTIN-001`: `key` and `op` in 002, `op`, `public_key` and `signature` in 003; 002 is also refused with `NIKA-SEC-006`: its secret key reaches `nika:hash` with no `egress:` sanction, which [01 §egress](spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification) refuses, so that cause is the fixture's) · lints **7/7** at the only door + 25 NO-DOOR (`NIKA_BIN=… python3 scripts/lints-differential.py`) | `5cd95cd` | 2026-10-28 |
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.124.0 · superseded by the row above) | Rust | ⚠️ **267/268** core fixtures by command (`NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep **443/450**: core 267/268 · deep 50/50 · stdlib 109/115 · values 10/10 · types 4/4 · gates 3/3). The one core red: `core/envelope/055-secret-source-vault-withdrawn-refused`, a `source: vault` secret the engine still admits after 01 withdrew it | ⚠️ **121/125 measured agree** · 4 diverge · 0 engine errors (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run, trace and access doors). The 4 that diverge, `runtime/access-harness/003 · 004 · 006 · 013`, run an `agent:` task on the scripted codex-acp seat. The engine runs an agent task on that seat only in its measured asking mode, `read-only`, which the fixtures' route world cannot offer, so it refuses with `NIKA-1805` before the first prompt (0.123.2 gives the same four). 46 of the 171 behavioral fixtures are UNSUPPORTED by this runner (no qualified adapter yet), named and never counted as passes | ⚠️ static surface **109/115**: `stdlib/001` and `stdlib/providers/001 · 002 · 006` (a bare `NIKA-PROVIDER` code with no number, which the runner's matching rule cannot match to the expected namespace; 006 is also refused with `NIKA-AUTH-006`: its agent names `nika:read`, which no `permits.tools` grants), `stdlib/hash/002 · 003` (the signing arguments of `nika:hash`, spec-ahead of this engine, refused with `NIKA-BUILTIN-001`: `key` and `op` in 002, `op`, `public_key` and `signature` in 003; 002 is also refused with `NIKA-SEC-006`: its secret key reaches `nika:hash` with no `egress:` sanction, which [01 §egress](spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification) refuses, so that cause is the fixture's) · lints **7/7** at the only door + 25 NO-DOOR (`NIKA_BIN=… python3 scripts/lints-differential.py`) | `5cd95cd` | 2026-10-27 |
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.123.0, the open-source reference release · superseded by the row above) | Rust | ⚠️ **247/248** core fixtures by command (`NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep **414/421**: core 247/248 · deep 50/50 · stdlib 100/106 · values 10/10 · types 4/4 · gates 3/3). The one core red: `core/envelope/055-secret-source-vault-withdrawn-refused`, a `source: vault` secret the engine still admits after 01 withdrew it | **124/124 measured agree** · 0 diverge · 0 engine errors (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run, trace and access doors); 46 of the 170 behavioral fixtures are UNSUPPORTED by this runner (no qualified adapter yet), named and never counted as passes | ⚠️ static surface **100/106**: `stdlib/001` and `stdlib/providers/001 · 002 · 006` (a bare `NIKA-PROVIDER` code with no number, which the runner's matching rule cannot match to the expected namespace), `stdlib/hash/002 · 003` (the signing arguments of `nika:hash`, spec-ahead of this engine, refused with `NIKA-BUILTIN-001`: `key` and `op` in 002, `op`, `public_key` and `signature` in 003; 002 is also refused with `NIKA-SEC-006`: its secret key reaches `nika:hash` with no `egress:` sanction, which [01 §egress](spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification) refuses, so that cause is the fixture's) · lints **7/7** at the only door + 25 NO-DOOR (`NIKA_BIN=… python3 scripts/lints-differential.py`) | `6390b08` | 2026-10-24 |
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.106.1 · superseded by the row above) | Rust | ✅ **131/131** core fixtures — BY COMMAND, never linkage (the Bowtie adapter · `NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep 213/217, every remaining divergence a NAMED engine owe: the codeless rungs [nika#761](https://github.com/supernovae-st/nika/issues/761)) | ✅ **56/56** behavioral fixtures by command (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run + trace doors) | ✅ static surface 28/32 (the 4 reds are the [#761](https://github.com/supernovae-st/nika/issues/761) codeless MODELS rung) · lints 4/4 at the only door + 25 NO-DOOR ([#763](https://github.com/supernovae-st/nika/issues/763)) · behavioral half pending | `63a6295` | 2026-07-30 |

The 0.124.4 row was replayed with the released binary (`nika 0.124.4
(9753cf41b)`, the macOS arm64 archive of the v0.124.4 release, checked
against its `SHA256SUMS`) on fixtures at `66dbdd6`, the commit engine
0.124.4 embeds (its `SPEC_PIN`). Two runs from fresh checkouts gave
identical verdicts: the static sweep, the runtime and lints
differentials, and `conformance/run.sh nika` (91 PASS · 10 DRIFT ·
0 DIVERGENT · 5 BUG, the files and codes named below). `66dbdd6` changes
no fixture, schema or example of `5a579bc`, the tree 0.124.3 was
measured on: it records that release in the prose. The released 0.124.3
binary, run the same way on the same tree, gives the verdict of 0.124.4
on every fixture, line for line in the four logs, and those are the
verdicts of the 0.124.3 row. What 0.124.4 adds, a standing cost rule an
operator gives `nika serve` at startup (`--cost-policy`), is engine API
outside the language, and no fixture exercises it. 0.124.4 earns no
level claim at that commit, for the reasons given for 0.124.0.

The 0.124.3 row was replayed with the released binary (`nika 0.124.3
(7cc1384b5)`, the macOS arm64 archive of the v0.124.3 release, checked
against its `SHA256SUMS`) on fixtures at `5a579bc`, the commit engine
0.124.3 embeds (its `SPEC_PIN`). Two runs from fresh checkouts gave
identical verdicts: the static sweep, the runtime and lints
differentials, and `conformance/run.sh nika` (91 PASS · 10 DRIFT ·
0 DIVERGENT · 5 BUG, the files and codes named below). `5a579bc` changes
no fixture, schema or example of `b4c692f`, the tree 0.124.2 was
measured on: it records that release in the prose. On every fixture
0.124.3 gives the verdict of the 0.124.2 row, line for line in the four
logs. What 0.124.3 adds, a `nika serve` route that reads what a
workflow's declared ACP route offers, is engine API outside the
language, and no fixture exercises it. 0.124.3 earns no level claim at
that commit, for the reasons given for 0.124.0.

The 0.124.2 row was replayed with the released binary (`nika 0.124.2
(47f277883)`, the macOS arm64 archive of the v0.124.2 release, checked
against its `SHA256SUMS`) on fixtures at `b4c692f`, the commit engine
0.124.2 embeds (its `SPEC_PIN`). Two runs from fresh checkouts gave
identical verdicts: the static sweep, the runtime and lints
differentials, and `conformance/run.sh nika` (91 PASS · 10 DRIFT ·
0 DIVERGENT · 5 BUG, the files and codes named below). `b4c692f` adds
ten static and ten behavioral fixtures for `run.access.service_tier` to
the tree 0.124.1 was measured on. 0.124.2 passes the ten static ones.
Of the ten behavioral ones, `runtime/access-harness/018` to `027`, five
agree and five diverge, for the causes the row names. The five that
agree, `021` and `023` to `026`, each expect a refusal before the first
prompt and get one with the expected code, `NIKA-1805`. On this scripted
seat the engine gives its release binding as the reason in all five, so
they show that nothing is sent; they do not exercise the cause each
fixture stages. The released 0.124.1 binary, run the same way on the
same tree, gives the same verdict as 0.124.2 on each of the 171
behavioral fixtures the two trees share and the same
`conformance/run.sh` result. It refuses `run.access.service_tier` as an
unknown key (`NIKA-PARSE-005`), so it passes 272 of the 278 core
fixtures there and diverges on all ten new behavioral ones. 0.124.2
earns no level claim at that commit, for the reasons given for 0.124.0.

The 0.124.1 row was replayed with the released binary (`nika 0.124.1
(bec4f5271)`, the macOS arm64 archive of the v0.124.1 release, checked
against its `SHA256SUMS`) on fixtures at `5cd95cd`, the commit engine
0.124.1 embeds (its `SPEC_PIN`), as 0.124.0 does. Two runs from fresh
checkouts gave identical verdicts, and the released 0.124.0 binary, run
the same way, gives the same verdicts and codes fixture by fixture: the
static sweep, the runtime and lints differentials, and
`conformance/run.sh nika` (91 PASS · 10 DRIFT · 0 DIVERGENT · 5 BUG, the
files and codes named below). It earns no level claim at that commit, for
the reasons given for 0.124.0.

The 0.124.0 row was replayed with the released binary (`nika 0.124.0
(866ed914b)`, the macOS arm64 archive of the v0.124.0 release) on
fixtures at `5cd95cd`, the commit engine 0.124.0 embeds (its
`SPEC_PIN`). It earns no level claim at that commit: Core has one red,
the Runtime and Stdlib v0.1 levels include Core
([07 §Level 2](spec/07-conformance.md#level-2--runtime-conformance)),
and four behavioral fixtures diverge. Every red is named above.

`conformance/run.sh nika` over its 106-file corpus at `5cd95cd` (macOS
arm64) gives 91 PASS · 10 DRIFT · 0 DIVERGENT · 5 BUG. The ten DRIFTs
and the five divergences to triage are the files named for 0.123.0
below, and each DRIFT reports the same codes.
`envelope/trifecta-human-gate-dominates`, a BUG at `6390b08`, is
repaired at this commit and passes.

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
where the file expects `NIKA-EXEC-001`). Four files are refused at check
by the reference oracle as well, before anything runs. Three use shapes
the language no longer accepts: `verbs/timeout-per-iteration` sets
`fail_fast` on the task instead of inside `for_each:` (`NIKA-PARSE-005`),
and `dag/foreach-fail-fast-false` and `dag/foreach-fail-fast-true` run
`exec:` with no `permits:` block (`NIKA-AUTH-006`) over a `const.items`
written as a typed declaration, an object where `for_each` needs an array
(the engine adds `NIKA-VAR-006`). Their bodies lag the spec, not their
expected-result headers, and the exec sandbox plays no part: they can be
repaired statically on any platform. The fourth,
`envelope/trifecta-human-gate-dominates`, broke the consent law
(`NIKA-SEC-014`) and is repaired after the pin. Five remain divergences to
triage: `dag/foreach-empty-skips`, `dag/when-false-skips`,
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
