# Baseline partial · qwen3.5:9b · k=3 · 2026-07-05

**Arm** · weakest docs bundle (llms.txt INDEX + one template · no chapter
content) · think:false · num_predict 1536 · local via ollama on a
contended M3 Pro (t3/t4 half stalled under GPU ping-pong with a parallel
session — rerun idle).

| task | L1 (nika check) | L1+L2 (expect) | pass^k |
|---|---|---|---|
| t1-hello-local | 3/3 | 2/3 | ✔ |
| t1-summarize-file | 3/3 | 3/3 | ✔ |
| t2-classify-structured | 2/3 | 0/3 | ✖ |
| t2-fetch-and-brief | 1/3 | 1/3 | ✔ |
| t2-retry-flaky | 0/3 | 0/3 | ✖ |

**PARTIAL (t1+t2 · 15 gens) · L1 60% · L1+L2 40%**

## The qualitative finding (the bench's value prop · live)

`t2-retry-flaky-g0`: the model invented `retries:`/`backoff:` as
`nika:fetch` ARGS (the real grammar is the task-level `retry:` block) —
plausible, wrong, and **`nika check` caught it at the ARGS rung before
any token**: `✖ ARGS · nika:fetch has no 'backoff' arg`. On the
index-only docs arm the model guesses grammar it never saw; the static
ladder is exactly the net the thesis claims. Next arms (chapters
included · llms-full) should close most of the L1 gap — that DELTA is
the measurable value of docs-in-context.
