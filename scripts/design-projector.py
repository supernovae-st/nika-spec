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

_HEX = re.compile(r"#[0-9a-fA-F]{6}")

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


def resolve_alias(tokens: dict, path: str) -> str | None:
    """Follow a dotted path into the token tree (`severity.fail` ·
    `brand.color.accent`).

    Returns the value ONLY when it lands on a stored hex. An alias that walks
    into a map, a list or a missing key is a violation, not a fallback — the
    whole point of storing a binding is that it cannot silently resolve to
    nothing the way a stylesheet's `var(--missing)` does."""
    cur: object = tokens
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur if isinstance(cur, str) and HEX_RE.match(cur) else None


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
    # THE AUDIT LADDER · the binding must name every level the node vocabulary
    # declares, in that order, and each alias must resolve here. A level with no
    # hue is exactly the hole this check exists to close: `audit_severity` named
    # three levels while the palette answered for none of them, so each surface
    # answered privately and the canvas's answer was the only one that existed.
    audit_hues = tokens.get("severity", {}).get("audit", {})
    audit_levels = tuple(
        tokens.get("material", {}).get("node", {}).get("audit_severity") or ()
    )
    if tuple(audit_hues.keys()) != audit_levels:
        print("design-projector · severity.audit must name exactly "
              f"material.node.audit_severity {audit_levels} in order, got "
              f"{tuple(audit_hues.keys())}", file=sys.stderr)
        sys.exit(2)
    for level, alias in audit_hues.items():
        if resolve_alias(tokens, alias) is None:
            print(f"design-projector · severity.audit.{level} alias {alias!r} "
                  "does not resolve to a stored #rrggbb", file=sys.stderr)
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

    def rnum(key):
        """The role's QUANTITIES — a weight, a mix percentage. Unquoted, and
        sparse by design: only the roles that carry a visual quantity have one.

        These were authored and then dropped on the floor: neither reached any
        consumer, so the website hand-typed both (a `color-mix(… 78% …)` and a
        `--fw-semibold`) beside a hardcoded fallback hex that duplicated
        severity.fail. Three copies of two numbers, none of them the source."""
        return " ".join(
            f"{n}: {roles[n][key]}," for n in roles if key in roles[n]
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
        "/** the role's visual QUANTITIES on the web · sparse: a role appears",
        " *  here only if it carries one. boundary reads at a heavier cut of the",
        " *  key ink (it is not a different colour, it is a firmer one); fail is",
        " *  the danger hue mixed INTO the key ink rather than replacing it, so a",
        " *  recovery word still reads as a key first. */",
        f"export const NIKA_ROLE_WEB_WEIGHT = {{ {rnum('web_weight')} }} as const",
        f"export const NIKA_ROLE_WEB_MIX_PCT = {{ {rnum('web_mix_pct')} }} as const",
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
    lines += _node_lines(tokens)
    lines += _category_lines(tokens)
    lines += _identity_lines(tokens)
    return "\n".join(lines)


def _ts_literal(value, indent: int = 0) -> str:
    """A dict/scalar as a TS object literal — unquoted keys, single-quoted
    strings, so the emitted module reads like hand-written source and passes
    the consumers' lint without a per-file exemption."""
    if isinstance(value, list):
        return "[" + ", ".join(_ts_literal(v, indent) for v in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(f"{k}: {_ts_literal(v, indent + 1)}" for k, v in value.items())
        return "{ " + inner + " }"
    if isinstance(value, str):
        return "'" + value.replace("'", "\\'") + "'"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _dotted(tokens: dict, path: str) -> str:
    """Resolve a dotted alias into the file and prove it lands on a hex.

    An alias is the whole point of the blocks that use this: a category never
    introduces a colour, it borrows the one its meaning already has. Resolving
    at PROJECTION time — rather than storing a second copy of the hex — is what
    makes that structural instead of a promise. A typo cannot survive it."""
    cur = tokens
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise SystemExit(f"design-projector · alias {path!r} does not resolve at {part!r}")
        cur = cur[part]
    if not (isinstance(cur, str) and _HEX.fullmatch(cur)):
        raise SystemExit(f"design-projector · alias {path!r} lands on {cur!r}, not a #rrggbb")
    return cur


def _identity_lines(tokens: dict) -> list[str]:
    """TARGET 1+2 · THE CARD'S IDENTITY — what a node card shows.

    All of it shipped in the canvas (src/core/cardIdentity.ts) and nowhere
    else, so the website and the design bench drew a text card: the vocabulary
    for a richer one lived in one repository. Promoted verbatim; the preview
    rule crosses as a decision table rather than a function, because a table is
    the same fact in a form every surface can read."""
    ci = tokens["card_identity"]
    prev, ess = ci["preview"], ci["essence"]
    return [
        "/** THE CARD'S IDENTITY · what a node shows beyond its verb.",
        " *  The category's mark, the preview slot it earns, and WHICH argument",
        " *  is a builtin's soul — a card that shows every arg shows nothing.",
        " *  Read off the canvas, which was the only surface that had them. */",
        f"export const NIKA_CATEGORY_GLYPH = {_ts_literal(ci['category_glyph'])} as const",
        f"export const NIKA_PREVIEW_KINDS = {_ts_literal(prev['kinds'])} as const",
        f"export const NIKA_PREVIEW_BY_CATEGORY = {_ts_literal(prev['by_category'])} as const",
        f"export const NIKA_PREVIEW_OVERRIDE = {_ts_literal(prev['overrides'])} as const",
        f"export const NIKA_ESSENCE_RENDERS = {_ts_literal(ess['renders'])} as const",
        f"export const NIKA_ESSENCE = {_ts_literal(ess['by_builtin'])} as const",
        f"export const NIKA_PORT = {_ts_literal(ci['port'])} as const",
        "",
        "/** THE PREVIEW SLOT · the category decides, four builtins differ.",
        " *  Same answer as the canvas's previewFor(), proven over the whole",
        " *  catalogue rather than asserted. */",
        "export function nikaPreviewOf(",
        "  builtin: string | undefined,",
        "  category: string | undefined,",
        "): (typeof NIKA_PREVIEW_KINDS)[number] {",
        "  if (!builtin) return 'none'",
        "  const over = (NIKA_PREVIEW_OVERRIDE as Record<string, string>)[builtin]",
        "  if (over) return over as (typeof NIKA_PREVIEW_KINDS)[number]",
        "  const byCat = (NIKA_PREVIEW_BY_CATEGORY as Record<string, string>)[category ?? '']",
        "  return (byCat ?? 'none') as (typeof NIKA_PREVIEW_KINDS)[number]",
        "}",
        "",
    ]


def _category_lines(tokens: dict) -> list[str]:
    """TARGET 1+2 · THE BUILTIN'S HOUSE — one hue per catalogue category.

    The canvas has painted these since its house-icon landed, resolved inside
    its own stylesheet as --nk-cat-*. Nothing in the shared vocabulary said what
    a category looks like, so the website painted none of them and the design
    bench could not show a builtin at all."""
    cat = tokens["builtin"]["category"]
    def one(v):
        """A path, or a stated ratio between two paths. Both are aliases: the
        mix introduces no colour, it names a proportion of two that exist."""
        if isinstance(v, str):
            return _dotted(tokens, v)
        a, b = (_dotted(tokens, p) for p in v["mix"])
        w = float(v["at"])
        chan = lambda h, i: int(h[1 + 2 * i:3 + 2 * i], 16)
        return "#" + "".join(f"{round(chan(a, i) * (1 - w) + chan(b, i) * w):02x}" for i in range(3))

    resolved = {k: one(v) for k, v in cat.items()}
    return [
        "/** THE BUILTIN'S HOUSE · one hue per catalogue category, ALIASED.",
        " *  A category never introduces a colour — it borrows the one its",
        " *  meaning already has: what touches your disk wears the success",
        " *  green, what leaves the machine wears the accent, what looks at the",
        " *  run itself wears the critical red. Resolved at projection time, so",
        " *  a moved palette moves these too. */",
        f"export const NIKA_CATEGORY_HUE = {_ts_literal(resolved)} as const",
        "",
    ]


def _node_lines(tokens: dict) -> list[str]:
    """TARGET 1+2 · THE NODE'S STATE VOCABULARY.

    Two axes, and keeping them apart is the whole point: a node holds exactly
    one STATUS and any number of MARKS. Collapsing them — which the website's
    bench did — produces a list where `stale` sits beside `success` as though a
    task could not be both. It can, and most finished tasks eventually are."""
    n = tokens["material"]["node"]
    audit_hue = " ".join(
        f"{lvl}: '{resolve_alias(tokens, alias)}',"
        for lvl, alias in tokens["severity"]["audit"].items()
    )
    return [
        "/** THE NODE · two axes, never one.",
        " *  ONE status, ANY marks. `pending` deliberately has no resting rule",
        " *  in the canvas — a task that has not started should not advertise",
        " *  itself. The anatomy is what verbAnatomies.test.ts asserts: head,",
        " *  mechanism, essence, why — except invoke, whose essence leads. */",
        f"export const NIKA_NODE_STATUS = {_ts_literal(n['status'])} as const",
        f"export const NIKA_NODE_MARKS = {_ts_literal(n['marks'])} as const",
        f"export const NIKA_AUDIT_SEVERITY = {_ts_literal(n['audit_severity'])} as const",
        "/** the hue each audit level wears. Aliases into the stored palette,",
        " *  never a colour of its own: a finding borrows the weight it already",
        " *  means (error = the failure red · warning = the retrying amber ·",
        " *  info = the brand accent). Bound in tokens.yaml `severity.audit` —",
        " *  before that the map lived only in the canvas's own stylesheet. */",
        f"export const NIKA_AUDIT_HUE = {{ {audit_hue} }} as const",
        f"export const NIKA_NODE_ANATOMY = {_ts_literal(n['anatomy'])} as const",
        f"export const NIKA_NODE_CLASSES = {_ts_literal(n['classes'])} as const",
        "",
        "/** THE ONE FUNCTION THAT NAMES A NODE.",
        " *  Three surfaces draw this card; before this, each spelled its class",
        " *  string by hand and two of the three were wrong in the same way —",
        " *  they hung the state on the CARD. It hangs on the WRAPPER, and the",
        " *  card inside carries none. Call this; do not re-spell it. */",
        "export function nikaNodeClass(n: {",
        "  status: (typeof NIKA_NODE_STATUS)[number]",
        "  verb: keyof typeof NIKA_NODE_ANATOMY",
        "  marks?: readonly (keyof typeof NIKA_NODE_CLASSES.mark)[]",
        "  auditWorst?: (typeof NIKA_AUDIT_SEVERITY)[number]",
        "}): string {",
        "  const c = NIKA_NODE_CLASSES",
        "  const out = [c.wrapper, c.status_prefix + n.status, c.verb_prefix + n.verb]",
        "  for (const m of n.marks ?? []) {",
        "    out.push(c.mark[m])",
        "    /* the severity rides WITH the audit mark — adjacent, not appended.",
        "       Order is nothing to CSS and everything to a parity test. */",
        "    if (m === 'audit') out.push(c.audit_prefix + (n.auditWorst ?? 'error'))",
        "  }",
        "  return out.join(' ')",
        "}",
        "",
    ]


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


def _cross(cell: float, arm: float, stroke: float, ink: str = "#ffffff",
           halo: float | None = None, width: float = 1.0) -> str:
    """A survey tick as a data-URI, BUILT from its quantities. Never a
    hand-encoded string: an escaped SVG copied between files drifts silently
    and nobody notices for a year."""
    c = cell / 2
    d = f"M{c} {c - arm}v{arm * 2}M{c - arm} {c}h{arm * 2}"
    halo_path = (
        f"<path d='{d}' stroke='#000000' stroke-opacity='{halo}' "
        f"stroke-width='{width + 2}' stroke-linecap='round'/>"
        if halo is not None else ""
    )
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{cell}' height='{cell}'>"
        f"{halo_path}"
        f"<g stroke='{ink}' stroke-opacity='{stroke}' stroke-width='{width}'"
        f"{" stroke-linecap='round'" if halo is not None else ""}>"
        f"<path d='{d}'/></g></svg>"
    )
    enc = svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")
    return f'url("data:image/svg+xml,{enc}")'


def _vignette(v: dict) -> str:
    return (
        f"radial-gradient({v['reach_x'] * 100}% {v['reach_y'] * 100}% "
        f"at 50% {v['at_y'] * 100}%, transparent {v['clear'] * 100}%, "
        f"rgb(0 0 0 / {v['edge']}) 100%)"
    )


def render_card_css(tokens: dict) -> str:
    """TARGET 1+2 · THE CARD'S GEOMETRY, for every surface that draws a node.

    Measured before it was written: the canvas styles 139 `.nc*` selectors, the
    design bench used 23, the website's own renderer 21 `.dv-*` — and the site
    shared ZERO with the canvas. Three surfaces drawing one object, each from a
    card it had invented, because there was nothing to draw one from.

    COLOUR IS DELIBERATELY ABSENT. The hues already project (verb.hex ·
    severity · status) and each surface binds them to its own host: the canvas
    to VS Code's theme variables, the site to its palette. Geometry was the half
    still being re-invented, so geometry is what lands here.

    EVERY RULE IS `:where()` — specificity zero. The canvas has 139 selectors of
    its own on top of these; a projected sheet that fought them would be a
    second opinion, not a source. It sits underneath and loses every argument.
    """
    c = tokens["material"]["card"]
    fs, sig = c["fs"], tokens["material"]["node"]["signal"]
    d = c["dot_px"]
    # THE SECOND SIGNAL · geometry only. A hue dies under forced-colors and
    # under a colour-blind eye, so each status owes a shape as well.
    # EACH SHAPE IS COMPLETE, never a delta off the base. `filled` first read
    # `border-radius: 50%` — the base value, so the rule was a no-op that a gate
    # counting declarations would happily pass. And a delta makes the cascade
    # order load-bearing: a card that goes running → success would keep the
    # ring's transparent background.
    #
    # NO box-shadow. The first working draft drew the rings with an inset
    # box-shadow, and FORCED-COLORS REMOVES box-shadow ENTIRELY — the rings
    # vanished in exactly the condition the second signal exists for, leaving
    # running, retrying and success as three identical 7px discs. Hollow-vs-
    # solid is carried by `border` and the outer ring by `outline`, both of
    # which forced-colors keeps and re-colours.
    def _geo(w, h, radius, border, outline, rot):
        """LA FORME · elle doit GAGNER sur la base `.nc-dot`, sinon elle ne
        s'applique qu'à moitié. Mesuré avant de livrer au canvas : sa base pose
        width/height en (0,1,0), et des règles en :where() (0,0,0) auraient
        donné à `cancelled` la rotation SANS le trait — une forme incohérente,
        pire que pas de forme."""
        return (f"box-sizing: border-box; width: {w}; height: {h};"
                f" border-radius: {radius}; border: {border};"
                f" outline: {outline}; transform: {rot};")

    def _ink(bg, shadow):
        """LA COULEUR · elle doit PERDRE contre l'hôte. Le canvas peint son point
        par statut et cette feuille ne doit jamais lui reprendre la main."""
        return f"background: {bg}; box-shadow: {shadow};"

    ring = "2px solid currentColor"
    shape = {
        "small": (_geo(f"{d - 3}px", f"{d - 3}px", "50%", "0 solid", "none", "none"),
                  _ink("currentColor", "none")),
        "ring": (_geo(f"{d}px", f"{d}px", "50%", ring, "none", "none"),
                 _ink("transparent", "none")),
        "filled": (_geo(f"{d}px", f"{d}px", "50%", "0 solid", "none", "none"),
                   _ink("currentColor", "none")),
        "diamond": (_geo(f"{d}px", f"{d}px", "1px", "0 solid", "none", "rotate(45deg)"),
                    _ink("currentColor", "none")),
        "ring_halo": (_geo(f"{d}px", f"{d}px", "50%", "1.5px solid currentColor",
                           "1px solid currentColor; outline-offset: 1px", "none"),
                      _ink("transparent", "none")),
        "bar": (_geo(f"{d}px", "2px", "1px", "0 solid", "none", "none"),
                _ink("currentColor", "none")),
        "bar_struck": (_geo(f"{d}px", "2px", "1px", "0 solid", "none", "rotate(-45deg)"),
                       _ink("currentColor", "none")),
    }
    signals = "\n".join(
        f"/* {name} */\n"
        f".dag-node.{tokens['material']['node']['classes']['status_prefix']}{st} :where(.nc-dot)"
        f" {{ {shape[name][0]} }}\n"
        f":where(.dag-node.{tokens['material']['node']['classes']['status_prefix']}{st} .nc-dot)"
        f" {{ {shape[name][1]} }}"
        for st, name in sig.items() if name in shape)
    return f"""/* node.generated.css — AUTO-GENERATED by nika-spec design-projector.
   DO NOT EDIT · regenerate: python3 scripts/design-projector.py --write
   Values live in design/tokens.yaml (material.card + material.node.signal),
   read out of the shipped canvas. Every surface that draws a node receives THIS
   file, so the site, the design bench and the VS Code canvas cannot drift.

   Colour is not here on purpose — it projects separately and each surface binds
   it to its own host. TYPE SIZE is host-bound for the same reason and one more:
   a card sits inside a page that owns a type scale, and the page must win. The
   canvas already defines --nk-fs-* (12.5 · 11 · 10.5 · 10 · 9.5), so it keeps
   ROW HEIGHTS ARE MINIMA, not fixed. They were `height:` — the canvas's exact
   pixel rows, sized for the canvas's own type. The moment type became
   host-bound, a surface with a larger ramp overflowed its row and the text sat
   ON the dashed rule below it: the card read as if it had dotted leaders
   running through every mechanism line. A row that must hold text the host
   sizes cannot be a fixed height. The canvas is unchanged — its content is
   exactly its old height, so the minimum is the height.

   its ramp untouched; the fallbacks below are whole pixels because a half step
   was measured three times to move nothing. The fallback ramp is COARSER than
   the bound one on purpose — six steps inside 3.5px cannot all be whole and
   distinct, so sub/body/meta collapse to one floor. It is a safety net for a
   surface that binds nothing, not the ramp. Everything is :where(), specificity zero: the canvas's own
   139 selectors sit on top and win. */
:where(.nc) {{
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: {c["pad_y_px"]}px {c["pad_x_px"]}px;
  border-radius: {c["radius_px"]}px;
  font-family: var(--nk-mono, ui-monospace, monospace);
  color: var(--nk-ink, currentColor);
  background: var(--nk-card, transparent);
  border: 1px solid var(--nk-card-border, currentColor);
}}
:where(.nc-head) {{
  display: flex;
  align-items: center;
  gap: {c["head_gap_px"]}px;
  min-height: {c["head_h_px"]}px;
  flex: none;
}}
:where(.nc-tile) {{
  flex: 0 0 auto;
  width: {c["tile_px"]}px;
  height: {c["tile_px"]}px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--nk-fs-label, {round(fs["label_px"])}px);
  border-radius: {c["tile_radius_px"]}px;
}}
:where(.nc-id) {{
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--nk-fs-heading, {round(fs["heading_px"])}px);
  font-weight: var(--nk-fw-strong, 600);
  letter-spacing: 0.01em;
}}
:where(.nc-st) {{
  flex: 0 0 {c["st_w_px"]}px;
  width: {c["st_w_px"]}px;
  min-height: {c["head_h_px"]}px;
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}}
:where(.nc-dot) {{
  flex: 0 0 auto;
  width: {d}px;
  height: {d}px;
  border-radius: 50%;
  background: currentColor;
  opacity: {c["dot_rest_alpha"]};
}}
:where(.nc-sub) {{
  flex: none;
  display: flex;
  align-items: baseline;
  gap: {c["sub_gap_px"]}px;
  min-height: {c["sub_h_px"]}px;
  font-size: var(--nk-fs-sub, {round(fs["sub_px"])}px);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}}
:where(.nc-sub-k) {{ flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis; }}
:where(.nc-sub-v) {{ flex: 0 0 auto; margin-left: auto; }}
:where(.nc-body) {{
  margin-top: {c["body_top_px"]}px;
  font-size: var(--nk-fs-body, {round(fs["body_px"])}px);
  line-height: {c["body_line_px"]}px;
  color: color-mix(in srgb, var(--nk-ink, currentColor) {int(c["body_ink"] * 100)}%, transparent);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: {c["body_clamp"]};
  -webkit-box-orient: vertical;
  word-break: break-word;
}}
:where(.nc-chip) {{
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: {c["chip_pad_y_px"]}px {c["chip_pad_x_px"]}px;
  font-size: var(--nk-fs-meta, {round(fs["meta_px"])}px);
  font-family: var(--nk-mono, ui-monospace, monospace);
  background: color-mix(in srgb, var(--nk-ink, currentColor) {int(c["chip_fill"] * 100)}%, transparent);
  border: 1px solid var(--nk-border, currentColor);
  border-radius: {c["chip_radius_px"]}px;
}}
:where(.nc-badge) {{
  flex: 0 0 auto;
  font-size: var(--nk-fs-meta, {round(fs["meta_px"])}px);
  padding-right: {c["badge_clear_px"]}px;
}}

/* THE SECOND SIGNAL · one geometry per status, because a hue dies under
   forced-colors and under a colour-blind eye. `pending` is the deliberate
   understatement: smaller, and nothing else. */
{signals}

@media (prefers-reduced-motion: reduce) {{
  :where(.nc) {{ transition: none; }}
}}
"""


def render_ground_css(tokens: dict) -> str:
    """TARGET 1+2 · THE GROUND, for every surface that draws the pool.

    This used to live as a JS generator in the website repo, which meant one
    source reached TWO surfaces and the canvas — a different repository — could
    not consume it. A generator that cannot reach a surface is not a source of
    truth for that surface; it is a source of truth for the surfaces that
    happen to share its language. So it moved here, beside the quantities, and
    is projected exactly like the token module.

    Everything below was READ out of nika-vscode src/webview/dag.css. The only
    thing decided here is the cursor, and even that is the ground's own tick."""
    g = tokens["material"]["ground"]
    grid, cur = g["grid"], g["cursor"]
    hot = cur["box_px"] / 2
    return f"""/* ground.generated.css — AUTO-GENERATED by nika-spec design-projector.
   DO NOT EDIT · regenerate: python3 scripts/design-projector.py --write
   Values live in design/tokens.yaml (material.ground), read out of the shipped
   canvas. Every surface that draws the pool receives THIS file, so the site,
   the design bench and the VS Code canvas cannot drift apart. */
.nk-ground {{
  position: relative;
  isolation: isolate;
  /* THE POINTER IS THE PLANE'S OWN TICK, larger and brighter — moving the
     sheet reads as moving a survey grid rather than dragging a page. The
     native cursor stays as the fallback, so a browser that refuses the image
     still says « you can grab this ». */
  cursor: {_cross(cur['box_px'], cur['arm_px'], 1, halo=cur['halo'], width=cur['stroke_px'])} {hot:g} {hot:g}, grab;
  background-color: var(--nk-page, var(--nk-bg));
  background-image: {_cross(grid['cell_px'], grid['arm_px'], grid['stroke'])};
  background-size: {grid['cell_px']}px {grid['cell_px']}px;
}}
/* held · the arms tighten, because a gripped plane is a smaller gesture */
.nk-ground:active {{
  cursor: {_cross(cur['box_px'], cur['arm_held_px'], 1, halo=cur['halo'], width=cur['stroke_px'])} {hot:g} {hot:g}, grabbing;
}}
/* zoomed out, a finer mesh becomes noise: coarser pitch, firmer stroke */
.nk-ground[data-lod='far'] {{
  background-image: {_cross(grid['far_cell_px'], grid['far_arm_px'], grid['far_stroke'])};
  background-size: {grid['far_cell_px']}px {grid['far_cell_px']}px;
}}
.nk-ground[data-grid='off'] {{ background-image: none; }}

/* the vignette · the pool falls away at its edges, AND IT KNOWS THE RUN.
   While tasks execute the falloff tightens and the rim darkens: it is the only
   ambient signal that a run is in flight. */
.nk-ground::before {{
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  border-radius: inherit;
  background: {_vignette(g['vignette'])};
  transition: background var(--dur-drawer) var(--ease-ui);
}}
.nk-ground[data-running]::before {{ background: {_vignette(g['vignette_running'])}; }}
.nk-ground[data-vignette='off']::before {{ background: none; }}

/* the spot · a blue lamp that follows the pointer. It existed in the canvas
   before the web invented a white one; this is the original. Coordinates in
   PIXELS, as the canvas writes them. */
.nk-ground::after {{
  content: '';
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  border-radius: inherit;
  opacity: var(--spot-on, 0);
  transition: opacity var(--dur-spot) ease-out;
  background: radial-gradient(
    {g['spot']['radius_px']}px circle at var(--spot-x, 50%) var(--spot-y, 40%),
    rgb({g['spot']['hue']} / {g['spot']['alpha']}),
    transparent {g['spot']['fade'] * 100}%
  );
}}
.nk-ground[data-spot='off']::after {{ opacity: 0; }}

@media (prefers-reduced-motion: reduce) {{
  .nk-ground::before,
  .nk-ground::after {{ transition: none; }}
}}
@media (forced-colors: active) {{
  /* mesh and vignette are DEPTH, not information: in forced colours they
     leave rather than eat the contrast the content needs */
  .nk-ground {{ background-image: none; cursor: grab; }}
  .nk-ground::before,
  .nk-ground::after {{ display: none; }}
}}
"""


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


MOTION_PATH = SPEC_ROOT / "design" / "motion.yaml"


def check_motion() -> bool:
    """TARGET 0b · motion.yaml's own gates, finally run.

    That file has declared five CI gates since it was written and NONE of them
    existed — it is the only design SSOT in this repo with no reader at all,
    which is why its `slow` drifted to a different value from the website's
    `slow` without anything noticing. Four of the five are checkable from the
    file alone and run here. The fifth (« css_keyframes exists verbatim
    site-side ») cannot be run honestly: no surface defines those keyframes
    yet, so the file no longer claims it is gated.

    Note gate 1 scopes to `frames`. `exec.edge_frames` is a FOUR-cell rail
    window by design — sweeping it here would have made the gate unshippable
    and taught us to delete it rather than fix it."""
    if not MOTION_PATH.exists():
        print("design-projector · design/motion.yaml missing", file=sys.stderr)
        sys.exit(2)
    m = yaml.safe_load(MOTION_PATH.read_text()).get("motion", {})
    fams = m.get("families", {})
    if tuple(fams.keys()) != CANON_VERBS:
        print(f"design-projector · motion.families must be exactly {CANON_VERBS} "
              f"in order, got {tuple(fams.keys())}", file=sys.stderr)
        sys.exit(2)
    floor = m.get("duration", {}).get("fast")
    ok = True

    def bad(msg: str) -> None:
        nonlocal ok
        ok = False
        print(f"design-projector · motion: {msg}", file=sys.stderr)

    rests, dones = set(), set()
    for verb, fam in fams.items():
        t = fam.get("terminal", {})
        frames, ascii_fb = t.get("frames", []), t.get("ascii_fallback", [])
        dur = fam.get("duration_ms")
        # 1 · one cell per frame
        for f in frames:
            if len(f) != 1:
                bad(f"{verb} frame {f!r} is {len(f)} cells, must be exactly 1")
        # 2 · the cadence divides evenly and never beats faster than the floor
        for name, seq in (("frames", frames), ("ascii_fallback", ascii_fb)):
            if not seq:
                bad(f"{verb} has no {name}")
                continue
            if dur % len(seq):
                bad(f"{verb} duration_ms {dur} is not divisible by {len(seq)} {name}")
            elif dur // len(seq) < floor:
                bad(f"{verb} {name} beats every {dur // len(seq)}ms, under the "
                    f"{floor}ms floor (duration.fast)")
        # 4 · the fallback is printable ASCII, or it is not a fallback
        for f in ascii_fb:
            if not all(0x20 <= ord(c) <= 0x7E for c in f):
                bad(f"{verb} ascii_fallback {f!r} leaves 0x20-0x7E")
        rests.add(t.get("rest"))
        dones.add(t.get("done"))
    # 5 · one vocabulary at rest and at done, across every family
    if len(rests) != 1 or len(dones) != 1:
        bad(f"rest/done differ across families: rest={rests} done={dones}")

    if ok:
        print(f"✓ motion gates · {len(fams)} families · 1 cell · cadence ≥ "
              f"{floor}ms · ascii fallback · one rest/done")
    return ok


def check_icon_ontology(tokens: dict, website: Path) -> bool:
    """TARGET 1 · every `verbs.*.icon` must name a real entity in the website's
    icon ontology.

    This field claims to be « the nika.sh ontology id » and nothing ever read
    it, so nothing ever disagreed with it: on 2026-07-28 three of the four were
    wrong — two had dropped the family prefix and `agent` named `agent-graph`,
    a string that appears nowhere in that file. A binding stored for a surface
    that never resolves it is decoration inside a source of truth.

    Absent ontology = skipped, not failed (a standalone spec clone has no
    website); a MALFORMED one is an environment error, because silently passing
    is how the field got here."""
    path = website.parent / "public" / "brand" / "icons.json"
    if not path.exists():
        print("· website icons.json absent · icon ontology check skipped")
        return True
    try:
        entities = json.loads(path.read_text()).get("entities", {})
    except (json.JSONDecodeError, OSError) as exc:
        print(f"design-projector · icons.json unreadable: {exc}", file=sys.stderr)
        sys.exit(2)
    ok = True
    for verb in CANON_VERBS:
        want = tokens["verbs"][verb]["icon"]
        got = (entities.get(f"verb/{verb}") or {}).get("glyph")
        if want != got:
            ok = False
            print(f"design-projector · verbs.{verb}.icon is {want!r} but the "
                  f"ontology says {got!r} (public/brand/icons.json · verb/{verb})",
                  file=sys.stderr)
    if ok:
        print(f"✓ icon ontology agrees · {len(CANON_VERBS)} verbs")
    return ok


def main() -> int:
    write = "--write" in sys.argv
    tokens = load_tokens()  # TARGET 0 · exits 2 on schema violation
    rendered = render_ts(tokens)
    ok = check_motion()     # TARGET 0b · motion.yaml's own five gates

    website = _sibling("NIKA_WEBSITE_SRC",
                       SPEC_ROOT.parent / "website" / "src",
                       SPEC_ROOT.parent.parent / "website" / "src")
    # THE GROUND, for every surface that draws the pool. It used to be a JS
    # generator inside the website repo, which meant one source reached TWO
    # surfaces and the canvas — a different repository — could not consume it.
    # A generator that cannot reach a surface is not that surface's source of
    # truth. So it is projected here, exactly like the token module.
    ground = render_ground_css(tokens)
    card = render_card_css(tokens)

    if website:
        ok &= project_ts(website / "design-tokens.generated.ts", rendered,
                         write, "website")
        ok &= project_ts(website / "styles" / "ground.generated.css", ground,
                         write, "website ground")
        ok &= project_ts(website / "styles" / "node.generated.css", card,
                         write, "website card")
        ok &= check_icon_ontology(tokens, website)
    else:
        print("· website src/ absent · skipped")

    vscode = _sibling("NIKA_VSCODE_SRC",
                      SPEC_ROOT.parent / "vscode" / "repo" / "src",
                      SPEC_ROOT.parent.parent / "vscode" / "repo" / "src",
                      SPEC_ROOT.parent / "vscode" / "src")
    if vscode:
        ok &= project_ts(vscode / "design-tokens.generated.ts", rendered,
                         write, "vscode")
        # the canvas draws the pool too · the file lands beside its own sheet
        webview = vscode / "webview"
        if webview.is_dir():
            ok &= project_ts(webview / "ground.generated.css", ground,
                             write, "vscode ground")
            ok &= project_ts(webview / "node.generated.css", card,
                             write, "vscode card")
        else:
            print("· vscode webview/ absent · ground + card skipped")
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
