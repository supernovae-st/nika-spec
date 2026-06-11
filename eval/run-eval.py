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
# Model syntax mirrors the spec's own `model:` convention ·
# `<provider>/<name>` — providers: claude · gemini · openai · ollama
# (local). A bare name defaults to the claude provider. Each adapter
# shells out to that provider's CLI; without it on PATH the harness
# exits 2 (env) — it never fakes data. A non-zero CLI exit is recorded
# as DATA (some CLIs print the error on stdout · both streams kept).
#
# Auth note (claude) · with ANTHROPIC_API_KEY exported, `claude -p`
# bills the API key. To use your subscription login instead, strip it
# at invocation · `env -u ANTHROPIC_API_KEY python3 eval/run-eval.py …`
# — auth belongs to the caller, the harness never mutates it.
#
# Usage ·
#   python3 eval/run-eval.py --model haiku --condition both [--limit N]
#   python3 eval/run-eval.py --model ollama/llama3.2:3b
#   python3 eval/run-eval.py --model gemini/gemini-2.5-flash
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
   REQUIRES depends_on: [X] · when: is a ${{ }} CEL boolean or the
   literal true/false (a bare string is rejected) · size() is the only
   CEL function · nika:jq's arg is `expression:` (never query/expr) ·
   nika:wait takes duration: XOR until: · nika:write needs content: ·
   nika:done only inside agent.tools · output: bindings are pure jq
   (never ${{ }} inside them) · timeout is a QUOTED Go-duration.

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


CALL_TIMEOUT = 240  # seconds · override with --timeout (local models load slowly)

# Agentic CLIs (claude · gemini) are NOT raw models — run from a repo they
# load workspace context (CLAUDE.md cascade · tools) and act on it: ask
# clarifying questions · read the tree · even EXECUTE the intent instead of
# authoring the workflow (observed empirically · 2026-06-10 haiku grid ·
# 19/24 replies were agent behavior, one cited « Based on the CLAUDE.md
# context »). The benchmark measures the MODEL on the PROMPT, so those
# adapters run context-free: neutral empty cwd · tools disabled · system
# prompt REPLACED (append leaves the agent persona in charge).
_NEUTRAL_CWD: str | None = None


def _neutral_cwd() -> str:
    global _NEUTRAL_CWD
    if _NEUTRAL_CWD is None:
        import tempfile
        _NEUTRAL_CWD = tempfile.mkdtemp(prefix="nika-eval-neutral-")
    return _NEUTRAL_CWD


# Strip ANSI/VT escape sequences. Some CLIs (ollama run) emit a progress
# SPINNER to the pipe even when not a TTY — cursor-hide, line-clear, sync-
# update + braille frames (^[[?25l ^[[K ^[[?2026h …). Left in, those bytes
# corrupt the captured YAML (the confounded 0/12 local-model grid · 2026-06-10).
# Covers CSI (^[[…), the ?-private modes (^[[?2026h), and OSC (^[]…BEL).
_ANSI = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|\][^\x07]*\x07|[@-Z\\-_])")


def _strip_ansi(s: str) -> str:
    return _ANSI.sub("", s)


def _run_cli(binary: str, argv: list[str], stdin_text: str | None,
             cwd: str | None = None, extra_env: dict | None = None) -> str:
    cli = shutil.which(binary)
    if not cli:
        print(f"env-error · `{binary}` CLI not on PATH — cannot run live eval", file=sys.stderr)
        sys.exit(2)
    import os
    env = {**os.environ, **extra_env} if extra_env else None
    r = subprocess.run([cli, *argv], input=stdin_text, cwd=cwd, env=env,
                       capture_output=True, text=True, timeout=CALL_TIMEOUT)
    if r.returncode != 0:
        # some CLIs report the failure on stdout (e.g. billing errors)
        detail = (_strip_ansi(r.stderr).strip() or _strip_ansi(r.stdout).strip())[:200]
        raise RuntimeError(f"model call failed · exit {r.returncode} · {detail}")
    # Defensive strip on EVERY adapter — escape bytes are never valid YAML.
    return _strip_ansi(r.stdout)


