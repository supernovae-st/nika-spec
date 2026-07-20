#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
#
# Reference Core conformance runner for the Nika v1 workflow language.
#
# Implements the STATIC layer that needs no LLM engine ·
#   (1) JSON Schema structural validation (schemas/workflow.schema.json)
#   (2) the engine-parse cross-reference rules the schema cannot express ·
#         NIKA-DAG-001  cycle in G_p = E_d ∪ E_c (including self-dependency)
#         NIKA-DAG-002  with:/after: references an undeclared task
#         NIKA-DAG-005  after: predicate outside the closed set
#         NIKA-DAG-006  statically dead task (03 §static liveness · conservative fold)
#         NIKA-DAG-007  status literal outside the vocabulary
#         NIKA-TYPE-001..005 + NIKA-PARSE-025  the type core (09-types.md · type_core.py)
#         NIKA-PARSE-024  depends_on is dead (data → with: · control → after:)
#         NIKA-VAR-021  a tasks.* reference outside the boundary (03-dag.md ·
#                       « anywhere — in when: · with: · any verb field … »)
#         NIKA-VAR-003  a `tasks.X.output.<path>` reference the producing
#                       task's declared schema: PROVABLY forbids (04 §Static
#                       binding validation · closed level / type exclusion)
#         NIKA-VAR-001  an unresolved `${{ }}` reference (04-variables.md
#                       §Resolution order) · non-existent task · undeclared
#                       inputs./config./const./with./secrets. entry · undefined namespace ·
#                       loop-local item/index outside a for_each task
#         NIKA-VAR      unclosed `${{` delimiter (validation_error · the
#                       substitution surface is 04-variables.md's)
#         NIKA-PARSE    duplicate task id (03-dag.md · unique within workflow)
#
# PLUS the Stdlib v0.1 STATIC-SURFACE layer (names + shapes · no execution) ·
#   NIKA-PROVIDER  a literal `model:` that is not `<provider>/<name>` OR whose
#                  prefix is not one of the canonical stdlib v0.1 providers
#                  (canon.yaml `providers:` · the provider is the prefix)
#   NIKA-BUILTIN   a literal `nika:fetch` `mode:` outside the canonical extract
#                  modes (canon.yaml `extract_modes:` + the implicit `raw`) ·
#                  a `jq:` argument without `mode: jq` (builtins-v0.1.md) ·
#                  the `nika:image_generate` static contracts (v0.1 reserved
#                  options · closed enums · ranges · size grammar ·
#                  transparent×jpeg — builtins-v0.1.md §nika:image_generate)
# The stdlib surface lists come from canon.yaml (the SSOT) · NEVER hardcoded.
# Behavioral Runtime/Stdlib fixtures (execution · mock provider) are separate
# (see 07-conformance.md §Suite status).
#
# This is the canonical ORACLE for Level-1 (Core) conformance · a language
# engine in any language re-implements the same checks; this reference runner
# proves the fixture suite is self-consistent and is CI-runnable today.
#
# Usage ·
#   python conformance/runner.py validate <workflow.nika.yaml>
#   python conformance/runner.py run <fixtures-dir>      # default · tests/core
#   python conformance/runner.py examples <dir>          # assert all are valid
#   python conformance/runner.py all                     # core + stdlib + deep + examples (the CI gate)
#
# Deps · pyyaml · jsonschema. Exit non-zero on any failure (CI contract).

from __future__ import annotations
import sys, json, re, pathlib
import yaml
from jsonschema import Draft202012Validator

from deep_static import deep_static_errors, policy_errors
from composition_core import composition_errors
from type_core import type_core_errors

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "reference"))
from values_core import values_core_errors  # noqa: E402 · the E-split value-authority layer

HERE = pathlib.Path(__file__).resolve().parent
SPEC_ROOT = HERE.parent
SCHEMA_PATH = SPEC_ROOT / "schemas" / "workflow.schema.json"
CANON_PATH = SPEC_ROOT / "canon.yaml"
TASK_REF = re.compile(r"\btasks\.([a-z][a-z0-9_]*)\b")
OUTPUT_PATH = re.compile(
    r"\btasks\.([a-z][a-z0-9_]*)\.output"
    r"((?:\.[A-Za-z_][A-Za-z0-9_]*|\[[0-9]+\]|\['[^']*'\]|\[\"[^\"]*\"\])+)")
PATH_STEP = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[([0-9]+)\]|\['([^']*)'\]|\[\"([^\"]*)\"\]")
# `${{ ... }}` substitution surface (04-variables.md) · `\${{` is an escaped literal.
EXPR_OPEN = re.compile(r"(?<!\\)\$\{\{")
EXPR_BODY = re.compile(r"(?<!\\)\$\{\{(.*?)\}\}", re.DOTALL)
STR_LIT = re.compile(r"'[^']*'|\"[^\"]*\"")
# An identifier ROOT (not preceded by `.`) + its first dotted segment if any.
ROOT_ID = re.compile(r"(?<![.\w])([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?")
CEL_BUILTINS = {"true", "false", "null", "in", "size"}  # v0.1 CEL subset · 03-dag.md
LOOP_LOCALS = {"item", "index"}  # for_each-scoped locals · 04-variables.md §namespaces
# Body fields where a `tasks.X` ref is OUTSIDE the boundary (NIKA-VAR-021 ·
# 04 §the reference boundary) · with:/after: are the edge doors · on_error.
# recover reads a fallback source · on_finally reads its PARENT only ·
# workflow outputs: read the settled world.
BODY_FIELDS = ("when", "for_each", "infer", "exec", "invoke", "agent")
AFTER_PREDICATES = {"success", "failure", "skipped", "terminal"}



def iter_tasks(doc):
    """W1 'the map': tasks is an ordered MAP keyed by task id. Returns
    [(tid, task_dict)] pairs - the single accessor every rule reads through."""
    tasks = doc.get("tasks")
    if not isinstance(tasks, dict):
        return []
    return [(k, v) for k, v in tasks.items() if isinstance(v, dict)]


def load_schema() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


