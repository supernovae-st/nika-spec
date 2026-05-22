# Schemas · machine-readable JSON Schemas

> JSON Schemas for the Nika workflow language · consumable by tools
> like `yaml-language-server` (VS Code · Cursor · etc.) for autocompletion
> and validation in editors.

---

## Status · DRAFT v0.1.0-draft

The schemas are **derived from the prose spec** (see `../spec/`). They
will be generated mechanically once the prose spec is finalized · for
v0.1.0 GA they will ship in this directory.

## Planned files

```
schemas/
├── workflow.schema.json         # the envelope + tasks structure
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
workflow: my-workflow
...
```

Editors with `yaml-language-server` integration will provide autocomplete,
inline documentation, and validation against the schema.

## Generation

The schemas will be generated from the reference engine's `nika-schema`
crate (Rust types annotated with `schemars`). This guarantees the schemas
match the engine's parser exactly.

---

🦋 *Schemas pending · v0.1.0 GA target.*
