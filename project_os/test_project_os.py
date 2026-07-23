"""Unit proofs for Project OS normalization and reconciliation."""

from __future__ import annotations

import pathlib
import unittest
from unittest.mock import patch

import yaml

from project_os.github import ActualItem, reconcile
from project_os.model import (
    BLOCK_BLOCKED,
    BLOCK_BLOCKING,
    BLOCK_BOTH,
    BLOCK_CLEAR,
    BLOCK_UNKNOWN,
    CI_GREEN,
    CI_RED,
    DesiredItem,
    ITEM_GATE,
    PROJECTION_ORPHANED,
    PROJECTION_QUARANTINED,
    PROJECTION_SYNCED,
    REVIEW_APPROVED,
    REVIEW_CHANGES_REQUESTED,
    REVIEW_DRAFT,
    SIGNAL_ACTIVE,
    SIGNAL_ATTENTION,
    SIGNAL_QUEUED,
    SIGNAL_READY,
    block_state,
    ci_state,
    extract_marker,
    issue_item,
    marker,
    pull_request_signal,
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
        gates = [
            item for item in items if item.fields["Item type"] == ITEM_GATE
        ]
        self.assertTrue(gates)
        for gate in gates:
            self.assertNotIn("When", gate.fields)
            self.assertNotIn("Start", gate.fields)
            self.assertNotIn("Target", gate.fields)

    def test_dependency_states(self) -> None:
        self.assertEqual(block_state(0, 0), BLOCK_CLEAR)
        self.assertEqual(block_state(1, 0), BLOCK_BLOCKED)
        self.assertEqual(block_state(0, 1), BLOCK_BLOCKING)
        self.assertEqual(block_state(1, 1), BLOCK_BOTH)
        self.assertEqual(block_state(None, 0), BLOCK_UNKNOWN)

    def test_review_and_ci_states(self) -> None:
        self.assertEqual(review_state({"draft": True}, []), REVIEW_DRAFT)
        reviews = [{"user": {"login": "nika"}, "state": "APPROVED"}]
        self.assertEqual(
            review_state({"draft": False}, reviews),
            REVIEW_APPROVED,
        )
        self.assertEqual(
            ci_state([{"status": "completed", "conclusion": "success"}]),
            CI_GREEN,
        )
        self.assertEqual(
            ci_state([{"status": "completed", "conclusion": "failure"}]),
            CI_RED,
        )

    def test_signal_is_derived_from_source_facts(self) -> None:
        base_issue = {
            "number": 42,
            "title": "Prove the signal",
            "body": "",
            "node_id": "ISSUE",
            "html_url": "https://github.com/supernovae-st/nika/issues/42",
            "created_at": "2026-07-23T00:00:00Z",
            "assignees": [],
            "labels": [],
        }
        queued = issue_item("nika", base_issue, 0, 0)
        self.assertEqual(queued.fields["Signal"], SIGNAL_QUEUED)
        active = issue_item(
            "nika",
            {**base_issue, "assignees": [{"login": "nika"}]},
            0,
            0,
        )
        self.assertEqual(active.fields["Signal"], SIGNAL_ACTIVE)
        blocked = issue_item("nika", base_issue, 1, 0)
        self.assertEqual(blocked.fields["Signal"], SIGNAL_ATTENTION)
        self.assertEqual(
            pull_request_signal(
                {"draft": False},
                REVIEW_APPROVED,
                CI_GREEN,
            ),
            SIGNAL_READY,
        )
        self.assertEqual(
            pull_request_signal(
                {"draft": False},
                REVIEW_CHANGES_REQUESTED,
                CI_GREEN,
            ),
            SIGNAL_ATTENTION,
        )


class ReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fields = {
            "SSOT ID": {"id": "F1", "dataType": "TEXT"},
            "Projection state": {
                "id": "F2",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O1", "name": PROJECTION_SYNCED},
                    {"id": "O2", "name": PROJECTION_ORPHANED},
                    {"id": "O3", "name": PROJECTION_QUARANTINED},
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
                "Projection state": PROJECTION_SYNCED,
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
        self.assertIn(
            f"{PROJECTION_ORPHANED.lower()} timeline:entry:retired",
            actions,
        )
        self.assertIn(
            f"{PROJECTION_QUARANTINED.lower()} Human note",
            actions,
        )
        self.assertFalse(any("delete" in action for action in actions))


if __name__ == "__main__":
    unittest.main()
