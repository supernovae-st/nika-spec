# SPDX-License-Identifier: Apache-2.0
"""Tests for the Project OS browser-only guardian contract."""

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

    def test_missing_hard_boundary_is_rejected(self) -> None:
        guardian = self.manifest["automation"]["ui_guardian"]
        guardian["forbids"].remove("items")

        self.assertIn(
            "UI guardian is missing forbidden surfaces ['items']",
            self.findings(),
        )

    def test_workflows_are_observe_only(self) -> None:
        guardian = self.manifest["automation"]["ui_guardian"]
        guardian["repairs"].append("built_in_workflows")

        self.assertIn(
            "UI guardian may repair only views and insights",
            self.findings(),
        )


if __name__ == "__main__":
    unittest.main()
