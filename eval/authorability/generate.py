#!/usr/bin/env python3
# generate.py · the authorability bench runner (local-first baseline)
# License · Apache-2.0 (part of the Nika spec)
#
# Protocol (README): docs-bundle + intent → model writes a *.nika.yaml →
# L1 judge = `nika check` (parse + static ladder) · L2 judge = the task's
# expect-block (verbs · DAG bounds · constructs) · pass^k over k gens.
#
# Local baseline = ollama (zero key · the sovereignty column). Frontier
# runs reuse the same harness via OPENAI-compatible endpoints later.
#
# Usage ·
#   python3 eval/authorability/generate.py --model qwen3.5:9b --k 3
#   python3 eval/authorability/generate.py --tasks t1-hello-local --k 1
# Outputs · eval/authorability/runs/<model>-k<k>-<stamp>/ (gens + verdicts
# jsonl + summary.md). Requires: ollama serving · nika on PATH.

import argparse, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_ROOT = ROOT.parent.parent

def docs_bundle() -> str:
    # The graduated in-context arm (Text2DSL-class): the curated index +
    # the two chapters a generator actually needs + one worked example.
    parts = []
    for rel in ["llms.txt", "templates/chain.nika.yaml"]:
        p = SPEC_ROOT / rel
        if p.is_file():
            parts.append(f"\n=== {rel} ===\n" + p.read_text(encoding="utf-8"))
    return "".join(parts)

PROMPT = """You are writing a Nika workflow file (*.nika.yaml).

Nika docs (authoritative · follow them exactly):
{docs}

Task intent:
{intent}

Rules:
- Output ONE complete workflow inside a single ```yaml fenced block.
- Start with `nika: v1`. Use only documented verbs/constructs.
- No commentary outside the fence.
"""

def ollama_generate(model: str, prompt: str, timeout: int = 600) -> str:
    # think:false + a hard num_predict cap — measured 2026-07-05: with
    # thinking ON, num_predict caps thinking+content TOGETHER and the
    # reasoning devours the whole budget (7.5k thinking chars · content
    # EMPTY · 103s); think:false yields the fenced yaml in 18s. The bench
    # measures direct authoring; a thinking arm is a separate future
    # column, not the default.
    body = json.dumps({
        "model": model, "stream": False, "think": False,
        "options": {"temperature": 0.7, "num_ctx": 8192, "num_predict": 1536},
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["message"]["content"]

def extract_yaml(text: str) -> str | None:
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.S)
    if m:
        return m.group(1)
    return text if text.strip().startswith("nika:") else None

def judge_l1(path: Path) -> tuple[bool, str]:
    r = subprocess.run(["nika", "check", str(path)],
                       capture_output=True, text=True, timeout=120)
    return r.returncode == 0, (r.stdout + r.stderr)[-400:]

def judge_l2(yaml_text: str, expect: dict) -> tuple[bool, list[str]]:
    fails = []
    for verb in expect.get("verbs", []):
        if not re.search(rf"^\s*{verb}\s*:", yaml_text, re.M):
            fails.append(f"missing verb {verb}")
    tasks = len(re.findall(r"^\s*-\s*id\s*:", yaml_text, re.M))
    lo, hi = expect.get("min_tasks", 0), expect.get("max_tasks", 999)
    if not (lo <= tasks <= hi):
        fails.append(f"task count {tasks} outside [{lo},{hi}]")
    for c in expect.get("constructs", []):
        if c not in yaml_text:
            fails.append(f"missing construct {c}")
    return not fails, fails

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:9b")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--tasks", default="")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in (ROOT / "tasks.jsonl").open()]
    if args.tasks:
        keep = set(args.tasks.split(","))
        tasks = [t for t in tasks if t["id"] in keep]

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = ROOT / "runs" / f"{args.model.replace(':','_').replace('/','_')}-k{args.k}-{stamp}"
    out.mkdir(parents=True)
    docs = docs_bundle()
    verdicts = []

    for t in tasks:
        for k in range(args.k):
            gen_id = f"{t['id']}-g{k}"
            try:
                raw = ollama_generate(args.model, PROMPT.format(docs=docs, intent=t["intent"]))
            except Exception as e:
                verdicts.append({"gen": gen_id, "l1": False, "l2": False, "err": f"gen: {e}"})
                print(f"✖ {gen_id} · generation failed: {e}", flush=True)
                continue
            yml = extract_yaml(raw)
            if yml is None:
                verdicts.append({"gen": gen_id, "l1": False, "l2": False, "err": "no yaml fence"})
                print(f"✖ {gen_id} · no yaml block", flush=True)
                continue
            p = out / f"{gen_id}.nika.yaml"
            p.write_text(yml, encoding="utf-8")
            ok1, detail = judge_l1(p)
            ok2, fails = judge_l2(yml, t.get("expect", {}))
            verdicts.append({"gen": gen_id, "task": t["id"], "l1": ok1, "l2": ok2,
                             "l1_tail": detail if not ok1 else "", "l2_fails": fails})
            print(f"{'✔' if ok1 and ok2 else '✖'} {gen_id} · L1={ok1} L2={ok2} {fails or ''}", flush=True)

    (out / "verdicts.jsonl").write_text(
        "\n".join(json.dumps(v) for v in verdicts) + "\n", encoding="utf-8")

    # summary · per-task pass^k + the headline rates
    by = {}
    for v in verdicts:
        if "task" in v:
            by.setdefault(v["task"], []).append(v)
    lines = [f"# Run summary · {args.model} · k={args.k} · {stamp}", "",
             "| task | L1 pass | L1+L2 pass | pass^k (any) |", "|---|---|---|---|"]
    tot1 = tot12 = n = 0
    for tid, vs in by.items():
        l1 = sum(1 for v in vs if v["l1"]); both = sum(1 for v in vs if v["l1"] and v["l2"])
        tot1 += l1; tot12 += both; n += len(vs)
        lines.append(f"| {tid} | {l1}/{len(vs)} | {both}/{len(vs)} | {'✔' if both else '✖'} |")
    if n:
        lines += ["", f"**L1 rate {tot1}/{n} ({100*tot1//n}%) · L1+L2 rate {tot12}/{n} ({100*tot12//n}%)**"]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-2:]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
