#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
#
# Reference Core conformance runner for the Nika v1 workflow language.
#
# Implements the STATIC layer that needs no LLM engine ·
#   (1) JSON Schema structural validation (schemas/workflow.schema.json)
#   (2) the engine-parse cross-reference rules the schema cannot express ·
#         NIKA-DAG-001  cycle in depends_on (including self-dependency)
#         NIKA-DAG-002  depends_on references an undeclared task
#         NIKA-DAG-003  a `${{ tasks.X }}` reference from when:/with:/for_each:/
#                       any verb body without depends_on:[X] (03-dag.md ·
#                       « anywhere — in when: · with: · any verb field … »)
#         NIKA-VAR-003  a `tasks.X.output.<path>` reference the producing
#                       task's declared schema: PROVABLY forbids (04 §Static
#                       binding validation · closed level / type exclusion)
#         NIKA-VAR-001  an unresolved `${{ }}` reference (04-variables.md
#                       §Resolution order) · non-existent task · undeclared
#                       vars./with./env./secrets. entry · undefined namespace ·
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

from deep_static import deep_static_errors

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
LOOP_LOCALS = {"item", "index"}  # for_each-scoped locals · 04-variables.md §5 namespaces
# Fields whose `tasks.X` refs REQUIRE depends_on:[X] (03-dag.md §Referencing a task) ·
# on_error/on_finally deliberately excluded (recover refs a fallback source ·
# on_finally refs the parent task itself · neither is an execution-order edge).
DAG_EDGE_FIELDS = ("when", "with", "for_each", "infer", "exec", "invoke", "agent")


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


def stdlib_surface_errors(doc: dict, canon: dict) -> list[dict]:
    """Stdlib v0.1 STATIC surface (names + shapes · no execution) ·
    - `model:` MUST be `<provider>/<name>` with a canonical provider prefix
      (providers-v0.1.md · «the provider is the prefix») → NIKA-PROVIDER
    - `nika:fetch` `mode:` MUST be a canonical extract mode → NIKA-BUILTIN
    - a `jq:` fetch argument is only valid with `mode: jq` (builtins-v0.1.md)
    - a `selector:` fetch argument is only valid with `mode: selector`
      (extract-modes-v0.1.md · symmetric to the jq pairing)
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

    tasks = doc.get("tasks") or []
    if not isinstance(tasks, list):
        return errs
    for t in tasks:
        if not isinstance(t, dict):
            continue
        where = f"task '{t.get('id')}'"
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
            elif root in ("vars", "env", "secrets", "with"):
                if seg and seg not in scopes[root]:
                    var_err(f"{root}.{seg} is not declared")
            elif root == "tasks":
                if seg and seg not in scopes["tasks"]:
                    var_err(f"tasks.{seg} references a non-existent task")
            elif seg:  # dotted unknown root · not one of the 5 namespaces
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
    tasks = doc.get("tasks") or []
    if not isinstance(tasks, list):
        return errs
    schemas = {}
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for verb in ("infer", "agent"):
            body = t.get(verb)
            if isinstance(body, dict) and isinstance(body.get("schema"), dict):
                schemas[t.get("id")] = body["schema"]
    if not schemas:
        return errs
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for body in _expr_bodies(t):
            for m in OUTPUT_PATH.finditer(body):
                tid, trail = m.group(1), m.group(2)
                schema = schemas.get(tid)
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


def cross_ref_errors(doc: dict) -> list[dict]:
    """The engine-parse cross-reference rules (beyond JSON Schema)."""
    errs: list[dict] = []
    tasks = doc.get("tasks") or []
    if not isinstance(tasks, list):
        return errs  # schema layer already rejected this
    ids = [t.get("id") for t in tasks if isinstance(t, dict)]
    idset = {i for i in ids if isinstance(i, str)}

    # NIKA-PARSE · duplicate task id (03-dag.md · id unique within workflow)
    seen: set[str] = set()
    for i in ids:
        if isinstance(i, str):
            if i in seen:
                errs.append({"namespace": "NIKA-PARSE", "category": "validation_error",
                             "detail": f"duplicate task id '{i}'"})
            seen.add(i)

    # Non-string depends_on entries (a mapping · a number) are schema-layer
    # violations · this layer must SURVIVE them (collected verdict · no crash).
    def _deps(t: dict) -> list[str]:
        raw = t.get("depends_on") or []
        return [d for d in raw if isinstance(d, str)] if isinstance(raw, list) else []

    # NIKA-DAG-002 · depends_on references an undeclared task
    for t in tasks:
        for dep in _deps(t):
            if dep not in idset:
                errs.append({"code": "NIKA-DAG-002", "category": "validation_error",
                             "detail": f"task '{t.get('id')}' depends_on undeclared '{dep}'"})

    # NIKA-DAG-001 · cycle in depends_on (DFS)
    graph = {t.get("id"): _deps(t) for t in tasks
             if isinstance(t, dict) and isinstance(t.get("id"), str)}
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

    if any(color[n] == WHITE and dfs(n) for n in graph):
        errs.append({"code": "NIKA-DAG-001", "category": "validation_error",
                     "detail": "cycle detected in depends_on"})

    # NIKA-DAG-003 · a `${{ tasks.X }}` reference from when:/with:/for_each:/any
    # verb body without depends_on:[X] (03-dag.md · the edge is never inferred)
    for t in tasks:
        if not isinstance(t, dict):
            continue
        declared = set(_deps(t))
        refs: set[str] = set()
        for field in DAG_EDGE_FIELDS:
            refs |= _expr_task_refs(t.get(field))
        missing = {r for r in refs if r in idset and r not in declared}
        for r in sorted(missing):
            errs.append({"code": "NIKA-DAG-003", "category": "validation_error",
                         "detail": f"task '{t.get('id')}' references tasks.{r} "
                                   f"without depends_on:[{r}]"})

    # NIKA-DAG-004 · on_error.recover references a task DOWNSTREAM of the
    # declaring task — the recovery-time await would deadlock (05 §recover
    # resolution · the 03 carve-out exempts recover from EDGES, not from
    # acyclicity). Transitive walk over depends_on.
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

    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
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

    vars_keys = _keys(doc.get("vars"))
    env_keys = _keys(doc.get("env"))
    secrets_keys = _keys(doc.get("secrets"))
    for t in tasks:
        if not isinstance(t, dict):
            continue
        scopes = {"vars": vars_keys, "env": env_keys, "secrets": secrets_keys,
                  "tasks": idset, "with": _keys(t.get("with")),
                  "in_for_each": "for_each" in t}
        where = f"task '{t.get('id')}'"
        errs.extend(_resolution_errors(t, scopes, where))
        errs.extend(_unclosed_expr_errors(t, where))
    out_scopes = {"vars": vars_keys, "env": env_keys, "secrets": secrets_keys,
                  "tasks": idset, "with": set(), "in_for_each": False}
    errs.extend(_resolution_errors(doc.get("outputs"), out_scopes, "outputs:"))
    errs.extend(_unclosed_expr_errors(doc.get("outputs"), "outputs:"))

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
                  canon: dict | None = None) -> dict:
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
    return validate_workflow(doc, validator, canon)


def validate_workflow(doc: dict, validator: Draft202012Validator,
                      canon: dict | None = None) -> dict:
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
        verdict = validate_text(inp.read_text(), validator, canon)
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
