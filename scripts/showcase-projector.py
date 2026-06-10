#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# showcase-projector.py — project examples/showcase/*.nika.yaml (the
# single source for every public workflow example) into the consumer
# surfaces. Sister of canon-projectors.py (canon.yaml → counts) · same
# law (projection-by-default) · same modes (--write | --check).
#
#   TARGET 1 · nika-docs   examples/<slug>.mdx     managed yaml block
#              (between `{/* showcase:begin <file> */}` and
#               `{/* showcase:end */}` markers · prose around the block
#               stays hand-crafted · the YAML inside is machine-owned)
#   TARGET 2 · nika.sh     src/sections/usecases-yaml.generated.ts
#              (slug → lean yaml string · fully generated module)
#
# « Lean » rendering · the SPDX header, the yaml-language-server hint
# and the leading comment banner are stripped for display (the prose
# explains; the file teaches) — body comments are kept.
#
# Target path resolution (priority order):
#   docs    · $NIKA_DOCS_ROOT    · else <spec-root>/../docs/
#   website · $NIKA_WEBSITE_SRC  · else <spec-root>/../website/src/
#   (a missing sibling is SKIPPED · standalone spec clones project nothing)
#
# Exit codes · 0 in-sync/written · 1 drift (--check) · 2 environment error.

