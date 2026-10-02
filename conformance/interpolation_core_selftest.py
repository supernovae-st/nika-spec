#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The lexical refusal boundary and its non-template exclusions."""

import unittest

from interpolation_core import has_reference_lookalike, interpolation_errors


class InterpolationTests(unittest.TestCase):
    def test_dotted_heads_closed_unclosed_and_unicode(self):
        for text in ["${ const.seed }", "é ${tasks.left.output}", "${inputs . topic", "${\u00a0const.seed}"]:
            with self.subTest(text=text):
                self.assertTrue(has_reference_lookalike(text))

    def test_legitimate_literals_and_islands(self):
        for text in ["$5", "${HOME}", "${name:-default}", "${items[0]}", "${constants.seed}", "${\u001cconst.seed}",
                     "${{ const.seed }}", "${{ '${ const.seed }' }}", r"\${{ const.seed }}"]:
            with self.subTest(text=text):
                self.assertFalse(has_reference_lookalike(text))

    def test_quote_aware_skip_does_not_hide_later_typo(self):
        self.assertTrue(has_reference_lookalike("${{ '}}' }} ${const.seed}"))
        self.assertTrue(has_reference_lookalike(r"\${{ inputs.x }} ${ const.seed }"))

    def test_escaped_opener_never_masks_a_later_typo(self):
        self.assertTrue(has_reference_lookalike(r"\${{ don't }} then ${ const.seed }"))
        self.assertTrue(has_reference_lookalike(r"\${{ don't }} ${const.seed} then ' }}"))
        self.assertTrue(has_reference_lookalike(r"\${{ '${const.seed}' }}"))
        self.assertFalse(has_reference_lookalike(r"\${{ don't }} then $5"))

    def test_shell_and_tool_are_interpolation_surfaces(self):
        for action in [{"exec": {"shell": "echo ${ const.seed }"}},
                       {"invoke": {"tool": "${ const.tool }"}}]:
            self.assertEqual(len(interpolation_errors({"tasks": {"t": action}})), 1)

    def test_metadata_and_raw_extract_are_not_interpolation_surfaces(self):
        doc = {"const": {"text": "${ const.seed }"},
               "tasks": {"t": {"infer": {"prompt": "plain"}, "extract": {"x": "${ const.seed }"}}},
               "outputs": {"out": {"value": "plain", "description": "${ const.seed }"}}}
        self.assertEqual(interpolation_errors(doc), [])
        doc["outputs"]["out"]["value"] = "${ const.seed }"
        self.assertEqual([error["code"] for error in interpolation_errors(doc)], ["NIKA-VAR-005"])


if __name__ == "__main__":
    unittest.main()
