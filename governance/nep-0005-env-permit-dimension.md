# NEP-0005 · The environment permit: a child's environment is composed, never inherited

- **NEP**: 0005 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint)
- **Title**: `env:` is a permit category: the child process environment is composed from a published floor plus the declared passthrough, never inherited
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-23

## Abstract

NEP-0003 made the absent boundary fail-closed and NEP-0004 made the
present boundary honest against attacker-controlled values. This NEP
closes the one capability plane the `permits:` block still does not name:
the process environment. Cloud and cluster credentials live in
environment variables, and today a spawned subprocess inherits the
engine's ENTIRE environment minus a dangerous-name denylist, so one
allowlisted program can read `AWS_SECRET_ACCESS_KEY` without a single
declared grant. `env:` becomes a permit category. A child process
environment is COMPOSED: the runner env floor (a fixed, spec-published
name list) ∪ the declared `env:` passthrough (exact names, resolved from
the engine's environment at spawn) ∪ the task's explicit `env:` map
(authored values) − the dangerous-name floor. Inheritance is dead: a
workflow that declares no `env:` spawns children that see the floor and
nothing else.

## Motivation

HF incident stage 3: the pivot from one compromised process to the
platform's cloud account rode ambient credentials in the environment.
A denylist scrub (the engine's dangerous-name floor) kills the INJECTION
class (`LD_PRELOAD`, `BASH_ENV`, interpreter hooks) and can never kill
the DISCLOSURE class: no list enumerates every secret-bearing name an
operator exports. Deny-by-default with a declared passthrough is the only
shape that contains the credential plane, and it is the exact posture the
engine's MCP stdio spawn already runs as an implementation choice
(`env_clear` plus a curated 8-name passthrough). This NEP promotes that
posture from an engine detail to the LAW of every child, governed by the
file: the `permits:` block finally names the reach that credentials ride.

## Specification

Definitions (normative · closed):

- **CHILD PROCESS** · any OS process an engine spawns on behalf of a
  workflow: the `exec` verb's subprocess (argv and shell forms) and a
  stdio tool server (`mcp:*`). The engine process itself is not a child:
  `infer` provider calls, first-party builtins, and the in-engine
  composition of a child WORKFLOW (14-composition) spawn nothing here.
- **RUNNER ENV FLOOR** · the fixed name list `PATH`, `HOME`, `TMPDIR`,
  `LANG`, `LC_ALL`, `TZ`, `USER`, `LOGNAME`. A loader path, a home for
  caches, scratch, locale and timezone: what a child needs to RUN, and
  nothing that names a credential. The list is a normative MAXIMUM: an
  engine MUST NOT pass any undeclared name beyond it and MAY pass fewer.
- **DANGEROUS-NAME FLOOR** · the injection-vector names an engine strips
  unconditionally and LAST: dynamic-linker injection, shell startup
  sourcing, tool command hooks, interpreter pre-exec hooks, and
  field-splitting (`IFS`). The engine's canonical list
  (`DANGEROUS_ENV_VARS`) is the reference; no grant overrides it.
- **`env:` CATEGORY** · a list of exact environment variable names. A
  name MUST match the POSIX shape `[A-Za-z_][A-Za-z0-9_]*`. No globs. A
  name is a permit BOUND: LAW-AUTH-0325 literality applies, so an
  interpolation in the list is a hard refusal (`NIKA-AUTH-007`).
- **COMPOSED ENVIRONMENT** · floor-resolved ∪ passthrough-resolved ∪ the
  task-level `env:` map, minus the dangerous-name floor. Resolution reads
  the ENGINE's environment at spawn time; a declared name absent from the
  engine environment passes nothing (no error, no empty-string synthesis).

The law (MUST/SHOULD):

1. A child process environment MUST be composed, never inherited. With no
   `env:` category (or no `permits:` block at all · NEP-0003), the child
   sees at most the runner env floor plus the task's explicit `env:` map.
2. A declared `env:` list passes exactly the named engine variables to
   every child process of the workflow. Presence in the list grants
   REACH; the engine environment supplies the value or nothing.
3. A name on the dangerous-name floor is never passable: an `env:` entry
   naming one is an inert dead grant and MUST be flagged at check
   (`NIKA-AUTH-009` · security_error), and a task-map entry naming one is
   stripped last (the floor wins, today's behavior kept).
4. An `env:` bound MUST be a literal exact POSIX name: interpolation in
   the list is `NIKA-AUTH-007` (LAW-AUTH-0325 covers every bound, this
   category included); a non-name string is a parse-level refusal.
5. Under composition (14) the effective category is the meet: child ∩
   parent, exact-name intersection. An absent parent block still means
   zero (NEP-0003): no child obtains a passthrough its parent could not
   grant.
6. The task-level `env:` map (02-verbs §exec) stays authored data: values
   the file carries, visible at review distance, applied AFTER the
   passthrough (an authored entry wins over an inherited one on the same
   name), still under the dangerous-name floor. Nothing about its grammar
   changes.
7. `env:` is not inferable. Permit-inference tooling MUST NOT invent the
   list: a subprocess's environment reads are opaque to static analysis.
   The undeclared-read failure mode is the child tool's own
   missing-variable error; an engine SHOULD document the one-line repair
   (`env: [NAME]`) next to that story.

Registry and prose touched:

- **LAW-AUTH-0326** is added to `canon/laws/authority.yaml` (status
  active) · the machine row of this law.
- `spec/01-envelope.md` §permits gains the `env` category row, the sample
  line, and « The environment category (normative) » · `spec/02-verbs.md`
  §exec `env:` gains the composed-never-inherited pointer ·
  `spec/10-authority.md` §the permit-parameterization taint counts env
  names among the literal bounds.
- `canon/diagnostics/registry.yaml` gains `NIKA-AUTH-009` (the AUTH
  family carries the defects of the boundary block itself: 006 absent ·
  007 non-literal bound · 008 re-gate escape · 009 dead grant; the SEC
  family stays the run-time floor and flow classes); the `NIKA-AUTH-007`
  teaching names env alongside host/glob/program.
- Implementation surfaces: the schema parser (the strict `permits:`
  grammar) · the check (dead-grant flag, bound literality, composition
  containment) · the spawn sites (the exec runner's clean slate, the MCP
  stdio scrub's declared allowlist) · the permits algebra (the meet).

## Conformance test

Four static pairs ship in `conformance/tests/core/authority/` (014-017,
continuing the NEP-0004 suite) plus two behavioral contracts
(`runtime/permits/005-006` · the reserved tier: the executable proof
lands engine-side, one canary flipped by one declared line).
Engine/reference differential per LAW-AUTH-0319.

## Compatibility impact

NOT additive at run for a workflow whose subprocess reads an undeclared
ambient variable · additive for every file in the reference corpora
(census at engine 042aeaf95 and spec 38614d2: zero engine, spec, or
example workflow reads ambient env in a command). The break surfaces as
the child tool's own missing-variable error, and the repair is one
declared line. The grammar change is additive (`env:` is a new optional
key under `permits:`; the `nika: v1` marker is untouched).

## Migration plan

**What changes for you.** A subprocess no longer sees the engine's
environment. It sees the runner env floor (`PATH`, `HOME`, `TMPDIR`,
`LANG`, `LC_ALL`, `TZ`, `USER`, `LOGNAME`), what your task's `env:` map
sets, and the variables your `permits.env:` names, nothing else:

```yaml
permits:
  exec: ["terraform"]
  env: ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]
```

Each passed credential is one greppable line in the file that IS the
blast radius. A tool failing with « VARIABLE not set » after this change
is the law working: add the name to `permits.env:`, or set the value in
the task's `env:` map when it is authored data. Two check errors teach
the block's own defects:

```
error[NIKA-AUTH-007]: permit bound `env[0]` is interpolated, not literal
  · a bound is the wall itself: write the exact variable name
error[NIKA-AUTH-009]: permit entry `env: ["LD_PRELOAD"]` is an inert dead grant
  · the dangerous-name floor strips this name unconditionally: the grant can never take effect · remove it
```

Nothing else changes: the verbs, the other categories, the task `env:`
map, and the `nika: v1` marker are untouched.

## Rejected alternatives

- **Deny-list only (the status quo)** · rejected: a denylist kills the
  injection class and structurally cannot kill the disclosure class; no
  list enumerates every secret-bearing name.
- **Glob passthrough (`AWS_*`)** · rejected for v1: the glob that matches
  the harmless id also matches the secret; exact names keep one line =
  one credential at review distance. A glob arm can only enter by NEP.
- **Values inside the permit (`env: {KEY: value}`)** · rejected: values
  are the task map's job (02-verbs); a permit names REACH, never data.
- **Per-task `env:` permits** · rejected for v1: the block is the
  workflow's blast radius (01 §permits posture); task-grain scoping
  arrives with the narrowing story, not here.
- **Synthesizing empty strings for absent names** · rejected: inventing a
  value masks a deployment defect; absence propagates honestly.
- **Refusing the run when a child reads an undeclared variable** ·
  rejected: environment reads happen inside the child, unobservable in
  general; composition is enforceable, interception is not. Composing the
  variable OUT is the enforceable truth, and the child's own error is the
  honest signal.
- **Exec-only scope (leaving `mcp:*` servers on the curated list)** ·
  rejected: one law for every child, or the hole migrates from the verb
  to the tool server.
