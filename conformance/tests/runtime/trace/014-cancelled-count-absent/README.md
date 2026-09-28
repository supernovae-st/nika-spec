# 014-cancelled-count-absent

Normative source: [§03 fan-out](../../../../../spec/03-dag.md) and
[§17 item observations and paging](../../../../../spec/17-trace.md).

The exact assertion and its rationale are in `expected-verify.json`.
`provenance.json` records the real source trace, engine identity and every
mutation. `clean` describes chain/lifecycle integrity; the separate `items`
assertion judges whether a complete item table is justified.
