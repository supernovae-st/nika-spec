#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Direct-output security refusals and static controls; no engine or secrets."""

import copy
import json
import unittest
from unittest.mock import patch

import deep_static
import runner
from secret_outputs import secret_output_errors


def workflow(output="${{ secrets.key }}"):
    return {"nika": "secret-output-check", "permits": {"tools": ["nika:jq"]},
            "secrets": {"key": {"source": "env", "key": "SYNTHETIC_FIXTURE_SECRET",
                                "egress": [{"to": "nika:jq"}, {"to": "outputs"}]}},
            "tasks": {"derive": {"with": {"key": "${{ secrets.key }}"},
                                 "invoke": {"tool": "nika:jq", "args": {
                                     "input": "${{ with.key }}", "expression": "length > 0"}}}},
            "outputs": {"exported": output}}


class SecretOutputTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(deep_static, "JQ_BIN", None))
        self.process = self.enterContext(patch.object(runner.subprocess, "run",
            side_effect=AssertionError("static security tests may not launch subprocesses")))
        self.schema, self.canon = runner.load_schema(), runner.load_canon()

    def verdict(self, doc):
        result = runner.validate_text(json.dumps(doc), self.schema, self.canon)
        self.process.assert_not_called()
        return result

    def test_direct_refusal_survives_output_egress(self):
        result = self.verdict(workflow())
        self.assertFalse(result["valid"])
        self.assertEqual([e.get("code") for e in result["errors"]], ["NIKA-SEC-007"])

    def test_direct_refusal_without_output_egress(self):
        doc = workflow()
        doc["secrets"]["key"]["egress"] = [{"to": "nika:jq"}]
        self.assertEqual([e.get("code") for e in self.verdict(doc)["errors"]], ["NIKA-SEC-007"])

    def test_derived_boolean_through_task_is_statically_valid(self):
        self.assertEqual(self.verdict(workflow("${{ tasks.derive.output }}")),
                         {"valid": True, "errors": []})

    def test_identity_alias_is_separate_from_publication_masking(self):
        doc = workflow("${{ tasks.derive.output }}")
        doc["tasks"]["derive"]["invoke"]["args"]["expression"] = "."
        self.assertEqual(self.verdict(doc), {"valid": True, "errors": []})

    def test_literals_and_escaped_islands_are_not_references(self):
        for value in ["secrets.key", "${{ 'secrets.key' }}", '${{ "secrets.key" }}',
                      r"\${{ secrets.key }}", '${{ "quoted \\\" secrets.key" }}']:
            with self.subTest(value=value):
                self.assertEqual(secret_output_errors(workflow(value)), [])

    def test_literal_closing_braces_do_not_end_an_island(self):
        self.assertEqual(secret_output_errors(workflow('${{ "}} secrets.key" }}')), [])
        self.assertEqual(len(secret_output_errors(workflow('${{ "}}" }}${{ secrets.key }}'))), 1)

    def test_other_namespace_member_is_not_secret_root(self):
        self.assertEqual(secret_output_errors(workflow("${{ inputs.secrets.key }}")), [])
        self.assertEqual(secret_output_errors(workflow("${{ tasks.secrets.output }}")), [])

    def test_literal_key_and_parenthesized_root_are_direct(self):
        for value in ["${{ secrets['key'] }}", '${{ secrets["key"] }}',
                      "${{ (secrets).key }}", "${{ ((secrets)).key }}",
                      "${{ secrets[('key')] }}", "${{ secrets . key }}",
                      "${{ 'x' in (secrets).key }}"]:
            with self.subTest(value=value):
                self.assertEqual(len(secret_output_errors(workflow(value))), 1)

    def test_function_result_and_method_name_are_not_secret_members(self):
        for value in ["${{ size(secrets).key }}", "${{ size((secrets)).key }}",
                      "${{ secrets.size() }}", "${{ secrets.contains('key') }}"]:
            doc = workflow(value)
            doc["secrets"]["size"] = copy.deepcopy(doc["secrets"]["key"])
            doc["secrets"]["contains"] = copy.deepcopy(doc["secrets"]["key"])
            with self.subTest(value=value):
                self.assertEqual(secret_output_errors(doc), [])

    def test_direct_roots_inside_compounds_and_dynamic_indices(self):
        for value in ["${{ [secrets.key] }}", "prefix ${{ secrets.key }} suffix",
                      "${{ inputs.items[secrets.key] }}", "${{ size(secrets.key) }}"]:
            with self.subTest(value=value):
                self.assertEqual(len(secret_output_errors(workflow(value))), 1)

    def test_one_finding_per_output_even_with_repeated_reads(self):
        doc = workflow("${{ secrets.key }}${{ secrets.key }}")
        doc["outputs"]["another"] = "${{ secrets.key }}"
        self.assertEqual(len(secret_output_errors(doc)), 2)

    def test_only_output_value_is_scanned(self):
        doc = workflow({"type": "string", "value": "public", "description": "${{ secrets.key }}"})
        self.assertEqual(secret_output_errors(doc), [])
        doc["outputs"]["exported"]["value"] = "${{ secrets.key }}"
        self.assertEqual(len(secret_output_errors(doc)), 1)
        doc["outputs"] = {"secrets.key": "public"}
        self.assertEqual(secret_output_errors(doc), [])

    def test_undeclared_secret_keeps_variable_refusal(self):
        result = self.verdict(workflow("${{ secrets.missing }}"))
        self.assertFalse(result["valid"])
        self.assertIn("NIKA-VAR-001", [e.get("code") for e in result["errors"]])
        self.assertNotIn("NIKA-SEC-007", [e.get("code") for e in result["errors"]])

    def test_unclosed_and_invalid_cel_keep_existing_refusals(self):
        for value in ["${{ secrets.key", "${{ secrets.key == == true }}"]:
            with self.subTest(value=value):
                result = self.verdict(workflow(value))
                self.assertFalse(result["valid"])
                self.assertNotIn("NIKA-SEC-007", [e.get("code") for e in result["errors"]])

    def test_unknown_envelope_key_is_still_refused(self):
        doc = workflow("public")
        doc["unknown"] = True
        self.assertFalse(self.verdict(doc)["valid"])

    def test_missing_exec_authority_is_still_refused(self):
        doc = workflow("public")
        del doc["permits"]
        doc["tasks"] = {"effect": {"exec": {"command": ["echo", "public"]}}}
        codes = [e.get("code") for e in self.verdict(doc)["errors"]]
        self.assertIn("NIKA-AUTH-006", codes)

    def test_malformed_output_shapes_do_not_crash_security_check(self):
        for value in [None, [], "literal", 1]:
            doc = workflow()
            doc["outputs"] = value
            self.assertEqual(secret_output_errors(doc), [])

    def test_input_document_is_not_mutated(self):
        doc = workflow()
        before = copy.deepcopy(doc)
        secret_output_errors(doc)
        self.assertEqual(doc, before)


if __name__ == "__main__":
    unittest.main()