import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("showcase-projector · pyyaml required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

SPEC_ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = SPEC_ROOT / "examples" / "showcase"

BEGIN = re.compile(r"\{/\* showcase:begin ([a-z0-9-]+\.nika\.yaml) \*/\}")
END = "{/* showcase:end */}"
DAG_BEGIN = re.compile(r"\{/\* showcase:dag-begin ([a-z0-9-]+\.nika\.yaml) \*/\}")
DAG_END = "{/* showcase:dag-end */}"
COVERAGE_BEGIN = "{/* showcase:coverage-begin */}"
COVERAGE_END = "{/* showcase:coverage-end */}"

MERMAID_CLASSES = (
    "  classDef infer fill:#5b8cff22,stroke:#5b8cff,color:#5b8cff\n"
    "  classDef exec fill:#ff7a3c22,stroke:#ff7a3c,color:#ff7a3c\n"
    "  classDef invoke fill:#22d3ee22,stroke:#22d3ee,color:#22d3ee\n"
    "  classDef agent fill:#b07bff22,stroke:#b07bff,color:#b07bff"
)


def lean(yaml_text: str) -> str:
    """Strip the comment banner (everything before the `nika: v1` line)."""
    lines = yaml_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("nika:"):
            return "\n".join(lines[i:]).rstrip() + "\n"
    print("showcase-projector · no `nika:` envelope line found", file=sys.stderr)
    sys.exit(2)


def load_showcase() -> dict[str, str]:
    if not SHOWCASE.is_dir():
        print(f"showcase-projector · {SHOWCASE} missing", file=sys.stderr)
        sys.exit(2)
    files = sorted(SHOWCASE.glob("*.nika.yaml"))
    if not files:
        print("showcase-projector · no showcase files", file=sys.stderr)
        sys.exit(2)
    return {f.name: lean(f.read_text()) for f in files}


def _task_lines(lean_text: str) -> dict[str, tuple[int, int]]:
    """0-based [start, end] line range of each task block in the LEAN yaml
    (the exact string the website renders · ranges drive the run-sim
    highlight)."""
    lines = lean_text.splitlines()
    starts: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^  - id: ([a-z][a-z0-9_]*)\s*$", line)
        if m:
            starts.append((m.group(1), i))
    ranges: dict[str, tuple[int, int]] = {}
    for n, (tid, start) in enumerate(starts):
        if n + 1 < len(starts):
            end = starts[n + 1][1] - 1
        else:
            end = len(lines) - 1
            for j in range(start + 1, len(lines)):
                if re.match(r"^[a-z]", lines[j]):  # next top-level key (outputs:)
                    end = j - 1
                    break
        while end > start and not lines[end].strip():
            end -= 1
        ranges[tid] = (start, end)
    return ranges


def _gloss(task: dict) -> str:
    """One plain-words line per task · what this action does (run-sim caption)."""
    if "infer" in task:
        body = task["infer"] or {}
        g = "ask the model for typed JSON" if isinstance(body, dict) and body.get("schema") else "ask the model"
        if isinstance(body, dict) and body.get("thinking"):
            g += " · thinking budget"
    elif "exec" in task:
        body = task["exec"] or {}
        cmd = (body.get("command", "") if isinstance(body, dict) else str(body)).strip()
        head = cmd.split()[0] if cmd.split() else "a command"
        g = f"run `{head}`"
    elif "invoke" in task:
        body = task["invoke"] or {}
        tool = body.get("tool", "a tool") if isinstance(body, dict) else "a tool"
        g = f"call `{tool}`"
    elif "agent" in task:
        body = task["agent"] or {}
        tools = body.get("tools") if isinstance(body, dict) else None
        n = len(tools) if isinstance(tools, list) else 0
        g = f"run an agent loop · {n} tools granted" if n else "run an agent loop · no tools (pure conversation)"
    else:
        g = "do its one thing"
    if "for_each" in task:
        g = "for each item · " + g
    if "when" in task:
        g += " — only if its condition holds"
    return g


def _flags(task: dict) -> list[str]:
    flags: list[str] = []
    if "for_each" in task:
        mp = task.get("max_parallel")
        flags.append(f"fan-out · ≤{mp} in flight" if mp else "fan-out")
        if task.get("fail_fast") is False:
            flags.append("collects errors")
    if "when" in task:
        flags.append("conditional")
    if "retry" in task:
        flags.append("retry")
    if "timeout" in task:
        flags.append(f"timeout {task['timeout']}")
    if "on_finally" in task:
        flags.append("cleanup always runs")
    for verb in ("infer", "agent"):
        body = task.get(verb)
        if isinstance(body, dict) and body.get("schema"):
            flags.append("typed output")
            break
    return flags


def _node_label(task: dict, tid: str) -> str:
    """Short diagram label · id + the load-bearing detail."""
    detail = ""
    if "invoke" in task and isinstance(task["invoke"], dict):
        detail = task["invoke"].get("tool", "")
    elif "exec" in task and isinstance(task["exec"], dict):
        cmd = (task["exec"].get("command") or "").strip()
        detail = cmd.split()[0] if cmd.split() else ""
    elif "infer" in task and isinstance(task["infer"], dict):
        if task["infer"].get("schema"):
            detail = "typed"
        if task["infer"].get("thinking"):
            detail = "thinking"
    elif "agent" in task and isinstance(task["agent"], dict):
        tools = task["agent"].get("tools") or []
        detail = f"{len(tools)} tools"
    parts = [tid]
    if "for_each" in task:
        parts.append("∥ for_each")
    if detail:
        parts.append(detail)
    return " · ".join(parts)


def render_mermaid(lean_text: str) -> str:
    """The docs DAG diagram · GENERATED from the same yaml (drift-proof) ·
    canonical verb palette · conditional edges dashed with the when label."""
    doc = yaml.safe_load(lean_text)
    tasks = doc.get("tasks") or []
    lines = ["flowchart LR"]
    verbs = {}
    for t in tasks:
        tid = t.get("id")
        verb = next((v for v in ("infer", "exec", "invoke", "agent") if v in t), "invoke")
        verbs[tid] = verb
        label = _node_label(t, tid).replace('"', "'")
        lines.append(f'  {tid}["{label}"]:::{verb}')
    for t in tasks:
        tid = t.get("id")
        arrow = "-.->" if "when" in t else "-->"
        for d in (t.get("depends_on") or []):
            lines.append(f"  {d} {arrow} {tid}")
    used = sorted(set(verbs.values()))
    cls = [c for c in MERMAID_CLASSES.split("\n")
           if any(f"classDef {v} " in c for v in used)]
    return "\n".join(lines + cls) + "\n"


# construct → (detector over the parsed doc · human label · reference href)
CONSTRUCTS = [
    ("for_each",      "fan-out over a collection",         "/concepts/workflows"),
    ("max_parallel",  "bounded concurrency",               "/concepts/workflows"),
    ("fail_fast",     "collect-errors batches",            "/concepts/workflows"),
    ("when",          "CEL conditional gate",              "/concepts/workflows"),
    ("retry",         "transient-error retry",             "/reference/error-codes"),
    ("timeout",       "task time-bound",                   "/concepts/workflows"),
    ("on_finally",    "cleanup that always runs",          "/concepts/workflows"),
    ("on_error",      "fallback recovery",                 "/reference/error-codes"),
    ("with",          "scoped aliasing",                   "/concepts/bindings"),
    ("output",        "jq output bindings",                "/concepts/bindings"),
    ("schema",        "typed (structured) output",         "/concepts/verbs"),
    ("thinking",      "extended thinking budget",          "/concepts/verbs"),
    ("secrets",       "vault-backed secrets",              "/reference/yaml-syntax"),
    ("typed_vars",    "typed workflow inputs",             "/reference/yaml-syntax"),
    ("outputs",       "typed workflow outputs (callable)", "/reference/yaml-syntax"),
    ("agent_tools",   "default-deny tool grants",          "/concepts/verbs"),
    ("capture",       "structured exec capture",           "/concepts/verbs"),
    ("local_model",   "sovereign local model",             "/concepts/providers"),
]


def _constructs_of(lean_text: str) -> set[str]:
    doc = yaml.safe_load(lean_text)
    tasks = doc.get("tasks") or []
    found: set[str] = set()
    model = doc.get("model") or ""
    if isinstance(model, str) and model.split("/")[0] in ("ollama", "lmstudio", "llamacpp", "localai", "vllm"):
        found.add("local_model")
    if doc.get("secrets"):
        found.add("secrets")
    if doc.get("outputs"):
        found.add("outputs")
    for v in (doc.get("vars") or {}).values():
        if isinstance(v, dict) and "type" in v:
            found.add("typed_vars")
    for t in tasks:
        for k in ("for_each", "max_parallel", "fail_fast", "when", "retry",
                  "timeout", "on_finally", "on_error", "with", "output"):
            if k in t:
                found.add(k)
        for verb in ("infer", "agent"):
            body = t.get(verb)
            if isinstance(body, dict):
                if body.get("schema"):
                    found.add("schema")
                if body.get("thinking"):
                    found.add("thinking")
        agent = t.get("agent")
        if isinstance(agent, dict) and agent.get("tools"):
            found.add("agent_tools")
        ex = t.get("exec")
        if isinstance(ex, dict) and ex.get("capture"):
            found.add("capture")
    return found


def render_coverage(workflows: dict[str, str]) -> str:
    """The constructs ↔ examples reverse index · 'find the example that
    teaches X' · fully derived · zero maintenance."""
    per_file = {name: _constructs_of(body) for name, body in workflows.items()}
    lines = ["", "| Construct | Taught by |", "|---|---|"]
    for key, label, href in CONSTRUCTS:
        users = sorted(n for n, cs in per_file.items() if key in cs)
        if not users:
            continue
        links = " · ".join(
            f"[{n.removesuffix('.nika.yaml').split('-', 1)[1]}](/examples/{n.removesuffix('.nika.yaml').split('-', 1)[1]})"
            for n in users)
        lines.append(f"| [{label}]({href}) | {links} |")
    lines.append("")
    return "\n".join(lines)


def render_showcase_snippet(workflows: dict[str, str]) -> str:
    tiers: dict[str, int] = {}
    for name in workflows:
        tiers[name[:2]] = tiers.get(name[:2], 0) + 1
    return (
        "{/* _showcase.mdx — AUTO-GENERATED by scripts/showcase-projector.py\n"
        "    (nika-spec repo) from examples/showcase/ — counts derive · never\n"
        "    hand-type. Regenerate: python3 scripts/showcase-projector.py --write */}\n\n"
        "export const SHOWCASE = {\n"
        f"  count: {len(workflows)},\n"
        f"  t1: {tiers.get('t1', 0)},\n"
        f"  t2: {tiers.get('t2', 0)},\n"
        f"  t3: {tiers.get('t3', 0)},\n"
        f"  t4: {tiers.get('t4', 0)},\n"
        "};\n"
    )


def build_dag(lean_text: str) -> dict:
    """The structured run-sim model · tasks (verb · deps · wave · gloss ·
    flags · line range) + workflow outputs. Derived from the SAME lean text
    the site renders — the model and the displayed file cannot drift."""
    doc = yaml.safe_load(lean_text)
    ranges = _task_lines(lean_text)
    tasks_out = []
    waves: dict[str, int] = {}
    tasks = doc.get("tasks") or []

    def wave_of(tid: str, seen=()) -> int:
        if tid in waves:
            return waves[tid]
        task = next((t for t in tasks if t.get("id") == tid), None)
        deps = [d for d in (task.get("depends_on") or []) if d not in seen] if task else []
        w = 0 if not deps else 1 + max(wave_of(d, (*seen, tid)) for d in deps)
        waves[tid] = w
        return w

    for t in tasks:
        tid = t.get("id")
        verb = next((v for v in ("infer", "exec", "invoke", "agent") if v in t), "invoke")
        line0, line1 = ranges.get(tid, (0, 0))
        tasks_out.append({
            "id": tid,
            "verb": verb,
            "deps": list(t.get("depends_on") or []),
            "wave": wave_of(tid),
            "gloss": _gloss(t),
            "flags": _flags(t),
            "line0": line0,
            "line1": line1,
        })
    return {
        "tasks": tasks_out,
        "outputs": list((doc.get("outputs") or {}).keys()),
        "waves": (max(waves.values()) + 1) if waves else 1,
    }


def render_ts(workflows: dict[str, str]) -> str:
    entries = []
    for name, body in workflows.items():
        slug = name.removesuffix(".nika.yaml")
        escaped = body.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
        entries.append(f"  '{slug}': `{escaped}`,")
    joined = "\n".join(entries)
    dag_entries = []
    for name, body in workflows.items():
        slug = name.removesuffix(".nika.yaml")
        dag_entries.append(f"  '{slug}': {json.dumps(build_dag(body), ensure_ascii=False)},")
    dag_joined = "\n".join(dag_entries)
    return (
        "// usecases-yaml.generated.ts — AUTO-GENERATED by\n"
        "// scripts/showcase-projector.py (nika-spec repo) from\n"
        "// examples/showcase/*.nika.yaml — the single source for every\n"
        "// public workflow example. DO NOT EDIT · regenerate:\n"
        "//   python3 scripts/showcase-projector.py --write\n"
        "// Drift gate: --check (wired into the SuperNovae run-all audit).\n\n"
        "export const SHOWCASE_YAML: Record<string, string> = {\n"
        f"{joined}\n"
        "}\n\n"
        "/** the run-sim model · derived from the SAME lean yaml above ·\n"
        "    waves = topological depth · line0/line1 = highlight range */\n"
        "export interface ShowcaseTask {\n"
        "  id: string\n"
        "  verb: 'infer' | 'exec' | 'invoke' | 'agent'\n"
        "  deps: string[]\n"
        "  wave: number\n"
        "  gloss: string\n"
        "  flags: string[]\n"
        "  line0: number\n"
        "  line1: number\n"
        "}\n"
        "export interface ShowcaseDag {\n"
        "  tasks: ShowcaseTask[]\n"
        "  outputs: string[]\n"
        "  waves: number\n"
        "}\n\n"
        "export const SHOWCASE_DAG: Record<string, ShowcaseDag> = {\n"
        f"{dag_joined}\n"
        "}\n"
    )


def _replace_blocks(text: str, begin_re, end_marker: str, page_name: str,
                    content_for) -> tuple[str, bool]:
    """Generic managed-block rewrite · returns (new_text, dirty)."""
    out, pos, dirty = [], 0, False
    for m in begin_re.finditer(text):
        key = m.group(1) if m.groups() else None
        end_idx = text.find(end_marker, m.end())
        if end_idx == -1:
            print(f"showcase-projector · {page_name} · unterminated block {key or end_marker}",
                  file=sys.stderr)
            sys.exit(2)
        managed = content_for(key)
        if text[m.end():end_idx] != managed:
            dirty = True
        out.append(text[pos:m.end()])
        out.append(managed)
        pos = end_idx
    out.append(text[pos:])
    return "".join(out), dirty


def project_docs_page(page: Path, workflows: dict[str, str], write: bool) -> bool:
    """Rewrite every managed block (yaml · dag mermaid · coverage matrix) in
    one docs page. True = in sync."""
    text = page.read_text()

    def yaml_for(fname):
        if fname not in workflows:
            print(f"showcase-projector · {page.name} references unknown {fname}",
                  file=sys.stderr)
            sys.exit(2)
        return f"\n```yaml {fname}\n{workflows[fname]}```\n"

    def dag_for(fname):
        if fname not in workflows:
            print(f"showcase-projector · {page.name} dag references unknown {fname}",
                  file=sys.stderr)
            sys.exit(2)
        return f"\n```mermaid\n{render_mermaid(workflows[fname])}```\n"

    text, d1 = _replace_blocks(text, BEGIN, END, page.name, yaml_for)
    text, d2 = _replace_blocks(text, DAG_BEGIN, DAG_END, page.name, dag_for)
    cov_re = re.compile(re.escape(COVERAGE_BEGIN))
    text, d3 = _replace_blocks(text, cov_re, COVERAGE_END, page.name,
                               lambda _k: render_coverage(workflows))
    dirty = d1 or d2 or d3
    if dirty and write:
        page.write_text(text)
    return not dirty


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--write", "--check"):
        print("showcase-projector · mode --write | --check", file=sys.stderr)
        return 2
    write = mode == "--write"
    workflows = load_showcase()
    rc = 0

    # TARGET 1 · docs managed blocks
    docs_env = os.environ.get("NIKA_DOCS_ROOT")
    docs_root = Path(docs_env) if docs_env else SPEC_ROOT.parent / "docs"
    pages_dir = docs_root / "examples"
    if pages_dir.is_dir():
        for page in sorted(pages_dir.glob("*.mdx")):
            in_sync = project_docs_page(page, workflows, write)
            if in_sync:
                continue
            if write:
                print(f"✓ wrote docs · {page.name}")
            else:
                print(f"showcase-projector · DRIFT · docs/{page.name} · run --write",
                      file=sys.stderr)
                rc = 1
    else:
        print("· docs examples/ absent · skipped")

    # Coverage · every showcase file must be referenced by ≥1 docs page
    # (an orphan showcase workflow would silently never reach the public
    # docs · the gallery + the explorer claim the full set).
    if pages_dir.is_dir():
        referenced: set[str] = set()
        for page in pages_dir.glob("*.mdx"):
            referenced |= set(BEGIN.findall(page.read_text()))
        orphans = sorted(set(workflows) - referenced)
        if orphans:
            msg = f"showcase-projector · {len(orphans)} showcase file(s) with NO docs page · {', '.join(orphans)}"
            if write:
                print(f"⚠ {msg}")
            else:
                print(msg, file=sys.stderr)
                rc = 1

    # TARGET 1b · docs counts snippet (next to _canon.mdx)
    snippets_dir = docs_root / "snippets"
    if snippets_dir.is_dir():
        target = snippets_dir / "_showcase.mdx"
        rendered = render_showcase_snippet(workflows)
        if write:
            target.write_text(rendered)
            print(f"✓ wrote docs snippet · {target.name}")
        elif not target.is_file() or target.read_text() != rendered:
            print("showcase-projector · DRIFT · docs snippets/_showcase.mdx · run --write",
                  file=sys.stderr)
            rc = 1

    # TARGET 2 · website generated module
    web_env = os.environ.get("NIKA_WEBSITE_SRC")
    web_src = Path(web_env) if web_env else SPEC_ROOT.parent / "website" / "src"
    if web_src.is_dir():
        target = web_src / "sections" / "usecases-yaml.generated.ts"
        rendered = render_ts(workflows)
        if write:
            target.write_text(rendered)
            print(f"✓ wrote website · {target}")
        elif not target.is_file() or target.read_text() != rendered:
            print("showcase-projector · DRIFT · website usecases-yaml.generated.ts · run --write",
                  file=sys.stderr)
            rc = 1
        else:
            print("✓ website in sync (usecases-yaml.generated.ts)")

        # Coverage · every showcase workflow must have a card in the
        # explorer (usecases-data.ts) — the docs have the same guard ·
        # an uncarded workflow would silently never reach the site.
        data_ts = web_src / "sections" / "usecases-data.ts"
        if data_ts.is_file():
            data_text = data_ts.read_text()
            uncarded = sorted(
                n for n in workflows
                if f"'{n.removesuffix('.nika.yaml')}'" not in data_text)
            if uncarded:
                msg = (f"showcase-projector · {len(uncarded)} workflow(s) with NO site card "
                       f"(usecases-data.ts) · {', '.join(uncarded)}")
                if write:
                    print(f"⚠ {msg}")
                else:
                    print(msg, file=sys.stderr)
                    rc = 1
    else:
        print("· website src/ absent · skipped")

    if rc == 0 and not write:
        print(f"✓ showcase projection in sync · {len(workflows)} workflows")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
