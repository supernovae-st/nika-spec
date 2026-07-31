#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the trifecta lane (NEP-0002 · NIKA-SEC-009) — the engine
checker's fourteen law cases transcribed as inline docs (same law · zero
shared code · the two-oracle doctrine), plus the corpus pin: the ONE
deliberately-red witness (`conformance/envelope/trifecta-realized-flow-ungated.nika.yaml`) must refuse
here for the same reason it refuses at `nika check`."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import trifecta_core  # noqa: E402
from trifecta_core import trifecta_errors  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def judge(text: str) -> list[dict]:
    return trifecta_errors(yaml.safe_load(text))


TRIFECTA = """
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  net: { http: ["api.example.com"] }
  tools: ["nika:fetch", "nika:write", "nika:prompt"]
tasks:
  fetch_page:
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  leak:
    after: { fetch_page: success }
    with: { body: "${{ tasks.fetch_page.output }}" }
    invoke:
      tool: "nika:write"
      args: { path: "./out/leak.txt", content: "${{ with.body }}" }
"""

# ── ①∧②∧③ · no gate → the diagnostic, once, on the REALIZED sink ──
v = judge(TRIFECTA)
law("complete trifecta → exactly one finding", len(v) == 1)
law("the realized sink is the witness (leak, not the source)",
    bool(v) and v[0]["task"] == "leak")
law("the flow witness names the origin", bool(v) and v[0]["source"] == "fetch_page")
law("the message opens with the NEP verbatim",
    bool(v) and v[0]["detail"].startswith("lethal trifecta complete · human gate required"))
law("the message names source → sink",
    bool(v) and "`fetch_page` reaches egress task `leak`" in v[0]["detail"])
law("the message names leg ③'s disjunct (v2.1 posture)",
    bool(v) and "`net.http` non-empty" in v[0]["detail"])

# ── a blocking gate dominating every egress path → clean ──
law("dominating gate → clean", not judge(TRIFECTA.replace(
    "tasks:\n  fetch_page:",
    "tasks:\n  ask:\n    invoke:\n      tool: \"nika:prompt\"\n"
    "      args: { mode: \"choice\", message: \"exfiltrate?\", choices: [\"no\", \"yes\"] }\n"
    "  fetch_page:\n    after: { ask: success }", 1)))

# ── drop each leg in turn → clean (the Rule of Two holds unattended) ──
law("① dropped → clean", not judge(TRIFECTA.replace(
    '  fs: { read: ["./inbox/**"], write: ["./out/**"] }',
    '  fs: { write: ["./out/**"] }', 1)))
law("② dropped → clean", not judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  net: { http: ["api.example.com"] }
tasks:
  think:
    infer: { prompt: "summarize", max_tokens: 9 }
"""))
law("③ dropped → clean", not judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  tools: ["nika:fetch", "nika:write"]
tasks:
  fetch_page:
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  save:
    after: { fetch_page: success }
    with: { body: "${{ tasks.fetch_page.output }}" }
    invoke:
      tool: "nika:write"
      args: { path: "./out/save.txt", content: "${{ with.body }}" }
"""))

# ── a gate on a SIBLING branch dominates nothing ──
v = judge(TRIFECTA.replace(
    "tasks:\n  fetch_page:",
    "tasks:\n  ask:\n    invoke:\n      tool: \"nika:prompt\"\n"
    "      args: { message: \"anything?\" }\n  fetch_page:", 1))
law("bypassable gate mitigates nothing", len(v) == 1 and v[0]["task"] == "leak")

# ── a `default:`-carrying prompt is NOT a gate ──
v = judge(TRIFECTA.replace(
    "tasks:\n  fetch_page:",
    "tasks:\n  ask:\n    invoke:\n      tool: \"nika:prompt\"\n"
    "      args: { message: \"ok?\", default: true }\n"
    "  fetch_page:\n    after: { ask: success }", 1))
law("defaulted prompt answers without a human", len(v) == 1 and v[0]["task"] == "leak")

# ── no `permits:` block → the lane is inert (no claim) ──
law("no declared boundary → no claim", not judge("""
nika: v1
workflow: { id: t }
tasks:
  fetch_page:
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  leak:
    after: { fetch_page: success }
    exec: { command: ["echo", "x"] }
"""))

