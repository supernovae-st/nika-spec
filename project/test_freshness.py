"""Metadata previews and public-source validation must precede writes."""
from __future__ import annotations

import contextlib
import copy
import io
import os
import unittest
from unittest.mock import MagicMock, patch

from project import cli
from project.github import update_project_metadata


class FreshnessTests(unittest.TestCase):
    def test_metadata_preview_detects_stale_brief_without_writing(self) -> None:
        client = MagicMock()
        definition = {"public": True, "short_description": "Current purpose"}
        current = {"id": "P", "public": True,
                   "shortDescription": "Current purpose", "readme": "September"}
        before = copy.deepcopy(current)
        actions = update_project_metadata(client, current, definition,
                                          "October", apply=False)
        self.assertEqual(actions, ["project metadata drift"])
        client.graphql.assert_not_called()
        self.assertEqual(current, before)
        current["readme"] = "October"
        self.assertEqual(update_project_metadata(client, current, definition,
                                                "October", apply=False), [])

    def test_private_source_refuses_before_any_project_mutation(self) -> None:
        manifest = cli.load_yaml(cli.MANIFEST_PATH)
        manifest["sources"]["github_issues"]["repositories"] = ["private-repo"]
        client = MagicMock()
        client.rest.side_effect = lambda method, path: {
            "private": path.endswith("/private-repo")
        }
        with patch.dict(os.environ, {"BOARD_PROJECT_TOKEN": "test-token"}), \
             patch("project.cli.GitHub", return_value=client), \
             patch("project.cli.load_yaml", side_effect=[manifest, {}]), \
             patch("project.cli.ensure_fields") as fields, \
             patch("project.cli.ensure_repository_links") as links, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["--apply"]), 2)
        fields.assert_not_called()
        links.assert_not_called()
        client.graphql.assert_not_called()
        self.assertTrue(all(call.args[0] == "GET" for call in client.rest.call_args_list))


if __name__ == "__main__":
    unittest.main()