def call_model(model: str, system: str, prompt: str) -> str:
    provider, _, name = model.partition("/")
    if not name:
        provider, name = "claude", model
    if provider == "claude":
        # NO --bare · it skips credential loading (« Not logged in » · observed)
        return _run_cli("claude", ["-p", "--model", name, "--tools", "",
                                   "--system-prompt", system],
                        prompt, cwd=_neutral_cwd())
    if provider == "gemini":
        # headless mode · no system slot → system prepended to the prompt
        return _run_cli("gemini", ["-m", name, "-p", f"{system}\n\n{prompt}"],
                        None, cwd=_neutral_cwd())
    if provider == "openai":
        return _run_cli("openai", ["api", "chat.completions.create", "-m", name,
                                   "-g", "system", system, "-g", "user", prompt], None)
    if provider == "ollama":
        # local · no key · no system slot → system prepended on stdin.
        # TERM=dumb + NO_COLOR suppress `ollama run`'s progress spinner (it
        # writes VT escapes to the pipe even when not a TTY · verified
        # 2026-06-11); _strip_ansi is the belt-and-suspenders backstop.
        return _run_cli("ollama", ["run", name], f"{system}\n\n{prompt}",
                        extra_env={"TERM": "dumb", "NO_COLOR": "1"})
    print(f"env-error · unknown provider '{provider}' · known: claude · gemini · openai · ollama",
          file=sys.stderr)
    sys.exit(2)


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
    # 220 chars keeps the prescriptive tail (path + allowed keys) intact
    return "\n".join(
        f"- {e.get('code') or e.get('namespace')}: {e.get('detail', '')[:220]}"
        for e in errors[:8])


ROUTING_SYSTEM = """You author Nika workflows by the deterministic protocol — but FIRST
you must ROUTE: pick the ONE canonical template family for the job from
the routing table below, then instantiate it mentally (you know the 6
skeleton shapes: chain · gate-and-act · fanout · etl-state · agent-loop ·
human-gated-ship).

ROUTING TABLE:
{routing}

Reply with the family name on the FIRST line (exactly one of the 6 ids),
then the final YAML file inside one ```yaml fence."""


def run_case(intent: dict, condition: str, model: str, validator, canon) -> dict:
    if condition == "protocol":
        template = TEMPLATES[intent["template_family"]].read_text()
        system = PROTOCOL_SYSTEM.replace("{template}", template)
    elif condition == "routing":
        # the routing arm · the model PICKS the family (scored vs ground
        # truth) and authors WITHOUT the template body — measures the
        # router half of the thesis that 'protocol' holds constant.
        routing_table = (SPEC_ROOT / "templates" / "README.md").read_text()
        system = ROUTING_SYSTEM.replace("{routing}", routing_table)
    else:
        system = FREEFORM_SYSTEM
    record = {"intent": intent["id"], "condition": condition,
              "family": intent["template_family"], "loops": []}
    reply = call_model(model, system, intent["prompt"])
    if condition == "routing":
        first_line = reply.strip().splitlines()[0].strip().strip("`").lower() if reply.strip() else ""
        record["routed_family"] = first_line
        record["routing_correct"] = first_line == intent["template_family"]
    text = extract_yaml(reply)
    for loop_n in range(4):  # first pass + up to 3 repairs
        if text is None:
            # keep the reply head — distinguishes a rambling model from a
            # CLI that reported an error on stdout (limits · billing)
            record["loops"].append({"n": loop_n, "errors": ["no yaml fence in reply"],
                                    "reply_head": reply.strip()[:200]})
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
    if not record["final_valid"] and text:
        # keep the failing artifact — clusters are named from evidence, not memory
        record["final_yaml"] = text[:4000]
    return record


def summarize(results: list[dict]) -> str:
    lines = ["| Condition | First-pass valid | Final valid | Avg repair loops |",
             "|---|---|---|---|"]
    for cond in ("protocol", "routing", "freeform"):
        rows = [r for r in results if r["condition"] == cond]
        if not rows:
            continue
        fp = sum(r["first_pass_valid"] for r in rows)
        fv = sum(r["final_valid"] for r in rows)
        avg = sum(r["repair_loops_used"] for r in rows) / len(rows)
        cell = f"| {cond} | {fp}/{len(rows)} | {fv}/{len(rows)} | {avg:.1f} |"
        routed = [r for r in rows if "routing_correct" in r]
        if routed:
            ok = sum(r["routing_correct"] for r in routed)
            cell += f" routing {ok}/{len(routed)} |"
        lines.append(cell)
    return "\n".join(lines)


