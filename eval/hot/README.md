# eval/hot — compile-HOT candidate inventory

**Not** the LLM authoring harness ([`../intents.yaml`](../intents.yaml) +
`run-eval.py`). **Not** the official template registry
(`canon/templates/registry.yaml`).

This directory is **research data** for:

- nika#1665 — HOT / prepared / fingerprint / 0 authoring provider calls
- nika#1666 — verified patterns HOT can reuse
- nika#1656 — measurement (false HOT, held-out, latency)

## Law

```
HOT = known semantic structure
    + typed value binding
    + zero provider calls during COMPILE
    + Check still runs
```

A HOT compile **may** emit a workflow whose **Run** still `infer`s / `agent`s.

False HOT (effect/policy/authority mismatch) is worse than a safe WARM/COLD miss.

Template count is **not** a KPI. Recount skeletons from the registry; do not
freeze “22”.

## Files

| File | Role |
|---|---|
| `families.yaml` / `families.json` | Candidate matrix (domains A–J). Status is **not** PROMOTED_HOT. |
| `first-wave.yaml` | High-confidence families to **test** first. |
| `validate.py` | Structural check of the inventory (ids, enums, no Zapier explosion). |

Schedule/trigger is **product** (supernovae#148), not a new skeleton.

Bindings (Gmail vs Slack) are **not** extra families.

```sh
python3 eval/hot/validate.py
```
