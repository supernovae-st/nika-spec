#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Mutations of the candidate inventory must fail its integrity gate."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import validate


class InventoryGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hot-inventory-")
        self.root = Path(self.temp.name) / "hot"
        shutil.copytree(validate.ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))
        self.addCleanup(self.temp.cleanup)

    def change_json(self, name, change):
        path = self.root / f"{name}.json"
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))

    def test_positive_corpus(self):
        self.assertEqual(validate.validate(self.root)["promoted_hot"], 0)

    def test_yaml_null_is_not_empty_list(self):
        path = self.root / "families.yaml"
        path.write_text(path.read_text().replace("policy_fields: []", "policy_fields: null", 1))
        with self.assertRaisesRegex(validate.CorpusError, "YAML/JSON drift"):
            validate.validate(self.root)

    def test_duplicate_family(self):
        self.change_json("families", lambda d: d["families"].append(d["families"][0]))
        with self.assertRaisesRegex(validate.CorpusError, "duplicate family_id"):
            validate.validate(self.root)

    def test_unmeasured_promotion(self):
        def promote(d):
            old = d["families"][0]["promotion_status"]
            d["families"][0]["promotion_status"] = "PROMOTED_HOT"
            d["counts"][old] -= 1
            d["counts"]["PROMOTED_HOT"] = 1
        self.change_json("families", promote)
        with self.assertRaisesRegex(validate.CorpusError, "no PROMOTED_HOT"):
            validate.validate(self.root)

    def test_unknown_family_reference(self):
        self.change_json("near-misses", lambda d: d["cases"][0].update(family_id="absent"))
        with self.assertRaisesRegex(validate.CorpusError, "unknown family"):
            validate.validate(self.root)

    def test_stale_source_digest(self):
        self.change_json("skeleton-audit", lambda d: d["skeletons"][0].update(sha256_file="sha256:wrong"))
        with self.assertRaisesRegex(validate.CorpusError, "stale source digest"):
            validate.validate(self.root)

    def test_invalid_proposed_workflow(self):
        path = self.root / "proposed-skeletons/facts-to-draft.nika.yaml"
        path.write_text(path.read_text().replace("expression:", "filter:"))
        with self.assertRaisesRegex(validate.CorpusError, "static conformance failed"):
            validate.validate(self.root)

    def test_unconditional_agent_is_rejected(self):
        path = self.root / "proposed-skeletons/known-path-agent-fallback.nika.yaml"
        path.write_text(path.read_text().replace('    when: ${{ with.classification.class == "unknown" }}\n', ""))
        with self.assertRaisesRegex(validate.CorpusError, "exceptional-branch gate drift"):
            validate.validate(self.root)

    def test_inverted_agent_gate_is_rejected(self):
        path = self.root / "proposed-skeletons/known-path-agent-fallback.nika.yaml"
        path.write_text(path.read_text().replace('class == "unknown"', 'class != "unknown"'))
        with self.assertRaisesRegex(validate.CorpusError, "exceptional-branch gate drift"):
            validate.validate(self.root)


if __name__ == "__main__":
    unittest.main()
