# SPDX-License-Identifier: Apache-2.0
"""The reference type core (spec 09-types.md) — the SECOND evaluator.

Parses the closed v1 type grammar, checks the static rules
(NIKA-TYPE-001..005 · NIKA-PARSE-025), lowers to JSON Schema 2020-12 and
decides the subtype lattice. Deliberately small and readable: an engine
in any language re-implements the same judgments; this module proves the
fixtures are self-consistent and gives the conformance runner its
type-rule layer.

Soundness stance (mirrors the runner's other layers): every refusal here
is provable from the document alone; anything uncertain stays silent —
the reference runner never refuses a valid program.
"""

from __future__ import annotations

import re

PRIMITIVES = {
    "null", "bool", "integer", "number", "string", "bytes",
    "uri", "path", "duration", "money", "timestamp",
}
RESERVED = {"result", "artifact", "secret"}  # named now · semantics land W4/W5
TYPE_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")
COMPOSITE_KEYS = {
    "array", "map", "object", "union", "optional", "enum",
    "integer", "number", "string",
}


class TypeError_(Exception):
    """One static type-rule violation · carries (code, detail)."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def err(code: str, detail: str) -> dict:
    category = "security_error" if code == "NIKA-TYPE-005" else "validation_error"
    return {"code": code, "category": category, "detail": detail}


# ── parse ────────────────────────────────────────────────────────────────

def parse_type(expr, names: set[str], where: str) -> dict:
    """Type expression → normalized internal form. Raises TypeError_ on a
    grammar violation the JSON Schema layer cannot see (unknown name)."""
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
        if expr in RESERVED or expr.split("<")[0] in RESERVED:
            raise TypeError_("NIKA-TYPE-001",
                             f"{where} · {expr!r} is reserved (its wave has not landed)")
        raise TypeError_("NIKA-TYPE-001", f"{where} · not a type: {expr!r}")
    if isinstance(expr, dict):
        keys = set(expr) - {"additional"}
        if len(keys) != 1 or not keys <= COMPOSITE_KEYS:
            raise TypeError_("NIKA-TYPE-001",
                             f"{where} · not a v1 type constructor: {sorted(expr)}")
        (k,) = keys
        v = expr[k]
        if k == "array" or k == "map" or k == "optional":
            inner = parse_type(v, names, f"{where}.{k}")
            if k == "optional":
                return _norm_union([inner, {"prim": "null"}])
            return {k: inner}
        if k == "object":
            if not isinstance(v, dict):
                raise TypeError_("NIKA-TYPE-001", f"{where}.object · fields must be a map")
            fields = {fk: parse_type(fv, names, f"{where}.object.{fk}")
                      for fk, fv in v.items()}
            out = {"object": fields}
            if expr.get("additional") is True:
                out["additional"] = True
            return out
        if k == "union":
            if not isinstance(v, list) or len(v) < 2:
                raise TypeError_("NIKA-TYPE-001", f"{where}.union · needs ≥ 2 members")
            return _norm_union([parse_type(m, names, f"{where}.union") for m in v])
        if k == "enum":
            if not isinstance(v, list) or not v or not all(isinstance(x, str) for x in v):
                raise TypeError_("NIKA-TYPE-001", f"{where}.enum · non-empty string list")
            return {"enum": sorted(set(v))}
        # refined numerics / string — the constructor name doubles as the base
        if not isinstance(v, dict):
            raise TypeError_("NIKA-TYPE-001", f"{where}.{k} · refinement must be a map")
        return {"refined": k, "bounds": dict(v)}
    raise TypeError_("NIKA-TYPE-001", f"{where} · not a type: {type(expr).__name__}")


def _norm_union(members: list[dict]) -> dict:
    flat: list[dict] = []
    for m in members:
        flat.extend(m["union"] if "union" in m else [m])
    seen, uniq = set(), []
    for m in flat:
        key = repr(sorted(m.items(), key=str))
        if key not in seen:
            seen.add(key)
            uniq.append(m)
    if len(uniq) == 1:
        return uniq[0]
    return {"union": sorted(uniq, key=repr)}


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

    parsed: dict[str, dict] = {}
    if isinstance(raw_types, dict):
        # acyclicity over the NAME graph first (parse would recurse forever)
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
                parsed[n] = parse_type(v, names, f"types.{n}")
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
            try:
                rt = parse_type(ret, names, f"tasks.{tid}.returns")
            except TypeError_ as e:
                errs.append(err(e.code, e.detail))
                rt = None
            # TYPE-003 · one contract, one spelling
            if isinstance(vbody, dict) and "schema" in vbody:
                errs.append(err("NIKA-TYPE-003",
                                f"tasks.{tid} · returns: and {verb}.schema: are two spellings "
                                "of one contract — keep returns: (the typed door) or the "
                                "schema: hatch, never both"))
            # TYPE-004 · returns unreachable from the declared decode
            if verb == "exec" and rt is not None:
                decode = vbody.get("decode", "text")
                capture = vbody.get("capture", "stdout")
                if capture != "structured" and isinstance(decode, str):
                    if not _decodable(rt, decode):
                        errs.append(err("NIKA-TYPE-004",
                                        f"tasks.{tid} · returns: cannot come out of decode: "
                                        f"{decode} — an object/array contract needs decode: "
                                        "json or jsonl"))
        # PARSE-025 · decode ⊥ capture: structured
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
    """Can a value of type t come out of the given decode? (conservative:
    unions are decodable when ANY member is)."""
    if "union" in t:
        return any(_decodable(m, decode) for m in t["union"])
    if "ref" in t:
        return True  # resolved shape unknown HERE · engine judges post-resolve
    if decode == "bytes":
        return t == {"prim": "bytes"}
    if decode in ("json", "jsonl"):
        return True  # JSON can produce any shape
    # decode: text → a string-family value
    if "prim" in t:
        return t["prim"] in {"string", "uri", "path", "duration", "money", "timestamp"}
    if "enum" in t or t.get("refined") == "string":
        return True
    return False


# ── lowering (spec 09 §lowering · one direction) ─────────────────────────

def lower(t: dict, named: dict[str, dict]) -> dict:
    if "ref" in t:
        return lower(named[t["ref"]], named)
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
            "money": {"type": "string"},
        }[p]
    if "enum" in t:
        return {"type": "string", "enum": t["enum"]}
    if t.get("refined") == "integer" or t.get("refined") == "number":
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
        for k, v in t["object"].items():
            props[k] = lower(_strip_null(v) if _is_optional(v) else v, named)
            if not _is_optional(v):
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


def _is_optional(t: dict) -> bool:
    return "union" in t and {"prim": "null"} in t["union"]


def _strip_null(t: dict) -> dict:
    members = [m for m in t["union"] if m != {"prim": "null"}]
    return members[0] if len(members) == 1 else {"union": members}


# ── the lattice · A ⊑ B ──────────────────────────────────────────────────

def subtype(a: dict, b: dict, named: dict[str, dict]) -> bool:
    if "ref" in a:
        return subtype(named[a["ref"]], b, named)
    if "ref" in b:
        return subtype(a, named[b["ref"]], named)
    if a == b:
        return True
    # unions
    if "union" in a:
        return all(subtype(m, b, named) for m in a["union"])
    if "union" in b:
        return any(subtype(a, m, named) for m in b["union"])
    # numeric widening + refinements
    if a == {"prim": "integer"} and b == {"prim": "number"}:
        return True
    if "enum" in a:
        if b == {"prim": "string"}:
            return True
        if "enum" in b:
            return set(a["enum"]) <= set(b["enum"])
        return False
    if a.get("refined") in ("integer", "number"):
        base = a["refined"]
        if b == {"prim": base} or (base == "integer" and b == {"prim": "number"}):
            return True
        if b.get("refined") == base:
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
                return False  # syntactic equality only — honest
            lo = "min_len" not in bb or ab.get("min_len", -1) >= bb["min_len"]
            hi = "max_len" not in bb or ("max_len" in ab and ab["max_len"] <= bb["max_len"])
            return lo and hi
        return False
    # string newtypes narrow string
    if a.get("prim") in ("uri", "path", "duration", "timestamp", "money") \
            and b == {"prim": "string"}:
        return True
    if "array" in a and "array" in b:
        return subtype(a["array"], b["array"], named)
    if "map" in a and "map" in b:
        return subtype(a["map"], b["map"], named)
    if "object" in a and "object" in b:
        af, bf = a["object"], b["object"]
        for k, bt in bf.items():
            if _is_optional(bt):
                if k in af and not subtype(af[k], bt, named):
                    return False
            else:
                if k not in af or not subtype(af[k], bt, named):
                    return False
        if not b.get("additional"):
            if any(k not in bf for k in af):
                return False
        return True
    return False

# ── runtime fit · does a decoded VALUE inhabit a type? (spec 09) ─────────

def fits(value, t: dict, named: dict[str, dict]) -> bool:
    """value ∈ T — the run-time half of the contract (`NIKA-TYPE-101`
    when an exec/invoke decoded value escapes its returns:). String
    newtypes check the FAMILY only (the format is the static contract);
    refined-string patterns are static-only here (no regex engine
    dependency — documented honest gap, both evaluators agree)."""
    if "ref" in t:
        rt = named.get(t["ref"])
        return rt is not None and fits(value, rt, named)
    if t == {"prim": "null"}:
        return value is None
    if "union" in t:
        return any(fits(value, m, named) for m in t["union"])
    if t.get("prim") == "bool":
        return isinstance(value, bool)
    if t.get("prim") == "integer":
        return isinstance(value, int) and not isinstance(value, bool) or (
            isinstance(value, float) and value.is_integer())
    if t.get("prim") == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t.get("prim") in ("string", "uri", "path", "duration", "money",
                         "timestamp", "bytes"):
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
        return ("min" not in b or value >= b["min"]) and                ("max" not in b or value <= b["max"])
    if t.get("refined") == "string":
        if not isinstance(value, str):
            return False
        b = t["bounds"]
        return ("min_len" not in b or len(value) >= b["min_len"]) and                ("max_len" not in b or len(value) <= b["max_len"])
    if "array" in t:
        return isinstance(value, list) and all(fits(v, t["array"], named) for v in value)
    if "map" in t:
        return isinstance(value, dict) and all(
            isinstance(k, str) and fits(v, t["map"], named) for k, v in value.items())
    if "object" in t:
        if not isinstance(value, dict):
            return False
        fields = t["object"]
        for k, ft in fields.items():
            if k in value:
                if not fits(value[k], ft, named):
                    return False
            elif not _is_optional(ft):
                return False
        if not t.get("additional") and any(k not in fields for k in value):
            return False
        return True
    return True  # Unknown-class · gradual
