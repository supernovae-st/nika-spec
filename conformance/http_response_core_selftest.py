#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observation policy refusal and deferred-expression negative controls."""

import unittest

from http_response_core import findings


class ResponsePolicyTests(unittest.TestCase):
    def test_exact_named_statuses(self):
        self.assertEqual(findings({"accept": [200, 404]}), [])
        self.assertEqual(findings({"accept": [599]}), [])
        self.assertEqual(findings({"accept": list(range(200, 216))}), [])

    def test_malformed_policies(self):
        for value in [None, True, [], {}, {"accept": []}, {"accept": 404},
                      {"accept": [404, 404]}, {"accept": [404.0]}, {"accept": [True]},
                      {"accept": ["404"]}, {"accept": [199]}, {"accept": [600]},
                      {"accept": [-1]}, {"accept": [404], "headers": []},
                      {"accept": list(range(200, 217))}]:
            with self.subTest(value=value):
                self.assertTrue(findings(value))

    def test_dynamic_parts_are_unknown(self):
        for value in ["${{ inputs.response }}", {"accept": "${{ inputs.codes }}"},
                      {"accept": [200, "${{ inputs.code }}"]}]:
            with self.subTest(value=value):
                self.assertEqual(findings(value), [])

    def test_unknown_never_hides_bad_literal_siblings(self):
        for value in [{"accept": ["${{ inputs.code }}", 99]},
                      {"accept": ["${{ inputs.code }}", 404, 404]},
                      {"accept": "${{ inputs.codes }}", "unknown": True}]:
            with self.subTest(value=value):
                self.assertTrue(findings(value))


if __name__ == "__main__":
    unittest.main()
