#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
#
# Reference Core conformance runner for the Nika v1 workflow language.
#
# Implements the STATIC layer that needs no LLM engine ·
#   (1) JSON Schema structural validation (schemas/workflow.schema.json)
#   (2) the 4 engine-parse cross-reference rules the schema cannot express ·
#         NIKA-DAG-001  cycle in depends_on
#         NIKA-DAG-002  depends_on references an undeclared task
#         NIKA-DAG-003  when:/with: references tasks.X without depends_on:[X]
#         NIKA-VAR-001  outputs:/expression references a non-existent task
#
# This is the canonical ORACLE for Level-1 (Core) conformance · a language
# engine in any language re-implements the same checks; this reference runner
# proves the fixture suite is self-consistent and is CI-runnable today.
#
# Usage ·
#   python conformance/runner.py validate <workflow.nika.yaml>
#   python conformance/runner.py run <fixtures-dir>      # default · tests/core
#   python conformance/runner.py examples <dir>          # assert all are valid
#
# Deps · pyyaml · jsonschema. Exit non-zero on any failure (CI contract).

from __future__ import annotations
import sys, json, re, pathlib
import yaml
from jsonschema import Draft202012Validator

HERE = pathlib.Path(__file__).resolve().parent
SPEC_ROOT = HERE.parent
SCHEMA_PATH = SPEC_ROOT / "schemas" / "workflow.schema.json"
TASK_REF = re.compile(r"\btasks\.([a-z][a-z0-9_]*)\b")


def load_schema() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


def _task_refs(value) -> set[str]:
    """All `tasks.<id>` ids referenced anywhere inside a value (str/dict/list)."""
    out: set[str] = set()
    if isinstance(value, str):
        out.update(TASK_REF.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            out |= _task_refs(v)
    elif isinstance(value, list):
        for v in value:
            out |= _task_refs(v)
    return out


def cross_ref_errors(doc: dict) -> list[dict]:
    """The 4 engine-parse cross-reference rules (beyond JSON Schema)."""
    errs: list[dict] = []
    tasks = doc.get("tasks") or []
    if not isinstance(tasks, list):
        return errs  # schema layer already rejected this
    ids = [t.get("id") for t in tasks if isinstance(t, dict)]
    idset = {i for i in ids if isinstance(i, str)}

    # NIKA-DAG-002 · depends_on references an undeclared task
    for t in tasks:
        for dep in (t.get("depends_on") or []):
            if dep not in idset:
                errs.append({"code": "NIKA-DAG-002", "category": "validation_error",
                             "detail": f"task '{t.get('id')}' depends_on undeclared '{dep}'"})

    # NIKA-DAG-001 · cycle in depends_on (DFS)
    graph = {t.get("id"): list(t.get("depends_on") or []) for t in tasks if isinstance(t, dict)}
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

    # NIKA-DAG-003 · when:/with: references tasks.X without depends_on:[X]
    for t in tasks:
        if not isinstance(t, dict):
            continue
        declared = set(t.get("depends_on") or [])
        refs = _task_refs(t.get("when")) | _task_refs(t.get("with"))
        missing = {r for r in refs if r in idset and r not in declared}
        for r in sorted(missing):
            errs.append({"code": "NIKA-DAG-003", "category": "validation_error",
                         "detail": f"task '{t.get('id')}' references tasks.{r} in when:/with: "
                                   f"without depends_on:[{r}]"})

    # NIKA-VAR-001 · outputs: (or any expression there) references a non-existent task
    for ref in _task_refs(doc.get("outputs")):
        if ref not in idset:
            errs.append({"code": "NIKA-VAR-001", "category": "variable_error",
                         "detail": f"outputs: references tasks.{ref} · no such task"})

    return errs


def validate_workflow(doc: dict, validator: Draft202012Validator) -> dict:
    """Combined verdict · {valid, errors:[{code|namespace, category, detail}]}."""
    errs: list[dict] = []
    for e in validator.iter_errors(doc):
        # Schema violations are spec-rule violations · NIKA-PARSE / validation_error.
        errs.append({"namespace": "NIKA-PARSE", "category": "validation_error",
                     "detail": e.message})
    errs.extend(cross_ref_errors(doc))
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


def run_fixtures(fixtures_dir: pathlib.Path, validator: Draft202012Validator) -> int:
    inputs = sorted(fixtures_dir.rglob("input.yaml"))
    passed = failed = 0
    for inp in inputs:
        rel = inp.parent.relative_to(fixtures_dir.parent)
        exp = json.loads((inp.parent / "expected.json").read_text())
        doc = yaml.safe_load(inp.read_text())
        verdict = validate_workflow(doc, validator)
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


def main(argv: list[str]) -> int:
    validator = load_schema()
    if len(argv) >= 2 and argv[1] == "validate" and len(argv) == 3:
        doc = yaml.safe_load(pathlib.Path(argv[2]).read_text())
        v = validate_workflow(doc, validator)
        print(json.dumps(v, indent=2))
        return 0 if v["valid"] else 1
    if len(argv) >= 2 and argv[1] == "run":
        d = pathlib.Path(argv[2]) if len(argv) == 3 else HERE / "tests" / "core"
        return run_fixtures(d, validator)
    if len(argv) == 3 and argv[1] == "examples":
        bad = 0
        for f in sorted(pathlib.Path(argv[2]).glob("*.nika.yaml")):
            v = validate_workflow(yaml.safe_load(f.read_text()), validator)
            print(f"{'PASS' if v['valid'] else 'FAIL'}  {f.name}")
            bad += 0 if v["valid"] else 1
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
