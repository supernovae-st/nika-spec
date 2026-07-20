#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# design-projector.py — project design/tokens.yaml (the SHARED visual
# vocabulary SSOT: verb colors · severity · brand core · per-surface icon
# bindings) to every consumer surface. Values change in tokens.yaml FIRST,
# then re-project. Companion of showcase-projector.py (which reads the same
# tokens for its mermaid classDefs — same repo, no generated copy).
#
#   TARGET 0 · in-repo      tokens.yaml schema self-check (verbs == the
#                           canonical 4 · hex shapes · bindings complete)
#   TARGET 1 · nika.sh      src/design-tokens.generated.ts
#   TARGET 2 · nika-vscode  src/design-tokens.generated.ts
#   TARGET 3 · nika-docs    docs.json theme colors (parity check · --write
#                           patches the 4 bound values surgically)
#
# Sibling resolution (env-overridable · missing sibling = skipped so a
# standalone spec clone projects nothing):
#   website · $NIKA_WEBSITE_SRC  · else <spec-root>/../website/src ·
#             else <spec-root>/../../website/src (container law)
#   vscode  · $NIKA_VSCODE_SRC   · else <spec-root>/../vscode/repo/src ·
#             else <spec-root>/../../vscode/repo/src · else .../vscode/src
#   docs    · $NIKA_DOCS_ROOT    · else <spec-root>/../docs ·
#             else <spec-root>/../../docs/repo
#
# Exit codes · 0 in-sync/written · 1 drift (--check) · 2 environment or
# schema error.

