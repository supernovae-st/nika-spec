#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
#
# run-eval.py — measure the agent-authoring thesis.
#
# Thesis (AGENTS.md §Writing a workflow) · « a weak model following the
# deterministic protocol beats a strong model improvising ». This
# harness turns that from a claim into a number ·
#
#   conditions   protocol  — system prompt = route→instantiate→check→
#                            repair + the matched TEMPLATE file inline
#                freeform  — same model · same intent · just « write a
#                            Nika workflow » + the envelope basics
#   metric       first-pass validity (oracle: conformance runner) ·
#                repair loops needed (≤3 · each loop feeds the exact
#                error list back) · final validity
#
# Model calls go through the `claude` CLI (claude -p · any installed
# model) — swap MODEL_CMD for another provider's CLI to compare engines.
# Without a CLI on PATH the harness exits 2 (env) — it never fakes data.
#
# Usage ·
#   python3 eval/run-eval.py --model haiku --condition both [--limit N]
#   python3 eval/run-eval.py --report eval/results/<file>.json
#
# Output · eval/results/<ts>-<model>.json + a markdown summary table.

from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPEC_ROOT = HERE.parent
sys.path.insert(0, str(SPEC_ROOT / "conformance"))

import yaml  # noqa: E402
from runner import load_canon, load_schema, validate_workflow  # noqa: E402

TEMPLATES = {p.stem.replace(".nika", ""): p for p in (SPEC_ROOT / "templates").glob("*.nika.yaml")}

PROTOCOL_SYSTEM = """You author Nika workflows by the deterministic protocol. Structure is
instantiated, never invented.

1. The canonical TEMPLATE for this job is given below. Copy it.
2. Fill every `# SLOT:` line for the user's intent. Delete slot comments.
   Creativity belongs ONLY in prompts, jq expressions and paths.
3. Hard rules the validator enforces: one verb per task · snake_case
   task ids · kebab-case workflow: · every ${{ tasks.X }} reference
   REQUIRES depends_on: [X] · when: must be a CEL boolean · size() is
   the only CEL function · nika:write needs content: · nika:done only
   inside agent.tools.

Reply with ONLY the final YAML file, inside one ```yaml fence.

TEMPLATE:
```yaml
{template}
```"""

FREEFORM_SYSTEM = """You author Nika workflows. A Nika workflow is a YAML file that starts
with `nika: v1` and `workflow: <kebab-case-id>`, then a `tasks:` list.
Each task has an id and exactly one verb: infer (LLM call), exec
(shell), invoke (tool call, e.g. nika:fetch, nika:write, nika:jq),
or agent (tool-using loop). Values interpolate with ${{ }}.

Reply with ONLY the final YAML file, inside one ```yaml fence."""

REPAIR_PROMPT = """The validator rejected the file with these errors:

{errors}

Fix exactly what the errors name — nothing else. Reply with ONLY the
corrected YAML file, inside one ```yaml fence."""


def call_model(model: str, system: str, prompt: str) -> str:
    cli = shutil.which("claude")
    if not cli:
        print("env-error · `claude` CLI not on PATH — cannot run live eval", file=sys.stderr)
        sys.exit(2)
    r = subprocess.run(
        [cli, "-p", "--model", model, "--append-system-prompt", system],
        input=prompt, capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(f"model call failed · {r.stderr[:200]}")
    return r.stdout


def extract_yaml(reply: str) -> str | None:
    m = re.search(r"```ya?ml\n(.*?)```", reply, re.DOTALL)
    if m:
        return m.group(1)
    if reply.strip().startswith("nika:"):
        return reply.strip() + "\n"
    return None


def validate(text: str, validator, canon) -> list[dict]:
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return [{"namespace": "NIKA-PARSE", "category": "parse_error",
                 "detail": f"YAML does not parse · {str(e)[:120]}"}]
    if not isinstance(doc, dict):
        return [{"namespace": "NIKA-PARSE", "category": "parse_error",
                 "detail": "top level is not a mapping"}]
    return validate_workflow(doc, validator, canon)["errors"]


def fmt_errors(errors: list[dict]) -> str:
    return "\n".join(
        f"- {e.get('code') or e.get('namespace')}: {e.get('detail', '')[:160]}"
        for e in errors[:8])


def run_case(intent: dict, condition: str, model: str, validator, canon) -> dict:
    if condition == "protocol":
        template = TEMPLATES[intent["template_family"]].read_text()
        system = PROTOCOL_SYSTEM.replace("{template}", template)
    else:
        system = FREEFORM_SYSTEM
    record = {"intent": intent["id"], "condition": condition,
              "family": intent["template_family"], "loops": []}
    reply = call_model(model, system, intent["prompt"])
    text = extract_yaml(reply)
    for loop_n in range(4):  # first pass + up to 3 repairs
        if text is None:
            record["loops"].append({"n": loop_n, "errors": ["no yaml fence in reply"]})
            break
        errors = validate(text, validator, canon)
        record["loops"].append({"n": loop_n, "error_count": len(errors),
                                "errors": [e.get("code") or e.get("namespace") for e in errors[:8]]})
        if not errors:
            break
        if loop_n == 3:
            break
        reply = call_model(model, system,
                           intent["prompt"] + "\n\nYour previous file:\n```yaml\n" + text +
                           "```\n\n" + REPAIR_PROMPT.replace("{errors}", fmt_errors(errors)))
        text = extract_yaml(reply)
    record["first_pass_valid"] = bool(record["loops"]) and record["loops"][0].get("error_count") == 0
    record["final_valid"] = bool(record["loops"]) and record["loops"][-1].get("error_count") == 0
    record["repair_loops_used"] = max(0, len(record["loops"]) - 1)
    return record


def summarize(results: list[dict]) -> str:
    lines = ["| Condition | First-pass valid | Final valid | Avg repair loops |",
             "|---|---|---|---|"]
    for cond in ("protocol", "freeform"):
        rows = [r for r in results if r["condition"] == cond]
        if not rows:
            continue
        fp = sum(r["first_pass_valid"] for r in rows)
        fv = sum(r["final_valid"] for r in rows)
        avg = sum(r["repair_loops_used"] for r in rows) / len(rows)
        lines.append(f"| {cond} | {fp}/{len(rows)} | {fv}/{len(rows)} | {avg:.1f} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--condition", choices=["protocol", "freeform", "both"], default="both")
    ap.add_argument("--limit", type=int, default=None, help="run only the first N intents")
    ap.add_argument("--report", help="re-print the summary of an existing results json")
    args = ap.parse_args()

    if args.report:
        data = json.loads(pathlib.Path(args.report).read_text())
        print(summarize(data["results"]))
        return 0

    intents = yaml.safe_load((HERE / "intents.yaml").read_text())["intents"]
    if args.limit:
        intents = intents[:args.limit]
    conditions = ["protocol", "freeform"] if args.condition == "both" else [args.condition]
    validator, canon = load_schema(), load_canon()

    results = []
    for intent in intents:
        for cond in conditions:
            print(f"· {intent['id']} [{cond}] …", flush=True)
            try:
                results.append(run_case(intent, cond, args.model, validator, canon))
            except Exception as e:  # a failed call is DATA, not a crash
                results.append({"intent": intent["id"], "condition": cond,
                                "family": intent["template_family"],
                                "error": str(e)[:200], "loops": [],
                                "first_pass_valid": False, "final_valid": False,
                                "repair_loops_used": 0})

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"{stamp}-{args.model}.json"
    out.write_text(json.dumps({"model": args.model, "results": results}, indent=2))
    print(f"\nwrote {out}\n")
    print(summarize(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
