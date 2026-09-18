# API input provenance witness

Law: [04 §typed workflow inputs](../../../../../spec/04-variables.md).
This journal was captured on 2026-09-18 from the production execution backend
through authenticated Serve admission, with a pure `nika:jq` workflow.
It is an observed development-engine journal, not a hand-constructed chain.
The source bytes and journal are preserved exactly; the recorded `spec_pin`
is the build’s prior pin, not a claim of qualification at this amendment.

`request.json` records the by-name POST body. Serve `golden.nika.yaml` as
`root.nika.yaml` in an isolated workflow directory, authenticate to the
listener and submit this body to `POST /v1/jobs` with a fresh idempotency
key. No provider, signing key or secret is needed. The expected output
retains the literal `@env:SERVER_SECRET`; it does not read an environment
variable. Supplied fields have `api-caller` origins; the default `region`
has `file` origin. The reference engine’s production regression is
`server::tests::inputs::inputs_reach_real_runtime_with_defaults_literal_strings_and_honest_origins`
in [nika#1642](https://github.com/supernovae-st/nika/issues/1642).

The conformance assertion here is the recorded channel map plus the clean
chain verdict. It does not authenticate the caller or grant any effect.
The differential judge’s negative selftests substitute other channels,
remove origins and supply malformed or duplicated maps; those assertions
must fail even when a chain can be coherently rewritten.
