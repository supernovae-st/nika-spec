# conformance/redteam/ · the adaptive jam's seeded corpus

> F-P10 (NEP-0014 à venir) · chaque fixture de ce répertoire est taguée
> `# SAF-T<NNNN>` et prouve qu'une technique d'attaque nommée meurt
> contre un gate DÉTERMINISTE (jamais un juge-LLM · ancre 2605.17634).
> La couverture est GÉNÉRÉE (`coverage-saf-t.tsv` · `scripts/gen-saf-t-coverage.py`
> · jamais hand-éditée) · une technique in-scope sans fixture NI bench
> NI hors-scope déclaré = FAIL du gate de couverture.

## The tags (SAFE-MCP attack taxonomy)

| tag | the attack class | the gate that kills it | fixture |
|---|---|---|---|
| SAF-T1001 | task/prompt injection into a tool argument | F-O1 (NEP-0004 · the taint re-gate) | `saf-t1001-untrusted-host-escape` |
| SAF-T2004 | data-as-code smuggling through a permitted fetch | F-O7 (NEP-0006 · the sink) | `saf-t2004-fetch-pickle-no-door` |
| SAF-T3009 | the encoded-extension composition (decode-then-trim) | F-O7 composition (the final review's own catch) | `saf-t3009-encoded-extension-refused` |

## The rule

A redteam fixture is a hostile workflow: it MUST be refused by the
deterministic gate, and the refusal MUST name the law (the NIKA code in
the header comment). The corpus seeds the metamorphic relation R3 (« the
gate's verdict is invariant under injection in a data position ») and
the defense-aware mutation operators that live beside each gate —
maker ≠ checker, regenerated nightly, zero paid LLM in CI.
