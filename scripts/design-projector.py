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


SCHEMA_PATH = SPEC_ROOT / "schemas" / "workflow.schema.json"

# The surfaces a word can be declared on, in the schema's own reading order —
# the same set the website's language projection walks. A role closes over
# THESE names, never over invented ones.
SCOPE_NODES = (
    ("envelope", ()),
    ("workflow", ("properties", "workflow")),
    ("task", ("$defs", "task")),
    ("infer", ("$defs", "infer")),
    ("exec", ("$defs", "exec")),
    ("invoke", ("$defs", "invoke")),
    ("agent", ("$defs", "agent")),
    ("retry", ("$defs", "retry")),
    ("on_error", ("$defs", "onError")),
    ("on_finally", ("$defs", "finallyStep")),
)


def _scopes_by_word() -> dict:
    """word -> the set of scopes the schema declares it on."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    out: dict = {}
    for scope, path in SCOPE_NODES:
        node = schema
        for step in path:
            node = (node or {}).get(step, {})
        for word in (node or {}).get("properties", {}):
            out.setdefault(word, set()).add(scope)
    return out


def role_members(tokens: dict) -> dict:
    """Each role's words, DERIVED from the schema and seeded by the three
    judgments the schema cannot state about itself (roles.*.seed).

    `inherit` decides the closure:
      none                 the seeds, and only the seeds
      descendants          resolved at the CONSUMER's tokenize time (position
                           tells `tools` under permits: from `tools` under
                           agent:), so the emission carries the heads
      scopes_closed_under  a word whose ONLY scopes are recovery scopes IS
                           failure grammar, however deep it sits
    """
    schema_scopes = _scopes_by_word()
    members = {}
    for name, role in tokens["roles"].items():
        words = set(role.get("seed", []))
        if role.get("inherit") == "scopes_closed_under":
            recovery = set(role.get("recovery_scopes", []))
            for word, scopes in schema_scopes.items():
                if scopes and scopes <= recovery:
                    words.add(word)
        unknown = sorted(w for w in words if w not in schema_scopes)
        if unknown:
            raise SystemExit(
                f"design-projector · role '{name}' seeds words the schema "
                f"does not declare: {', '.join(unknown)}"
            )
        members[name] = sorted(words)
    overlap = [
        (a, b, sorted(set(members[a]) & set(members[b])))
        for i, a in enumerate(members)
        for b in list(members)[i + 1:]
        if set(members[a]) & set(members[b])
    ]
    if overlap:
        raise SystemExit(f"design-projector · roles overlap (a word has ONE role): {overlap}")
    return members


def render_ts(tokens: dict) -> str:
    """The ONE generated-module shape both website and vscode consume."""
    verbs = tokens["verbs"]
    sev = tokens["severity"]
    st = tokens["status"]
    c = tokens["brand"]["color"]

    def vmap(key):  # deterministic canon order
        return " ".join(f"{n}: '{verbs[n][key]}'," for n in CANON_VERBS)

    roles = tokens["roles"]
    members = role_members(tokens)

    def rmap(key):
        return " ".join(
            f"{n}: '{roles[n][key]}'," for n in roles if key in roles[n]
        )

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
        "/** the semantic ROLE a .nika.yaml key carries — MEANING, not syntax.",
        " *  A generic highlighter colours by syntax class because it does not",
        " *  know the language; nika is a closed contract, so `command` reads as",
        " *  exec's because it cannot live anywhere else. Membership is DERIVED",
        " *  from schemas/workflow.schema.json (roles.*.seed + the closure) —",
        " *  add a word to the schema and its role follows on the next",
        " *  projection. Space-joined: a string costs a fraction of a literal",
        " *  array in a consumer bundle. */",
        f"export const NIKA_ROLE_WORDS = {{ {' '.join(chr(39).join([n + ': ', ' '.join(members[n]), '']) + ',' for n in roles)} }} as const",
        "export type NikaRoleName = keyof typeof NIKA_ROLE_WORDS",
        "/** how each role MARKS its words — no role invents a hue, because the",
        " *  seven layer hues already collide with the four verb hues by",
        " *  construction (flow IS infer's blue, boundary IS exec's orange). */",
        f"export const NIKA_ROLE_MARK = {{ {rmap('mark')} }} as const",
        f"export const NIKA_ROLE_CODICON = {{ {rmap('codicon')} }} as const",
        "/** the web binding: the CSS custom property each role reuses */",
        f"export const NIKA_ROLE_WEB_TOKEN = {{ {rmap('web_token')} }} as const",
        "/** the editor binding — a vscode semantic-token type, so an EDITOR can",
        " *  speak the same roles the site does while its colours stay the",
        " *  user's theme (LOCK-005: the skin is theme-driven, the MEANING is",
        " *  ours). A DocumentSemanticTokensProvider maps these verbatim. */",
        f"export const NIKA_ROLE_VSCODE = {{ {rmap('vscode_semantic')} }} as const",
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
    lines += _material_lines(tokens)
    return "\n".join(lines)


def _ts_literal(value, indent: int = 0) -> str:
    """A dict/scalar as a TS object literal — unquoted keys, single-quoted
    strings, so the emitted module reads like hand-written source and passes
    the consumers' lint without a per-file exemption."""
    if isinstance(value, dict):
        inner = ", ".join(f"{k}: {_ts_literal(v, indent + 1)}" for k, v in value.items())
        return "{ " + inner + " }"
    if isinstance(value, str):
        return "'" + value.replace("'", "\\'") + "'"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _material_lines(tokens: dict) -> list[str]:
    """TARGET 1+2 · the PLATE. The website and the VS Code canvas both draw the
    same physical object; the docs target has no plates and ignores this.

    Quantities, not CSS — how far the light reaches, how deep the well is cut,
    how much the edge takes. The one exception is the easing curves: the canvas
    is a WEBVIEW, so it and the site share a rendering engine and a damping
    profile written once as linear() is the same curve in both."""
    m = tokens["material"]
    return [
        "/** THE PLATE · one physical object, three surfaces.",
        " *  The website, the VS Code canvas and the design bench all draw a",
        " *  plate: a top edge that catches light, a face with a paper tooth, a",
        " *  well cut into it where code sits, and two shadows — one where it",
        " *  touches, one where it hangs. Before this block each surface",
        " *  invented its own: three radii, three shadow recipes, three ideas",
        " *  of how much an edge should glint.",
        " *",
        " *  THE LAMP IS THE POINT. One light in the room; every plate obeys it.",
        " *  A plate alone cannot know where the light is, so these are",
        " *  quantities on a SCENE — one gradient lights a hundred plates. */",
        f"export const NIKA_MATERIAL = {_ts_literal(m)} as const",
        "",
    ]


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
