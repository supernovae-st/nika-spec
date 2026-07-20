# SPDX-License-Identifier: Apache-2.0
"""The reference type core (spec 09-types.md) — the SECOND evaluator.

Parses the closed v1 type grammar, checks the static rules
(NIKA-TYPE-001..006 · NIKA-PARSE-025), lowers to JSON Schema 2020-12 and
decides the three relations of 09 §the relations:

- ``subtype``    · A ⊑ B  — a PARTIAL ORDER on known types (reflexive ·
  transitive · antisymmetric · ``Unknown`` comparable only to itself ·
  ``Never`` is bottom).
- ``consistent`` · A ~ B  — gradual consistency (reflexive · symmetric ·
  NOT transitive · ``Unknown ~ T`` · structural elsewhere).
- ``assignable`` · A ⊑~ B — consistent subtyping (Siek-Taha): what every
  static judge consumes (the walk · TYPE-004 · the static fit).

Independence stance: this file is written BY HAND against the spec prose
— never generated from, nor generating, the Rust implementation. The
differential (``type_differential.py``) is the bridge; a shared bug
would have to be born twice.
"""

from __future__ import annotations

import re

PRIMITIVES = {
    "null", "bool", "integer", "number", "string", "bytes",
    "uri", "path", "duration", "timestamp",
}
STRING_NEWTYPES = {"uri", "path", "duration", "timestamp"}
# the sole public reserved constructor of the group (spec 09 §reserved · R6)
# result/secret/money are WITHDRAWN (R6 points 1/2/4): not reserved, not
# known — they refuse as unknown type names, never with a wave claim.
RESERVED = {
    "artifact": "reserved-not-implemented",
}
TYPE_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")
COMPOSITE_KEYS = {
    "array", "map", "object", "union", "optional", "enum",
    "integer", "number", "string",
}
NEVER = {"never": True}   # internal bottom — no value inhabits it · never authorable
UNKNOWN = {"unknown": True}  # gradual — absence of static information

MAX_PATTERN_LEN = 512