import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("design-projector · pyyaml required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

SPEC_ROOT = Path(__file__).resolve().parent.parent
TOKENS_PATH = SPEC_ROOT / "design" / "tokens.yaml"

CANON_VERBS = ("infer", "exec", "invoke", "agent")
HEX_RE = re.compile(r"^#[0-9a-f]{6}$")
BINDINGS = ("color", "text", "codicon", "fa", "glyph", "icon")
# icons.features · keys stay TS-identifier-safe (bare object keys in the
# generated module) · values are codicon slugs (kebab). Deliberate asymmetry.
FEATURE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CODICON_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def load_tokens() -> dict:
    """TARGET 0 — load + schema self-check. Exit 2 on any violation."""
    if not TOKENS_PATH.exists():
        print("design-projector · design/tokens.yaml missing", file=sys.stderr)
        sys.exit(2)
    tokens = yaml.safe_load(TOKENS_PATH.read_text())
    if tokens.get("version") != 1:
        print("design-projector · unknown tokens version (want 1)", file=sys.stderr)
        sys.exit(2)
    verbs = tokens.get("verbs", {})
    if tuple(verbs.keys()) != CANON_VERBS:
        print(f"design-projector · verbs must be exactly {CANON_VERBS} in order, "
              f"got {tuple(verbs.keys())}", file=sys.stderr)
        sys.exit(2)
    for name, v in verbs.items():
        for b in BINDINGS:
            if not v.get(b):
                print(f"design-projector · verb {name} missing binding `{b}`",
                      file=sys.stderr)
                sys.exit(2)
        for b in ("color", "text"):
            if not HEX_RE.match(v[b]):
                print(f"design-projector · verb {name} {b} {v[b]!r} is not "
                      "a lowercase #rrggbb", file=sys.stderr)
                sys.exit(2)
    for k in ("ok", "fail", "fail_text"):
        if not HEX_RE.match(tokens.get("severity", {}).get(k, "")):
            print(f"design-projector · severity.{k} missing or malformed",
                  file=sys.stderr)
            sys.exit(2)
    status = tokens.get("status", {})
    if tuple(status.keys()) != ("running", "retrying", "muted"):
        print("design-projector · status must be exactly (running, retrying, "
              f"muted) in order, got {tuple(status.keys())}", file=sys.stderr)
        sys.exit(2)
    for k, v in status.items():
        if not HEX_RE.match(v or ""):
            print(f"design-projector · status.{k} missing or malformed",
                  file=sys.stderr)
            sys.exit(2)
    color = tokens.get("brand", {}).get("color", {})
    for k in ("bg", "bg_base", "bg_elevated", "accent", "accent_strong",
              "accent_bright"):
        if not HEX_RE.match(color.get(k, "")):
            print(f"design-projector · brand.color.{k} missing or malformed",
                  file=sys.stderr)
            sys.exit(2)
    feats = tokens.get("icons", {}).get("features", {})
    if not feats or not all(
        FEATURE_KEY_RE.match(k or "") and CODICON_RE.match(v or "")
        for k, v in feats.items()
    ):
        print("design-projector · icons.features must be a non-empty map of "
              "feature slugs (ts-identifier-safe) to codicon ids (kebab)",
              file=sys.stderr)
        sys.exit(2)
    for k in ("ice", "glow", "ink"):
        if not HEX_RE.match(color.get("mark", {}).get(k, "")):
            print(f"design-projector · brand.color.mark.{k} missing or malformed",
                  file=sys.stderr)
            sys.exit(2)
    alpha = tokens.get("rules", {}).get("mermaid_fill_alpha", "")
    if not re.match(r"^[0-9a-f]{2}$", alpha):
        print("design-projector · rules.mermaid_fill_alpha must be 2 hex digits",
              file=sys.stderr)
        sys.exit(2)
    apca = tokens.get("rules", {}).get("contrast_apca", {})
    if not all(isinstance(apca.get(k), int) and apca.get(k) > 0
               for k in ("body", "glyph", "nontext")):
        print("design-projector · rules.contrast_apca needs positive integer "
              "Lc floors (body · glyph · nontext)", file=sys.stderr)
        sys.exit(2)
    grid = tokens.get("rules", {}).get("icon_grid", {})
    if not (isinstance(grid.get("size"), int) and grid.get("size") > 0
            and grid.get("style") and grid.get("fill")):
        print("design-projector · rules.icon_grid needs size (px int) · "
              "style · fill", file=sys.stderr)
        sys.exit(2)
    order = tokens.get("presentation", {}).get("providers_order", [])
    if not order or len(set(order)) != len(order) or not all(
        re.match(r"^[a-z][a-z0-9]*$", p or "") for p in order
    ):
        print("design-projector · presentation.providers_order must be a "
              "non-empty list of unique lowercase provider slugs",
              file=sys.stderr)
        sys.exit(2)
    return tokens


def _sibling(env_var: str, *candidates: Path) -> Path | None:
    override = os.environ.get(env_var)
    if override:
        return Path(override)
    return next((c for c in candidates if c.is_dir()), None)


def _rgb(hexv: str) -> str:
    r, g, b = (round(int(hexv[i:i + 2], 16) / 255, 4) for i in (1, 3, 5))
    return f"[{r}, {g}, {b}]"


def render_ts(tokens: dict) -> str:
    """The ONE generated-module shape both website and vscode consume."""
    verbs = tokens["verbs"]
    sev = tokens["severity"]
    st = tokens["status"]
    c = tokens["brand"]["color"]

    def vmap(key):  # deterministic canon order
        return " ".join(f"{n}: '{verbs[n][key]}'," for n in CANON_VERBS)

    lines = [
        "// design-tokens.generated.ts — AUTO-GENERATED by nika-spec",
        "// scripts/design-projector.py from design/tokens.yaml (the shared",
        "// visual vocabulary SSOT). DO NOT EDIT — values change SPEC-FIRST.",
        "// Regenerate: python3 scripts/design-projector.py --write",
        "// Drift gate: --check (spec CI + consumer gates).",
        "",
        f"export const NIKA_VERB_HEX = {{ {vmap('color')} }} as const",
        "export type NikaVerbName = keyof typeof NIKA_VERB_HEX",
        "",
        "/** normalized 0..1 triples — the three.js seam (no hand conversion) */",
        "export const NIKA_VERB_RGB: Record<NikaVerbName, readonly [number, number, number]> = {",
    ]
    for n in CANON_VERBS:
        lines.append(f"  {n}: {_rgb(verbs[n]['color'])},")
    feats = tokens["icons"]["features"]
    fmap = " ".join(f"{k}: '{feats[k]}'," for k in feats)
    lines += [
        "}",
        "",
        "/** the verb hues re-anchored for BODY COPY — clear rules.contrast_apca",
        " *  .body (APCA Lc >= 60) on NIKA_BRAND.bgBase AND bgElevated; invoke",
        " *  clears at its base hue, so its ramp is the identity. */",
        f"export const NIKA_VERB_TEXT = {{ {vmap('text')} }} as const",
        "",
        f"export const NIKA_VERB_GLYPH = {{ {vmap('glyph')} }} as const",
        f"export const NIKA_VERB_CODICON = {{ {vmap('codicon')} }} as const",
        f"export const NIKA_VERB_FA = {{ {vmap('fa')} }} as const",
        "/** nika.sh ontology ids (public/brand/icons.json) */",
        f"export const NIKA_VERB_ICON = {{ {vmap('icon')} }} as const",
        "",
        "/** per-FEATURE codicon bindings (icons.features · an OPEN set, unlike",
        " *  the 4 verbs) — drawn on the icon_grid contract: 16px · filled ·",
        " *  currentColor. cost = credit-card interim (bespoke SVG is owed). */",
        f"export const NIKA_FEATURE_CODICON = {{ {fmap} }} as const",
        "",
        f"export const NIKA_SEVERITY = {{ ok: '{sev['ok']}', fail: '{sev['fail']}' }} as const",
        "/** the severity pair's body-copy ramp (fail only — ok has no consumer yet) */",
        f"export const NIKA_SEVERITY_TEXT = {{ fail: '{sev['fail_text']}' }} as const",
        "",
        "/** the LIVE run-state palette — done/failed ARE severity (one storage,",
        " *  aliased here); running deliberately equals the infer hue. The vscode",
        " *  EDITOR skin stays theme-driven (LOCK-005) — its NIKA skin pins these. */",
        f"export const NIKA_STATUS = {{ running: '{st['running']}', "
        f"done: '{sev['ok']}', failed: '{sev['fail']}', "
        f"retrying: '{st['retrying']}', muted: '{st['muted']}' }} as const",
        "",
        "export const NIKA_BRAND = {",
        f"  bg: '{c['bg']}',",
        "  /** the two proving planes every *_TEXT ramp clears (APCA floors) */",
        f"  bgBase: '{c['bg_base']}',",
        f"  bgElevated: '{c['bg_elevated']}',",
        f"  accent: '{c['accent']}',",
        f"  accentStrong: '{c['accent_strong']}',",
        f"  accentBright: '{c['accent_bright']}',",
        f"  markIce: '{c['mark']['ice']}',",
        f"  markGlow: '{c['mark']['glow']}',",
        f"  markInk: '{c['mark']['ink']}',",
        "} as const",
        "",
        "/** The provider PRESENTATION order (operator lock 2026-06-12):",
        " *  local & open-weight lead, cloud incumbents never the first",
        " *  suggestion. Providers absent here rank after, alphabetically.",
        " *  Binds the TEACHING surface (pickers · docs), never adapters. */",
        "export const NIKA_PROVIDERS_ORDER: readonly string[] = [",
    ]
    for p in tokens["presentation"]["providers_order"]:
        lines.append(f"  '{p}',")
    lines += [
        "] as const",
        "",
    ]
    return "\n".join(lines)


def _origin_main_text(dest: Path) -> str | None:
    """The sibling REPO's truth for dest (origin/main blob · offline · local ref).

    A sibling working tree is arbitrary local state — another session's WIP,
    a stale checkout, a mid-rebase tree. Judging it as if it were the repo
    produced the F13 false positive (2026-07-13: a 112-commit-stale website
    checkout read as DRIFT while origin/main was in sync). None = not a git
    repo / no origin/main / path absent there; caller falls back to the
    working-tree verdict.
    """
    try:
        top = subprocess.run(
            ["git", "-C", str(dest.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        rel = dest.resolve().relative_to(Path(top).resolve())
        blob = subprocess.run(
            ["git", "-C", top, "show", f"origin/main:{rel.as_posix()}"],
            capture_output=True, text=True, check=True,
        )
        return blob.stdout
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def project_ts(dest: Path, rendered: str, write: bool, label: str) -> bool:
    """True = in sync (repo truth · origin/main outranks a stale working tree)."""
    current = dest.read_text() if dest.exists() else None
    if current == rendered:
        return True
    if write:
        dest.write_text(rendered)
        print(f"✓ wrote {label} · {dest}")
        return True
    if _origin_main_text(dest) == rendered:
        print(f"· {label} checkout stale ({dest.name} behind origin/main, "
              f"which IS in sync) · pull the sibling · not a repo drift")
        return True
    print(f"design-projector · DRIFT · {label} {dest.name} · run --write",
          file=sys.stderr)
    return False


# docs.json key → tokens path (the 4 bound values · parity, not rewrite)
DOCS_BINDINGS = (
    (("colors", "primary"), ("brand", "color", "accent_strong")),
    (("colors", "dark"), ("brand", "color", "accent_strong")),
    (("colors", "light"), ("brand", "color", "accent_bright")),
    (("background", "color", "dark"), ("brand", "color", "bg")),
)


def project_docs(docs_root: Path, tokens: dict, write: bool) -> bool:
    docs_json = docs_root / "docs.json"
    if not docs_json.exists():
        print("· docs docs.json absent · skipped")
        return True
    text = docs_json.read_text()
    doc = json.loads(text)
    ok = True
    for doc_path, tok_path in DOCS_BINDINGS:
        node = doc
        for k in doc_path[:-1]:
            node = node.get(k, {})
        have = node.get(doc_path[-1])
        want = tokens
        for k in tok_path:
            want = want[k]
        if have is None or have.lower() == want.lower():
            continue
        ok = False
        if write:
            # Surgical: replace the exact "key": "value" pair, preserving the
            # hand-authored file byte-for-byte everywhere else.
            pat = re.compile(r'("%s"\s*:\s*)"%s"' % (doc_path[-1], re.escape(have)))
            text, n = pat.subn(r'\1"%s"' % want, text, count=1)
            if n:
                print(f"✓ docs.json {'.'.join(doc_path)} · {have} → {want}")
        else:
            print(f"design-projector · DRIFT · docs.json {'.'.join(doc_path)} "
                  f"= {have} · tokens say {want}", file=sys.stderr)
    if write and not ok:
        docs_json.write_text(text)
        return True
    return ok


def main() -> int:
    write = "--write" in sys.argv
    tokens = load_tokens()  # TARGET 0 · exits 2 on schema violation
    rendered = render_ts(tokens)
    ok = True

    website = _sibling("NIKA_WEBSITE_SRC",
                       SPEC_ROOT.parent / "website" / "src",
                       SPEC_ROOT.parent.parent / "website" / "src")
    if website:
        ok &= project_ts(website / "design-tokens.generated.ts", rendered,
                         write, "website")
    else:
        print("· website src/ absent · skipped")

    vscode = _sibling("NIKA_VSCODE_SRC",
                      SPEC_ROOT.parent / "vscode" / "repo" / "src",
                      SPEC_ROOT.parent.parent / "vscode" / "repo" / "src",
                      SPEC_ROOT.parent / "vscode" / "src")
    if vscode:
        ok &= project_ts(vscode / "design-tokens.generated.ts", rendered,
                         write, "vscode")
    else:
        print("· vscode src/ absent · skipped")

    docs = _sibling("NIKA_DOCS_ROOT",
                    SPEC_ROOT.parent / "docs",
                    SPEC_ROOT.parent.parent / "docs" / "repo")
    if docs:
        ok &= project_docs(docs, tokens, write)
    else:
        print("· docs root absent · skipped")

    if ok:
        print("✓ design tokens in sync · 4 verbs · text ramps · severity · "
              "status · brand core · feature icons")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
