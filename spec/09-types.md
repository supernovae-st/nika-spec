# 09 · Types

> Nika has a **decidable type core**. A workflow declares named types
> once (`types:`), tasks declare what they return (`returns:`), and the
> engine checks every deep reference, compiles structured-output
> contracts, and types every value edge — **before a token is spent**.
> The type language is deliberately small: every judgment (subtyping ·
> path validity · contract compilation) terminates, by construction.
>
> One direction, one truth: a Nika type **lowers** to JSON Schema
> 2020-12 (the lingua franca every structured-output provider speaks).
> The schema sent to a provider is a *projection* of the type — never a
> second truth to keep in sync. A raw JSON Schema stays usable as an
> escape hatch (`schema:` · [02](./02-verbs.md)); its static analysis is
> honestly weaker ([04 §static binding validation](./04-variables.md#static-binding-validation-against-a-declared-schema-normative)).

---

## The `types:` block · *optional · named type declarations*

```yaml
nika: v1
workflow:
  id: research-pipeline

types:
  Summary:
    object:
      title: string
      bullets: { array: string }
      score: { integer: { min: 0, max: 100 } }

tasks:
  summarize:
    with: { article: "${{ tasks.fetch.output }}" }
    infer:
      prompt: "Summarize · ${{ with.article }}"
    returns: Summary
```

- A type name matches `^[A-Z][A-Za-z0-9]*$` (PascalCase — disjoint from
  task ids and from the lowercase primitive names by construction).
- A name may reference other named types. References must be **acyclic**:
  a recursive type is rejected (`NIKA-TYPE-002` — unbounded recursion
  would make subtyping and lowering undecidable; v1 keeps every judgment
  total).
- An unknown name (in `types:`, `returns:`, an `outputs:` `type:`, or a
  field position) is `NIKA-TYPE-001`, with a did-you-mean fix when a
  declared name is close.

## The type grammar (closed · v1)

A **type expression** is one of ·

| Form | Meaning |
|---|---|
| `null` · `bool` · `integer` · `number` · `string` · `bytes` · `uri` · `path` · `duration` · `timestamp` | the primitives |
| `money` | a decimal amount + ISO-4217 currency (reserved refinements land with the decision core — see §reserved) |
| `PascalName` | a reference to a declared named type |
| `{ array: T }` | homogeneous list |
| `{ map: T }` | string-keyed map with homogeneous values |
| `{ object: { field: T, … } }` | **closed** record — see §closed objects |
| `{ union: [T, …] }` | untagged union (≥ 2 members) |
| `{ optional: T }` | exactly `union: [T, null]` (sugar · normalized away) |
| `{ enum: ["a", "b", …] }` | closed string enumeration (≥ 1 member · unique) |
| `{ integer: { min?, max? } }` · `{ number: { min?, max? } }` | bounded numerics (inclusive bounds) |
| `{ string: { pattern?, min_len?, max_len? } }` | refined string (`pattern` is a regular expression **without backreferences or lookaround** — linear-time matchable) |

Three constructors are **declared and reserved** — they parse nowhere in
v1 and their semantics land with their owning wave ·

| Reserved | Owner | Why it is named now |
|---|---|---|
| `result<T>` | Outcome IR (W5) | a task outcome is a *contract*, not a convention — the slot is reserved so no user type squats the name |
| `artifact<mime>` | artifact lanes (W5) | `outputs:` already speak it informally; the typed form needs runtime identity first |
| `secret<T>` | authority wave (W4) | a secret is a *confidentiality*, not a shape — see §secrets never lower |

### Closed objects (normative)

`{ object: … }` is **closed by default**: at run time, a member outside
the declared fields is a violation; statically, a reference to an
undeclared member is **provably invalid** (`NIKA-VAR-003` — the same
code, the same class, one voice with the schema walk of
[04](./04-variables.md#static-binding-validation-against-a-declared-schema-normative)).
Opt out per object with `additional: true` ·

```yaml
types:
  Loose: { object: { id: string }, additional: true }
```

An **optional field** is declared with `optional:` on the field type ·

```yaml
types:
  Story:
    object:
      headline: string                 # required
      byline: { optional: string }     # may be absent or null
```

### Normalization (normative)

Two type expressions are compared **after normalization** ·

1. `optional: T` rewrites to `union: [T, null]`.
2. Unions flatten (`union` inside `union`), deduplicate structurally,
   and order canonically (member order never carries meaning).
3. A one-member union collapses to its member.

## The lattice · `⊑` (normative)

`A ⊑ B` (« every A value is a B value ») is decidable and total ·

- every type `⊑` itself (after normalization) ·
- `integer ⊑ number` ·
- `{ enum: E } ⊑ string` · `{ enum: E1 } ⊑ { enum: E2 }` iff `E1 ⊆ E2` ·
- bounded numerics: `{ integer: {min: a, max: b} } ⊑ { integer: {min: c, max: d} }`
  iff `c ≤ a` and `b ≤ d` (absent bound = unbounded) · same for `number`
  · a bounded form `⊑` its bare primitive ·
- refined strings: `⊑` bare `string` always; between two refined strings,
  `⊑` holds iff the bounds nest and the patterns are **syntactically
  equal** (regex inclusion is not decided — honest, never guessed) ·
- `uri ⊑ string` · `path ⊑ string` · `duration ⊑ string` ·
  `timestamp ⊑ string` (the newtypes narrow strings; nothing else) ·
- `array/map`: covariant in the element type ·
- objects: **width + depth** — `A ⊑ B` iff every required field of B
  exists in A with the field type in `⊑`; a closed B admits no A field
  outside B's declared fields; `additional: true` on B lifts that
  restriction ·
- unions: `A ⊑ union U` iff `A ⊑` some member; `union U ⊑ B` iff
  **every** member `⊑ B` ·
- `Unknown` (the type of any undeclared producer · §gradual) satisfies
  `Unknown ⊑ T` and `T ⊑ Unknown` for every T — gradual, permissive,
  and *named*: the check never invents a rejection where it has no
  knowledge. **This makes the Unknown arm a *consistency* relation, not
  an order**: reflexivity and transitivity are laws of the Unknown-free
  fragment only, and an `Unknown` in the middle never launders an
  unrelated pair (`null ~ Unknown ~ bool`, yet `null ⋢ bool` — the
  classic gradual-typing law, property-pinned in both evaluators).

Join (`⊔`) and meet (`⊓`) exist for every pair (union-of / structural
intersection, collapsing to `Unknown` where no informative bound
exists) — engines use them internally (edge typing · inference); they
are not authorable surface.

## Lowering · Nika type → JSON Schema 2020-12 (normative · one direction)

`lower(T)` is the **single** projection every consumer uses — the
structured-output contract for `infer:`/`agent:`, the callable-workflow
schema, the editor's completion source. It is total on the v1 grammar ·

| Nika type | JSON Schema |
|---|---|
| `null` | `{ "type": "null" }` |
| `bool` | `{ "type": "boolean" }` |
| `integer` | `{ "type": "integer" }` |
| `number` | `{ "type": "number" }` |
| `string` | `{ "type": "string" }` |
| `bytes` | `{ "type": "string", "contentEncoding": "base64" }` |
| `uri` | `{ "type": "string", "format": "uri" }` |
| `path` | `{ "type": "string" }` (the path meaning is Nika-side · no portable format) |
| `duration` | `{ "type": "string", "pattern": "^[0-9]+(\\.[0-9]+)?(ns\|us\|µs\|ms\|s\|m\|h)([0-9]+(\\.[0-9]+)?(ns\|us\|µs\|ms\|s\|m\|h))*$" }` (the quoted Go-duration of [01](./01-envelope.md)) |
| `timestamp` | `{ "type": "string", "format": "date-time" }` |
| `money` | `{ "type": "string" }` (decimal + currency refinements land with the decision core) |
| `{ enum: E }` | `{ "type": "string", "enum": E }` |
| `{ integer: {min,max} }` | `{ "type": "integer", "minimum": min, "maximum": max }` (absent bound omitted) · same shape for `number` |
| `{ string: {pattern,min_len,max_len} }` | `{ "type": "string", "pattern": …, "minLength": …, "maxLength": … }` |
| `{ array: T }` | `{ "type": "array", "items": lower(T) }` |
| `{ map: T }` | `{ "type": "object", "additionalProperties": lower(T) }` |
| `{ object: F }` closed | `{ "type": "object", "properties": …, "required": [non-optional fields], "additionalProperties": false }` |
| `{ object: F, additional: true }` | same, without `"additionalProperties": false` |
| `{ union: [T…] }` | `{ "anyOf": [lower(T)…] }` |
| named reference | **inlined** at its use site (acyclicity makes this total · no `$ref` in the lowered document, maximizing provider compatibility) |

Two laws ride the table ·

- **One direction.** There is no `raise(schema)` — an authored JSON
  Schema is never reverse-engineered into a Nika type. The hatch stays a
  hatch.
- **Secrets never lower.** No position that lowers (a `returns:`, an
  `outputs:` type, a callable-workflow input) may contain `secret<…>`
  when it lands in W4 — a type that would ship a secret's *shape* to a
  provider is refused statically (`NIKA-TYPE-005`). Reserved now so the
  hole never opens.

## `returns:` · the task's output contract (normative)

`returns:` declares **what a task's `.output` is**. One field, one
meaning, per verb ·

| Verb | What `returns:` does | Decode mechanics |
|---|---|---|
| `infer:` | compiles `lower(returns)` as the structured-output contract — the reply **is** validated against it (the same enforcement lane as `schema:` · [02](./02-verbs.md#infer--llm-inference)) | provider-side structured output · engine-side validation |
| `agent:` | same as `infer:`, over the loop's **final message** | same |
| `exec:` | asserts the **decoded** value: `Type(decoded) ⊑ returns` at run time (`NIKA-TYPE-101` on violation) | explicit `decode:` — see below |
| `invoke:` | the tool's canonical contract stays the truth; `returns:` **refines** it (statically checked against a builtin's declared output shape when the engine knows one · otherwise asserted at run time like `exec:`) | tool-defined |

- `returns:` takes a named type or an inline type expression.
- **One contract per task** · `returns:` and a verb-level `schema:` on
  the same task is `NIKA-TYPE-003` (two spellings of one contract — the
  one-obvious-way law). `schema:` alone stays legal: it is the
  out-of-core hatch, with the weaker static walk.
- **Gradual and honest** · no `returns:` = the output is `Unknown`.
  Nothing is invented: completion offers nothing beneath it, the walk
  stops, and every read is a run-time concern (exactly today's
  schema-less behavior — [04](./04-variables.md)).
- The static walk of [04 §static binding validation](./04-variables.md#static-binding-validation-against-a-declared-schema-normative)
  runs on `returns:` types with **full precision**: the v1 type grammar
  has no open construct, so every level is walkable (closed objects
  refuse phantom members as `NIKA-VAR-003`; `additional: true` and
  `Unknown` make a level open, the walk stops — sound, never guessy).

### `decode:` · how `exec:` bytes become a value (normative)

The type never silently changes how the runtime reads bytes — decoding
is **declared** ·

```yaml
tasks:
  stats:
    exec:
      command: ["jq", "-c", ".stats", "report.json"]
      decode: json               # text (default) · json · jsonl · bytes
    returns: { object: { count: integer, mean: number } }
```

- `decode:` applies to the captured **string** stream (`capture:
  stdout` · `stderr` · `combined`) · `text` (default — the value is the
  string, trailing newline trimmed as today) · `json` (parse one JSON
  document) · `jsonl` (parse newline-delimited JSON into an array) ·
  `bytes` (no decoding · the value is opaque bytes).
- `decode:` with `capture: structured` is rejected (`NIKA-PARSE-025`) —
  the structured capture *is* already an object
  (`{ stdout, stderr, exit_code }`); a `returns:` on such a task types
  that object directly.
- A `decode: json`/`jsonl` whose stream does not parse settles the task
  `failure` (`NIKA-EXEC` lane · the decode is task-stage work, inside
  `on_error:` scope like every verb-stage failure · [03 §dispatch
  pipeline](./03-dag.md#the-gate-algebra-v2-normative)).
- Static coherence: a `returns:` whose type cannot come out of the
  declared decode (an `object` contract over `decode: text` · anything
  over `decode: bytes` except `bytes`) is `NIKA-TYPE-004` at check time.
- `decode: artifact-ref` is **reserved** (artifact lanes · W5).

## Typed value edges (normative)

A `with:` binding's type is **derived, never declared** ·

- `with.x` bound to `${{ tasks.P.output }}` has type
  `optional<returns(P)>` — optional because a **skipped** producer
  passes a value edge and reads defined-`null`
  ([03 §gate algebra](./03-dag.md#the-gate-algebra-v2-normative) ·
  [04 §value rendering](./04-variables.md)). A consumer that runs only
  on `after: { P: succeeded }` + reads the same binding still types it
  `optional` — the type follows the edge, not the gate (simple, uniform,
  and safe: `null`-handling is never a surprise).
- A deep read (`tasks.P.output.count`) types as the walked field type.
- `.status` observations type `{ enum: ["success","failure","skipped","cancelled"] }`
  (the closed vocabulary of [03](./03-dag.md) — `NIKA-DAG-007` guards the
  literals) · `.duration_ms` types `integer` · `.error` types the error
  record of [05](./05-errors.md) (an `object`, `additional: true`).
- Producer without `returns:` → the binding is `Unknown` (gradual).

The **workflow-contract halves stay flat for now** · typed `vars:` and
typed `outputs:` keep their flat closed enum (`string · number · integer
· boolean · array · object` · [01](./01-envelope.md)) until the
input-authority window (G9) widens BOTH halves to this grammar in one
deliberate break — the callable contract never speaks two type languages
at once. This chapter's grammar binds `types:` and `returns:` today.

## Errors (the `NIKA-TYPE` namespace · new in this chapter)

| Code | Failure | Category | `transient` |
|---|---|---|---|
| `NIKA-TYPE-001` | unknown type name (in `types:` · `returns:` · an `outputs:` type) — did-you-mean when close | `validation_error` | false |
| `NIKA-TYPE-002` | recursive type reference — the `types:` graph must be acyclic | `validation_error` | false |
| `NIKA-TYPE-003` | `returns:` and `schema:` on the same task — one contract, one spelling | `validation_error` | false |
| `NIKA-TYPE-004` | `returns:` type unreachable from the declared `decode:` (an object over `decode: text` · …) | `validation_error` | false |
| `NIKA-TYPE-005` | a secret-carrying type in a lowered position (reserved with `secret<T>` · W4) | `security_error` | false |
| `NIKA-TYPE-101` | run-time contract violation — the decoded value does not fit `returns:` (`exec:`/`invoke:` lane; `infer:`/`agent:` violations stay `NIKA-INFER-002`-class, one voice with the structured-output lane) | `validation_error` | false |

## One obvious way (normative for linters)

| Rule | Instead of | Write |
|---|---|---|
| `one-obvious-way/011` | `schema:` on an `infer:`/`agent:` task whose shape fits the v1 type grammar | `returns:` (the typed door — the hatch is for out-of-core shapes) |
| `one-obvious-way/012` | an inline `returns:` object repeated across tasks | a named type in `types:` (one declaration, N references) |

## What v1 deliberately does not do

- **No recursion** in named types (undecidable walks — `NIKA-TYPE-002`).
- **No generics / type parameters** (the reserved `result<T>` ·
  `artifact<mime>` · `secret<T>` are engine-owned constructors, not a
  user-parameterizable surface).
- **No regex inclusion** judgments (syntactic equality only — honest).
- **No implicit coercions** — `integer ⊑ number` is the single numeric
  widening; a string is never silently a number.
- **No reverse lowering** — JSON Schema in, Nika types out, does not
  exist. The hatch stays a hatch.

---

## Related

- [01 · Envelope](./01-envelope.md) — typed `vars:` (the callable-input
  half) · `outputs:` (the return half)
- [02 · Verbs](./02-verbs.md) — `returns:`/`decode:` rows per verb ·
  `schema:` the hatch
- [03 · DAG](./03-dag.md) — the value-edge semantics `returns:` types
- [04 · Variables](./04-variables.md) — the static walk `returns:`
  sharpens
- [05 · Errors](./05-errors.md) — the `NIKA-TYPE` registry rows
