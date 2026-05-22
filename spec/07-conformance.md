# 07 · Conformance

> An engine MAY claim « v0.1-compliant » if it passes the conformance
> test suite at [`../conformance/tests/`](../conformance/). This document
> defines the conformance levels and what each requires.

---

## Conformance levels

Three nested levels · increasing scope ·

| Level | What it covers | Use case |
|---|---|---|
| **Core** | Parse + validate · DAG semantics · variable resolution · error structure | Linters · spec editors · static analyzers |
| **Runtime** | Core + verb execution | Working engine (with own provider/tool impls) |
| **Stdlib v0.1** | Runtime + the 8 providers + 9 extract modes + 36 builtins | Full reference-impl-equivalent engine |

A higher level **includes** the lower levels.

---

## Level 1 · Core conformance

An engine claims « Core v0.1-compliant » if it ·

1. **Parses** any valid v0.1 workflow YAML correctly
   - Accepts `apiVersion: nika.sh/v1` · `schema: nika/workflow@v1` · `workflow: <id>`
   - Validates the `workflow` identifier kebab-case
   - Recognizes the 5 verbs (`infer` · `exec` · `fetch` · `invoke` · `agent`)
   - Rejects unknown top-level fields with a clear error OR ignores with warning (engine's choice · documented behavior)

2. **Computes DAG topology** correctly
   - Detects cycles · rejects with `NIKA-DAG-001`
   - Detects unresolved `depends_on` references · rejects with `NIKA-DAG-002`
   - Computes topological waves for parallel execution

3. **Resolves variables** correctly
   - `${{ vars.x }}` from envelope `vars:`
   - `${{ with.x }}` from task `with:` block
   - `${{ tasks.X.field }}` from upstream task outputs
   - `${{ env.X }}` from environment (engine MAY restrict)
   - Reports undefined references with `NIKA-VAR-001`

4. **Produces typed errors** matching the v0.1 spec
   - `code` follows `NIKA-<NAMESPACE>-<NNN>` format
   - `category` is one of the closed enum values
   - `transient` correctly set

5. **Passes** all tests in `conformance/tests/core/`

A Core-compliant engine does NOT need to execute verbs. It needs to parse · validate · build the DAG · resolve variables · produce typed errors.

**Use case** · linters · spec editors · LSP server intelligence · static analyzers.

---

## Level 2 · Runtime conformance

An engine claims « Runtime v0.1-compliant » if it satisfies Core conformance PLUS ·

1. **Executes the 5 verbs** with correct semantics
   - `infer:` calls a configured provider · returns response
   - `exec:` runs the command in a shell · honors timeout + security
   - `fetch:` issues the HTTP request · applies extract mode
   - `invoke:` resolves and calls the tool · returns response
   - `agent:` runs the multi-turn loop · honors max_turns + tools whitelist

2. **Honors task fields** correctly
   - `depends_on` blocks until deps resolve
   - `when` skips when false
   - `timeout_ms` hard-kills on timeout
   - `retry` strategy honored on transient errors
   - `on_error` recovery honored on terminal errors
   - `with` scope injected into task body
   - `output` binding via JSONPath

3. **Implements security policies**
   - `exec:` blocklist (engine SHOULD ship a sane default · MAY allow override)
   - `fetch:` SSRF defense for private IP ranges
   - `invoke:` capability checks (engine's choice of capability model)

4. **Emits workflow events**
   - `task.started` · `task.completed` · `task.failed` · `task.skipped`
   - `workflow.started` · `workflow.completed` · `workflow.failed`
   - Event payload includes `task_id` · timestamp · status · duration

5. **Passes** all tests in `conformance/tests/runtime/`

Runtime-compliant engines may bring **their own** provider implementations · tool implementations · MCP server registries. They are not required to ship the canonical stdlib.

**Use case** · custom engines for specialized environments (embedded · WASM · custom LLM gateway · etc.).

---

## Level 3 · Stdlib v0.1 conformance

An engine claims « Stdlib v0.1-compliant » if it satisfies Runtime conformance PLUS ·

1. **Ships all 8 canonical providers** (per [stdlib/providers-v0.1.md](../stdlib/providers-v0.1.md))
2. **Ships all 9 canonical extract modes** (per [stdlib/extract-modes-v0.1.md](../stdlib/extract-modes-v0.1.md))
3. **Ships at least all 36 canonical builtins (post pantheon 2026-05-22)** (core 7 + file 5 + data 19 + introspection 6 · the 24 media builtins are optional)
4. **Passes** all tests in `conformance/tests/stdlib/`

A Stdlib-compliant engine is functionally equivalent to the reference implementation for any workflow that uses only the canonical stdlib elements.

**Use case** · the default level for production engines.

---

## Conformance test structure

```
conformance/
├── tests/
│   ├── core/                  # parsing · validation · DAG · variables · errors
│   │   ├── envelope/
│   │   ├── verbs-shape/
│   │   ├── dag-topology/
│   │   ├── variables/
│   │   └── errors/
│   │
│   ├── runtime/               # verb execution · task fields · events
│   │   ├── infer/
│   │   ├── exec/
│   │   ├── fetch/
│   │   ├── invoke/
│   │   ├── agent/
│   │   └── workflow-lifecycle/
│   │
│   └── stdlib/                # provider/extract/builtin canonical behavior
│       ├── providers/
│       ├── extract-modes/
│       └── builtins/
│
└── runner-protocol.md          # how to run the suite against any engine
```

Each test is a pair · `input.yaml` (the workflow to feed) + `expected.json` (the expected output or error structure).

For tests that require executing against real LLMs / networks · the suite uses the `mock` provider and HTTP mocks to keep tests deterministic.

---

## Runner protocol

A conformance runner ·

1. Reads each `input.yaml`
2. Pipes it to the engine being tested (`engine run --input -`)
3. Captures the engine's output (stdout JSON · structured)
4. Compares against `expected.json`
5. Reports pass/fail per test · final summary

See `conformance/runner-protocol.md` for the exact JSON wire format.

---

## Claiming conformance

To claim « v0.1-compliant » publicly · an engine ·

1. MUST pass the conformance suite at the claimed level
2. SHOULD document the level (Core · Runtime · or Stdlib v0.1)
3. MAY open a PR on [supernovae-st/nika-spec](https://github.com/supernovae-st/nika-spec) to be listed in `CONFORMANT_IMPLEMENTATIONS.md`

The reference implementation [supernovae-st/nika](https://github.com/supernovae-st/nika) targets Stdlib v0.1 conformance.

---

## Versioning

A conformance claim is **specific to a spec version**. As the stdlib evolves to v0.2 · engines re-claim conformance against the new suite. The Core conformance level is stable forever within v1 of the language.

---

🦋 *Next · [08 · Out of scope](./08-out-of-scope.md)*
