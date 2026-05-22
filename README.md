# Nika · the workflow language for AI

> A declarative YAML language for orchestrating AI workflows ·
> sovereign · multi-provider · local-first.
>
> **Status** · v0.1.0-draft (working) · **License** · Apache-2.0
>
> **Version note** · The LANGUAGE is locked at `nika: v1` · forever (this is
> the envelope you write in every workflow file · cohérent SQL/GraphQL/
> Dockerfile pattern of « one stable contract · evolves additively »). The
> reference ENGINE today targets `v0.81.0` (its own semver cadence ·
> forever-v0.x per ADR-002 · breaking changes ship on MINOR). The two
> version axes are independent · the `nika: v1` contract stays stable while
> the engine evolves through `v0.81 → v0.82 → ... → v0.99 → v0.100`.

---

## What is Nika?

Nika is a **language**. Not a framework, not a runtime, not a SaaS.

The language describes the **what** of an AI workflow ·
- which LLMs to call (`infer:`)
- which commands to run (`exec:`)
- which tools to invoke (`invoke:`)
- which agentic loops to spawn (`agent:`)

The **how** lives in conformant engines. The reference implementation
is at [supernovae-st/nika](https://github.com/supernovae-st/nika)
(Rust · AGPL-3.0-or-later).

**Analogies** ·
- `SQL` is to PostgreSQL what `Nika` is to its reference engine
- `Dockerfile` is to Docker what `Nika YAML` is to a workflow runtime
- `GitHub Actions YAML` is to GitHub Actions what `Nika YAML` is to its engine

---

## Hello world

```yaml
nika: v1
workflow: hello

model: anthropic/claude-haiku-4-5

tasks:
  - id: greet
    infer:
      prompt: "Say hello in French"
```

Run it (with the reference engine) ·

```bash
nika run hello.nika.yaml
```

**New to Nika?** → [**QUICKSTART.md**](./QUICKSTART.md) builds a real workflow in 5 minutes.

---

## The 5 pillars · immutable forever

1. **Envelope** — one line · `nika: v1` + `workflow:` header (+ typed `vars` · `env` · `secrets`)
2. **The 4 verbs** — `infer:` · `exec:` · `invoke:` · `agent:` (4, absolute · `fetch` is a tool via `invoke`)
3. **DAG shape** — tasks + `depends_on` + `when` + `for_each` + output binding
4. **Variables** — one `${{ ... }}` syntax · 5 namespaces (`vars` · `with` · `tasks` · `env` · `secrets`)
5. **Error model** — `NIKA-<NS>-<NNN>` codes · retry semantics · structured output

These 5 things never change. Everything else (providers · builtins ·
extract modes · etc.) lives in the **stdlib** and evolves separately.

See [spec/](./spec/) for the full specification.

---

## Repository layout

```
nika-spec/
├── spec/                      ← THE specification (~30 pages markdown)
│   ├── 00-overview.md           one-page vision
│   ├── 01-envelope.md           nika: v1 + workflow + typed vars/env/secrets
│   ├── 02-verbs.md              the 4 verbs · signatures + semantics
│   ├── 03-dag.md                tasks · depends_on · when · for_each · output
│   ├── 04-variables.md          ${{ }} · 5 namespaces · vars/with/tasks/env/secrets
│   ├── 05-errors.md             error codes · retry · structured output
│   ├── 06-stdlib-contract.md    how the stdlib versions independently
│   ├── 07-conformance.md        what « v0.1-compliant » means
│   └── 08-out-of-scope.md       explicit defer list (memory · macros · etc.)
│
├── schemas/                   ← machine-readable JSON Schemas
├── examples/                  ← 26 canonical workflows
├── conformance/               ← test suite for any implementation
│
└── stdlib/                    ← versioned independently
    ├── providers-v0.1.md        13 providers canonical (anthropic · openai · …)
    ├── extract-modes-v0.1.md    9 extract modes (markdown · article · jsonpath · …)
    └── builtins-v0.1.md         37 builtins curated (core · file · data · …)
```

---

## For implementers

If you want to implement Nika in your language ·

1. Read [`spec/`](./spec/) (~30 pages · the contract)
2. Pass [`conformance/`](./conformance/) (test suite · « v0.1-compliant »)
3. Optionally implement the [`stdlib/`](./stdlib/) (providers + extract + builtins)
4. Open a PR on this repo to be listed as a conformant impl

**License**: this spec is **Apache-2.0** with patent grant. Use it freely.

---

## Reference implementation

[supernovae-st/nika](https://github.com/supernovae-st/nika) · the reference engine · Rust · AGPL-3.0-or-later.

The reference impl ·
- Implements the v0.1 spec end-to-end
- Ships as `cargo install nika` (binary `nika`)
- Exposes the engine via MCP server (`nika mcp serve`) for harness integration (Claude Code · Cursor · Hermes · etc.)
- Exposes a Rust SDK (`nika-sdk` crate · embeddable)

---

## Why a language?

Today every AI harness reinvents workflows · Python files · TS classes ·
prompts inline · DAGs imperative · skills crystallized into their own
runtime. **None of them are portable.**

A portable language means ·
- One YAML workflow · runs on any conformant engine (Rust · Python · Go · …)
- Read · share · review · diff like any other text
- The **language is the contract** · the runtime is implementation

Standards work · SQL · GraphQL · OpenAPI · Dockerfile · GitHub Actions YAML.
Nika is that for AI workflows.

---

## Status

- v0.1.0-draft · spec drafted · examples + conformance + schemas pending
- v0.1.0 GA · target Q3 2026 (after spec review + examples +
  conformance suite + schemas)

Forever after GA · the 5 pillars are locked. Stdlib evolves independently.

---

## Governance

- **Editor** · SuperNovae Studio (Thibaut Melen + Nicolas)
- **Discussion** · GitHub Issues on this repo
- **Decisions** · summarized in this repo's CHANGELOG.md
- **RFC process** · TBD post-v0.1 GA · when external implementations emerge

---

## Related

- [supernovae-st/nika](https://github.com/supernovae-st/nika) · reference engine (Rust · AGPL-3.0-or-later)
- [supernovae-st/nika-docs](https://github.com/supernovae-st/nika-docs) · Mintlify docs (tutorials · concepts · how-to)
- [supernovae-st/nika-client](https://github.com/supernovae-st/nika-client) · TypeScript SDK
- [nika.sh](https://nika.sh) · marketing landing

---

## License

This spec · its examples · its conformance tests · its JSON schemas are
all licensed **Apache-2.0** with patent grant. See [LICENSE](./LICENSE).

The reference implementation (separate repo) is AGPL-3.0-or-later.

---

🦋 *Forever-v0.x · less but better · Rams principle 10.*
