# Schemas · machine-readable JSON Schemas

> JSON Schemas for the Nika workflow language · consumable by tools
> like `yaml-language-server` (VS Code · Cursor · etc.) for autocompletion
> and validation in editors.

---

## Status · `workflow.schema.json` SHIPPED (interim · hand-derived) · rest pending

`workflow.schema.json` is **shipped** — a complete Draft 2020-12 structural
contract for the v1 envelope + the 4 verbs (inlined as `$defs`), **hand-derived
from the prose spec** and proven against the example suite: all 7 foundation
examples validate, and a negative control (`nika: v1.0` + bad id + two-verb
task) is correctly rejected. This is the **Phase L1 authorability** lever: an
LLM can validate its own generated Nika against this schema, and editors with
`yaml-language-server` get autocomplete + inline errors today.

It is marked **interim** (`$comment` in the file): the prose spec is the single
source of truth, and at engine GA the mechanically-generated `nika-schema`
(schemars) output supersedes this hand-derived file — both derive from the same
prose source and are diffed against it.

The remaining per-verb + stdlib-enum schemas below are pending (the single
`workflow.schema.json` already inlines the verb shapes via `$defs`, so it is
self-contained for editor use).

## Files

```
schemas/
├── workflow.schema.json         ✅ envelope + tasks + 4 verbs ($defs) · 7 examples ⊨ · negative-control verified
├── verb-infer.schema.json       # infer: action shape
├── verb-exec.schema.json        # exec: action shape
├── verb-fetch.schema.json       # fetch: action shape
├── verb-invoke.schema.json      # invoke: action shape
├── verb-agent.schema.json       # agent: action shape
├── stdlib-providers.schema.json # providers v0.1 enum
├── stdlib-builtins.schema.json  # builtins v0.1 enum
└── stdlib-extract-modes.schema.json
```

## How to use (planned)

```yaml
# yaml-language-server: $schema=https://nika.sh/spec/v1/workflow.schema.json
nika: v1
workflow:
  id: my-workflow
...
```

Editors with `yaml-language-server` integration will provide autocomplete,
inline documentation, and validation against the schema.

## Generation

The schemas will be generated from the reference engine's `nika-schema`
crate (Rust types annotated with `schemars`). This guarantees the schemas
match the engine's parser exactly.

---

🦋 *workflow.schema.json shipped (interim · hand-derived · 7 examples ⊨) · per-verb + stdlib enums pending · v0.1.0 GA.*
