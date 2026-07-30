# Conformant implementations

> Registry of engines that pass the [conformance suite](conformance/runner-protocol.md).
> A row is added (or upgraded) only with a verifiable run of the suite at a
> pinned spec commit · per [spec/07-conformance.md](spec/07-conformance.md)
> §Claiming conformance. The claim string is « **Nika v1 Conformant —
> <Level> (spec <commit>)** » · one form everywhere.
> SPDX-License-Identifier: Apache-2.0

| Implementation | Language | Core | Runtime | Stdlib | Spec commit | Verified |
|---|---|---|---|---|---|---|
| [nika](https://github.com/supernovae-st/nika) (reference engine · 0.106.1) | Rust | ✅ **131/131** core fixtures — BY COMMAND, never linkage (the Bowtie adapter · `NIKA_BIN=… sh scripts/parity-sweep.sh` · full static sweep 213/217, every remaining divergence a NAMED engine owe: the codeless rungs [nika#761](https://github.com/supernovae-st/nika/issues/761)) | ✅ **56/56** behavioral fixtures by command (`NIKA_BIN=… python3 scripts/runtime-differential.py` · the run + trace doors) | ✅ static surface 28/32 (the 4 reds are the [#761](https://github.com/supernovae-st/nika/issues/761) codeless MODELS rung) · lints 4/4 at the only door + 25 NO-DOOR ([#763](https://github.com/supernovae-st/nika/issues/763)) · behavioral half pending | `63a6295` | 2026-07-30 |

## How to be listed

1. Run the suite against your engine ·
   `<engine> conformance run conformance/tests/<level>` (or validate each
   fixture per the [runner protocol](conformance/runner-protocol.md)).
2. Open a PR on [supernovae-st/nika-spec](https://github.com/supernovae-st/nika-spec)
   adding a row · include the spec commit you ran against and a reproducible
   command or CI link.
3. Levels are claimed independently · `Core` alone is a valid claim.

---

🦋 *The suite is the contract · machine-checkable forever.*