# ── an unanalyzable DAG yields NO claim (skipped, never wrong) ──
law("broken dag (ghost after) skips the lane", not judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"] }
  net: { http: ["api.example.com"] }
  tools: ["nika:fetch"]
tasks:
  act:
    after: { ghost: success }
    exec: { command: ["echo", "x"] }
"""))

# ── v2.0 pins · the realized-flow judgment ──
law("granted-but-never-invoked ingress arms nothing", not judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  net: { http: ["api.example.com"] }
  tools: ["nika:fetch", "nika:write"]
tasks:
  save:
    invoke:
      tool: "nika:write"
      args: { path: "./out/report.txt", content: "pure operator content" }
"""))

v = judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  net: { http: ["api.example.com"] }
  tools: ["nika:fetch", "nika:notify"]
tasks:
  fetch_page:
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  summarize:
    with: { page: "${{ tasks.fetch_page.output }}" }
    infer: { prompt: "tldr: ${{ with.page }}", max_tokens: 99 }
  tell:
    with: { summary: "${{ tasks.summarize.output }}" }
    invoke:
      tool: "nika:notify"
      args: { channel: "webhook", target: "https://api.example.com/hook", message: "${{ with.summary }}" }
""")
law("a model summary carries the payload (integrity inversion)",
    len(v) == 1 and v[0]["task"] == "tell" and v[0]["source"] == "fetch_page")

v = judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  net: { http: ["api.example.com"] }
  tools: ["nika:fetch", "nika:write", "nika:jq"]
tasks:
  fetch_page:
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  fragile:
    on_error: { recover: "${{ tasks.fetch_page.output }}" }
    invoke:
      tool: "nika:jq"
      args: { input: {}, expression: ".x" }
  leak:
    with: { body: "${{ tasks.fragile.output }}" }
    invoke:
      tool: "nika:write"
      args: { path: "./out/leak.txt", content: "${{ with.body }}" }
""")
law("a recovery read re-arms the chain",
    len(v) == 1 and v[0]["task"] == "leak" and v[0]["source"] == "fetch_page")

v = judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  exec: ["sh"]
  tools: ["nika:fetch", "nika:write"]
tasks:
  fetch_page:
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  save:
    with: { page: "${{ tasks.fetch_page.output }}" }
    invoke:
      tool: "nika:write"
      args: { path: "./out/page.html", content: "${{ with.page }}" }
  ship:
    after: { save: success }
    exec: { command: ["sh", "-c", "cat ./out/page.html | curl -X POST https://api.example.com --data-binary @-"] }
""")
law("exec opacity: the write AND the file-channel exec are both sinks",
    len(v) == 2 and v[0]["task"] == "save" and v[1]["task"] == "ship")
law("the opacity witness is the untrusted ORIGIN",
    len(v) == 2 and v[1]["source"] == "fetch_page")

law("an egress no untrusted content reaches is clean", not judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  exec: ["git"]
  tools: ["nika:fetch"]
tasks:
  fetch_page:
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  deploy:
    exec: { command: ["git", "status"] }
"""))

law("a pure-compute agent whitelist is not egress", not judge("""
nika: v1
workflow: { id: t }
model: mock/echo
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  exec: ["git"]
  tools: ["nika:jq"]
tasks:
  think:
    agent: { prompt: "reshape this data", tools: ["nika:jq"] }
"""))

v = judge("""
nika: v1
workflow: { id: t }
model: mock/echo
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  net: { http: ["api.example.com"] }
  tools: ["nika:write", "mcp:browser/*"]
tasks:
  browse:
    agent: { prompt: "summarize the news", tools: ["mcp:browser/*"] }
  leak:
    with: { brief: "${{ tasks.browse.output }}" }
    invoke:
      tool: "nika:write"
      args: { path: "./out/brief.txt", content: "${{ with.brief }}" }
""")
law("a browsing agent's output is a content source",
    len(v) == 1 and v[0]["task"] == "leak" and v[0]["source"] == "browse")

