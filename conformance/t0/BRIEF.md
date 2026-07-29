# T0 · the executor's brief (the weekend re-implementation rule)

> You are re-implementing the CORE of the Nika checker, cold, in one
> weekend. This file is everything you may read besides the spec and
> the fixtures. You may NOT look at the reference engine's code, and
> you may NOT contact the designers directly — every question goes in
> `GAP_LOG.md` (each entry there is a spec bug by definition).

## What you get (nothing else)

- this repository (`supernovae-st/nika-spec`) — the spec text, the
  JSON schema, the NEPs
- the conformance fixtures, selected mechanically by the `t0` tier:

```bash
python3 conformance/runner.py run conformance/tests/core --tier t0
```

- 2 full days (a weekend), the language of your choice

## What you build (the T0 subset)

1. **Parse + envelope** — read a `.nika.yaml`, validate the structure
   (fixtures `core/envelope/001-008`).
2. **The permits law** — an absent `permits:` block means ZERO
   authority (default-deny · fixtures `core/authority/001-006`).
3. **Default-deny per category** — fs / host / program / tool refused
   when the category is omitted.
4. **The error taxonomy for this scope** — the exact codes the
   fixtures name (`core/errors/001-006`).
5. **ONE verb of your choice** (`infer` or `exec`) — enough to measure
   depth without demanding everything.

Out of scope (declared): narrowing/inference · receipts/crypto · MCP ·
agents · replay · the OS sandbox.

## The rules (clean-room, strict)

```
YOU RECEIVE · the spec repo + the t0 fixtures + 2 days
YOU NEVER GET · the engine's code · the designers' ear
EVERY QUESTION · goes in GAP_LOG.md (timestamped · verbatim)
EVERY BLOCKER · goes in GAP_LOG.md (what you tried · what you expected)
```

## The schedule

```
Day 1 morning   read the spec · open GAP_LOG.md
Day 1 afternoon parse + envelope · the envelope fixtures green
Day 2 morning   permits + default-deny · fixtures 2-4 green
Day 2 afternoon your verb + the report (the gap log IS the report)
```

## The verdict (what your weekend measures)

| Measure | Consequence |
|---|---|
| ≤ 1 weekend | the golden rule is TRUE — we get to say it publicly, measured |
| > 1 weekend | the spec is too complex — the gap log says where · it gets simplified BEFORE any freeze · then we re-measure |
| abandoned | same, at maximum severity — the freeze is blocked de facto |

The dry-run does not measure you. It measures the spec.
