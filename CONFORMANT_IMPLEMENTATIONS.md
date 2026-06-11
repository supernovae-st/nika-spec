# Conformant implementations

> Registry of engines that pass the [conformance suite](conformance/runner-protocol.md).
> A row is added (or upgraded) only with a verifiable run of the suite at a
> pinned spec commit · per [spec/07-conformance.md](spec/07-conformance.md)
> §Claiming conformance. SPDX-License-Identifier: Apache-2.0.

| Implementation | Language | Core | Runtime | Stdlib | Spec commit | Verified |
|---|---|---|---|---|---|---|
| [nika](https://github.com/supernovae-st/nika) (reference engine) | Rust | ✅ 57/57 core fixtures (`cargo test -p nika-schema --test conformance_core` · the 2026-06-11 hardening gaps closed in [nika#121](https://github.com/supernovae-st/nika/pull/121)) | — (no runtime crates yet) | — | `6c18927` lineage | 2026-06-11 |

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
