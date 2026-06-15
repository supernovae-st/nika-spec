# Nika · the workflow language for AI

> A declarative YAML language for orchestrating AI workflows ·
> sovereign · multi-provider · local-first.
>
> **Status** · v0.1.0-draft (working) · **License** · Apache-2.0
>
> The language is locked at `nika: v1` — forever. That's the envelope you
> write in every workflow file; it evolves additively and never breaks (the
> SQL / Dockerfile contract model). The reference engine versions separately.

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

model: ollama/llama3.1   # local · zero key · swap for any of the 14 providers

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
2. **The 4 verbs** — `infer:` (LLM) · `exec:` (shell) · `invoke:` (tools/MCP) · `agent:` (autonomous loop)
3. **DAG shape** — tasks + `depends_on` + `when` + `for_each` + output binding
4. **Variables** — one `${{ ... }}` syntax · <!-- canon:namespaces -->5<!-- /canon --> namespaces (`vars` · `with` · `tasks` · `env` · `secrets`)
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
├── examples/                  ← foundation + showcase workflows (the versioned pack)
├── templates/                 ← 6 instantiable skeletons · the agent authoring path
├── conformance/               ← test suite for any implementation (3 static tiers)
├── eval/                      ← the agent-authoring benchmark (protocol vs routing vs freeform)
├── scripts/                   ← projectors (docs · website · pack stay byte-derived)
├── canon.yaml                 ← machine-readable counts + registries (THE source)
├── AGENTS.md                  ← the deterministic authoring protocol (agents start here)
│
└── stdlib/                    ← versioned independently
    ├── providers-v0.1.md        14 providers canonical (anthropic · openrouter · …)
    ├── extract-modes-v0.1.md    9 extract modes (markdown · article · jq · …)
    └── builtins-v0.1.md         23 builtins curated (core · file · data · …)
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

The reference impl (the Diamond rebuild · in flight · runnable end-to-end
at its v0.81 milestone) ·
- Targets full v0.1 spec conformance (Stdlib level)
- Will ship as `cargo install nika` (binary `nika` · self-contained ·
  embeds this spec + schema + examples)
- Will expose the engine via MCP server (`nika mcp serve`) for harness
  integration (Claude Code · Cursor · Hermes · etc.)
- Today · the [conformance oracle](./conformance/) in this repo validates
  any workflow statically (`python3 conformance/runner.py validate <file>`)
  — authoring and checking work NOW · execution lands with the engine
  milestone

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

## The examples pack (versioned · embedded in the binary)

**Every spec version ships its pack.** [`examples/manifest.yaml`](examples/manifest.yaml)
(generated · `pack_version` = the [`VERSION`](VERSION) file) lists every
canonical workflow — foundation + showcase — with tier, constructs and a
sha256 over the exact text every surface renders. The contract:

- the **docs** and the **website** render projections of these files (never copies)
- the **reference engine embeds the pack of its version** — `nika examples`
  / `nika docs` / `nika schema` work offline, and an installed binary always
  carries the canonical examples *of the language version it speaks*
- the manifest hashes make the pack **verifiable end-to-end** — a tampered or
  drifted example fails the check, anywhere it travels

## Tooling (deterministic mesh)

| Tool | Role |
|---|---|
| [`canon.yaml`](canon.yaml) | THE source for every language count (verbs · namespaces · builtins · providers · modes · error namespaces) |
| [`scripts/canon-projectors.py`](scripts/canon-projectors.py) | projects canon counts → docs snippet + website module (`--write` / `--check`) |
| [`scripts/showcase-projector.py`](scripts/showcase-projector.py) | projects [`examples/showcase/`](examples/showcase/) → docs example pages + website explorer (yaml · diagrams · run-sim model · coverage matrix) |
| [`conformance/runner.py`](conformance/runner.py) | the static oracle · core + stdlib fixtures + every example as a conformance input (the CI gate) |
| [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) | pre-commit hook ids for downstream engines consuming this spec |

Prose counts carry `<!-- canon:X -->N<!-- /canon -->` markers — machine-updatable
(the monorepo `canon-fix` gate rewrites them when canon.yaml moves · drift is a
CI failure, not a maybe).

## Status

- v0.1.0-draft · spec drafted · 7 foundation + 20 showcase examples + 6 templates · workflow.schema.json · 83 static conformance fixtures across three tiers (core · deep · stdlib surface — `python3 conformance/runner.py all` is the live count) — every example gated in CI · runtime/behavioral conformance pending
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
- [docs.nika.sh](https://docs.nika.sh) · end-user docs (source · [supernovae-st/nika-docs](https://github.com/supernovae-st/nika-docs))
- [supernovae-st/nika-client](https://github.com/supernovae-st/nika-client) · TypeScript SDK
- [nika.sh](https://nika.sh) · marketing landing

---

## License

This spec · its examples · its conformance tests · its JSON schemas are
all licensed **Apache-2.0** with patent grant. See [LICENSE](./LICENSE).

The reference implementation (separate repo) is AGPL-3.0-or-later.

---

🦋 *Forever-v0.x · less but better · Rams principle 10.*