def load_canon() -> dict:
    """The stdlib v0.1 surface lists · from canon.yaml (the SSOT · never hardcode).

    `raw` joins the extract-mode set as the documented implicit mode
    (extract-modes-v0.1.md §«Plus an implicit») · not part of the canonical 9.
    """
    c = yaml.safe_load(CANON_PATH.read_text())
    prov = c["providers"]["items"]
    return {
        "providers": set(prov["cloud"]) | set(prov["local"]) | set(prov["test"]),
        "builtins": set(c["builtins"]["items"]),
        "extract_modes": set(c["extract_modes"]["items"]) | {"raw"},
    }


def _is_static(value) -> bool:
    """A scalar is statically checkable when it carries no `${{ }}` expression."""
    return isinstance(value, str) and not EXPR_OPEN.search(value)


def _fetch_payload_errors(where: str, args: dict) -> list[dict]:
    """fetch vNext payload families (builtins-v0.1.md §nika:fetch · payload
    exclusivity) · body ⊥ form ⊥ multipart · form/multipart need a
    body-bearing method · form is a flat object · the multipart part shape
    is CLOSED. Templated values are skipped (runtime's job)."""
    errs: list[dict] = []
    err = lambda detail: errs.append({"namespace": "NIKA-BUILTIN",
                                      "category": "validation_error",
                                      "detail": f"{where} · {detail}"})
    declared = [k for k in ("body", "form", "multipart") if k in args]
    if len(declared) > 1:
        err("at most one of body · form · multipart (builtins-v0.1.md §nika:fetch)")
    wants_payload = "form" in args or "multipart" in args
    method = args.get("method")
    if wants_payload:
        if method is None:
            err("form:/multipart: need method: POST (or PUT/PATCH) — the default GET carries no body")
        elif _is_static(method) and str(method).upper() not in ("POST", "PUT", "PATCH"):
            err(f"form:/multipart: need a body-bearing method — '{method}' carries no body")
        headers = args.get("headers")
        if isinstance(headers, dict) and any(k.lower() == "content-type" for k in headers):
            err("form:/multipart: own their content-type — drop the headers: entry")
    form = args.get("form")
    if form is not None and not isinstance(form, dict) and _is_static(form):
        err("form: must be an object of scalar fields (builtins-v0.1.md §nika:fetch)")
    if isinstance(form, dict):
        for k, v in form.items():
            if not isinstance(v, (str, int, float, bool)):
                err(f"form.{k}: must be a string, number or boolean — reshape nested data with nika:jq")
    parts = args.get("multipart")
    if parts is not None and not isinstance(parts, list) and _is_static(parts):
        err("multipart: must be an array of parts (builtins-v0.1.md §nika:fetch)")
    if isinstance(parts, list):
        if not parts:
            err("multipart: needs at least one part")
        for i, part in enumerate(parts):
            if not isinstance(part, dict):
                err(f"multipart part {i} must be an object")
                continue
            unknown = [k for k in part if k not in ("name", "value", "path", "filename", "content_type")]
            if unknown:
                err(f"multipart part {i}: unknown key '{unknown[0]}' — the shape is "
                    "{name, value} or {name, path, filename?, content_type?}")
            if "name" not in part:
                err(f"multipart part {i} needs a name:")
            has_value, has_path = "value" in part, "path" in part
            if has_value == has_path:
                err(f"multipart part {i}: exactly one of value: (text) | path: (file)")
            elif has_value and ("filename" in part or "content_type" in part):
                err(f"multipart part {i}: filename:/content_type: belong to file parts (path:)")
    return errs


def _fetch_traverse_errors(where: str, args: dict) -> list[dict]:
    """fetch vNext traverse (builtins-v0.1.md §nika:fetch · traverse) ·
    the crawl owns the whole arg surface: excludes the single-fetch
    extraction/payload families · GET only · closed spec shape ·
    max_pages 1..=25 required. Templated values are skipped."""
    errs: list[dict] = []
    err = lambda detail: errs.append({"namespace": "NIKA-BUILTIN",
                                      "category": "validation_error",
                                      "detail": f"{where} · {detail}"})
    for key in ("mode", "selector", "jq", "body", "form", "multipart"):
        if key in args:
            err(f"traverse: excludes {key}: — the crawl emits the fixed page-digest "
                "shape (builtins-v0.1.md §nika:fetch · traverse)")
    method = args.get("method")
    if method is not None and _is_static(method) and str(method).upper() != "GET":
        err(f"traverse: crawls with GET only — drop method: {method}")
    spec = args.get("traverse")
    if _is_static(spec) and not isinstance(spec, dict):
        err("traverse: must be an object — { max_pages: N, respect_robots?: bool }")
        return errs
    if not isinstance(spec, dict):
        return errs
    unknown = [k for k in spec if k not in ("max_pages", "respect_robots")]
    if unknown:
        err(f"traverse.{unknown[0]}: is not a traverse field — the shape is closed")
    pages = spec.get("max_pages")
    if pages is None:
        err("traverse.max_pages: is required — an integer 1..=25 (the crawl bound)")
    elif isinstance(pages, bool) or (not isinstance(pages, int) and _is_static(pages)):
        err("traverse.max_pages: must be an integer 1..=25")
    elif isinstance(pages, int) and not 1 <= pages <= 25:
        err(f"traverse.max_pages: {pages} out of range — 1..=25")
    robots = spec.get("respect_robots")
    if robots is not None and not isinstance(robots, bool) and _is_static(robots):
        err("traverse.respect_robots: must be a boolean")
    return errs


