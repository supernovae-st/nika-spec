#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""C2 Session B local proof harness · maker != checker.

The maker (this branch feat/c2-language-def) wrote the new-world language
definition: schemas/workflow.schema.json v-next (the four value authorities
inputs/config/const/secrets · vars/env dead · TypeExpr widen) and
reference/values_core.py (the reference judge · NIKA-VALUES-001..003 ·
NIKA-DEFAULT-001). This checker judges every conformance/values/** fixture
against BOTH surfaces and compares the verdict to expected.json ·
positives admit, negatives refuse with the ruled code. It also runs the
inverse mutation (strip a secret's source · the schema must catch it).

It is STANDALONE · schema (jsonschema) + values_core only · it never runs
the full conformance/runner.py. The full runner goes red on the old-world
corpus by design (a new-world schema + an old-world corpus · R8 loi 14 · the
parity gates). This harness proves the language definition in isolation ·
the atomic flip that reconciles the whole tree is Session C.

Run: python3 conformance/values_proof.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "conformance"))
from values_core import values_core_errors  # noqa: E402

SCHEMA = json.loads((ROOT / "schemas" / "workflow.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA)
FIXTURES = ROOT / "conformance" / "values"


def verdict(doc) -> dict:
    """Combined verdict · schema (structural · namespace NIKA-PARSE) + the
    reference value core (NIKA-VALUES-* · NIKA-DEFAULT-*). Same shape as
    conformance/runner.py validate_workflow · {valid, errors:[...]}."""
    errs: list[dict] = []
    if not isinstance(doc, dict):
        return {"valid": False, "errors": [
            {"code": "NIKA-PARSE-001", "namespace": "NIKA-PARSE",
             "category": "parse_error", "detail": "not a mapping"}]}
    for e in VALIDATOR.iter_errors(doc):
        where = "".join(f"[{p}]" if isinstance(p, int) else f".{p}"
                        for p in e.absolute_path).lstrip(".") or "(root)"
        errs.append({"namespace": "NIKA-PARSE", "category": "validation_error",
                     "detail": f"{where} · {e.message}"})
    errs.extend(values_core_errors(doc))
    return {"valid": not errs, "errors": errs}


def _matches(expected: dict, emitted: list[dict]) -> bool:
    """An expected error matches when code matches, or namespace prefix
    matches, or only-category matches. Copied from runner-protocol.md ·
    conformance/runner.py _matches (the SAME acceptance the real runner
    will apply once Session C wires values_core into validate_workflow)."""
    for em in emitted:
        if "code" in expected and em.get("code") == expected["code"]:
            return True
        if "namespace" in expected:
            cd = em.get("code", "") or ""
            ns = em.get("namespace", "") or ""
            if cd.startswith(expected["namespace"] + "-") or ns == expected["namespace"]:
                return True
        if set(expected.keys()) <= {"category"} and em.get("category") == expected.get("category"):
            return True
    return False


def run_fixtures() -> tuple[int, int]:
    inputs = sorted(FIXTURES.rglob("input.yaml"))
    if not inputs:
        print(f"FAIL  {FIXTURES} · no fixtures found (0 inputs)")
        return 0, 1
    passed = failed = 0
    for inp in inputs:
        rel = inp.parent.relative_to(FIXTURES)
        exp = json.loads((inp.parent / "expected.json").read_text(encoding="utf-8"))
        doc = yaml.safe_load(inp.read_text(encoding="utf-8"))
        v = verdict(doc)
        ok = v["valid"] == exp["valid"]
        if ok and not exp["valid"]:
            ok = all(_matches(e, v["errors"]) for e in exp.get("errors", [])) or not exp.get("errors")
        got = [e.get("code") or e.get("namespace") for e in v["errors"]] or "valid"
        if ok:
            passed += 1
            print(f"PASS  {rel}  ->  {got}")
        else:
            failed += 1
            print(f"FAIL  {rel} · expected valid={exp['valid']} "
                  f"errors={exp.get('errors')} · got valid={v['valid']} {got}")
    return passed, failed


def inverse_mutation() -> bool:
    """Strip the source: from a secret of a passing positive fixture · the
    schema MUST catch it (secrets.source is required · R8). A guard that
    proves the positive was passing FOR THE RIGHT REASON, not by accident."""
    src = FIXTURES / "valid" / "four-authority-namespaces" / "input.yaml"
    doc = yaml.safe_load(src.read_text(encoding="utf-8"))
    before = verdict(doc)
    if not before["valid"]:
        print(f"FAIL  inverse-mutation · the base positive is not valid ({before['errors']})")
        return False
    doc["secrets"]["api_key"].pop("source", None)
    after = verdict(doc)
    refused = not after["valid"] and any(
        (e.get("namespace") == "NIKA-PARSE" or (e.get("code") or "").startswith("NIKA-PARSE"))
        for e in after["errors"])
    if refused:
        print("PASS  inverse-mutation · secret sans source refused after stripping source:")
    else:
        print(f"FAIL  inverse-mutation · stripped source: still valid={after['valid']} "
              f"{[e.get('code') or e.get('namespace') for e in after['errors']]}")
    return refused


def main() -> int:
    print("== conformance/values · schema v-next + values_core ==")
    passed, failed = run_fixtures()
    print("\n== inverse mutation ==")
    ok = inverse_mutation()
    if not ok:
        failed += 1
    else:
        passed += 1
    print(f"\nSummary · {passed}/{passed + failed} passed"
          + (f" · {failed} failed" if failed else " · ALL GREEN"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
