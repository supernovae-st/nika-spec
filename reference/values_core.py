#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The reference value-authority core (E-split · R3a + R3b defaults).

STATUS · the value authorities of nika: v1 are EXACTLY three ·
`inputs` · `const` · `secrets`. `config` died with the envelope nuke: it
had zero WORK usage, its `default:` was its only possible source, and
under the taint lattice `config.p` and `inputs.p` produced the SAME
`NIKA-AUTH-008` by the same path — indiscernible. A deployment-supplied
value is an `inputs:` entry with `required: false` and a `default:`. This
module is the reference judge of that family at the envelope. It resolves
the declared authorities, refuses the dead forms `vars:`/`env:`, refuses a
value-namespace reference outside the family, and validates every declared
default/constant against its declared type (the P0 soundness hole
`{type: integer, default: "abc"}` that passed check AND run).

Sources (locked rulings only · nothing here is invented):
  · RULINGS_2026-07-15.md §R3a (E-split · vars/env die · classify-not-rename)
  · RULINGS_2026-07-15.md §R3b (TypeExpr widen · validate the defaults)
  · canon/laws/values.yaml  (LAW-SURFACE-0201 · LAW-GRAMMAR-0201 · 0202 · LAW-SURFACE-0202)
  · canon/laws/types.yaml   (LAW-TYPE-0211 · a default conforms to its declared type)

Diagnostic codes (canon/laws/values.yaml + types.yaml · c0-proposed namespace):
  NIKA-VALUES-001   the dead `vars:` envelope field OR a `${{ vars.X }}` read
  NIKA-VALUES-002   the dead `env:` envelope field OR a `${{ env.X }}` read
  NIKA-VALUES-003   a value-namespace read outside the three-authority family
  NIKA-DEFAULT-001  a declared default/constant value not conforming to its type

Independence stance: this value core is the SECOND evaluator · written BY
HAND against the laws, never generated from nor generating the Rust engine.
It reuses the reference type core (`type_core.parse_type` + `fits`) so a
declared default is judged by the SAME type relation the returns-contract
already uses (reference/semantics.py W3 slice) · one type truth, two call
sites.

Determinism law: judging is a pure function of the parsed workflow · no
clocks, no randomness, no I/O.

HONEST LIMIT (C2 Session B · the STOP-not-guess principle): the `${{ }}`
reference scan is a SURFACE scan (islands · quoted strings stripped · dotted
roots). A CEL comprehension-bound local spelled like a namespace
(`list.all(config, config)`) is out of scope here · the full CEL binder
lands with the checker wiring (Session C · conformance/runner.py). The
fixtures reference only unambiguous namespace roots.
"""

from __future__ import annotations

import re
import sys as _sys
from pathlib import Path as _Path

# the reference type core lives in conformance/ · reuse ONE type truth
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "conformance"))
from type_core import parse_type as _parse_type  # noqa: E402
from type_core import fits as _fits  # noqa: E402
from type_core import TypeError_ as _TypeError  # noqa: E402

import yaml  # noqa: E402


# the closed three-authority family (R3a · LAW-SURFACE-0201 · `config`
# died with the envelope nuke — the deployment-supplied role folded into
# `inputs:` + `required: false`)
VALUE_AUTHORITIES = ("inputs", "const", "secrets")
# the runtime / local namespaces · legal in ${{ }}, never value authorities.
# `group` is the fan-in reader (03 §group) — the PLURAL of `tasks`, same
# runtime family, so the value-authority family and the namespace count are
# both untouched by it.
RUNTIME_NAMESPACES = frozenset({"tasks", "group", "with", "item", "index"})
# the dead forms · each carries its own teaching (LAW-GRAMMAR-0201 · 0202)
DEAD_FORMS = {"vars": "NIKA-VALUES-001", "env": "NIKA-VALUES-002"}

# an unescaped `${{ ... }}` island · a leading backslash (`\${{`) escapes the
# opener to a literal, exactly as the runner's substitution surface reads it
# (04-variables.md · EXPR_OPEN) — an escaped island is text, never a reference
_ISLAND = re.compile(r"(?<!\\)\$\{\{(.*?)\}\}", re.DOTALL)
_QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"' + r"|'(?:[^'\\]|\\.)*'")
# a namespace root · a lowercase identifier followed by '.', not itself a member
_ROOT = re.compile(r"(?<![\w.])([a-z][a-z0-9_]*)\s*\.")


class ValueError_(Exception):
    """One value-authority violation · carries (code, detail)."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def err(code: str, detail: str) -> dict:
    """One value-authority violation in the runner's error shape
    (code · category · detail) · every value-core code is a validation_error."""
    return {"code": code, "category": "validation_error", "detail": detail}


# ── resolution · the envelope value environment (R3a) ────────────────────

def resolve_envelope(doc: dict) -> dict:
    """Parse the envelope into the resolved value environment · the three
    authorities keyed by name (R3a). `inputs` carries a declared
    `type` (+ optional `required`/`default`); `const` carries a bare literal
    or a typed `{type, value}`; `secrets` carries a governed store reference.
    The dead forms are NOT resolved here · they refuse in
    values_core_errors."""
    env: dict[str, dict] = {a: {} for a in VALUE_AUTHORITIES}
    if not isinstance(doc, dict):
        return env
    for auth in VALUE_AUTHORITIES:
        block = doc.get(auth)
        if isinstance(block, dict):
            env[auth] = dict(block)
    return env


def resolve_reference(namespace: str, name: str, env: dict):
    """Resolve `${{ <namespace>.<name> }}` to its declared entry, or None
    when the name is not declared in that authority. Membership of the
    family is judged separately (see values_core_errors) · this helper is
    the read half of the resolution."""
    block = env.get(namespace)
    if isinstance(block, dict):
        return block.get(name)
    return None