def clusters(runs: list[dict]) -> str:
    """Aggregate failure codes across runs · the README's feedback table input."""
    agg: dict[str, dict] = {}
    for run in runs:
        for r in run["results"]:
            seen_in_record = set()
            for loop in r.get("loops", []):
                for code in loop.get("errors", []):
                    key = code if isinstance(code, str) else str(code)
                    c = agg.setdefault(key, {"count": 0, "families": set(),
                                             "conditions": set(), "models": set()})
                    c["count"] += 1
                    seen_in_record.add(key)
            for key in seen_in_record:
                agg[key]["families"].add(r["family"])
                agg[key]["conditions"].add(r["condition"])
                agg[key]["models"].add(run["model"])
    if not agg:
        return "(no failures · nothing to cluster)"
    lines = ["| Code | Hits | Families | Conditions | Models |", "|---|---|---|---|---|"]
    for code, c in sorted(agg.items(), key=lambda kv: -kv[1]["count"]):
        lines.append(f"| {code} | {c['count']} | {' '.join(sorted(c['families']))} "
                     f"| {' '.join(sorted(c['conditions']))} | {' '.join(sorted(c['models']))} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--condition", choices=["protocol", "routing", "freeform", "both", "all"], default="both")
    ap.add_argument("--limit", type=int, default=None, help="run only the first N intents")
    ap.add_argument("--timeout", type=int, default=240,
                    help="per-call timeout in seconds (raise for local models)")
    ap.add_argument("--report", nargs="+",
                    help="re-print summary of existing results json(s) · "
                         "N files → per-model tables + the failure-cluster table")
    args = ap.parse_args()
    global CALL_TIMEOUT
    CALL_TIMEOUT = args.timeout

    if args.report:
        runs = [json.loads(pathlib.Path(p).read_text()) for p in args.report]
        for run in runs:
            print(f"\n## {run['model']}\n")
            print(summarize(run["results"]))
        if len(runs) > 1 or any(not r["final_valid"] for run in runs for r in run["results"]):
            print("\n## failure clusters (codes → the fix lands per eval/README)\n")
            print(clusters(runs))
        return 0

    if args.model.startswith("ollama/"):
        # pre-warm OUTSIDE the per-case budget · cold model load (and a
        # loaded machine) otherwise eats the whole case timeout — observed
        # 2026-06-11: even a 0.5b timed out at 240s under concurrent cargo
        # builds because load+first-token landed inside the case window.
        name = args.model.partition("/")[2]
        print(f"· pre-warming {name} …", flush=True)
        try:
            subprocess.run(["ollama", "run", name], input="Say OK",
                           capture_output=True, text=True, timeout=600)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"⚠ pre-warm failed ({e.__class__.__name__}) — the machine may be "
                  "too loaded for local eval right now", flush=True)

    intents = yaml.safe_load((HERE / "intents.yaml").read_text())["intents"]
    if args.limit:
        intents = intents[:args.limit]
    conditions = {"both": ["protocol", "freeform"],
                  "all": ["protocol", "routing", "freeform"]}.get(args.condition, [args.condition])
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
    safe_model = re.sub(r"[^A-Za-z0-9._-]+", "-", args.model)
    out = out_dir / f"{stamp}-{safe_model}.json"
    oracle_sha = subprocess.run(["git", "-C", str(SPEC_ROOT), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip() or "unknown"
    dirty = bool(subprocess.run(["git", "-C", str(SPEC_ROOT), "status", "--porcelain",
                                 "conformance/", "schemas/", "canon.yaml",
                                 "templates/", "eval/"],
                                capture_output=True, text=True).stdout.strip())
    out.write_text(json.dumps({"model": args.model,
                               "oracle": oracle_sha + ("-dirty" if dirty else ""),
                               "results": results}, indent=2))
    print(f"\nwrote {out}\n")
    print(summarize(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
