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
    candidate = SPEC_ROOT.parent / sibling
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

    for cat in ("verbs", "builtins", "extract_modes", "error_namespaces", "pillars"):
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


MARKER_RE = re.compile(r"(<!-- canon:([a-z_]+) -->)([^<]*)(<!-- /canon -->)")


def marker_values(canon: dict) -> dict:
    """TARGET 0 vocabulary · every `<!-- canon:KEY -->` maps to one canon count."""
    return {
        "verbs": canon["verbs"]["count"],
        "builtins": canon["builtins"]["count"],
        "providers": canon["providers"]["count"],
        "extract_modes": canon["extract_modes"]["count"],
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
    for path in sorted(SPEC_ROOT.rglob("*.md")):
        rel = path.relative_to(SPEC_ROOT)
        if any(part.startswith(".") for part in rel.parts):
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
