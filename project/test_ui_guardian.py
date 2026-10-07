# SPDX-License-Identifier: Apache-2.0
"""The retired UI guardian must not restore a duplicate planning surface."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFY_PATH = ROOT / "project" / "verify.py"
SPEC = importlib.util.spec_from_file_location("project_verify", VERIFY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load the Project OS verifier")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class UiGuardianContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = yaml.safe_load(
            (ROOT / "project" / "project-os.yaml").read_text(encoding="utf-8")
        )
        self.timeline = yaml.safe_load(
            (ROOT / "timeline" / "timeline.yaml").read_text(encoding="utf-8")
        )

    def findings(self) -> list[str]:
        return VERIFY.offline_findings(self.manifest, self.timeline)

    def test_canonical_guardian_contract_is_valid(self) -> None:
        self.assertEqual([], self.findings())

    def test_restored_ui_repairs_are_rejected(self) -> None:
        self.manifest["automation"]["ui_guardian"]["repairs"] = ["views"]
        self.assertIn(
            "retired UI guardian must have no repairs or cadence", self.findings()
        )

    def test_reactivated_publisher_is_rejected(self) -> None:
        self.manifest["automation"]["publisher"] = "enabled"
        self.assertIn(
            "retired Project automation.publisher must be disabled", self.findings()
        )


if __name__ == "__main__":
    unittest.main()