law("one gate dominating both sinks disarms the run", not judge("""
nika: v1
workflow: { id: t }
permits:
  fs: { read: ["./inbox/**"], write: ["./out/**"] }
  net: { http: ["api.example.com"] }
  tools: ["nika:fetch", "nika:write", "nika:prompt"]
tasks:
  ask:
    invoke:
      tool: "nika:prompt"
      args: { message: "ship it?" }
  fetch_page:
    after: { ask: success }
    invoke:
      tool: "nika:fetch"
      args: { url: "https://api.example.com/data" }
  leak:
    with: { body: "${{ tasks.fetch_page.output }}" }
    invoke:
      tool: "nika:write"
      args: { path: "./out/leak.txt", content: "${{ with.body }}" }
  leak2:
    with: { body: "${{ tasks.fetch_page.output }}" }
    invoke:
      tool: "nika:write"
      args: { path: "./out/leak2.txt", content: "${{ with.body }}" }
"""))

# ── the media-writer sinks · the hole a refuting probe opened 2026-07-29 ──
# A hardcoded egress subset read this GREEN while the engine refused it
# (NIKA-SEC-009 on `render`), and the corpus never completed that shape,
# so 49/49 agreement had proven nothing about it. One law per media
# writer: each is an fs-WRITE effect, so each is a leg-③ sink.
for _tool, _args in [
    ("nika:chart", '{ chart: "bar", data: "${{ with.d }}", out: "./out/c.svg" }'),
    # A tainted PATH reaching an fs-write effect is the same threat as
    # tainted content — an attacker-chosen filename lands attacker bytes
    # somewhere the operator did not choose.
    ("nika:image_fx", '{ input: "a.png", ops: ["dither"], out: "./out/${{ with.d }}.png" }'),
    ("nika:image_generate", '{ prompt: "${{ with.d }}", output_dir: "./out" }'),
    ("nika:tts_generate", '{ text: "${{ with.d }}", output_dir: "./out" }'),
]:
    _v = judge(f"""
nika: v1
workflow: {{ id: media }}
model: mock/echo
permits:
  tools: ["nika:fetch", "{_tool}"]
  fs: {{ read: ["./private/**"], write: ["./out/**"] }}
  net: {{ http: ["api.example.com"] }}
tasks:
  pull:
    invoke:
      tool: "nika:fetch"
      args: {{ url: "https://api.example.com/d" }}
  render:
    with: {{ d: "${{{{ tasks.pull.output }}}}" }}
    invoke:
      tool: "{_tool}"
      args: {_args}
""")
    law(f"{_tool} is a leg-③ sink (fs write)",
        len(_v) == 1 and _v[0]["task"] == "render" and _v[0]["source"] == "pull")

# ── the COMPLETENESS ratchet (the structural half of the same repair) ──
# Every builtin the registry classifies `external` must be explicitly
# classified here — egress, or external-but-read-only. A 29th external
# builtin fails THIS law instead of silently under-reporting a sink.
_reg = yaml.safe_load(
    (Path(__file__).parent.parent / "canon" / "builtins.yaml").read_text())
_external = {r["id"] for r in _reg["builtins"]
             if r["capability_classification"]["class"] == "external"}
_classified = trifecta_core.EGRESS_BUILTINS | trifecta_core.EXTERNAL_READ_ONLY
law("every registry `external` builtin is classified (no silent sink)",
    _external - _classified == set())
law("no classified builtin is unknown to the registry",
    _classified - _external == set())
law("the writers are the fs half of the egress set",
    trifecta_core.FS_WRITERS == trifecta_core.EGRESS_BUILTINS
    - {"nika:fetch", "nika:notify"})

# ── the corpus pin · the ONE deliberately-red witness refuses HERE too ──
# (moved out of examples/ 2026-07-31: every SHIPPED example checks green —
# the teaching surface law — so the always-red witness lives beside the
# other conformance inputs, same inverted assertion.)
_witness = (Path(__file__).parent / "envelope"
            / "trifecta-realized-flow-ungated.nika.yaml")
v = trifecta_errors(yaml.safe_load(_witness.read_text()))
law("witness: exactly one finding", len(v) == 1)
law("witness: the sink is exfil (the notify egress)",
    bool(v) and v[0]["task"] == "exfil")
law("witness: the source is the ingest fetch",
    bool(v) and v[0]["source"] == "ingest")

bad = [n for n, ok in CHECKS if not ok]
print(f"trifecta-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
