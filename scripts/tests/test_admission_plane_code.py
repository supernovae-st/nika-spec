# SPDX-License-Identifier: Apache-2.0
"""The pre-admission plane is an exact allowset, never a numeric block.

spec#160 (2026-09-18 ruling): the diagnostics schema admits the shipped
bare-numeric NIKA-1708 and NOTHING else outside the canonical namespaced
grammar — no 17xx range, no reserved block, no 25th error namespace.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "schemas" / "registries.schema.json").read_text(encoding="utf-8")
)
ID_PATTERN = re.compile(
    SCHEMA["$defs"]["diagnosticRow"]["properties"]["id"]["pattern"]
)


class AdmissionPlaneCodeTests(unittest.TestCase):
    def test_shipped_admission_code_is_admitted(self):
        self.assertTrue(ID_PATTERN.match("NIKA-1708"))

    def test_canonical_grammar_unchanged(self):
        for code in ("NIKA-PARSE-001", "NIKA-BUILTIN-WAIT-001", "NIKA-BUILTIN-JSON_MERGE_PATCH-001"):
            self.assertTrue(ID_PATTERN.match(code), code)

    def test_other_numeric_codes_are_rejected(self):
        # The launch family the engine carries is NOT admitted by shape:
        # each future mint is a normative amendment, never an edit.
        for code in ("NIKA-1700", "NIKA-1707", "NIKA-1709", "NIKA-1799"):
            self.assertIsNone(ID_PATTERN.match(code), code)

    def test_malformed_numeric_forms_are_rejected(self):
        # NIKA-LAUNCH-001 is NOT a negative case: it matches the canonical
        # namespaced grammar (grammar ≠ registration — the allocation table
        # carries no such namespace, which is a separate gate).
        for code in ("NIKA-170", "NIKA-17080", "NIKA-17O8", "NIKA-1708-1"):
            self.assertIsNone(ID_PATTERN.match(code), code)

    def test_compiler_allowset_is_exactly_1708(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ssot_compiler", ROOT / "scripts" / "ssot-compiler.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.ADMISSION_PLANE_CODES, {"NIKA-1708"})


if __name__ == "__main__":
    unittest.main()
