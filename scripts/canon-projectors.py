#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# canon-projectors.py — project canon.yaml (the Nika language SSOT) into
# the PUBLIC consumer surfaces (renamed from docs-canon-snippet.py ·
# 2026-06-10 · multi-target):
#
#   TARGET 0 · this repo    <!-- canon:KEY -->N<!-- /canon --> markers in *.md
#   TARGET 1 · nika-docs   snippets/_canon.mdx       (Mintlify · import { CANON })
#   TARGET 2 · nika.sh     src/canon.generated.ts    (website · import { CANON })
#
# THE LAW (projection-by-default) · canon.yaml is THE source · each target
# is a PROJECTION · pages/components import { CANON } and interpolate —
# they NEVER hand-type a volatile language fact. Sister of the engine's
# scripts/mintlify-snapshot.sh (ENGINE facts → _status-snapshot.mdx as
# STATUS). Two SSOTs · spec facts ⊥ engine facts (mirrors Apache/AGPL).
# Live proof of the drift class · the website still said « 13 providers »
# (pre-openrouter) in 3 src sites while llms.txt said 14.
#
# Target path resolution (priority order):
#   docs    · $NIKA_DOCS_SNIPPETS  · else <spec-root>/../docs/snippets/
#   website · $NIKA_WEBSITE_SRC    · else <spec-root>/../website/src/
#   (a missing sibling is SKIPPED · standalone spec clones project nothing)
#
# Usage:
#   python3 scripts/canon-projectors.py --write   # regenerate all targets
#   python3 scripts/canon-projectors.py --check   # drift gate (exit 1 on diff)
#
# Both modes always cover TARGET 0 (in-repo markers) · external siblings
# are covered when present. History note · the in-repo markers were
# hand-maintained until 2026-07-06 and drifted 14/24 vs canon 16/25 across
# 12 sites while every external projection stayed green — hence TARGET 0.
#
# Exit codes · 0 in-sync/written · 1 drift (--check) · 2 environment or
# intra-canon error (counts != len(items) · unknown marker key · bad schema).

