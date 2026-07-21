# Contributing to the Nika spec

Thanks for wanting to improve the standard. This project follows the
[Contributor Covenant](./CODE_OF_CONDUCT.md). Two doors, depending on
what you are changing:

## Normative changes → a NEP

Anything that changes the language surface, the stdlib contract, the
conformance suite's meaning, or the trace formats goes through a **NEP**
(Nika Enhancement Proposal). Start at
[governance/NEP-0000](./governance/nep-0000-the-nep-process.md), copy
[the template](./governance/nep-template.md), open a PR. Nobody amends
the standard directly — the maintainers included.

Not sure it deserves a NEP yet? Ideate first in the engine's
[Ideas discussions](https://github.com/supernovae-st/nika/discussions/categories/ideas) —
the fastest lane to pressure-test a language idea before writing one.

## Everything else → a plain PR

Errata (prose contradicting the corpus), typos, teaching improvements,
new conformance fixtures for already-specified behavior, tooling under
`scripts/` — open a PR directly.

## The bar every PR passes

CI runs the full static gate (`.github/workflows/conformance.yml`):

- `python3 conformance/runner.py all` — every fixture + every example
- the per-domain evaluator selftests (`conformance/*_selftest.py`)
- the SSOT gates (`scripts/ssot-compiler.py --check` + `--check-canon`) —
  `canon.yaml` is a GENERATED projection; never edit it by hand
- the projector checks (canon markers · showcase · llms · starters ·
  authoring · design) — if you touch `README.md` or `spec/*.md`, rerun
  `python3 scripts/llms-projector.py --write`

## Test policy (normative for contributions)

**A change to specified behavior lands with its corpus case.** Every
normative sentence is traceable to at least one conformance fixture and
every fixture cites the prose it enforces — a PR that changes behavior
without touching the corpus does not merge. New major functionality in
the tooling ships with tests in the same PR.

## Style

- BCP-14 keywords (MUST/SHOULD/MAY) only in their normative sense.
- Counts are never hand-written in prose — cite `canon.yaml` or use a
  `<!-- canon:KEY -->N<!-- /canon -->` marker the projector maintains.
- One concept, one word — see [GLOSSARY.md](./GLOSSARY.md); qualify
  ambiguous terms at first mention (« MCP oracle » · « conformance
  oracle » · « human gate »).
- Workflow files are named `<name>.nika.yaml`
  ([01 §File naming](./spec/01-envelope.md#file-naming-normative)).

## License

The spec is Apache-2.0 with patent grant. By contributing you agree your
contribution is licensed under Apache-2.0
([LICENSE](./LICENSE) · [REUSE.toml](./REUSE.toml)).
