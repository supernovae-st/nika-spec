"""Retired planning must never contact or repair the GitHub Project."""
from __future__ import annotations

import contextlib
import io
import os
import unittest
from unittest.mock import patch

from project import cli, verify

import yaml


class RetirementTests(unittest.TestCase):
    def test_every_cli_mode_stops_before_client_creation(self) -> None:
        for arguments in ([], ["--check"], ["--apply"]):
            with self.subTest(arguments=arguments), \
                 patch.dict(os.environ, {"BOARD_PROJECT_TOKEN": "test-token"}), \
                 patch("project.cli.GitHub") as client, \
                 contextlib.redirect_stderr(io.StringIO()) as message:
                self.assertEqual(cli.main(arguments), 2)
                self.assertIn("retired", message.getvalue())
                self.assertIn("https://linear.app/nika-supernovae", message.getvalue())
                client.assert_not_called()

    def test_manifest_cannot_silently_reactivate_missing_lifecycle(self) -> None:
        manifest = cli.load_yaml(cli.MANIFEST_PATH)
        manifest.pop("lifecycle", None)
        with patch.dict(os.environ, {"BOARD_PROJECT_TOKEN": "test-token"}), \
             patch("project.cli.load_yaml", return_value=manifest), \
             patch("project.cli.GitHub") as client, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["--apply"]), 2)
            client.assert_not_called()

    def test_live_verifier_stops_before_client_creation(self) -> None:
        with patch.dict(os.environ, {"BOARD_PROJECT_TOKEN": "test-token"}), \
             patch("project.verify.GitHub") as client, \
             contextlib.redirect_stderr(io.StringIO()) as message:
            self.assertEqual(verify.main([]), 2)
            self.assertIn("retired", message.getvalue())
            client.assert_not_called()

    def test_workflow_only_validates_offline(self) -> None:
        # BaseLoader preserves GitHub's YAML `on` key as a string.
        workflow = yaml.load(
            (cli.ROOT / ".github/workflows/board.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        self.assertEqual(set(workflow["on"]), {"push", "pull_request", "workflow_dispatch"})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["jobs"]), {"audit"})
        for step in workflow["jobs"]["audit"]["steps"]:
            self.assertNotIn("BOARD_PROJECT_TOKEN", str(step))
            self.assertNotIn("project.cli", step.get("run", ""))


if __name__ == "__main__":
    unittest.main()
