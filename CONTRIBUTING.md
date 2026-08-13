# Contributing to the Nika spec

Thanks for wanting to improve the standard. This project follows the
[Contributor Covenant](./CODE_OF_CONDUCT.md). Two doors, depending on
what you are changing:

## Normative changes → a PR against `spec/`, until the v1 pre-freeze

Anything that changes the language surface, the stdlib contract, the
conformance suite's meaning, or the trace formats is a **normative**
change. Until the language is pre-frozen at v1 it goes through a plain
PR that edits [`spec/`](./spec/) directly, with its conformance fixtures
in the same PR — a proposal process only has meaning against something
frozen, and this draft is not.

At the pre-freeze that flips: every normative change becomes a **NEP**
(Nika Enhancement Proposal) and nobody amends the standard directly, the
maintainers included. The door is already built and waiting —
[governance/NEP-0000](./governance/nep-0000-the-nep-process.md) carries
the process and [the template](./governance/nep-template.md) the shape.
[governance/README.md](./governance/README.md) records the twenty
proposals folded into the draft on 2026-08-14, and where each law lives
now.

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

## Developer Certificate of Origin

Every PR commit carries a `Signed-off-by` trailer matching the commit
author ([DCO 1.1](https://developercertificate.org) — the lightweight
alternative to a CLA: you certify you have the right to submit the
change under this repository's license). `git commit -s` appends it;
repair an existing branch with `git rebase --signoff origin/main` and
force-push. CI enforces it (`.github/workflows/dco.yml`); merge commits
and bot authors are exempt.

## License

The spec is Apache-2.0 with patent grant. By contributing you agree your
contribution is licensed under Apache-2.0
([LICENSE](./LICENSE) · [REUSE.toml](./REUSE.toml)).