# ── the ${{ }} reference scan (surface) ──────────────────────────────────

def _reference_roots(text) -> list[str]:
    """Every dotted namespace root inside every ${{ }} island of `text`,
    quoted strings stripped first (a dotted path inside a CEL string literal
    is data, never a namespace)."""
    roots: list[str] = []
    for m in _ISLAND.finditer(str(text)):
        body = _QUOTED.sub('""', m.group(1))
        roots.extend(_ROOT.findall(body))
    return roots


def _walk_strings(node):
    """Yield every string scalar in the document (prompts · with · args ·
    command · when) · the reference scan reads them all."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _walk_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_strings(v)


# ── the default / constant type check (R3b · LAW-TYPE-0211) ──────────────

def _default_errors(doc: dict, env: dict) -> list[dict]:
    """Every declared default (inputs) and every typed constant
    value (const `{type, value}`) MUST conform to its declared type
    (R3b · LAW-TYPE-0211 · NIKA-DEFAULT-001). Reuses the reference type
    core: parse the declared type, then fit the value. An invalid declared
    type is reported elsewhere (schema · type_core) · the check skips it."""
    errs: list[dict] = []
    # named types died with the `types:` block — a type expression is
    # self-contained (spec/09-types.md), so the name environment is empty
    names: set[str] = set()
    named: dict[str, dict] = {}

    def _check(where: str, type_expr, value) -> None:
        try:
            t = _parse_type(type_expr, names, where)
        except _TypeError:
            return  # an invalid declared type refuses via the schema / type core
        if not _fits(value, t, named):
            errs.append(err(
                "NIKA-DEFAULT-001",
                f"{where} · the value {value!r} does not conform to its declared "
                f"type · the P0 soundness hole (a value that passes check and "
                f"fails at run) is closed (R3b · LAW-TYPE-0211)"))

    for name, decl in env.get("inputs", {}).items():
        if isinstance(decl, dict) and "type" in decl and "default" in decl:
            _check(f"inputs.{name}.default", decl["type"], decl["default"])

    for name, decl in env.get("const", {}).items():
        if isinstance(decl, dict) and "type" in decl and "value" in decl:
            _check(f"const.{name}.value", decl["type"], decl["value"])

    return errs


# ── the value-authority layer (mirrors type_core.type_core_errors) ───────

def values_core_errors(doc: dict) -> list[dict]:
    """The reference value-authority layer (E-split · R3a + R3b defaults).
    Returns refusals in a stable order; [] admits. Shaped like
    type_core.type_core_errors · the checker (Session C) extends
    validate_workflow with this list the SAME way it already extends it with
    type_core_errors, one type/value truth flowing to every surface."""
    errs: list[dict] = []
    if not isinstance(doc, dict):
        return errs

    # ── the dead envelope fields (LAW-GRAMMAR-0201 · 0202) ──────────────
    if "vars" in doc:
        errs.append(err(
            "NIKA-VALUES-001",
            "vars: is a dead envelope field (R3a · the E-split) · a typed parameter "
            "is an `inputs:` declaration, a fixed value is a `const:` entry "
            "(classify-not-rename · equivalence-or-stop · never a bulk rename)"))
    if "env" in doc:
        errs.append(err(
            "NIKA-VALUES-002",
            "env: is a dead envelope field (R3a · the E-split) · non-sensitive "
            "runtime configuration is an `inputs:` declaration with "
            "`required: false` and a `default:`, a governed store reference is a "
            "`secrets:` entry"))

    # ── the value-namespace family (LAW-SURFACE-0201) ──────────────────
    env = resolve_envelope(doc)
    seen: set[tuple[str, str]] = set()
    for text in _walk_strings(doc):
        for root in _reference_roots(text):
            if root in VALUE_AUTHORITIES or root in RUNTIME_NAMESPACES:
                resolve_reference(root, "", env)  # a family / runtime read · never refuse
                continue
            if root in DEAD_FORMS:
                code = DEAD_FORMS[root]
                detail = (
                    f"${{{{ {root}.X }}}} reads the dead `{root}` namespace "
                    f"(R3a · the E-split) · read the value authority its role "
                    f"commands ({' · '.join(VALUE_AUTHORITIES)})")
            else:
                code = "NIKA-VALUES-003"
                detail = (
                    f"${{{{ {root}.X }}}} reads `{root}`, a value namespace outside "
                    f"the three-authority family (R3a · LAW-SURFACE-0201) · the "
                    f"authorities are exactly {' · '.join(VALUE_AUTHORITIES)}")
            key = (code, root)
            if key not in seen:
                seen.add(key)
                errs.append(err(code, detail))

    # ── defaults / constants conform to their declared type (LAW-TYPE-0211)
    errs.extend(_default_errors(doc, env))
    return errs


# ── CLI (imitates conformance/yaml_profile_core.py) ──────────────────────

def judge_file(path: _Path) -> list[dict]:
    doc = yaml.safe_load(_Path(path).read_text(encoding="utf-8"))
    return values_core_errors(doc if isinstance(doc, dict) else {})


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: values_core.py <file.nika.yaml> [...]", file=_sys.stderr)
        return 2
    refused = False
    for name in argv[1:]:
        errs = judge_file(_Path(name))
        if not errs:
            print(f"ADMIT  {name}")
            continue
        refused = True
        for e in errs:
            print(f"REFUSE {name} · {e['code']} · {e['detail']}")
    return 1 if refused else 0


if __name__ == "__main__":
    _sys.exit(main(_sys.argv))