import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("canon-projectors · pyyaml required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

SPEC_ROOT = Path(__file__).resolve().parent.parent
SUPPORTED_SCHEMA = 1


def resolve_target(env_var: str, sibling: str, filename: str):
    env = os.environ.get(env_var)
    if env:
        return Path(env) / filename
    # Sibling layouts differ per host checkout: flat (`../docs/`) or
    # repo-container (`../../docs/repo/` — the spec itself lives one level
    # deeper as `spec/repo/` there, hence the extra parent).
    head, _, tail = sibling.partition("/")
    candidates = (
        SPEC_ROOT.parent / sibling,
        SPEC_ROOT.parent.parent / sibling,
        SPEC_ROOT.parent.parent / head / "repo" / tail,
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate / filename
    return None


def load_canon() -> dict:
    canon_path = SPEC_ROOT / "canon.yaml"
    if not canon_path.is_file():
        print(f"canon-projectors · canon.yaml not found at {canon_path}", file=sys.stderr)
        sys.exit(2)
    with canon_path.open() as f:
        canon = yaml.safe_load(f)
    if canon.get("schema_version") != SUPPORTED_SCHEMA:
        print(
            f"canon-projectors · unsupported schema_version "
            f"{canon.get('schema_version')!r} (supported: {SUPPORTED_SCHEMA}) · "
            "upgrade this projector explicitly",
            file=sys.stderr,
        )
        sys.exit(2)
    return canon


def self_check(canon: dict) -> None:
    """The intra-canon law · every category's count == len(items)."""

    def die(cat: str, count: int, actual: int) -> None:
        print(
            f"canon-projectors · intra-canon drift · {cat} count: {count} "
            f"!= len(items) {actual} · fix canon.yaml first",
            file=sys.stderr,
        )
        sys.exit(2)

    for cat in ("verbs", "builtins", "extract_modes", "templates", "error_namespaces", "pillars", "error_codes"):
        count = canon[cat]["count"]
        actual = len(canon[cat]["items"])
        if count != actual:
            die(cat, count, actual)
    p = canon["providers"]
    actual = sum(len(v) for v in p["items"].values())
    if p["count"] != actual:
        die("providers", p["count"], actual)
    for sub in ("tools", "protocol_versions"):
        m = canon["mcp"][sub]
        if m["count"] != len(m["items"]):
            die(f"mcp.{sub}", m["count"], len(m["items"]))

    # The top-level counts: row is a PROJECTION of its category block — it must
    # never drift on its own (the 50-vs-53 error_codes drift class, 2026-07-13).
    counts = canon["counts"]
    derived = {
        "verbs": len(canon["verbs"]["items"]),
        "builtins": len(canon["builtins"]["items"]),
        "extract_modes": len(canon["extract_modes"]["items"]),
        "templates": len(canon["templates"]["items"]),
        "error_namespaces": len(canon["error_namespaces"]["items"]),
        "pillars": len(canon["pillars"]["items"]),
        "error_codes": len(canon["error_codes"]["items"]),
        "providers": sum(len(v) for v in canon["providers"]["items"].values()),
        "mcp_tools": len(canon["mcp"]["tools"]["items"]),
        "mcp_protocol_versions": len(canon["mcp"]["protocol_versions"]["items"]),
    }
    for key, actual in derived.items():
        if counts.get(key) != actual:
            die(f"counts.{key}", counts.get(key), actual)

    # The canon↔reference law (the #291 class · measured 2026-08-26: the
    # stdlib doc's mode table carried `raw` while the canon items did not —
    # count == len(items) held on both sides, so the intra-canon check
    # passed on a canon that contradicted its own reference). The stdlib
    # mode table is parsed and compared SET-equal to the canon items.
    # Fail-closed (adversarial-review hardening): a missing doc or a table
    # yielding zero rows is rc=2, never a silent pass — a gate that skips
    # on absence reads green forever.
    modes_doc = SPEC_ROOT / "stdlib" / "extract-modes-v0.1.md"
    if not modes_doc.is_file():
        print(
            f"canon-projectors · {modes_doc.name} missing · the "
            "canon↔reference cross-check refuses blind",
            file=sys.stderr,
        )
        sys.exit(2)
    doc_modes = set()
    for line in modes_doc.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([a-z_]+)`\s*\|", line)
        if m:
            doc_modes.add(m.group(1))
    if not doc_modes:
        print(
            f"canon-projectors · {modes_doc.name} mode table has no rows · "
            "refusing blind",
            file=sys.stderr,
        )
        sys.exit(2)
    canon_modes = set(canon["extract_modes"]["items"])
    if doc_modes != canon_modes:
        print(
            f"canon-projectors · canon↔reference drift · extract_modes "
            f"doc-only: {sorted(doc_modes - canon_modes)} · "
            f"canon-only: {sorted(canon_modes - doc_modes)} · "
            f"one list must move (canon.yaml is the SSOT)",
            file=sys.stderr,
        )
        sys.exit(2)

    # The same law, generalized to the class: the 05-errors « Error code
    # namespaces » allocation table vs canon error_namespaces — both
    # directions, fail-closed on a missing heading or an empty table. Two
    # rows are DECLARED ahead of canon (the CF-05 pattern · named, cited,
    # never silent) and a stale declaration is itself a red. The row regex
    # normalizes `NIKA-BUILTIN-<B>` to NIKA-BUILTIN.
    ns_ahead = {
        "NIKA-YAML": "kernel-ahead · live registry rows · canon/EXCEPTIONS.md CF-05",
        "NIKA-REG": "engine-ahead · reference-engine ADR-106 allocation",
    }
    ns_doc = SPEC_ROOT / "spec" / "05-errors.md"
    ns_heading = "## Error code namespaces"
    try:
        ns_text = ns_doc.read_text(encoding="utf-8")
    except OSError as e:
        print(f"canon-projectors · {ns_doc} unreadable · {e}", file=sys.stderr)
        sys.exit(2)
    _, sep, tail = ns_text.partition(ns_heading)
    if not sep:
        print(
            f"canon-projectors · {ns_doc.name} lost its {ns_heading!r} table · "
            "the cross-check refuses blind",
            file=sys.stderr,
        )
        sys.exit(2)
    ns_section = tail.split("\n### ", 1)[0].split("\n## ", 1)[0]
    table_ns = set(re.findall(r"^\| `(NIKA-[A-Z]+)", ns_section, re.MULTILINE))
    if not table_ns:
        print(
            f"canon-projectors · {ns_doc.name} namespace table has no rows · "
            "refusing blind",
            file=sys.stderr,
        )
        sys.exit(2)
    canon_ns = set(canon["error_namespaces"]["items"])
    missing_rows = sorted(canon_ns - table_ns)
    if missing_rows:
        print(
            f"canon-projectors · error_namespaces ≠ the {ns_doc.name} "
            f"allocation table · canon-only (no table row): {missing_rows}",
            file=sys.stderr,
        )
        sys.exit(2)
    undeclared = sorted(table_ns - canon_ns - set(ns_ahead))
    if undeclared:
        print(
            f"canon-projectors · error_namespaces ≠ the {ns_doc.name} "
            f"allocation table · table-only, undeclared: {undeclared} · "
            "declare it (the CF-05 pattern) or count it in canon",
            file=sys.stderr,
        )
        sys.exit(2)
    stale = sorted(set(ns_ahead) - (table_ns - canon_ns))
    if stale:
        print(
            f"canon-projectors · declared table-ahead rows no longer ahead: "
            f"{stale} · retire the declaration (a stale exception is drift)",
            file=sys.stderr,
        )
        sys.exit(2)

    # The prose-count law (the « 15 error namespaces » fossil class): a
    # literal count inside any canon prose VALUE naming a counted category
    # must equal counts:. Digits only, by decision — « fifteen » in words
    # would pass; word numbers widen the subset-reading false-positive
    # class (« the four media builtins » counts a subset, not the
    # category), declined until a word-number fossil is observed.
    prose_re = re.compile(
        r"\b(\d+)\s+(error namespaces?|error codes?|error categor(?:y|ies)|"
        r"extract modes?|builtins?|providers?|templates?|pillars?)\b"
    )
    noun_keys = {
        "error namespace": "error_namespaces",
        "error code": "error_codes",
        "error category": "error_categories",
        "error categorie": "error_categories",
        "extract mode": "extract_modes",
        "builtin": "builtins",
        "provider": "providers",
        "template": "templates",
        "pillar": "pillars",
    }

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            for pm in prose_re.finditer(node):
                key = noun_keys[pm.group(2).rstrip("s")]
                if counts.get(key) != int(pm.group(1)):
                    print(
                        f"canon-projectors · fossil count in prose · {path} "
                        f"says « {pm.group(0)} » but counts.{key} is "
                        f"{counts.get(key)} · cite the count key, never "
                        "retype the number",
                        file=sys.stderr,
                    )
                    sys.exit(2)

    walk(canon, "canon")


MARKER_RE = re.compile(r"(<!-- canon:([a-z_]+) -->)([^<]*)(<!-- /canon -->)")


def marker_values(canon: dict) -> dict:
    """TARGET 0 vocabulary · every `<!-- canon:KEY -->` maps to one canon count."""
    return {
        "verbs": canon["verbs"]["count"],
        "builtins": canon["builtins"]["count"],
        "providers": canon["providers"]["count"],
        "extract_modes": canon["extract_modes"]["count"],
        "templates": canon["templates"]["count"],
        "namespaces": canon["namespaces"]["count"],
        "error_namespaces": canon["error_namespaces"]["count"],
        "error_categories": canon["error_categories"]["count"],
        "error_codes": canon["error_codes"]["count"],
        "pillars": canon["pillars"]["count"],
        "mcp_tools": canon["mcp"]["tools"]["count"],
        "mcp_versions": canon["mcp"]["protocol_versions"]["count"],
    }


def project_repo_markers(canon: dict, write: bool) -> bool:
    """TARGET 0 · rewrite (or check) every in-repo marker against canon.yaml.

    Returns True when drift was found. Unknown marker keys exit 2 — a typo'd
    key is a silent-drift hole, not a soft warning.
    """
    values = marker_values(canon)
    drift = False
    # Nested git worktrees (a directory carrying a `.git` FILE pointer) hold
    # ANOTHER branch's tree — their markers are that branch's business, not
    # this checkout's drift. Observed 2026-07-08: a wt-*/ worktree parked
    # inside the checkout red-flagged the whole mesh with its behind-main
    # markers and blocked an unrelated monorepo push.
    nested_worktrees = {
        p.parent for p in SPEC_ROOT.rglob(".git") if p.is_file() and p.parent != SPEC_ROOT
    }
    for path in sorted(SPEC_ROOT.rglob("*.md")):
        rel = path.relative_to(SPEC_ROOT)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if any(wt in path.parents for wt in nested_worktrees):
            continue
        text = path.read_text()
        stale: list[str] = []

        def sub(m: re.Match) -> str:
            key = m.group(2)
            if key not in values:
                print(
                    f"canon-projectors · unknown marker canon:{key} in {rel} · "
                    "add it to marker_values() or fix the typo",
                    file=sys.stderr,
                )
                sys.exit(2)
            expected = str(values[key])
            if m.group(3) != expected:
                stale.append(f"canon:{key} {m.group(3)!r} → {expected}")
                return m.group(1) + expected + m.group(4)
            return m.group(0)

        rewritten = MARKER_RE.sub(sub, text)
        if stale:
            drift = True
            if write:
                path.write_text(rewritten)
                print(f"✓ reprojected {rel} · " + " · ".join(stale))
            else:
                print(
                    f"canon-projectors · DRIFT · {rel} · " + " · ".join(stale),
                    file=sys.stderr,
                )
    return drift


def js_str_list(items: list) -> str:
    return "[" + ", ".join(f'"{i}"' for i in items) + "]"


def canon_fields(canon: dict) -> dict:
    """The shared CANON shape both emitters render."""
    providers = canon["providers"]["items"]
    return {
        "schemaVersion": canon["schema_version"],
        "verbs": canon["verbs"]["count"],
        "verbNames": [v["name"] for v in canon["verbs"]["items"]],
        "namespaces": canon["namespaces"]["count"],
        "namespaceNames": canon["namespaces"]["items"],
        "builtins": canon["builtins"]["count"],
        "builtinNames": canon["builtins"]["items"],
        "providers": canon["providers"]["count"],
        "providersCloud": len(providers["cloud"]),
        "providersLocal": len(providers["local"]),
        "providersTest": len(providers["test"]),
        "providerIdsCloud": providers["cloud"],
        "providerIdsLocal": providers["local"],
        "providerIdsTest": providers["test"],
        "extractModes": canon["extract_modes"]["count"],
        "extractModeNames": canon["extract_modes"]["items"],
        "templates": canon["templates"]["count"],
        "templateNames": canon["templates"]["items"],
        "mcpTools": canon["mcp"]["tools"]["count"],
        "mcpToolNames": canon["mcp"]["tools"]["items"],
        "mcpProtocolVersions": canon["mcp"]["protocol_versions"]["items"],
        "mcpLatestProtocol": canon["mcp"]["protocol_versions"]["latest"],
        "errorNamespaces": canon["error_namespaces"]["count"],
        "errorNamespaceNames": canon["error_namespaces"]["items"],
        "errorCategories": canon["error_categories"]["count"],
        "errorCodes": canon["error_codes"]["count"],
        "pillars": canon["pillars"]["count"],
    }


def render_object_body(f: dict) -> str:
    """The literal `{ ... }` body shared by the MDX and TS emitters.

    String scalars are quoted — a bare `2026-07-28` is a strict-mode
    octal SyntaxError in MDX/acorn and a silent arithmetic 1991 in TS
    (caught live by the docs mint gate · 2026-07-06)."""
    lines = []
    for key, value in f.items():
        if isinstance(value, list):
            rendered = js_str_list(value)
        elif isinstance(value, str):
            rendered = f'"{value}"'
        else:
            rendered = str(value)
        lines.append(f"  {key}: {rendered},")
    return "{\n" + "\n".join(lines) + "\n}"


def render_mdx(f: dict) -> str:
    return (
        "{/* _canon.mdx — AUTO-GENERATED by scripts/canon-projectors.py (nika-spec repo)\n"
        "    from canon.yaml — the Nika language single source of truth.\n"
        "    DO NOT EDIT · regenerate: python3 scripts/canon-projectors.py --write\n"
        "    Drift gate: --check (wired into the SuperNovae run-all audit). */}\n\n"
        f"export const CANON = {render_object_body(f)};\n"
    )


def render_ts(f: dict) -> str:
    return (
        "// canon.generated.ts — AUTO-GENERATED by scripts/canon-projectors.py\n"
        "// (nika-spec repo) from canon.yaml — the Nika language single source\n"
        "// of truth. DO NOT EDIT · regenerate:\n"
        "//   python3 scripts/canon-projectors.py --write\n"
        "// Drift gate: --check (wired into the SuperNovae run-all audit).\n\n"
        f"export const CANON = {render_object_body(f)} as const;\n"
    )


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--write", "--check"):
        print(f"canon-projectors · unknown mode {mode!r} (--write | --check)", file=sys.stderr)
        return 2

    canon = load_canon()
    self_check(canon)
    fields = canon_fields(canon)

    targets = []
    docs = resolve_target("NIKA_DOCS_SNIPPETS", "docs/snippets", "_canon.mdx")
    if docs is not None:
        targets.append(("docs", docs, render_mdx(fields)))
    website = resolve_target("NIKA_WEBSITE_SRC", "website/src", "canon.generated.ts")
    if website is not None:
        targets.append(("website", website, render_ts(fields)))

    drift = project_repo_markers(canon, write=(mode == "--write"))
    if not drift and mode == "--check":
        print("✓ repo markers in sync (TARGET 0)")

    if not targets:
        print("canon-projectors · no sibling targets found · external projection skipped")
        return 1 if (drift and mode == "--check") else 0
    for name, path, rendered in targets:
        if mode == "--write":
            path.write_text(rendered)
            print(f"✓ wrote {name} · {path}")
        else:
            if not path.is_file() or path.read_text() != rendered:
                print(
                    f"canon-projectors · DRIFT · {name} · {path} differs from "
                    "canon.yaml projection · run --write",
                    file=sys.stderr,
                )
                drift = True
            else:
                print(f"✓ {name} in sync ({path.name})")

    if mode == "--write":
        c = fields
        print(
            f"  verbs={c['verbs']} builtins={c['builtins']} providers={c['providers']} "
            f"extract_modes={c['extractModes']} error_namespaces={c['errorNamespaces']}"
        )
    return 1 if (drift and mode == "--check") else 0


if __name__ == "__main__":
    sys.exit(main())
