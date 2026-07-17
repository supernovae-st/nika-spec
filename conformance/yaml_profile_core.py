#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The reference YAML-profile judge (RULINGS R11 · LAW-GRAMMAR-0101..0111).

Judges a `.nika.yaml` SOURCE at the byte + event level — never through a
composing load. R11 point 6: no engine may expand anchors silently; the
refusal happens BEFORE any construction, so nothing here ever resolves
an alias or merges a key. R11 point 4: every refusal is a dedicated,
pedagogical diagnostic — YAML valid but not admitted by the Nika
profile, never a generic parse error. THE teachings live in
canon/diagnostics/registry.yaml (NIKA-YAML-001..011) — this module
loads them so the verdict and the registry speak with one voice.

The ruled caps (D-2026-07-17-N5 · a net refusal, never truncation):

  NIKA-YAML-001  anchor present (even unreferenced · R11 point 3)
  NIKA-YAML-002  alias present
  NIKA-YAML-003  merge key `<<` present
  NIKA-YAML-004  duplicate mapping key
  NIKA-YAML-005  scalar > 65 536 bytes (64 KiB · closes gap P5)
  NIKA-YAML-006  custom tag (outside the YAML core schema)
  NIKA-YAML-007  non-string mapping key
  NIKA-YAML-008  non-finite float (.nan / .inf / -.inf)
  NIKA-YAML-009  document depth > 64 levels
  NIKA-YAML-010  document > 1 048 576 bytes (1 MiB)
  NIKA-YAML-011  BOM present, or source bytes not NFC

A source that does not parse at all is NOT a profile refusal — it
surfaces as NIKA-PARSE-001 pass-through (the profile question needs a
parseable event stream). PyYAML's implicit resolver is YAML 1.1 (`yes`
resolves bool), slightly wider than the 1.2 core schema an engine may
use — fixtures stay inside the intersection (`123:` is an int in both).
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import yaml
from yaml.nodes import ScalarNode
from yaml.resolver import Resolver

# The ruled caps — D-2026-07-17-N5. The registry declaration lives in
# canon/grammar.yaml (yaml_scalar_cap · yaml_document_caps value_shape
# ids encode the same numbers); the selftest cross-checks the two.
DEPTH_CAP = 64                 # levels · root collection = level 1
DOCUMENT_CAP = 1_048_576       # bytes of source (1 MiB)
SCALAR_CAP = 65_536            # UTF-8 bytes of one scalar value (64 KiB)

YAML_CORE_TAGS = {
    "tag:yaml.org,2002:str", "tag:yaml.org,2002:int", "tag:yaml.org,2002:float",
    "tag:yaml.org,2002:bool", "tag:yaml.org,2002:null", "tag:yaml.org,2002:map",
    "tag:yaml.org,2002:seq",
}
STR_TAG = "tag:yaml.org,2002:str"
FLOAT_TAG = "tag:yaml.org,2002:float"
NON_FINITE = re.compile(r"^(?:[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$")
BOM_BYTES = b"\xef\xbb\xbf"

# One voice with the registry: teachings come from the diagnostics rows.
_REGISTRY = yaml.safe_load(
    (Path(__file__).parent.parent / "canon" / "diagnostics" / "registry.yaml")
    .read_text(encoding="utf-8"))
TEACHING = {row["id"]: row["teaching"] for row in _REGISTRY["diagnostics"]
            if row["id"].startswith(("NIKA-YAML-", "NIKA-PARSE-001"))}

_RESOLVER = Resolver()


def _mark(mark) -> str:
    return f"line {mark.line + 1}, column {mark.column + 1}" if mark else "unknown position"


def _refuse(code: str, detail: str) -> dict:
    return {"code": code, "namespace": "NIKA-YAML", "category": "profile_violation",
            "detail": detail, "teaching": TEACHING[code]}


def _parse_error(detail: str) -> dict:
    return {"code": "NIKA-PARSE-001", "namespace": "NIKA-PARSE",
            "category": "parse_error", "detail": detail,
            "teaching": TEACHING["NIKA-PARSE-001"]}


def _resolved_tag(event) -> str:
    """The tag a core-schema loader would give this scalar event."""
    if event.tag is not None:
        return event.tag
    if event.style is None:  # plain · implicit resolution applies
        return _RESOLVER.resolve(ScalarNode, event.value, (True, False))
    return STR_TAG  # quoted / literal / folded scalars are strings


class _Frame:
    """One open collection during the event walk."""

    __slots__ = ("kind", "expect_key", "seen_keys")

    def __init__(self, kind: str):
        self.kind = kind          # "map" | "seq"
        self.expect_key = True    # maps alternate key / value
        self.seen_keys: set[str] = set()