class TypeError_(Exception):
    """One static type-rule violation · carries (code, detail)."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def err(code: str, detail: str) -> dict:
    category = "security_error" if code == "NIKA-TYPE-005" else "validation_error"
    return {"code": code, "category": category, "detail": detail}


# ── the regex dialect (spec 09 §the regex dialect · locked whitelist) ────

def regex_dialect_violation(pattern: str) -> str | None:
    """None when the pattern is inside the locked dialect · else the
    offending construct (the NIKA-TYPE-006 detail). A hand scanner —
    NEVER the host regex engine's own parser (both evaluators must
    accept/refuse identically)."""
    if len(pattern) > MAX_PATTERN_LEN:
        return f"pattern longer than {MAX_PATTERN_LEN} chars"
    i, n = 0, len(pattern)
    in_class = False
    prev_quantifiable = False
    while i < n:
        c = pattern[i]
        if in_class:
            if c == "\\":
                if i + 1 >= n:
                    return "trailing backslash"
                nxt = pattern[i + 1]
                if nxt in "dDwWsS\\.^$+*?()[]{}|/-nrt":
                    i += 2
                    continue
                return f"escape \\{nxt} (out of dialect)"
            if c == "]":
                in_class = False
            i += 1
            continue
        if c == "\\":
            if i + 1 >= n:
                return "trailing backslash"
            nxt = pattern[i + 1]
            if nxt.isdigit():
                return f"backreference \\{nxt}"
            if nxt in ("b", "B"):
                return f"word boundary \\{nxt}"
            if nxt in ("p", "P"):
                return "unicode property class \\p{…}"
            if nxt in ("x", "u"):
                return f"hex/unicode escape \\{nxt} (out of dialect)"
            if nxt in "dDwWsS\\.^$+*?()[]{}|/-nrt":
                prev_quantifiable = True
                i += 2
                continue
            return f"escape \\{nxt} (out of dialect)"
        if c == "(":
            if pattern.startswith("(?:", i):
                i += 3
                prev_quantifiable = False
                continue
            if pattern.startswith("(?", i):
                return f"group construct {pattern[i:i+4]!r} (only (…) and (?:…) are in dialect)"
            i += 1
            prev_quantifiable = False
            continue
        if c == "[":
            in_class = True
            i += 1
            if i < n and pattern[i] == "^":
                i += 1
            prev_quantifiable = True
            # a class counts as one quantifiable unit once closed; the
            # flag is set on ']' exit — handled by the in_class branch
            continue
        if c in "*+?":
            if not prev_quantifiable:
                return f"quantifier {c!r} with nothing to repeat"
            if i + 1 < n and pattern[i + 1] in "?+":
                return f"lazy/possessive quantifier {pattern[i:i+2]!r}"
            prev_quantifiable = False
            i += 1
            continue
        if c == "{":
            m = re.match(r"\{[0-9]+(,[0-9]*)?\}", pattern[i:])
            if not m:
                return "malformed {m,n} quantifier"
            if not prev_quantifiable:
                return "quantifier {…} with nothing to repeat"
            end = i + m.end()
            if end < n and pattern[end] in "?+":
                return f"lazy/possessive quantifier {pattern[i:end+1]!r}"
            prev_quantifiable = False
            i = end
            continue
        # plain char · . · | · ^ · $ · ] · } (literal when unmatched)
        prev_quantifiable = c not in "|^$"
        i += 1
    if in_class:
        return "unterminated character class"
    return None


# ── parse ────────────────────────────────────────────────────────────────

def parse_type(expr, names: set[str], where: str) -> dict:
    """Type expression → normalized internal form. `{ optional: T }` is
    a FIELD-PRESENCE modifier and is refused here — only the object
    parser accepts it, at field positions (spec 09 §optional is
    presence, not null)."""
    if expr is None:
        return {"prim": "null"}   # the bare YAML null scalar spells the null type
    if isinstance(expr, str):
        if expr in PRIMITIVES:
            return {"prim": expr}
        if TYPE_NAME.match(expr):
            if expr not in names:
                close = _closest(expr, names)
                hint = f" — did you mean `{close}`?" if close else ""
                raise TypeError_("NIKA-TYPE-001",
                                 f"{where} · unknown type name {expr!r}{hint}")
            return {"ref": expr}
        base = expr.split("<")[0]
        if base in RESERVED:
            raise TypeError_("NIKA-TYPE-001",
                             f"{where} · {expr!r} is {RESERVED[base]} — not authorable")
        raise TypeError_("NIKA-TYPE-001", f"{where} · not a type: {expr!r}")
    if isinstance(expr, dict):
        keys = set(expr) - {"additional"}
        if keys == {"optional"}:
            raise TypeError_("NIKA-TYPE-001",
                             f"{where} · optional is a field-presence modifier — for a "
                             "nullable value write union: [T, null]")
        if len(keys) != 1 or not keys <= COMPOSITE_KEYS:
            raise TypeError_("NIKA-TYPE-001",
                             f"{where} · not a v1 type constructor: {sorted(expr)}")
        (k,) = keys
        v = expr[k]
        if k in ("array", "map"):
            return {k: parse_type(v, names, f"{where}.{k}")}
        if k == "object":
            return _parse_object(expr, v, names, where)
        if k == "union":
            if not isinstance(v, list) or len(v) < 2:
                raise TypeError_("NIKA-TYPE-001", f"{where}.union · needs ≥ 2 members")
            return norm_union([parse_type(m, names, f"{where}.union") for m in v])
        if k == "enum":
            if not isinstance(v, list) or not v or not all(isinstance(x, str) for x in v):
                raise TypeError_("NIKA-TYPE-001", f"{where}.enum · non-empty string list")
            return {"enum": sorted(set(v))}
        # refined numerics / string
        if not isinstance(v, dict):
            raise TypeError_("NIKA-TYPE-001", f"{where}.{k} · refinement must be a map")
        if k == "string":
            bad = set(v) - {"pattern", "min_len", "max_len"}
            if bad:
                raise TypeError_("NIKA-TYPE-001",
                                 f"{where}.string · not a refinement: {sorted(bad)}")
            pat = v.get("pattern")
            if pat is not None:
                if not isinstance(pat, str):
                    raise TypeError_("NIKA-TYPE-001", f"{where}.string.pattern · not a string")
                offense = regex_dialect_violation(pat)
                if offense:
                    raise TypeError_("NIKA-TYPE-006",
                                     f"{where}.string.pattern · out of the locked dialect: {offense}")
            for lk in ("min_len", "max_len"):
                lv = v.get(lk)
                if lv is not None and (isinstance(lv, bool) or not isinstance(lv, int) or lv < 0):
                    raise TypeError_("NIKA-TYPE-001",
                                     f"{where}.string.{lk} · must be a non-negative integer")
            if v.get("min_len") is not None and v.get("max_len") is not None \
                    and v["min_len"] > v["max_len"]:
                raise TypeError_("NIKA-TYPE-001",
                                 f"{where}.string · empty range: min_len > max_len")
            if not v:
                return {"prim": "string"}   # unbounded refinement IS its primitive
            return {"refined": "string", "bounds": dict(v)}
        bad = set(v) - {"min", "max"}
        if bad:
            raise TypeError_("NIKA-TYPE-001", f"{where}.{k} · not a refinement: {sorted(bad)}")
        for bk in ("min", "max"):
            bv = v.get(bk)
            if bk in v and (isinstance(bv, bool) or not isinstance(bv, (int, float))):
                raise TypeError_("NIKA-TYPE-001", f"{where}.{k}.{bk} · must be a number")
        if "min" in v and "max" in v and v["min"] > v["max"]:
            raise TypeError_("NIKA-TYPE-001", f"{where}.{k} · empty range: min > max")
        if not v:
            return {"prim": k}   # unbounded refinement IS its primitive
        return {"refined": k, "bounds": dict(v)}
    raise TypeError_("NIKA-TYPE-001", f"{where} · not a type: {type(expr).__name__}")


def _parse_object(expr: dict, fields_raw, names: set[str], where: str) -> dict:
    if not isinstance(fields_raw, dict):
        raise TypeError_("NIKA-TYPE-001", f"{where}.object · fields must be a map")
    fields: dict[str, dict] = {}
    for fk, fv in fields_raw.items():
        optional = False
        if isinstance(fv, dict) and set(fv) == {"optional"}:
            optional = True
            fv = fv["optional"]
        fields[fk] = {"ty": parse_type(fv, names, f"{where}.object.{fk}"),
                      "opt": optional}
    out = {"object": fields}
    if expr.get("additional") is True:
        out["additional"] = True
    return out


def canon_key(t: dict) -> str:
    """The canonical sort/dedup key of a normalized member — canonical
    JSON of the INTERNAL form (sorted keys · no spaces · raw UTF-8).
    Cross-language: the Rust core emits the same key byte-for-byte, so
    both evaluators agree on the canonical union order."""
    import json as _json
    return _json.dumps(t, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def norm_union(members: list[dict]) -> dict:
    """Flatten · dedup · ABSORB Unknown · COLLAPSE subsumed ref-free
    members · sort by canon_key. Canonical forms make ⊑ antisymmetric
    AS EQUALITY: two types admitting the same values normalize to the
    same form (`union: [integer, number]` IS `number`)."""
    flat: list[dict] = []
    for m in members:
        flat.extend(m["union"] if "union" in m else [m])
    # a union with an Unknown member knows NOTHING more than Unknown —
    # joining with no information is no information (absorption)
    if any(m == UNKNOWN for m in flat):
        return UNKNOWN
    seen, uniq = set(), []
    for m in flat:
        key = canon_key(m)
        if key not in seen:
            seen.add(key)
            uniq.append(m)
    # subsumption collapse — drop m when some OTHER member already
    # admits every m-value. Ref-free only: a ref is nominal here (no
    # env at normalization time), it never subsumes nor is subsumed.
    kept = [m for i, m in enumerate(uniq)
            if not (_ref_free(m)
                    and any(j != i and _ref_free(n) and subtype(m, n, {})
                            for j, n in enumerate(uniq)))]
    if len(kept) == 1:
        return kept[0]
    return {"union": sorted(kept, key=canon_key)}


def _ref_free(t: dict) -> bool:
    if "ref" in t:
        return False
    if "union" in t:
        return all(_ref_free(m) for m in t["union"])
    if "array" in t:
        return _ref_free(t["array"])
    if "map" in t:
        return _ref_free(t["map"])
    if "object" in t:
        return all(_ref_free(f["ty"]) for f in t["object"].values())
    return True


def admits_null(t: dict) -> bool:
    if t == {"prim": "null"} or t == UNKNOWN:
        return True
    if "union" in t:
        return any(admits_null(m) for m in t["union"])
    return False


def _closest(name: str, names: set[str]) -> str | None:
    best, bd = None, 3
    for c in names:
        d = _lev(name.lower(), c.lower())
        if d < bd:
            best, bd = c, d
    return best


def _lev(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# ── the workflow-level rules ─────────────────────────────────────────────

def type_core_errors(doc: dict) -> list[dict]:
    """The NIKA-TYPE static layer + NIKA-PARSE-025 (spec 09-types.md)."""
    errs: list[dict] = []
    raw_types = doc.get("types")
    names: set[str] = set(raw_types) if isinstance(raw_types, dict) else set()

    if isinstance(raw_types, dict):
        graph = {n: _name_refs(v) & names for n, v in raw_types.items()}
        state: dict[str, int] = {}

        def dfs(n: str) -> bool:
            state[n] = 1
            for m in graph.get(n, ()):
                if state.get(m) == 1 or (state.get(m) is None and dfs(m)):
                    return True
            state[n] = 2
            return False

        cyclic = {n for n in graph if state.get(n) is None and dfs(n)} \
            | {n for n, s in state.items() if s == 1}
        for n in sorted(cyclic):
            errs.append(err("NIKA-TYPE-002",
                            f"types.{n} · recursive type reference — the types: graph must be acyclic"))
        for n, v in raw_types.items():
            if n in cyclic:
                continue
            try:
                parse_type(v, names, f"types.{n}")
            except TypeError_ as e:
                errs.append(err(e.code, e.detail))

    # ── the io declaration positions (R3b · LAW-GRAMMAR-0211) ────────────
    # The `type:` of typed inputs:/config:/const:/outputs: speaks the SAME
    # full TypeExpr as types:/returns: — one type truth, every declaration
    # position judged by the same parser. The schema's pattern layer refuses
    # these too (NIKA-PARSE), but the prose and the law name the class
    # (NIKA-TYPE-001 · NIKA-TYPE-006 for the regex dialect) — the type core
    # owns it at every io position, never the schema alone.
    for auth in ("inputs", "config"):
        block = doc.get(auth)
        if isinstance(block, dict):
            for name, decl in block.items():
                if isinstance(decl, dict) and "type" in decl:
                    try:
                        parse_type(decl["type"], names, f"{auth}.{name}.type")
                    except TypeError_ as e:
                        errs.append(err(e.code, e.detail))
    raw_const = doc.get("const")
    if isinstance(raw_const, dict):
        for name, decl in raw_const.items():
            # the typed-constant discriminator (01-envelope · normative): an
            # object carrying BOTH `type` and `value` IS a typed constant —
            # an object missing either key is a bare literal (its `type` key
            # is data, never a declaration).
            if isinstance(decl, dict) and "type" in decl and "value" in decl:
                try:
                    parse_type(decl["type"], names, f"const.{name}.type")
                except TypeError_ as e:
                    errs.append(err(e.code, e.detail))
    raw_outputs = doc.get("outputs")
    if isinstance(raw_outputs, dict):
        for name, decl in raw_outputs.items():
            # typed form { value, type, description } · the untyped form is
            # a bare ${{ }} reference (a string · skipped by isinstance).
            if isinstance(decl, dict) and "type" in decl:
                try:
                    parse_type(decl["type"], names, f"outputs.{name}.type")
                except TypeError_ as e:
                    errs.append(err(e.code, e.detail))

    tasks = doc.get("tasks")
    if not isinstance(tasks, dict):
        return errs
    for tid, t in tasks.items():
        if not isinstance(t, dict):
            continue
        verb = next((v for v in ("infer", "exec", "invoke", "agent") if v in t), None)
        vbody = t.get(verb) if isinstance(t.get(verb), dict) else {}
        ret = t.get("returns")
        if ret is not None:
            rt = None
            try:
                rt = parse_type(ret, names, f"tasks.{tid}.returns")
            except TypeError_ as e:
                errs.append(err(e.code, e.detail))
            if isinstance(vbody, dict) and "schema" in vbody:
                errs.append(err("NIKA-TYPE-003",
                                f"tasks.{tid} · returns: and {verb}.schema: are two spellings "
                                "of one contract — keep returns: (the typed door) or the "
                                "schema: hatch, never both"))
            if verb == "exec" and rt is not None:
                decode = vbody.get("decode", "text")
                capture = vbody.get("capture", "stdout")
                if capture != "structured" and isinstance(decode, str) \
                        and not _decodable(rt, decode):
                    errs.append(err("NIKA-TYPE-004",
                                    f"tasks.{tid} · returns: cannot come out of decode: "
                                    f"{decode} — an object/array contract needs decode: "
                                    "json or jsonl"))
        if verb == "exec" and isinstance(vbody, dict) and "decode" in vbody \
                and vbody.get("capture") == "structured":
            errs.append({"code": "NIKA-PARSE-025", "category": "validation_error",
                         "detail": f"tasks.{tid} · decode: with capture: structured — that "
                                   "capture already IS an object · type it with returns:"})
    return errs


def _name_refs(expr) -> set[str]:
    out: set[str] = set()
    if isinstance(expr, str):
        if TYPE_NAME.match(expr):
            out.add(expr)
    elif isinstance(expr, dict):
        for v in expr.values():
            out |= _name_refs(v)
    elif isinstance(expr, list):
        for v in expr:
            out |= _name_refs(v)
    return out


def _decodable(t: dict, decode: str) -> bool:
    if "union" in t:
        return any(_decodable(m, decode) for m in t["union"])
    if "ref" in t:
        return True
    if decode == "bytes":
        return t == {"prim": "bytes"}
    if decode in ("json", "jsonl"):
        return True
    if "prim" in t:
        return t["prim"] in {"string"} | STRING_NEWTYPES
    if "enum" in t or t.get("refined") == "string":
        return True
    return False


# ── lowering (spec 09 §lowering · one direction) ─────────────────────────

def lower(t: dict, named: dict[str, dict]) -> dict:
    if "ref" in t:
        r = named.get(t["ref"])
        return lower(r, named) if r is not None else {}
    if t == UNKNOWN:
        return {}
    if t == NEVER:
        return {"not": {}}   # the empty type · JSON Schema's honest bottom
    if "prim" in t:
        p = t["prim"]
        return {
            "null": {"type": "null"},
            "bool": {"type": "boolean"},
            "integer": {"type": "integer"},
            "number": {"type": "number"},
            "string": {"type": "string"},
            "bytes": {"type": "string", "contentEncoding": "base64"},
            "uri": {"type": "string", "format": "uri"},
            "path": {"type": "string"},
            "duration": {"type": "string",
                         "pattern": r"^[0-9]+(\.[0-9]+)?(ns|us|µs|ms|s|m|h)([0-9]+(\.[0-9]+)?(ns|us|µs|ms|s|m|h))*$"},
            "timestamp": {"type": "string", "format": "date-time"},
        }[p]
    if "enum" in t:
        return {"type": "string", "enum": t["enum"]}
    if t.get("refined") in ("integer", "number"):
        out = {"type": t["refined"]}
        b = t["bounds"]
        if "min" in b:
            out["minimum"] = b["min"]
        if "max" in b:
            out["maximum"] = b["max"]
        return out
    if t.get("refined") == "string":
        out = {"type": "string"}
        b = t["bounds"]
        if "pattern" in b:
            out["pattern"] = b["pattern"]
        if "min_len" in b:
            out["minLength"] = b["min_len"]
        if "max_len" in b:
            out["maxLength"] = b["max_len"]
        return out
    if "array" in t:
        return {"type": "array", "items": lower(t["array"], named)}
    if "map" in t:
        return {"type": "object", "additionalProperties": lower(t["map"], named)}
    if "object" in t:
        props, required = {}, []
        for k, f in t["object"].items():
            props[k] = lower(f["ty"], named)
            if not f["opt"]:
                required.append(k)
        out = {"type": "object", "properties": props}
        if required:
            out["required"] = required
        if not t.get("additional"):
            out["additionalProperties"] = False
        return out
    if "union" in t:
        return {"anyOf": [lower(m, named) for m in t["union"]]}
    raise AssertionError(f"unloworable: {t}")


# ── the three relations (spec 09 §the relations) ─────────────────────────

def subtype(a: dict, b: dict, named: dict[str, dict]) -> bool:
    """A ⊑ B — the PARTIAL ORDER. Unknown is comparable only to itself;
    Never is bottom. Reflexive · transitive · antisymmetric."""
    if a == NEVER:
        return True
    if a == UNKNOWN or b == UNKNOWN:
        return a == b
    return _sub(a, b, named, gradual=False)


def consistent(a: dict, b: dict, named: dict[str, dict]) -> bool:
    """A ~ B — gradual consistency. Symmetric · NOT transitive ·
    Unknown ~ everything · structural elsewhere (same-shape modulo
    Unknown — subsumption does NOT ride here)."""
    if a == UNKNOWN or b == UNKNOWN:
        return True
    if "ref" in a:
        ra = named.get(a["ref"])
        return ra is not None and consistent(ra, b, named)
    if "ref" in b:
        rb = named.get(b["ref"])
        return rb is not None and consistent(a, rb, named)
    if "union" in a or "union" in b:
        ams = a["union"] if "union" in a else [a]
        bms = b["union"] if "union" in b else [b]
        # consistent unions: every a-member consistent with some b-member
        # and vice versa (shape compatibility both ways — symmetric).
        return all(any(consistent(x, y, named) for y in bms) for x in ams) \
            and all(any(consistent(x, y, named) for x in ams) for y in bms)
    if "array" in a and "array" in b:
        return consistent(a["array"], b["array"], named)
    if "map" in a and "map" in b:
        return consistent(a["map"], b["map"], named)
    if "object" in a and "object" in b:
        fa, fb = a["object"], b["object"]
        common = set(fa) & set(fb)
        return all(consistent(fa[k]["ty"], fb[k]["ty"], named) for k in common)
    return a == b


def assignable(a: dict, b: dict, named: dict[str, dict]) -> bool:
    """A ⊑~ B — consistent subtyping (Siek-Taha): subtyping with Unknown
    accepting at the leaves. THE relation every static judge consumes."""
    if a == NEVER or a == UNKNOWN or b == UNKNOWN:
        return True
    return _sub(a, b, named, gradual=True)


def _sub(a: dict, b: dict, named: dict[str, dict], gradual: bool) -> bool:
    rec = (lambda x, y: assignable(x, y, named)) if gradual \
        else (lambda x, y: subtype(x, y, named))
    if "ref" in a:
        ra = named.get(a["ref"])
        return ra is not None and rec(ra, b)
    if "ref" in b:
        rb = named.get(b["ref"])
        return rb is not None and rec(a, rb)
    if "union" in a:
        return all(rec(m, b) for m in a["union"])
    if "union" in b:
        return any(rec(a, m) for m in b["union"])
    if a == b:
        return True
    if a.get("prim") == "integer" and b.get("prim") == "number":
        return True
    if a.get("prim") in STRING_NEWTYPES and b == {"prim": "string"}:
        return True
    if "enum" in a:
        if b == {"prim": "string"}:
            return True
        return "enum" in b and set(a["enum"]) <= set(b["enum"])
    if a.get("refined") in ("integer", "number"):
        base = a["refined"]
        if b == {"prim": base} or (base == "integer" and b == {"prim": "number"}):
            return True
        if b.get("refined") == base or (base == "integer" and b.get("refined") == "number"):
            ab, bb = a["bounds"], b["bounds"]
            lo = "min" not in bb or ("min" in ab and ab["min"] >= bb["min"])
            hi = "max" not in bb or ("max" in ab and ab["max"] <= bb["max"])
            return lo and hi
        return False
    if a.get("refined") == "string":
        if b == {"prim": "string"}:
            return True
        if b.get("refined") == "string":
            ab, bb = a["bounds"], b["bounds"]
            if "pattern" in bb and ab.get("pattern") != bb["pattern"]:
                return False
            lo = "min_len" not in bb or ab.get("min_len", -1) >= bb["min_len"]
            hi = "max_len" not in bb or ("max_len" in ab and ab["max_len"] <= bb["max_len"])
            return lo and hi
        return False
    if "array" in a and "array" in b:
        return rec(a["array"], b["array"])
    if "map" in a and "map" in b:
        return rec(a["map"], b["map"])
    if "object" in a and "object" in b:
        fa, fb = a["object"], b["object"]
        a_open, b_open = bool(a.get("additional")), bool(b.get("additional"))
        # an OPEN a leaves undeclared keys carrying ANY value — only an
        # open b that adds no constraint of its own can admit that
        if a_open and (not b_open or any(k not in fa for k in fb)):
            return False
        for k, bf in fb.items():
            af = fa.get(k)
            if af is None:
                if not bf["opt"]:
                    return False
                continue
            # a required a-field may serve an optional b-slot; an
            # optional a-field cannot serve a REQUIRED b-slot (it may
            # be absent).
            if af["opt"] and not bf["opt"]:
                return False
            if not rec(af["ty"], bf["ty"]):
                return False
        if not b_open and any(k not in fb for k in fa):
            return False
        return True
    return False


# ── join and meet (spec 09 · honest three-way meet) ──────────────────────

def join(a: dict, b: dict) -> dict:
    """A ⊔ B — the language has unions, so the join is always expressible."""
    return norm_union([a, b])


def meet(a: dict, b: dict, named: dict[str, dict]):
    """A ⊓ B — EXACT when computable · NEVER when provably disjoint ·
    None when not computed (never guessed · spec 09 §meet)."""
    if a == UNKNOWN or b == UNKNOWN:
        return None          # insufficient information ≠ impossibility
    if a == NEVER or b == NEVER:
        return NEVER
    if subtype(a, b, named):
        return a
    if subtype(b, a, named):
        return b
    if "enum" in a and "enum" in b:
        inter = sorted(set(a["enum"]) & set(b["enum"]))
        return {"enum": inter} if inter else NEVER
    ra, rb = a.get("refined"), b.get("refined")
    if ra in ("integer", "number") and rb in ("integer", "number"):
        lo = max(a["bounds"].get("min", float("-inf")), b["bounds"].get("min", float("-inf")))
        hi = min(a["bounds"].get("max", float("inf")), b["bounds"].get("max", float("inf")))
        if lo > hi:
            return NEVER
        base = "integer" if "integer" in (ra, rb) else "number"
        bounds = {}
        if lo != float("-inf"):
            bounds["min"] = lo
        if hi != float("inf"):
            bounds["max"] = hi
        return {"refined": base, "bounds": bounds}
    # provably disjoint primitive families → Never (impossibility, named)
    if _family(a) is not None and _family(b) is not None and _family(a) != _family(b):
        return NEVER
    return None


def _family(t: dict) -> str | None:
    if t.get("prim") in ("integer", "number") or t.get("refined") in ("integer", "number"):
        return "numeric"
    if t.get("prim") in {"string"} | STRING_NEWTYPES or "enum" in t \
            or t.get("refined") == "string":
        return "textual"
    if t.get("prim") == "bool":
        return "bool"
    if t.get("prim") == "null":
        return "null"
    if "array" in t:
        return "array"
    if "map" in t or "object" in t:
        return "objectish"
    return None


# ── runtime fit · does a decoded VALUE inhabit a type? (spec 09) ─────────

def fits(value, t: dict, named: dict[str, dict]) -> bool:
    """value ∈ T — the run-time half (`NIKA-TYPE-101`). Optional is a
    FIELD-PRESENCE fact judged by the object arm (absent → ok when
    optional; PRESENT null is refused unless T admits null). String
    newtypes check the family (formats are the static contract);
    refined-string patterns are static-only here."""
    if "ref" in t:
        rt = named.get(t["ref"])
        return rt is not None and fits(value, rt, named)
    if t == UNKNOWN:
        return True
    if t == NEVER:
        return False
    if t == {"prim": "null"}:
        return value is None
    if "union" in t:
        return any(fits(value, m, named) for m in t["union"])
    if t.get("prim") == "bool":
        return isinstance(value, bool)
    if t.get("prim") == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if t.get("prim") == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t.get("prim") in {"string", "bytes"} | STRING_NEWTYPES:
        return isinstance(value, str)
    if "enum" in t:
        return isinstance(value, str) and value in t["enum"]
    if t.get("refined") in ("integer", "number"):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        if t["refined"] == "integer" and not (
                isinstance(value, int) or float(value).is_integer()):
            return False
        b = t["bounds"]
        return ("min" not in b or value >= b["min"]) and \
               ("max" not in b or value <= b["max"])
    if t.get("refined") == "string":
        if not isinstance(value, str):
            return False
        b = t["bounds"]
        return ("min_len" not in b or len(value) >= b["min_len"]) and \
               ("max_len" not in b or len(value) <= b["max_len"])
    if "array" in t:
        return isinstance(value, list) and all(fits(v, t["array"], named) for v in value)
    if "map" in t:
        return isinstance(value, dict) and all(
            isinstance(k, str) and fits(v, t["map"], named) for k, v in value.items())
    if "object" in t:
        if not isinstance(value, dict):
            return False
        fields = t["object"]
        for k, f in fields.items():
            if k in value:
                if not fits(value[k], f["ty"], named):
                    return False
            elif not f["opt"]:
                return False
        if not t.get("additional") and any(k not in fields for k in value):
            return False
        return True
    return True
