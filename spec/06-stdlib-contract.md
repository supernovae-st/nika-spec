# 06 · Stdlib contract

> The stdlib is the set of **providers** · **extract modes** · and
> **builtins** that ship with v0.1 conformant engines. The stdlib is
> versioned **independently** from the core language · it may evolve
> while the 5 pillars remain frozen.

---

## What is the stdlib?

```
CORE LANGUAGE                          STDLIB
─────────────                          ──────
envelope                                providers (infer · agent)
5 verbs (signatures only)               extract modes (fetch)
DAG semantics                           builtins (invoke)
variable substitution
error model

Locked forever at v1.                   Versioned · stdlib v0.x · evolves.
```

A workflow that uses **only** the core language is portable across
engines forever. Adding stdlib dependencies (e.g. specific provider names ·
specific builtins) constrains portability to engines that ship those
stdlib elements.

---

## Why split core vs stdlib?

Three reasons ·

1. **Forward compat** · we need to add providers (new LLMs ship every quarter), add builtins, add extract modes. Locking these in the core would mean breaking the language every few months. Splitting lets the core stay frozen.

2. **Optional surface** · an engine may choose not to ship the full stdlib. A minimal engine may support only `mock` provider for testing. A specialized engine may ship only a subset of builtins. The conformance level reflects this (see [07-conformance.md](./07-conformance.md)).

3. **Audience clarity** · the core is the contract between workflow author and engine. The stdlib is the curated library of building blocks an engine ships.

---

## Versioning

The stdlib has **independent versioning** ·

- `stdlib/providers-v0.1.md` — the 8 canonical providers for v0.1
- `stdlib/extract-modes-v0.1.md` — the 9 canonical extract modes for v0.1
- `stdlib/builtins-v0.1.md` — the 36 canonical builtins for v0.1

When the stdlib evolves to v0.2 · those files become `*-v0.2.md` and new versions are published. The core language contract (`nika: v1`) is unchanged.

A workflow MAY declare a stdlib version dependency · though v0.1 does not require this. v0.2 may introduce an optional `stdlib:` field in the envelope.

---

## Inclusion criteria

For an element to enter the stdlib · it MUST satisfy ·

1. **Empirical demand** · documented use in real workflows (canonical examples)
2. **Mature implementation** · battle-tested in at least one engine · bug-stable
3. **Forward-compat safe** · signature stable · no breaking semantic risk
4. **Sovereignty-aligned** · prefers local-first OR multi-vendor (no single-cloud lock-in)

Reference implementation (Diamond Rust engine) provides these elements with quality gates (12-gate admission per ADR-003). Other engines may match this bar.

---

## What's IN stdlib v0.1

### Providers (9)

`anthropic` · `openai` · `mistral` · `groq` · `deepseek` · `gemini` · `xai` · `native` · `mock`

See [stdlib/providers-v0.1.md](../stdlib/providers-v0.1.md).

### Extract modes (9)

`markdown` · `article` · `jsonpath` · `text` · `selector` · `metadata` · `links` · `feed` · `sitemap`

See [stdlib/extract-modes-v0.1.md](../stdlib/extract-modes-v0.1.md).

### Builtins (36)

6 core (sleep · log · emit · assert · prompt · done)
+ 5 file (read · write · edit · glob · grep)
+ 19 data (jq · json_merge · yaml_validate · …)
+ 6 introspection (cost · records · dag_info · task_status · threads · orchestrate)
= **36 canonical builtins** (Stdlib v0.1)
(+ 24 media · pdf_extract · chart · qr_validate · … · **deferred** to stdlib v0.x · NOT in the v0.1 count · per D-2026-05-22-N8)

See [stdlib/builtins-v0.1.md](../stdlib/builtins-v0.1.md).

---

## What's OUT of stdlib v0.1

Deliberately deferred to stdlib v0.x ·

- **24 media builtins** · pdf_extract · svg_render · chart · phash · thumbhash · provenance · etc. (heavy · high maintenance · niche audience)
- **Advanced agent presets** · multi-agent coordination patterns · supervisor/worker · etc.
- **Memory recall builtins** · awaiting Diamond memory subsystem ship (`nika-memory` orchestrator + satellites · v0.5+)
- **Workflow include / import** · single-file workflows in v0.1

When these mature · they enter stdlib v0.x. The core language doesn't need to change.

---

## How a workflow references the stdlib

### Provider

```yaml
provider: anthropic           # references stdlib/providers-v0.1.md
model: claude-3-5-sonnet      # provider-specific
```

### Extract mode

```yaml
fetch:
  url: "https://example.com"
  mode: article               # references stdlib/extract-modes-v0.1.md
```

### Builtin

```yaml
invoke:
  tool: "nika:read"            # nika:* namespace = builtin
  args:
    path: "./config.yaml"
```

---

## How a workflow references non-stdlib tools

For MCP tools (not in the stdlib · provided by external MCP servers) ·

```yaml
invoke:
  tool: "mcp:postgres/query"   # mcp:<server>/<tool> namespace (one colon · slash path)
  args:
    sql: "..."
```

These are not stdlib · they depend on the engine's MCP server registry being configured.

## Namespace ownership · `nika:` · `mcp:` · `x-` (post pantheon 2026-05-22)

The three canonical tool namespaces ·

| Namespace | Owner | Source of truth | Examples |
|---|---|---|---|
| `nika:*` | **Spec-owned** | `stdlib/builtins-v0.1.md` (this directory's sibling) | `nika:read` · `nika:jq` · `nika:done` |
| `mcp:<server>/*` | Engine + user | Engine's MCP server registry config | `mcp:postgres/query` · `mcp:browser/navigate` |
| `x-<vendor>:*` | **Custom · engine-specific** | Engine documentation (OUT of spec) | `x-superclever:research` · `x-myengine:custom_tool` |

The `nika:*` namespace is **spec-owned**. A custom engine MUST NOT add tools to the `nika:*` namespace · it would violate portability (a workflow using a vendor's `nika:custom` builtin would not run on a different engine).

Custom engines that want to ship engine-specific builtins MUST use the `x-<vendor>:*` prefix. Workflows referencing `x-*` tools are explicitly NOT portable across engines · the workflow author acknowledges the vendor lock-in.

This is the OpenAPI `x-` extension pattern · industry canonical. Pantheon council ratified 2026-05-22 (4-0 vote).

---

## Conformance levels

See [07-conformance.md](./07-conformance.md). In summary ·

| Level | Stdlib requirement |
|---|---|
| Core | None · only parse + DAG + variable + error · no execution needed |
| Runtime | Must execute the 5 verbs · provider/tool implementations engine's choice |
| Stdlib v0.1 | Must ship the 8 providers + 9 extract modes + 36 builtins |
| Stdlib v0.1+media | Stdlib v0.1 + 24 media builtins |

A v0.1-compliant engine for a workflow author depends on which level they need.

---

## Forward-compat

The **split between core and stdlib** is locked at v1. The contents of the stdlib v0.x evolve.

Out of scope for v0.1 · explicit stdlib version pinning in the workflow envelope · per-task stdlib version overrides · stdlib element discovery API. See [08-out-of-scope.md](./08-out-of-scope.md).

---

🦋 *Next · [07 · Conformance](./07-conformance.md)*