def profile_errors(source: bytes | str) -> list[dict]:
    """Judge one source against the full Nika YAML profile (R11 +
    D-2026-07-17-N5). Returns refusals in document order; [] admits.
    A document over the 1 MiB cap refuses NET — nothing else is judged
    past the resource boundary (never a truncate-and-continue)."""
    raw = source.encode("utf-8") if isinstance(source, str) else source
    errs: list[dict] = []

    # ── byte-level laws (before any parse) ──────────────────────────────
    if len(raw) > DOCUMENT_CAP:
        return [_refuse("NIKA-YAML-010",
                        f"document is {len(raw)} bytes · the profile caps a document "
                        f"at {DOCUMENT_CAP} bytes (1 MiB · D-2026-07-17-N5) — a net "
                        "refusal, never truncation")]
    bom = raw.startswith(BOM_BYTES)
    if bom:
        errs.append(_refuse("NIKA-YAML-011",
                            "byte order mark (U+FEFF) at byte 0 · the profile refuses "
                            "a BOM (D-2026-07-17-N5)"))
        raw = raw[len(BOM_BYTES):]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        errs.append(_parse_error(f"source is not UTF-8 ({exc})"))
        return errs
    if not unicodedata.is_normalized("NFC", text):
        errs.append(_refuse("NIKA-YAML-011",
                            "source bytes are not NFC-normalized · the profile requires "
                            "NFC (D-2026-07-17-N5) — two encodings of the same text "
                            "must never hash apart"))

    # ── event-level laws (parse, never compose) ─────────────────────────
    stack: list[_Frame] = []
    depth_reported = False

    def consume_slot() -> str:
        """Advance the enclosing map's key/value alternation; return the
        role ('key' | 'value' | 'item' | 'root') the current node fills."""
        if not stack:
            return "root"
        top = stack[-1]
        if top.kind == "seq":
            return "item"
        role = "key" if top.expect_key else "value"
        top.expect_key = not top.expect_key
        return role

    try:
        for event in yaml.parse(text):
            where = _mark(getattr(event, "start_mark", None))
            if isinstance(event, yaml.events.AliasEvent):
                errs.append(_refuse("NIKA-YAML-002",
                                    f"alias (*{event.anchor}) at {where} · R11 point 1"))
                consume_slot()
                continue
            anchor = getattr(event, "anchor", None)
            if anchor is not None and not isinstance(event, yaml.events.AliasEvent):
                errs.append(_refuse("NIKA-YAML-001",
                                    f"anchor (&{anchor}) at {where} · R11 points 1+3: "
                                    "refused even when never referenced"))
            tag = getattr(event, "tag", None)
            if tag is not None and tag not in YAML_CORE_TAGS:
                errs.append(_refuse("NIKA-YAML-006",
                                    f"custom tag {tag} at {where} · R11 point 13: only "
                                    "the YAML core schema (str, int, float, bool, null, "
                                    "map, seq) is admitted"))
            if isinstance(event, (yaml.events.MappingStartEvent,
                                  yaml.events.SequenceStartEvent)):
                role = consume_slot()
                if role == "key":
                    errs.append(_refuse("NIKA-YAML-007",
                                        f"collection used as a mapping key at {where} · "
                                        "R11 point 13: mapping keys are strings"))
                kind = "map" if isinstance(event, yaml.events.MappingStartEvent) else "seq"
                stack.append(_Frame(kind))
                if len(stack) > DEPTH_CAP and not depth_reported:
                    depth_reported = True
                    errs.append(_refuse("NIKA-YAML-009",
                                        f"nesting reaches level {len(stack)} at {where} · "
                                        f"the profile caps depth at {DEPTH_CAP} levels "
                                        "(D-2026-07-17-N5)"))
                continue
            if isinstance(event, (yaml.events.MappingEndEvent,
                                  yaml.events.SequenceEndEvent)):
                stack.pop()
                continue
            if isinstance(event, yaml.events.ScalarEvent):
                size = len(event.value.encode("utf-8"))
                if size > SCALAR_CAP:
                    errs.append(_refuse("NIKA-YAML-005",
                                        f"scalar of {size} bytes at {where} · the profile "
                                        f"caps a scalar at {SCALAR_CAP} bytes (64 KiB · "
                                        "D-2026-07-17-N5) — move the payload to a "
                                        "referenced file"))
                role = consume_slot()
                if role == "key":
                    if event.style is None and event.value == "<<":
                        errs.append(_refuse("NIKA-YAML-003",
                                            f"merge key (<<) at {where} · R11 point 1: "
                                            "compose mappings explicitly"))
                        continue
                    rtag = _resolved_tag(event)
                    if rtag != STR_TAG:
                        errs.append(_refuse("NIKA-YAML-007",
                                            f"non-string mapping key {event.value!r} "
                                            f"(resolves {rtag.rsplit(':', 1)[-1]}) at "
                                            f"{where} · R11 point 13"))
                        continue
                    if event.value in stack[-1].seen_keys:
                        errs.append(_refuse("NIKA-YAML-004",
                                            f"duplicate mapping key {event.value!r} at "
                                            f"{where} · R11 points 5+13: no silent "
                                            "last-wins"))
                    stack[-1].seen_keys.add(event.value)
                elif _resolved_tag(event) == FLOAT_TAG and NON_FINITE.match(event.value):
                    errs.append(_refuse("NIKA-YAML-008",
                                        f"non-finite float {event.value!r} at {where} · "
                                        "R11 point 13: the canonical JSON of the "
                                        "Semantic IR admits only finite numbers"))
    except yaml.YAMLError as exc:
        errs.append(_parse_error(str(exc).replace("\n", " · ")))

    # de-dup (a multi-document stream can repeat a byte-level finding)
    seen: set[tuple[str, str]] = set()
    out = []
    for e in errs:
        k = (e["code"], e["detail"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out


def judge_file(path: Path) -> list[dict]:
    return profile_errors(path.read_bytes())


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: yaml_profile_core.py <file.nika.yaml> [...]", file=sys.stderr)
        return 2
    refused = False
    for name in argv[1:]:
        errs = judge_file(Path(name))
        if not errs:
            print(f"ADMIT  {name}")
            continue
        refused = True
        for e in errs:
            print(f"REFUSE {name} · {e['code']} · {e['detail']}")
            print(f"       teaching: {e['teaching']}")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
