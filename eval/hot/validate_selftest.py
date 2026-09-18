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
        path = self.root / "proposed-skeletons/facts-to-draft.nika"
        path.write_text(path.read_text().replace("expression:", "filter:"))
        with self.assertRaisesRegex(validate.CorpusError, "static conformance failed"):
            validate.validate(self.root)

    def test_unconditional_agent_is_rejected(self):
        path = self.root / "proposed-skeletons/known-path-agent-fallback.nika"
        path.write_text(path.read_text().replace('    when: ${{ with.classification.class == "unknown" }}\n', ""))
        with self.assertRaisesRegex(validate.CorpusError, "exceptional-branch gate drift"):
            validate.validate(self.root)

    def test_inverted_agent_gate_is_rejected(self):
        path = self.root / "proposed-skeletons/known-path-agent-fallback.nika"
        path.write_text(path.read_text().replace('class == "unknown"', 'class != "unknown"'))
        with self.assertRaisesRegex(validate.CorpusError, "exceptional-branch gate drift"):
            validate.validate(self.root)

    def test_splits_held_out_empty_on_this_pin(self):
        report = validate.validate(self.root)
        self.assertEqual(report["splits"]["held_out"], 0)
        self.assertEqual(report["splits"]["adversarial"], 0)
        self.assertEqual(report["promoted_hot"], 0)

    def test_splits_must_parse(self):
        (self.root / "splits.json").write_text("{")
        with self.assertRaises(json.JSONDecodeError):
            validate.validate(self.root)

    def test_development_id_cannot_also_be_held_out(self):
        def leak(d):
            d["splits"]["HELD-OUT"]["ids"] = [d["splits"]["DEVELOPMENT"]["ids"][0]]
        self.change_json("splits", leak)
        with self.assertRaisesRegex(validate.CorpusError, "DEVELOPMENT id is also in HELD-OUT"):
            validate.validate(self.root)

    def test_already_read_id_cannot_move_to_held_out(self):
        def move(d):
            d["splits"]["DEVELOPMENT"]["ids"].remove("golden:G01")
            d["splits"]["HELD-OUT"]["ids"] = ["golden:G01"]
        self.change_json("splits", move)
        with self.assertRaisesRegex(validate.CorpusError, "already-read"):
            validate.validate(self.root)

    def test_splits_cannot_claim_promotion(self):
        self.change_json("splits", lambda d: d.update(promoted_hot=1))
        with self.assertRaisesRegex(validate.CorpusError, "PROMOTED_HOT"):
            validate.validate(self.root)

    def test_consent_extension_cannot_move_to_a_scoring_split(self):
        original = (self.root / "splits.json").read_text()
        for bucket in ("HELD-OUT", "ADVERSARIAL"):
            with self.subTest(bucket=bucket):
                (self.root / "splits.json").write_text(original)

                def move(d):
                    d["splits"]["DEVELOPMENT"]["ids"].remove("scenario:X13")
                    d["splits"][bucket]["ids"].append("scenario:X13")

                self.change_json("splits", move)
                with self.assertRaisesRegex(validate.CorpusError, "already-read"):
                    validate.validate(self.root)

    def test_development_id_cannot_also_be_adversarial(self):
        self.change_json("splits", lambda d: d["splits"]["ADVERSARIAL"]["ids"].append("scenario:X13"))
        with self.assertRaisesRegex(validate.CorpusError, "DEVELOPMENT id is also in ADVERSARIAL"):
            validate.validate(self.root)

    def test_unseen_id_cannot_belong_to_both_scoring_splits(self):
        def overlap(d):
            for bucket in ("HELD-OUT", "ADVERSARIAL"):
                d["splits"][bucket]["ids"].append("scenario:unseen")
        self.change_json("splits", overlap)
        with self.assertRaisesRegex(validate.CorpusError, "HELD-OUT id is also in ADVERSARIAL"):
            validate.validate(self.root)

    def test_splits_cannot_claim_compiler_generated(self):
        self.change_json("splits", lambda d: d.update(compiler_generated=1))
        with self.assertRaisesRegex(validate.CorpusError, "compiler-generated"):
            validate.validate(self.root)

    def test_stale_split_pin(self):
        self.change_json("goldens", lambda d: d["positive"][0].update(title="mutated"))
        with self.assertRaisesRegex(validate.CorpusError, "stale pin goldens.json"):
            validate.validate(self.root)


if __name__ == "__main__":
    unittest.main()