def stdlib_surface_errors(doc: dict, canon: dict) -> list[dict]:
    """Stdlib v0.1 STATIC surface (names + shapes · no execution) ·
    - `model:` MUST be `<provider>/<name>` with a canonical provider prefix
      (providers-v0.1.md · «the provider is the prefix») → NIKA-PROVIDER
    - `nika:fetch` `mode:` MUST be a canonical extract mode → NIKA-BUILTIN
    - a `jq:` fetch argument is only valid with `mode: jq` (builtins-v0.1.md)
    - a `selector:` fetch argument is only valid with `mode: selector`
      (extract-modes-v0.1.md · symmetric to the jq pairing)
    - fetch payload exclusivity: at most one of `body`/`form`/`multipart`;
      `form`/`multipart` need a body-bearing method (POST · PUT · PATCH) ·
      the multipart part shape is closed (builtins-v0.1.md §nika:fetch)
    - fetch `traverse:` owns its surface (excludes mode/selector/jq/body/
      form/multipart · GET only · closed spec · max_pages 1..=25 required)
    Dynamic values (`${{ }}`) are skipped · runtime's job."""
    errs: list[dict] = []

    def check_model(where: str, model):
        if not _is_static(model):
            return
        prefix, sep, _name = model.partition("/")
        if not sep or not _name:
            errs.append({"namespace": "NIKA-PROVIDER", "category": "validation_error",
                         "detail": f"{where} · model '{model}' is not '<provider>/<name>' · "
                                   "the provider is the prefix (providers-v0.1.md)"})
        elif prefix not in canon["providers"]:
            valid = " · ".join(sorted(canon["providers"]))
            errs.append({"namespace": "NIKA-PROVIDER", "category": "validation_error",
                         "detail": f"{where} · unknown provider prefix '{prefix}' · "
                                   f"canonical v0.1 prefixes: {valid} (canon.yaml)"})

    # the ENVELOPE default model — the template slot every author fills first
    check_model("(envelope) model", doc.get("model"))

    tasks = iter_tasks(doc)
    for tid, t in tasks:
        where = f"task '{tid}'"
        for verb in ("infer", "agent"):
            body = t.get(verb)
            if isinstance(body, dict):
                check_model(f"{where} {verb}.model", body.get("model"))
        inv = t.get("invoke")
        if isinstance(inv, dict) and inv.get("tool") == "nika:fetch":
            args = inv.get("args")
            if not isinstance(args, dict):
                continue
            mode = args.get("mode")
            if _is_static(mode) and mode not in canon["extract_modes"]:
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"{where} · unknown extract mode '{mode}' · "
                                       "not a canonical stdlib v0.1 extract mode (canon.yaml)"})
            if "jq" in args and args.get("mode") != "jq":
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"{where} · 'jq' argument is only valid with mode: jq "
                                       "(builtins-v0.1.md · nika:fetch)"})
            if "selector" in args and args.get("mode") != "selector":
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"{where} · 'selector' argument is only valid with "
                                       "mode: selector (extract-modes-v0.1.md · nika:fetch)"})
            errs.extend(_fetch_payload_errors(where, args))
            if "traverse" in args:
                errs.extend(_fetch_traverse_errors(where, args))
        if isinstance(inv, dict) and inv.get("tool") == "nika:image_generate":
            args = inv.get("args")
            if not isinstance(args, dict):
                continue
            # `mode:` — generate (default) or edit (M2.2 · 2026-07-06). An
            # edit REQUIRES a source (`image:` XOR `images:`); a non-mode is
            # a loud error; edit-only keys are refused in generate mode
            # (builtins-v0.1.md §nika:image_generate edit-block).
            mode = args.get("mode")
            is_edit = _is_static(mode) and mode == "edit"
            if _is_static(mode) and mode not in ("generate", "edit"):
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"{where} · mode '{mode}' is not a mode — one of "
                                       "generate · edit (builtins-v0.1.md §nika:image_generate)"})
            elif is_edit:
                if "image" not in args and "images" not in args:
                    errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                                 "detail": f"{where} · mode: edit requires a source · image: "
                                           "(one path) or images: (paths)"})
                if "image" in args and "images" in args:
                    errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                                 "detail": f"{where} · image: and images: are mutually exclusive"})
            else:
                for key in ("image", "images", "mask"):
                    if key in args:
                        errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                                     "detail": f"{where} · '{key}:' requires mode: edit"})
            if "reference_images" in args:
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"{where} · 'reference_images' is reserved in v0.1 "
                                       "(media roadmap · builtins-v0.1.md §nika:image_generate)"})
            if args.get("save") is False:
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"{where} · 'save: false' is reserved in v0.1 — assets "
                                       "always land in output_dir (builtins-v0.1.md)"})
            enums = {"provider": {"local", "openai", "gemini", "xai", "mock"},
                     "format": {"png", "jpeg", "jpg", "webp"},
                     "quality": {"auto", "low", "medium", "high", "ultra"},
                     "background": {"auto", "transparent", "opaque"},
                     "aspect_ratio": {"1:1", "16:9", "9:16", "4:3", "3:4",
                                      "3:2", "2:3", "21:9"}}
            for key, allowed in enums.items():
                v = args.get(key)
                if _is_static(v) and v not in allowed:
                    errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                                 "detail": f"{where} · {key} '{v}' is not in the closed set "
                                           f"(builtins-v0.1.md §nika:image_generate)"})
            for key, lo, hi in (("n", 1, 10), ("compression", 0, 100),
                                ("timeout_ms", 1_000, 600_000)):
                v = args.get(key)
                if isinstance(v, int) and not isinstance(v, bool) and not lo <= v <= hi:
                    errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                                 "detail": f"{where} · {key} {v} is out of range {lo}..={hi} "
                                           "(builtins-v0.1.md §nika:image_generate)"})
            size = args.get("size")
            if _is_static(size) and size != "auto":
                w, sep, h = size.partition("x")
                if not sep or not w.isdigit() or not h.isdigit():
                    errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                                 "detail": f"{where} · size '{size}' must be WIDTHxHEIGHT or "
                                           "'auto' (builtins-v0.1.md §nika:image_generate)"})
            if args.get("background") == "transparent" and args.get("format") in ("jpeg", "jpg"):
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"{where} · background: transparent needs an "
                                       "alpha-capable format — png or webp (builtins-v0.1.md)"})
    return errs


