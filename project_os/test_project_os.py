"""Unit proofs for Project OS normalization and reconciliation."""

from __future__ import annotations

import pathlib
import unittest
from unittest.mock import patch

import yaml

from project_os.github import ActualItem, reconcile
from project_os.model import (
    DesiredItem,
    block_state,
    ci_state,
    extract_marker,
    marker,
    review_state,
    timeline_items,
)


ROOT = pathlib.Path(__file__).resolve().parent.parent


class ModelTests(unittest.TestCase):
    def test_marker_round_trip(self) -> None:
        identity = "timeline:entry:diamond-genesis"
        self.assertEqual(extract_marker(marker(identity)), identity)

    def test_timeline_ids_are_unique_and_gates_have_no_dates(self) -> None:
        timeline = yaml.safe_load(
            (ROOT / "timeline" / "timeline.yaml").read_text(encoding="utf-8")
        )
        items = timeline_items(timeline)
        identities = [item.ssot_id for item in items]
        self.assertEqual(len(identities), len(set(identities)))
        gates = [item for item in items if item.fields["Item type"] == "Gate"]
        self.assertTrue(gates)
        for gate in gates:
            self.assertNotIn("When", gate.fields)
            self.assertNotIn("Start", gate.fields)
            self.assertNotIn("Target", gate.fields)

    def test_dependency_states(self) -> None:
        self.assertEqual(block_state(0, 0), "Clear")
        self.assertEqual(block_state(1, 0), "Blocked")
        self.assertEqual(block_state(0, 1), "Blocking")
        self.assertEqual(block_state(1, 1), "Both")
        self.assertEqual(block_state(None, 0), "Unknown")

    def test_review_and_ci_states(self) -> None:
        self.assertEqual(review_state({"draft": True}, []), "Draft")
        reviews = [{"user": {"login": "nika"}, "state": "APPROVED"}]
        self.assertEqual(review_state({"draft": False}, reviews), "Approved")
        self.assertEqual(
            ci_state([{"status": "completed", "conclusion": "success"}]),
            "Green",
        )
        self.assertEqual(
            ci_state([{"status": "completed", "conclusion": "failure"}]),
            "Red",
        )


class ReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fields = {
            "SSOT ID": {"id": "F1", "dataType": "TEXT"},
            "Projection state": {
                "id": "F2",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O1", "name": "Synced"},
                    {"id": "O2", "name": "Orphaned"},
                    {"id": "O3", "name": "Quarantined"},
                ],
            },
        }
        self.definitions = [
            {"name": "SSOT ID", "type": "TEXT", "writer": "projector"},
            {
                "name": "Projection state",
                "type": "SINGLE_SELECT",
                "writer": "projector",
            },
        ]

    def test_legacy_title_migrates_without_add_or_delete(self) -> None:
        actual = ActualItem(
            item_id="ITEM",
            content_id="DRAFT",
            content_kind="DraftIssue",
            title="Diamond genesis",
            body="legacy",
            url=None,
            fields={},
        )
        desired = DesiredItem(
            ssot_id="timeline:entry:diamond-genesis",
            title="Diamond genesis",
            body=marker("timeline:entry:diamond-genesis"),
            fields={
                "SSOT ID": "timeline:entry:diamond-genesis",
                "Projection state": "Synced",
            },
            managed_content=True,
            legacy_titles=("Diamond genesis",),
        )
        with patch("project_os.github.snapshot_items", return_value=[actual]):
            actions = reconcile(
                object(),
                "PROJECT",
                [desired],
                self.fields,
                self.definitions,
                apply=False,
            )
        self.assertFalse(any(action.startswith("add ") for action in actions))
        self.assertFalse(any("delete" in action for action in actions))
        self.assertIn("content timeline:entry:diamond-genesis", actions)

    def test_unknown_and_retired_items_are_retained(self) -> None:
        actual = [
            ActualItem(
                item_id="KNOWN",
                content_id="D1",
                content_kind="DraftIssue",
                title="Retired",
                body=marker("timeline:entry:retired"),
                url=None,
                fields={"SSOT ID": "timeline:entry:retired"},
            ),
            ActualItem(
                item_id="UNKNOWN",
                content_id="D2",
                content_kind="DraftIssue",
                title="Human note",
                body="not projected",
                url=None,
                fields={},
            ),
        ]
        with patch("project_os.github.snapshot_items", return_value=actual):
            actions = reconcile(
                object(),
                "PROJECT",
                [],
                self.fields,
                self.definitions,
                apply=False,
            )
        self.assertIn("orphaned timeline:entry:retired", actions)
        self.assertIn("quarantined Human note", actions)
        self.assertFalse(any("delete" in action for action in actions))


if __name__ == "__main__":
    unittest.main()