def _strings(value):
    """Yield every string scalar nested anywhere inside a value (str/dict/list)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _expr_bodies(value):
    """Every unescaped `${{ ... }}` expression body · quoted CEL literals stripped."""
    for s in _strings(value):
        for m in EXPR_BODY.finditer(s):
            yield STR_LIT.sub(" ", m.group(1))


def _expr_task_refs(value) -> set[str]:
    """All `tasks.<id>` ids referenced inside `${{ }}` expressions of a value."""
    return {ref for body in _expr_bodies(value) for ref in TASK_REF.findall(body)}


BARE_TASK_REF = re.compile(
    r"\btasks\.([a-z][a-z0-9_]*)(?![a-z0-9_])(?!\s*[.\[])")


def _bare_envelope_errors(value, where: str) -> list[dict]:
    """D2 (#75 - 0.103): bare `tasks.X` is the ENVELOPE, not a value - the
    projection set (.output/.status/.error/.duration_ms) is closed and
    required. Fires when a `tasks.X` root carries no projection."""
    errs = []
    for body in _expr_bodies(value):
        for m in BARE_TASK_REF.finditer(body):
            errs.append({"code": "NIKA-VAR-020", "namespace": "NIKA-VAR",
                         "category": "validation_error",
                         "detail": f"{where} - bare `tasks.{m.group(1)}` is the envelope, "
                                   "not a value - pick `.output` (or .status/.error/"
                                   ".duration_ms - 04 namespaces - closed projection set)"})
    return errs


def _unclosed_expr_errors(value, where: str) -> list[dict]:
    """NIKA-VAR validation_error · an unescaped `${{` with no closing `}}` (04)."""
    errs: list[dict] = []
    for s in _strings(value):
        if len(EXPR_OPEN.findall(s)) > len(EXPR_BODY.findall(s)):
            errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                         "detail": f"unclosed '${{{{' delimiter in {where} · {s[:60]!r}"})
    return errs


def _resolution_errors(value, scopes: dict, where: str) -> list[dict]:
    """NIKA-VAR-001 · unresolved `${{ }}` references per 04-variables.md ·
    namespace roots resolve against declared envelope/task scopes ·
    loop-locals (item/index) resolve only inside a for_each task."""
    errs: list[dict] = []

    def var_err(detail: str) -> None:
        errs.append({"code": "NIKA-VAR-001", "category": "variable_error",
                     "detail": f"{where} · {detail}"})

    for body in _expr_bodies(value):
        for root, seg in ROOT_ID.findall(body):
            if root in CEL_BUILTINS:
                continue
            if root in LOOP_LOCALS:
                if not scopes["in_for_each"]:
                    var_err(f"'{root}' is a for_each loop-local · no for_each here")
            elif root in ("inputs", "config", "const", "secrets", "with"):
                if seg and seg not in scopes[root]:
                    var_err(f"{root}.{seg} is not declared")
            elif root == "tasks":
                if scopes.get("tasks_mode") == "skip":
                    continue  # boundary surfaces report DAG-002/VAR-021 instead
                if seg and seg not in scopes["tasks"]:
                    var_err(f"tasks.{seg} references a non-existent task")
            elif seg:  # dotted unknown root · not one of the 6 namespaces
                var_err(f"'{root}.{seg}' uses an undefined namespace '{root}'")
            # bare unknown identifiers are tolerated (conservative · CEL terms)
    return errs


def _provably_invalid(schema, steps):
    """04 §Static binding validation · walk the v0.1 subset (properties ·
    items · type · additionalProperties) · return a reason string when a
    step is PROVABLY invalid · None when the path is valid-or-open."""
    level = schema
    for kind, val in steps:
        if not isinstance(level, dict):
            return None
        # any non-subset construct makes the level OPEN · stop walking
        if any(k in level for k in ("$ref", "oneOf", "anyOf", "allOf",
                                    "patternProperties", "not", "if")):
            return None
        t = level.get("type")

        def type_excludes(name):
            if t is None:
                return False
            return name not in t if isinstance(t, list) else t != name

        if kind == "member":
            if type_excludes("object"):
                return f"member step '.{val}' on a level whose type excludes object"
            props = level.get("properties")
            if isinstance(props, dict) and val in props:
                level = props[val]
                continue
            if level.get("additionalProperties") is False:
                return (f"key '{val}' absent from a closed level "
                        "(additionalProperties: false)")
            return None  # open level
        # index step
        if type_excludes("array"):
            return f"index step '[{val}]' on a level whose type excludes array"
        items = level.get("items")
        if isinstance(items, dict):
            level = items
            continue
        return None
    return None


def _schema_path_errors(doc: dict) -> list[dict]:
    """NIKA-VAR-003 · static binding validation (04 §Static binding
    validation) · only provably-invalid paths are rejected (sound)."""
    errs: list[dict] = []
    tasks = iter_tasks(doc)
    schemas = {}
    for tid, t in tasks:
        for verb in ("infer", "agent"):
            body = t.get(verb)
            if isinstance(body, dict) and isinstance(body.get("schema"), dict):
                schemas[tid] = body["schema"]
    if not schemas:
        return errs
    for tid, t in tasks:
        for body in _expr_bodies(t):
            for m in OUTPUT_PATH.finditer(body):
                ref_id, trail = m.group(1), m.group(2)
                schema = schemas.get(ref_id)
                if schema is None:
                    continue  # dynamic producer · never rejected
                steps = []
                for sm in PATH_STEP.finditer(trail):
                    member, idx, sq, dq = sm.groups()
                    if member is not None:
                        steps.append(("member", member))
                    elif idx is not None:
                        steps.append(("index", idx))
                    else:
                        steps.append(("member", sq if sq is not None else dq))
                reason = _provably_invalid(schema, steps)
                if reason:
                    errs.append({"code": "NIKA-VAR-003",
                                 "category": "variable_error",
                                 "detail": f"task '{t.get('id')}' · "
                                           f"tasks.{tid}.output{trail} · {reason}"})
    return errs


# Field → edge role → pass-set (03 §gate algebra v2 · mirrors the engine's
# analyzer::edges::role_of_field). A named output is a value read.
_PASS_ALL = frozenset({"success", "failure", "skipped", "cancelled"})
_PASS_VALUE = frozenset({"success", "skipped"})
_PASS_FAILURE_OBS = frozenset({"failure", "skipped"})
_AFTER_PASS = {
    "success": frozenset({"success"}),
    "failure": frozenset({"failure"}),
    "skipped": frozenset({"skipped"}),
    "terminal": _PASS_ALL,
}
TASK_FIELD_REF = re.compile(r"\btasks\.([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)\b")


def _binding_pass(field: str) -> frozenset:
    if field in {"status", "duration_ms", "started_at", "ended_at"}:
        return _PASS_ALL          # terminal-observation
    if field == "error":
        return _PASS_FAILURE_OBS  # failure-observation
    return _PASS_VALUE            # value (output · named output)


def _static_liveness_errors(tasks, idset) -> list[dict]:
    """NIKA-DAG-006 · fold reachable settled-state sets over G_p (acyclic
    by the time this runs). `when:` literal false → {skipped}; literal
    true/absent → {success·failure}; a string expression widens to all
    three; for_each / on_error.skip add skipped; cancelled always reachable."""
    errs: list[dict] = []
    by_id = dict(tasks)
    possible: dict[str, frozenset] = {}

    def incoming(t: dict) -> list[tuple[str, frozenset, str]]:
        edges = []
        for body in _expr_bodies_raw(t.get("with")):
            for producer, field in TASK_FIELD_REF.findall(body):
                if producer in idset:
                    edges.append((producer, _binding_pass(field), "with"))
        raw_after = t.get("after")
        for target, pred in (raw_after if isinstance(raw_after, dict) else {}).items():
            if isinstance(target, str) and target in idset \
                    and isinstance(pred, str) and pred in _AFTER_PASS:
                edges.append((target, _AFTER_PASS[pred], f"after: {pred}"))
        return edges

    def fold(tid: str) -> frozenset:
        if tid in possible:
            return possible[tid]
        t = by_id[tid]
        alive = True
        for producer, mask, door in incoming(t):
            if not (fold(producer) & mask):
                alive = False
                errs.append({
                    "code": "NIKA-DAG-006", "category": "validation_error",
                    "detail": f"task '{tid}' is statically dead — the {door} "
                              f"edge from '{producer}' can never admit "
                              f"(producer settles only "
                              f"{{{' · '.join(sorted(fold(producer)))}}})"})
        states = {"cancelled"}
        if alive:
            when = t.get("when", True)
            if when is False:
                states.add("skipped")   # the documented never-pattern
            elif when is True:
                states.update({"success", "failure"})
            else:
                states.update({"success", "failure", "skipped"})
            if "for_each" in t:
                states.add("skipped")
        on_error = t.get("on_error")
        if isinstance(on_error, dict) and on_error.get("skip") is True:
            states.add("skipped")
        possible[tid] = frozenset(states)
        return possible[tid]

    for tid, _ in tasks:
        fold(tid)
    return errs


_STATUS_CMP = re.compile(
    r"(?:with\.([a-z][a-z0-9_]*)\s*(?:==|!=)\s*'([^']*)'"
    r"|'([^']*)'\s*(?:==|!=)\s*with\.([a-z][a-z0-9_]*))")


def _status_vocabulary_errors(tasks) -> list[dict]:
    """NIKA-DAG-007 · a status observation compared against a literal
    outside {success·failure·skipped·cancelled} never matches. Conservative:
    ==/!= against a single-quoted literal on a direct `.status` binding."""
    errs: list[dict] = []
    vocab = {"success", "failure", "skipped", "cancelled"}
    for tid, t in tasks:
        status_bindings = set()
        with_block = t.get("with")
        if isinstance(with_block, dict):
            for name, expr in with_block.items():
                if isinstance(expr, str):
                    islands = EXPR_BODY.findall(expr)
                    if len(islands) == 1 and re.fullmatch(
                            r"\s*tasks\.[a-z][a-z0-9_]*\.status\s*", islands[0]):
                        status_bindings.add(name)
        when = t.get("when")
        if not (status_bindings and isinstance(when, str)):
            continue
        for body in EXPR_BODY.findall(when):
            for m in _STATUS_CMP.finditer(body):
                name = m.group(1) or m.group(4)
                lit = m.group(2) if m.group(1) else m.group(3)
                if name in status_bindings and lit not in vocab:
                    errs.append({
                        "code": "NIKA-DAG-007", "category": "validation_error",
                        "detail": f"task '{tid}' when: compares a status "
                                  f"observation against '{lit}' — not in the "
                                  "vocabulary {success · failure · skipped · "
                                  "cancelled}"})
    return errs


def _expr_bodies_raw(value):
    """Every `${{ ... }}` body WITH string literals intact (the liveness
    fold reads task-field refs; the vocabulary scan reads the literals)."""
    for s in _strings(value):
        for m in EXPR_BODY.finditer(s):
            yield m.group(1)


def cross_ref_errors(doc: dict) -> list[dict]:
    """The engine-parse cross-reference rules (beyond JSON Schema)."""
    errs: list[dict] = []
    tasks = iter_tasks(doc)
    if not tasks:
        return errs  # schema layer already rejected a non-map tasks:
    idset = {tid for tid, _ in tasks}
    # duplicate task identity is now a duplicate MAP KEY — the YAML loader
    # itself rejects it before this layer (PARSE-007 mechanics · W1).

    # NIKA-PARSE-024 · depends_on is dead (W2 · data → with: · control → after:)
    for tid, t in tasks:
        if "depends_on" in t:
            errs.append({"code": "NIKA-PARSE-024", "category": "validation_error",
                         "detail": f"task '{tid}' carries depends_on: — dead since W2 · "
                                   "data → with: bindings · control → after: predicates "
                                   "(check --fix migrates the provable cases)"})

    # Malformed after: shapes are schema-layer violations · this layer must
    # SURVIVE them (collected verdict · no crash).
    def _after(t: dict) -> dict:
        raw = t.get("after")
        return raw if isinstance(raw, dict) else {}

    # NIKA-DAG-005 · after: predicate outside the closed set
    # NIKA-DAG-002 · after: references an undeclared task
    for tid, t in tasks:
        for target, pred in _after(t).items():
            if not isinstance(target, str):
                continue  # schema-layer shape violation · survived
            if target not in idset:
                errs.append({"code": "NIKA-DAG-002", "category": "validation_error",
                             "detail": f"task '{tid}' after: references undeclared '{target}'"})
            if not (isinstance(pred, str) and pred in AFTER_PREDICATES):
                errs.append({"code": "NIKA-DAG-005", "category": "validation_error",
                             "detail": f"task '{tid}' after.{target}: {pred!r} ∉ "
                                       "{success · failure · skipped · terminal}"})

    # NIKA-DAG-002 · a with: binding references an undeclared task (the
    # binding IS an edge · an edge to nowhere is a DAG error, not a VAR one)
    for tid, t in tasks:
        for r in sorted(_expr_task_refs(t.get("with"))):
            if r not in idset:
                errs.append({"code": "NIKA-DAG-002", "category": "validation_error",
                             "detail": f"task '{tid}' with: references undeclared '{r}'"})

    # NIKA-DAG-001 · cycle in G_p = E_d(with) ∪ E_c(after) (DFS)
    graph = {
        tid: sorted((_expr_task_refs(t.get("with")) & idset)
                    | {k for k in _after(t) if isinstance(k, str) and k in idset})
        for tid, t in tasks
    }
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}

    def dfs(n: str) -> bool:
        color[n] = GREY
        for m in graph.get(n, []):
            if m not in color:
                continue  # undeclared dep · already flagged by DAG-002
            if color[m] == GREY:
                return True
            if color[m] == WHITE and dfs(m):
                return True
        color[n] = BLACK
        return False

    # a self-edge is a 1-cycle (a after a · a with-ref to itself)
    self_cycle = False
    for tid in graph:
        if tid in graph[tid]:
            self_cycle = True
            errs.append({"code": "NIKA-DAG-001", "category": "validation_error",
                         "detail": f"task '{tid}' edges to itself (1-cycle)"})
    has_cycle = any(color[n] == WHITE and dfs(n) for n in graph)
    if has_cycle:
        errs.append({"code": "NIKA-DAG-001", "category": "validation_error",
                     "detail": "cycle detected in G_p = E_d ∪ E_c"})

    # NIKA-DAG-006 / NIKA-DAG-007 · static liveness (03 §static liveness).
    # The CONSERVATIVE mirror of the engine's gate-v2 abstract evaluator:
    # fold each task's reachable settled-state set over G_p edge pass-sets.
    # A string `when:` widens to {success·failure·skipped} (the engine's
    # status-observation judge can refuse MORE — this oracle only refuses
    # what is provably dead from structure alone, never a valid program).
    if not (has_cycle or self_cycle):
        errs.extend(_static_liveness_errors(tasks, idset))
    errs.extend(_status_vocabulary_errors(tasks))

    # NIKA-VAR-021 · a tasks.* reference outside the boundary (04 §the
    # reference boundary) · body fields read LOCAL names only — hoist into
    # with: (the machine-applicable fix) · on_finally reads its PARENT only
    for tid, t in tasks:
        for field in BODY_FIELDS:
            for r in sorted(_expr_task_refs(t.get(field))):
                errs.append({"code": "NIKA-VAR-021", "category": "validation_error",
                             "detail": f"task '{tid}' {field}: references tasks.{r} — "
                                       "outside the boundary · hoist it into with: "
                                       "and read ${{ with.<name> }}"})
        for r in sorted(_expr_task_refs(t.get("on_finally")) - {tid}):
            errs.append({"code": "NIKA-VAR-021", "category": "validation_error",
                         "detail": f"task '{tid}' on_finally references tasks.{r} — "
                                   "the parent is the only readable task inside a "
                                   "cleanup (a sibling read would race)"})

    # NIKA-VAR-005 · for_each is a PRE-fan-out surface: a with-binding it
    # reads must not itself reference item/index (circular · 03 §for_each)
    for tid, t in tasks:
        fe = t.get("for_each")
        if not isinstance(fe, str):
            continue
        with_block = t.get("with") if isinstance(t.get("with"), dict) else {}
        for body in _expr_bodies(fe):
            for root, seg in ROOT_ID.findall(body):
                if root == "with" and seg in with_block:
                    binding_roots = {rt for b in _expr_bodies(with_block[seg])
                                     for rt, _ in ROOT_ID.findall(b)}
                    if binding_roots & LOOP_LOCALS:
                        errs.append({
                            "code": "NIKA-VAR-005", "category": "validation_error",
                            "detail": f"task '{tid}' for_each reads with.{seg} whose "
                                      "binding references item/index — the collection "
                                      "is evaluated BEFORE iterations exist (circular)"})

    # NIKA-DAG-004 · on_error.recover references a task DOWNSTREAM of the
    # declaring task — the recovery-time await would deadlock (05 §recover
    # resolution · the recovery surface is exempt from EDGES, not from
    # acyclicity). Transitive walk over G_p.
    def _transitive_deps(start: str) -> set[str]:
        seen: set[str] = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(graph.get(n, []))
        return seen

    for tid, t in tasks:
        on_error = t.get("on_error")
        if not isinstance(on_error, dict) or not isinstance(tid, str):
            continue
        recover = on_error.get("recover")
        for target in sorted(_expr_task_refs(recover)):
            if target in idset and tid in _transitive_deps(target):
                errs.append({"code": "NIKA-DAG-004", "category": "validation_error",
                             "detail": f"task '{tid}' on_error.recover reads tasks.{target} "
                                       f"— '{target}' depends (transitively) on '{tid}' · the "
                                       "recovery await would deadlock · recover from an "
                                       "upstream or independent source (05 §recover)"})

    # NIKA-VAR-001 + unclosed-`${{` · resolve every `${{ }}` reference statically
    def _keys(v) -> set:
        return set(v.keys()) if isinstance(v, dict) else set()

    inputs_keys = _keys(doc.get("inputs"))
    config_keys = _keys(doc.get("config"))
    const_keys = _keys(doc.get("const"))
    secrets_keys = _keys(doc.get("secrets"))
    for tid, t in tasks:
        # tasks-root existence inside a task body is judged by the boundary
        # rules (with:/after: ghosts → DAG-002 · body refs → VAR-021 · the
        # recover ghost check below) — never double-reported as VAR-001.
        scopes = {"inputs": inputs_keys, "config": config_keys, "const": const_keys,
                  "secrets": secrets_keys,
                  "tasks": idset, "with": _keys(t.get("with")),
                  "in_for_each": "for_each" in t, "tasks_mode": "skip"}
        where = f"task '{tid}'"
        errs.extend(_resolution_errors(t, scopes, where))
        errs.extend(_unclosed_expr_errors(t, where))
        errs.extend(_bare_envelope_errors(t, where))
        on_error = t.get("on_error")
        recover = on_error.get("recover") if isinstance(on_error, dict) else None
        for r in sorted(_expr_task_refs(recover)):
            if r not in idset:
                errs.append({"code": "NIKA-VAR-001", "category": "variable_error",
                             "detail": f"task '{tid}' on_error.recover reads "
                                       f"tasks.{r} — a non-existent task"})
    out_scopes = {"inputs": inputs_keys, "config": config_keys, "const": const_keys,
                  "secrets": secrets_keys,
                  "tasks": idset, "with": set(), "in_for_each": False}
    errs.extend(_resolution_errors(doc.get("outputs"), out_scopes, "outputs:"))
    errs.extend(_unclosed_expr_errors(doc.get("outputs"), "outputs:"))
    errs.extend(_bare_envelope_errors(doc.get("outputs"), "outputs:"))
    # The envelope `model:` is the template slot every author fills first — a
    # `${{ }}` template is legal there (schema-permissive), so an unresolved
    # ref must be caught the same as one in a task body. It was not: a typo'd
    # `model: "${{ inputs.nope }}"` sailed through while the identical ref inside
    # a task raised NIKA-VAR-001 (04-variables §Resolution order).
    errs.extend(_resolution_errors(doc.get("model"), out_scopes, "(envelope) model:"))
    errs.extend(_unclosed_expr_errors(doc.get("model"), "(envelope) model:"))

    # NIKA-VAR-003 · static binding validation vs declared schema: (04)
    errs.extend(_schema_path_errors(doc))

    return errs


class _UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader that REFUSES duplicate mapping keys instead of silently
    keeping the last one. `yaml.safe_load` drops the earlier value with no
    signal — but which key wins is exactly what NIKA-PARSE-017 (05-errors ·
    "no silent last-wins") forbids leaving ambiguous, so the oracle must
    reject the document, not quietly resolve it (a false green otherwise:
    a shadowed `permits:` / `exec:` would sail through)."""


def _no_duplicate_keys(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate mapping key {key!r}", key_node.start_mark)
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def validate_text(text: str, validator: Draft202012Validator,
                  canon: dict | None = None,
                  base_dir: 'pathlib.Path | None' = None) -> dict:
    """Parse a workflow under test — rejecting duplicate mapping keys per
    NIKA-PARSE-017 — then validate. The only entry point the runner uses for
    documents under test; canon.yaml (trusted) still loads via safe_load."""
    try:
        doc = yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.constructor.ConstructorError as e:
        return {"valid": False, "errors": [{
            "code": "NIKA-PARSE-017", "namespace": "NIKA-PARSE",
            "category": "validation_error",
            "detail": f"{e.problem} — no silent last-wins (NIKA-PARSE-017)"}]}
    except yaml.YAMLError as e:
        # A document that fails to SCAN is a rejection, never an oracle crash
        # (found by the broken-modeline fixtures · engine #323). When an early
        # line is a de-commented editor modeline, name the CAUSE — the raw
        # scanner error points at the first mapping line (the symptom) and
        # repair loops chase the wrong line forever.
        detail = str(getattr(e, "problem", None) or e)
        for i, line in enumerate(text.splitlines()[:8], start=1):
            if line.lstrip().startswith("$schema="):
                detail = (f"a bare `$schema=` line (line {i}) is a broken editor "
                          "modeline — restore the `# yaml-language-server: "
                          "$schema=…` comment prefix (or delete the line; it is "
                          "editor-only)")
                break
        return {"valid": False, "errors": [{
            "code": "NIKA-PARSE-001", "namespace": "NIKA-PARSE",
            "category": "parse_error", "detail": detail}]}
    return validate_workflow(doc, validator, canon, base_dir=base_dir)


def validate_workflow(doc: dict, validator: Draft202012Validator,
                      canon: dict | None = None,
                      base_dir: 'pathlib.Path | None' = None) -> dict:
    """Combined verdict · {valid, errors:[{code|namespace, category, detail}]}.

    `canon` enables the Stdlib v0.1 static-surface layer (always on for this
    reference runner · a Core-only engine implements the schema + cross-ref
    layers and skips it · stdlib fixtures only bind Stdlib-level claims)."""
    errs: list[dict] = []
    for e in validator.iter_errors(doc):
        # Schema violations are spec-rule violations · NIKA-PARSE / validation_error.
        # The detail is prescriptive on purpose (repair loops converge on it) ·
        # WHERE the violation sits + WHAT the schema allows there.
        where = "".join(f"[{p}]" if isinstance(p, int) else f".{p}"
                        for p in e.absolute_path).lstrip(".") or "(root)"
        detail = f"{where} · {e.message}"
        if e.validator == "pattern" and where.endswith(".id"):
            detail = (f"{where} · {e.instance!r} is not snake_case · task ids match "
                      "^[a-z][a-z0-9_]*$ (lowercase · digits · underscores · NO hyphens — "
                      "a hyphen is CEL subtraction · 03-dag §id)")
        elif e.validator == "type" and where.endswith(".timeout") and isinstance(e.instance, (int, float)):
            detail = (f"{where} · timeout must be a QUOTED Go-duration string · "
                      f"write \"{e.instance}s\" not {e.instance} (03-dag §timeout)")
        elif e.validator == "additionalProperties" and isinstance(e.schema, dict):
            allowed = sorted(e.schema.get("properties", {}))
            if allowed:
                detail += f" · allowed keys: {' · '.join(allowed)}"
        elif e.validator in ("oneOf", "anyOf"):
            # name the choice instead of dumping the instance · when every
            # branch is a bare {required:[k]} the rule IS « exactly one of » ·
            # the recurring case: a task must carry exactly one verb key
            branches = e.validator_value if isinstance(e.validator_value, list) else []
            keys = [b["required"][0] for b in branches
                    if isinstance(b, dict) and list(b) == ["required"]
                    and isinstance(b.get("required"), list) and len(b["required"]) == 1]
            if len(keys) == len(branches) and keys:
                got = " · ".join(sorted(e.instance)) if isinstance(e.instance, dict) else "?"
                detail = (f"{where} · must carry exactly one of: {' · '.join(keys)} "
                          f"(as a key) · got keys: {got}")
        errs.append({"namespace": "NIKA-PARSE", "category": "validation_error",
                     "detail": detail})
    errs.extend(cross_ref_errors(doc))
    errs.extend(deep_static_errors(doc))
    errs.extend(type_core_errors(doc))
    errs.extend(values_core_errors(doc))
    errs.extend(policy_errors(doc))
    errs.extend(composition_errors(doc, base_dir))
    if canon is not None:
        errs.extend(stdlib_surface_errors(doc, canon))
    return {"valid": not errs, "errors": errs}


def _matches(expected_err: dict, emitted: list[dict]) -> bool:
    """An expected error matches when code matches, or namespace prefix matches
    (category advisory), or only-category matches. Per runner-protocol.md."""
    for em in emitted:
        if "code" in expected_err and em.get("code") == expected_err["code"]:
            return True
        if "namespace" in expected_err:
            cd = em.get("code", "") or ""
            ns = em.get("namespace", "") or ""
            if cd.startswith(expected_err["namespace"] + "-") or ns == expected_err["namespace"]:
                return True
        if set(expected_err.keys()) <= {"category"} and em.get("category") == expected_err.get("category"):
            return True
    return False


def run_fixtures(fixtures_dir: pathlib.Path, validator: Draft202012Validator,
                 canon: dict | None = None) -> int:
    inputs = sorted(fixtures_dir.rglob("input.yaml"))
    if not inputs:
        # A tier that finds zero fixtures must NOT report "0/0 passed · exit 0":
        # a renamed or emptied directory would sail through the CI gate having
        # proven nothing. An absent tier fails loudly.
        print(f"FAIL  {fixtures_dir} · no fixtures found (0 inputs)")
        return 1
    passed = failed = 0
    for inp in inputs:
        rel = inp.parent.relative_to(fixtures_dir.parent)
        exp = json.loads((inp.parent / "expected.json").read_text())
        verdict = validate_text(inp.read_text(), validator, canon, base_dir=inp.parent)
        ok = verdict["valid"] == exp["valid"]
        if ok and not exp["valid"]:
            # at least one expected error must match an emitted one
            ok = all(_matches(e, verdict["errors"]) for e in exp.get("errors", [])) or not exp.get("errors")
        if ok:
            passed += 1
            print(f"PASS  {rel}")
        else:
            failed += 1
            got = [e.get("code") or e.get("namespace") for e in verdict["errors"]] or "valid"
            print(f"FAIL  {rel} · expected valid={exp['valid']} errors={exp.get('errors')} · got valid={verdict['valid']} {got}")
    print(f"\nSummary · {passed}/{passed + failed} passed" + (f" · {failed} failed" if failed else ""))
    return 1 if failed else 0


def run_examples(examples_dir: pathlib.Path, validator: Draft202012Validator,
                 canon: dict | None = None) -> int:
    """Every example IS a conformance input · asserted valid at the full
    static level (Core cross-refs + Stdlib surface) · the moat-proof gate."""
    bad = 0
    for f in sorted(examples_dir.glob("*.nika.yaml")):
        v = validate_text(f.read_text(), validator, canon)
        print(f"{'PASS' if v['valid'] else 'FAIL'}  {f.name}")
        if not v["valid"]:
            for e in v["errors"]:
                print(f"      {e.get('code') or e.get('namespace')} · {e.get('detail', '')[:100]}")
            bad += 1
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    validator = load_schema()
    canon = load_canon()
    if len(argv) >= 2 and argv[1] == "validate" and len(argv) == 3:
        v = validate_text(pathlib.Path(argv[2]).read_text(), validator, canon)
        print(json.dumps(v, indent=2))
        return 0 if v["valid"] else 1
    if len(argv) >= 2 and argv[1] == "run":
        d = pathlib.Path(argv[2]) if len(argv) == 3 else HERE / "tests" / "core"
        return run_fixtures(d, validator, canon)
    if len(argv) == 3 and argv[1] == "examples":
        return run_examples(pathlib.Path(argv[2]), validator, canon)
    if len(argv) == 2 and argv[1] == "all":
        # The CI gate · core fixtures + stdlib static-surface fixtures +
        # every example executed as a conformance input (each must be valid).
        rc = 0
        print("== tests/core ==")
        rc |= run_fixtures(HERE / "tests" / "core", validator, canon)
        print("\n== tests/stdlib (static surface) ==")
        rc |= run_fixtures(HERE / "tests" / "stdlib", validator, canon)
        print("\n== tests/deep (CEL parse · jq compile · durations · schema-meta) ==")
        rc |= run_fixtures(HERE / "tests" / "deep", validator, canon)
        print("\n== examples (each example = a conformance input) ==")
        rc |= run_examples(SPEC_ROOT / "examples", validator, canon)
        showcase = SPEC_ROOT / "examples" / "showcase"
        if showcase.is_dir():
            print("\n== examples/showcase (industry workflows · same gate) ==")
            rc |= run_examples(showcase, validator, canon)
        templates = SPEC_ROOT / "templates"
        if templates.is_dir():
            print("\n== templates (instantiable skeletons · must stay valid) ==")
            rc |= run_examples(templates, validator, canon)
        return rc
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
