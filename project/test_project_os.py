"""Unit proofs for Project OS normalization and reconciliation."""

from __future__ import annotations

import io
import pathlib
import urllib.error
import unittest
from unittest.mock import MagicMock, patch

import yaml

from project.github import ActualItem, GitHub, GitHubError, reconcile
from project.model import (
    BLOCK_BLOCKED,
    BLOCK_BLOCKING,
    BLOCK_BOTH,
    BLOCK_CLEAR,
    BLOCK_UNKNOWN,
    CERTAINTY_COMMITTED,
    CERTAINTY_PROVEN,
    CERTAINTY_UNKNOWN,
    CI_GREEN,
    CI_NOT_APPLICABLE,
    CI_RED,
    DesiredItem,
    ITEM_GATE,
    ITEM_ISSUE,
    PROJECTION_ORPHANED,
    PROJECTION_QUARANTINED,
    PROJECTION_SYNCED,
    REVIEW_APPROVED,
    REVIEW_CHANGES_REQUESTED,
    REVIEW_DRAFT,
    REVIEW_NOT_APPLICABLE,
    SIGNAL_ACTIVE,
    SIGNAL_ATTENTION,
    SIGNAL_QUEUED,
    SIGNAL_READY,
    SIGNAL_SETTLED,
    STAGE_CLOSED_COMPLETED,
    STAGE_CLOSED_NOT_INTEGRATED,
    STAGE_MERGED,
    STAGE_SHIPPED,
    STAGE_WORK,
    STATUS_IN_PROGRESS,
    accountable,
    block_state,
    ci_state,
    extract_marker,
    issue_item,
    marker,
    pull_request_signal,
    review_state,
    terminal_classification,
    timeline_items,
)
from project.sources import (
    desired_from_sources,
    ensure_public_repositories,
    pull_request_items,
    release_items,
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

    def test_accountable_does_not_invent_issue_ownership(self) -> None:
        unassigned = {
            "assignees": [],
            "user": {"login": "issue-author"},
        }
        self.assertIsNone(accountable(unassigned))
        self.assertEqual(
            accountable(unassigned, include_author=True),
            "issue-author",
        )
        assigned = {
            "assignees": [
                {"login": "nika"},
                {"login": "thibaut"},
            ],
            "user": {"login": "issue-author"},
        }
        self.assertEqual(accountable(assigned), "nika, thibaut")

    def test_terminal_classification_reads_actual_source_state(self) -> None:
        self.assertEqual(
            terminal_classification(
                {
                    "__typename": "Issue",
                    "state": "CLOSED",
                    "stateReason": "COMPLETED",
                }
            ),
            (STAGE_CLOSED_COMPLETED, CERTAINTY_COMMITTED),
        )
        for reason in ("NOT_PLANNED", "DUPLICATE", None):
            self.assertEqual(
                terminal_classification(
                    {
                        "__typename": "Issue",
                        "state": "CLOSED",
                        "stateReason": reason,
                    }
                ),
                (STAGE_CLOSED_NOT_INTEGRATED, CERTAINTY_UNKNOWN),
            )
        self.assertEqual(
            terminal_classification(
                {"__typename": "PullRequest", "state": "MERGED"}
            ),
            (STAGE_MERGED, CERTAINTY_COMMITTED),
        )
        self.assertEqual(
            terminal_classification(
                {
                    "__typename": "PullRequest",
                    "state": "CLOSED",
                    "merged": True,
                }
            ),
            (STAGE_MERGED, CERTAINTY_COMMITTED),
        )
        self.assertEqual(
            terminal_classification(
                {
                    "__typename": "PullRequest",
                    "state": "CLOSED",
                    "merged": False,
                }
            ),
            (STAGE_CLOSED_NOT_INTEGRATED, CERTAINTY_UNKNOWN),
        )
        self.assertIsNone(
            terminal_classification({"__typename": "Issue", "state": "OPEN"})
        )
        self.assertIsNone(
            terminal_classification({"__typename": "PullRequest", "state": "OPEN"})
        )
        self.assertIsNone(terminal_classification({"__typename": "DraftIssue"}))
        self.assertIsNone(terminal_classification({}))

    def test_terminal_stages_are_never_shipped(self) -> None:
        for stage in (
            STAGE_CLOSED_COMPLETED,
            STAGE_MERGED,
            STAGE_CLOSED_NOT_INTEGRATED,
        ):
            self.assertNotEqual(stage, STAGE_SHIPPED)


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
            "Status": {
                "id": "F3",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O4", "name": "Todo"},
                    {"id": "O5", "name": STATUS_IN_PROGRESS},
                    {"id": "O6", "name": "Done"},
                ],
            },
            "Stage": {
                "id": "F4",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O7", "name": STAGE_WORK},
                    {"id": "O8", "name": STAGE_CLOSED_COMPLETED},
                    {"id": "O9", "name": STAGE_MERGED},
                    {"id": "O10", "name": STAGE_CLOSED_NOT_INTEGRATED},
                ],
            },
            "Signal": {
                "id": "F5",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O11", "name": SIGNAL_QUEUED},
                    {"id": "O12", "name": SIGNAL_ACTIVE},
                    {"id": "O13", "name": SIGNAL_SETTLED},
                ],
            },
            "Certainty": {
                "id": "F6",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O14", "name": CERTAINTY_COMMITTED},
                    {"id": "O15", "name": CERTAINTY_UNKNOWN},
                    {"id": "O16", "name": CERTAINTY_PROVEN},
                ],
            },
            "Proof": {
                "id": "F7",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O17", "name": "◌ pending"},
                    {"id": "O18", "name": "✓ proven"},
                ],
            },
            "Horizon": {
                "id": "F8",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O19", "name": "● now"},
                    {"id": "O20", "name": "→ next"},
                ],
            },
            "Block state": {
                "id": "F9",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O23", "name": BLOCK_CLEAR},
                    {"id": "O24", "name": BLOCK_UNKNOWN},
                ],
            },
            "Review state": {
                "id": "F10",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O25", "name": REVIEW_NOT_APPLICABLE},
                    {"id": "O26", "name": REVIEW_APPROVED},
                ],
            },
            "CI state": {
                "id": "F11",
                "dataType": "SINGLE_SELECT",
                "options": [
                    {"id": "O27", "name": CI_NOT_APPLICABLE},
                ],
            },
            "Start": {"id": "F12", "dataType": "DATE"},
            "Target": {"id": "F13", "dataType": "DATE"},
            "Priority": {
                "id": "F14",
                "dataType": "SINGLE_SELECT",
                "options": [{"id": "O28", "name": "High"}],
            },
            "Effort": {
                "id": "F15",
                "dataType": "SINGLE_SELECT",
                "options": [{"id": "O29", "name": "Medium"}],
            },
            "Item type": {
                "id": "F16",
                "dataType": "SINGLE_SELECT",
                "options": [{"id": "O30", "name": ITEM_ISSUE}],
            },
        }
        self.definitions = [
            {"name": "SSOT ID", "type": "TEXT", "writer": "projector"},
            {
                "name": "Projection state",
                "type": "SINGLE_SELECT",
                "writer": "projector",
            },
            {
                "name": "Status",
                "type": "SINGLE_SELECT",
                "writer": "projector",
            },
            {"name": "Stage", "type": "SINGLE_SELECT", "writer": "projector"},
            {"name": "Signal", "type": "SINGLE_SELECT", "writer": "projector"},
            {
                "name": "Certainty",
                "type": "SINGLE_SELECT",
                "writer": "projector",
            },
            {"name": "Proof", "type": "SINGLE_SELECT", "writer": "projector"},
            {"name": "Horizon", "type": "SINGLE_SELECT", "writer": "projector"},
            {
                "name": "Block state",
                "type": "SINGLE_SELECT",
                "writer": "projector",
            },
            {
                "name": "Review state",
                "type": "SINGLE_SELECT",
                "writer": "projector",
            },
            {"name": "CI state", "type": "SINGLE_SELECT", "writer": "projector"},
            {"name": "Start", "type": "DATE", "writer": "github"},
            {"name": "Target", "type": "DATE", "writer": "github"},
            {"name": "Priority", "type": "SINGLE_SELECT", "writer": "human"},
            {"name": "Effort", "type": "SINGLE_SELECT", "writer": "human"},
            {
                "name": "Item type",
                "type": "SINGLE_SELECT",
                "writer": "projector",
            },
        ]

    def capture_changes(
        self,
        actual: list[ActualItem],
        desired: list[DesiredItem],
    ) -> list[tuple[str, object]]:
        with patch(
            "project.github.snapshot_items", return_value=actual
        ), patch("project.github.apply_field_changes") as apply_mock:
            reconcile(
                object(),
                "PROJECT",
                desired,
                self.fields,
                self.definitions,
                apply=True,
            )
        return [
            change
            for call in apply_mock.call_args_list
            for change in call.args[4]
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
        with patch("project.github.snapshot_items", return_value=[actual]):
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
        with patch("project.github.snapshot_items", return_value=actual):
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

    def test_projector_repairs_the_native_status_field(self) -> None:
        actual = ActualItem(
            item_id="ITEM",
            content_id="ISSUE",
            content_kind="PullRequest",
            title="Ready pull request",
            body="",
            url="https://github.com/supernovae-st/nika/pull/1",
            fields={
                "SSOT ID": "github:pr:supernovae-st/nika#1",
                "Status": "Todo",
            },
        )
        desired = DesiredItem(
            ssot_id="github:pr:supernovae-st/nika#1",
            title="Ready pull request",
            body="",
            fields={
                "SSOT ID": "github:pr:supernovae-st/nika#1",
                "Status": STATUS_IN_PROGRESS,
            },
            content_id="ISSUE",
            content_kind="PullRequest",
        )
        with patch("project.github.snapshot_items", return_value=[actual]):
            actions = reconcile(
                object(),
                "PROJECT",
                [desired],
                self.fields,
                self.definitions,
                apply=False,
            )
        self.assertIn(
            "field github:pr:supernovae-st/nika#1 · Status",
            actions,
        )

    @staticmethod
    def open_issue(number: int) -> dict:
        return {
            "number": number,
            "title": f"Issue {number}",
            "body": "",
            "node_id": f"ISSUE{number}",
            "html_url": f"https://github.com/supernovae-st/nika/issues/{number}",
            "created_at": "2026-09-01T00:00:00Z",
            "assignees": [],
            "labels": [],
        }

    def test_stale_closed_item_settles_from_actual_state(self) -> None:
        ssot = "github:issue:supernovae-st/nika#651"
        actual = ActualItem(
            item_id="ITEM651",
            content_id="ISSUE651",
            content_kind="Issue",
            title="Stale closed issue",
            body="",
            url="https://github.com/supernovae-st/nika/issues/651",
            fields={
                "SSOT ID": ssot,
                "Stage": STAGE_WORK,
                "Signal": SIGNAL_QUEUED,
                "Status": STATUS_IN_PROGRESS,
                "Horizon": "● now",
                "Certainty": CERTAINTY_COMMITTED,
                "Proof": "✓ proven",
                "Priority": "High",
                "Effort": "Medium",
                "Projection state": PROJECTION_SYNCED,
            },
            terminal=(STAGE_CLOSED_COMPLETED, CERTAINTY_COMMITTED),
        )
        with patch("project.github.snapshot_items", return_value=[actual]):
            actions = reconcile(
                object(), "PROJECT", [], self.fields, self.definitions,
                apply=False,
            )
        self.assertIn(f"field {ssot} · Stage", actions)
        self.assertIn(f"field {ssot} · Signal", actions)
        self.assertIn(f"field {ssot} · Status", actions)
        self.assertFalse(any("orphaned" in action for action in actions))
        self.assertFalse(any(action.startswith("add ") for action in actions))
        self.assertFalse(
            any("Priority" in action or "Effort" in action for action in actions)
        )

        changes = self.capture_changes([actual], [])
        self.assertIn(("Stage", STAGE_CLOSED_COMPLETED), changes)
        self.assertIn(("Status", "Done"), changes)
        self.assertIn(("Signal", SIGNAL_SETTLED), changes)
        self.assertIn(("Horizon", None), changes)
        # A stale false-proof claim is repaired to pending, never kept.
        self.assertIn(("Proof", "◌ pending"), changes)
        self.assertNotIn(("Stage", STAGE_SHIPPED), changes)
        self.assertFalse(
            any(name in {"Priority", "Effort"} for name, _ in changes)
        )

    def test_merged_and_unmerged_pull_requests_settle_distinctly(self) -> None:
        merged = ActualItem(
            item_id="ITEM1",
            content_id="PR1",
            content_kind="PullRequest",
            title="Merged pull request",
            body="",
            url="https://github.com/supernovae-st/nika/pull/1",
            fields={"SSOT ID": "github:pr:supernovae-st/nika#1"},
            terminal=(STAGE_MERGED, CERTAINTY_COMMITTED),
        )
        unmerged = ActualItem(
            item_id="ITEM2",
            content_id="PR2",
            content_kind="PullRequest",
            title="Closed unmerged pull request",
            body="",
            url="https://github.com/supernovae-st/nika/pull/2",
            fields={"SSOT ID": "github:pr:supernovae-st/nika#2"},
            terminal=(STAGE_CLOSED_NOT_INTEGRATED, CERTAINTY_UNKNOWN),
        )
        merged_changes = self.capture_changes([merged], [])
        self.assertIn(("Stage", STAGE_MERGED), merged_changes)
        self.assertIn(("Certainty", CERTAINTY_COMMITTED), merged_changes)
        self.assertIn(("Status", "Done"), merged_changes)
        unmerged_changes = self.capture_changes([unmerged], [])
        self.assertIn(("Stage", STAGE_CLOSED_NOT_INTEGRATED), unmerged_changes)
        self.assertIn(("Certainty", CERTAINTY_UNKNOWN), unmerged_changes)
        for changes in (merged_changes, unmerged_changes):
            self.assertIn(("Proof", "◌ pending"), changes)
            self.assertNotIn(("Stage", STAGE_SHIPPED), changes)
            self.assertNotIn(("Certainty", CERTAINTY_PROVEN), changes)

    def test_unmanaged_closed_item_is_quarantined_untouched(self) -> None:
        actual = ActualItem(
            item_id="ITEMH",
            content_id="ISSUE9",
            content_kind="Issue",
            title="Human note",
            body="not projected",
            url="https://github.com/supernovae-st/nika/issues/9",
            fields={"Stage": STAGE_WORK, "Status": "Todo"},
            terminal=(STAGE_CLOSED_COMPLETED, CERTAINTY_COMMITTED),
        )
        with patch("project.github.snapshot_items", return_value=[actual]):
            actions = reconcile(
                object(), "PROJECT", [], self.fields, self.definitions,
                apply=False,
            )
        self.assertIn(
            f"{PROJECTION_QUARANTINED.lower()} Human note", actions
        )
        self.assertFalse(any(action.startswith("field ") for action in actions))
        self.assertFalse(any("synced" in action for action in actions))

    def test_reopen_race_clears_stale_terminal_claims(self) -> None:
        ssot = "github:issue:supernovae-st/nika#42"
        actual = ActualItem(
            item_id="ITEM42",
            content_id="ISSUE42",
            content_kind="Issue",
            title="Reopened before discovery caught it",
            body="",
            url="https://github.com/supernovae-st/nika/issues/42",
            fields={
                "SSOT ID": ssot,
                "Stage": STAGE_CLOSED_COMPLETED,
                "Signal": SIGNAL_SETTLED,
                "Status": "Done",
                "Certainty": CERTAINTY_COMMITTED,
                "Proof": "◌ pending",
                "Priority": "High",
                "Projection state": PROJECTION_SYNCED,
            },
            terminal=None,
        )
        with patch("project.github.snapshot_items", return_value=[actual]):
            actions = reconcile(
                object(), "PROJECT", [], self.fields, self.definitions,
                apply=False,
            )
        self.assertIn(f"{PROJECTION_ORPHANED.lower()} {ssot}", actions)
        self.assertIn(f"field {ssot} · Stage", actions)
        self.assertFalse(any("Priority" in action for action in actions))

        changes = self.capture_changes([actual], [])
        self.assertIn(("Stage", None), changes)
        self.assertIn(("Signal", None), changes)
        self.assertIn(("Status", None), changes)
        self.assertIn(("Certainty", CERTAINTY_UNKNOWN), changes)
        self.assertIn(("Projection state", PROJECTION_ORPHANED), changes)
        self.assertNotIn(("Status", "Done"), changes)
        self.assertNotIn(("Stage", STAGE_WORK), changes)

    def test_desired_item_closed_by_snapshot_time_settles(self) -> None:
        desired = issue_item("nika", self.open_issue(42), 0, 0)
        actual = ActualItem(
            item_id="ITEM42",
            content_id="ISSUE42",
            content_kind="Issue",
            title="Issue 42",
            body="",
            url="https://github.com/supernovae-st/nika/issues/42",
            fields={
                "SSOT ID": desired.ssot_id,
                "Stage": STAGE_WORK,
                "Signal": SIGNAL_QUEUED,
                "Status": "Todo",
                "Projection state": PROJECTION_SYNCED,
            },
            terminal=(STAGE_CLOSED_COMPLETED, CERTAINTY_COMMITTED),
        )
        changes = self.capture_changes([actual], [desired])
        self.assertIn(("Stage", STAGE_CLOSED_COMPLETED), changes)
        self.assertIn(("Status", "Done"), changes)
        self.assertIn(("Signal", SIGNAL_SETTLED), changes)
        self.assertNotIn(("Stage", STAGE_WORK), changes)
        self.assertNotIn(("Signal", SIGNAL_QUEUED), changes)

    def test_desired_matched_with_null_content_stays_unknown(self) -> None:
        desired = issue_item("nika", self.open_issue(77), 0, 0)
        actual = ActualItem(
            item_id="ITEM77",
            content_id=None,
            content_kind=None,
            title="Vanished source",
            body="",
            url=None,
            fields={
                "SSOT ID": desired.ssot_id,
                "Stage": STAGE_WORK,
                "Signal": SIGNAL_ACTIVE,
                "Status": STATUS_IN_PROGRESS,
                "Certainty": CERTAINTY_COMMITTED,
                "Proof": "◌ pending",
                "Priority": "High",
                "Projection state": PROJECTION_SYNCED,
            },
        )
        changes = self.capture_changes([actual], [desired])
        self.assertIn(("Stage", None), changes)
        self.assertIn(("Signal", None), changes)
        self.assertIn(("Status", None), changes)
        self.assertIn(("Certainty", CERTAINTY_UNKNOWN), changes)
        self.assertIn(("Projection state", PROJECTION_ORPHANED), changes)
        self.assertNotIn(("Stage", STAGE_WORK), changes)
        self.assertNotIn(("Status", "Done"), changes)
        self.assertFalse(
            any(name in {"Priority", "Effort"} for name, _ in changes)
        )

    def test_adopted_terminal_item_receives_identity(self) -> None:
        desired = issue_item("nika", self.open_issue(88), 0, 0)
        actual = ActualItem(
            item_id="ITEM88",
            content_id="ISSUE88",
            content_kind="Issue",
            title="Issue 88",
            body="",
            url="https://github.com/supernovae-st/nika/issues/88",
            fields={},
            terminal=(STAGE_CLOSED_COMPLETED, CERTAINTY_COMMITTED),
        )
        changes = self.capture_changes([actual], [desired])
        self.assertIn(("SSOT ID", desired.ssot_id), changes)
        self.assertIn(("Item type", ITEM_ISSUE), changes)
        self.assertIn(("Stage", STAGE_CLOSED_COMPLETED), changes)
        self.assertIn(("Status", "Done"), changes)
        self.assertIn(("Signal", SIGNAL_SETTLED), changes)
        self.assertIn(("Projection state", PROJECTION_SYNCED), changes)
        self.assertNotIn(("Stage", STAGE_WORK), changes)

    def test_reopened_item_regains_active_fields(self) -> None:
        desired = issue_item("nika", self.open_issue(99), 0, 0)
        actual = ActualItem(
            item_id="ITEM99",
            content_id="ISSUE99",
            content_kind="Issue",
            title="Issue 99",
            body="",
            url="https://github.com/supernovae-st/nika/issues/99",
            fields={
                "SSOT ID": desired.ssot_id,
                "Stage": STAGE_CLOSED_COMPLETED,
                "Signal": SIGNAL_SETTLED,
                "Status": "Done",
                "Certainty": CERTAINTY_COMMITTED,
                "Proof": "◌ pending",
                "Projection state": PROJECTION_SYNCED,
            },
            terminal=None,
        )
        changes = self.capture_changes([actual], [desired])
        self.assertIn(("Stage", STAGE_WORK), changes)
        self.assertIn(("Signal", SIGNAL_QUEUED), changes)
        self.assertIn(("Status", "Todo"), changes)
        self.assertIn(("Horizon", "→ next"), changes)
        self.assertFalse(
            any(value == STAGE_CLOSED_COMPLETED for _, value in changes)
        )


class SourceTests(unittest.TestCase):
    manifest = {
        "project": {"repositories": ["nika"]},
        "sources": {
            "github_issues": {
                "repositories": ["nika"],
                "exclude_labels": ["gate"],
            },
            "github_pull_requests": {"repositories": ["nika"]},
            "github_releases": {
                "repositories": ["nika"],
                "limit_per_repository": 12,
            },
        },
    }
    timeline = {"entries": [], "gates": []}

    def test_private_repository_is_rejected(self) -> None:
        client = MagicMock()
        client.rest.return_value = {"private": True}
        with self.assertRaisesRegex(ValueError, "private repository rejected"):
            ensure_public_repositories(client, ["nika-lab"])

    def test_inaccessible_repository_fails_the_run(self) -> None:
        client = MagicMock()
        client.rest.side_effect = GitHubError("repos/nika-lab: HTTP 404")
        with self.assertRaises(GitHubError):
            ensure_public_repositories(client, ["nika-lab"])

    def test_duplicate_normalized_identity_is_rejected(self) -> None:
        issue = {
            "number": 7,
            "title": "Duplicated by the API",
            "body": "",
            "node_id": "ISSUE7",
            "html_url": "https://github.com/supernovae-st/nika/issues/7",
            "created_at": "2026-09-01T00:00:00Z",
            "assignees": [],
            "labels": [],
        }

        def pages(path: str, optional: bool = False) -> list | None:
            if "dependencies" in path:
                return None
            if "milestones" in path:
                return []
            if "labels=gate" in path:
                return []
            if "issues?state=open" in path:
                return [issue, dict(issue)]
            if "pulls?state=open" in path:
                return []
            if "releases" in path:
                return []
            raise AssertionError(f"unexpected path: {path}")

        client = MagicMock()
        client.pages.side_effect = pages
        client.rest.return_value = {"private": False}
        with self.assertRaisesRegex(ValueError, "duplicate normalized SSOT IDs"):
            desired_from_sources(
                client, self.manifest, self.timeline, apply_gate_issues=False
            )

    def test_review_read_failure_fails_loudly(self) -> None:
        pull = {
            "number": 5,
            "title": "A pull request",
            "body": "",
            "node_id": "PR5",
            "html_url": "https://github.com/supernovae-st/nika/pull/5",
            "created_at": "2026-09-01T00:00:00Z",
            "assignees": [],
            "labels": [],
            "head": {"sha": "abc123"},
        }

        def pages(path: str, optional: bool = False) -> list:
            if "pulls?state=open" in path:
                return [pull]
            if path.endswith("/reviews"):
                raise GitHubError("pulls/5/reviews: HTTP 500")
            raise AssertionError(f"unexpected path: {path}")

        client = MagicMock()
        client.pages.side_effect = pages
        with self.assertRaises(GitHubError):
            pull_request_items(client, ["nika"])

    def test_drafts_do_not_evict_published_releases_from_the_window(self) -> None:
        def release(tag: str, day: int, **flags: bool) -> dict:
            return {
                "tag_name": tag,
                "name": tag,
                "html_url": f"https://github.com/supernovae-st/nika/releases/tag/{tag}",
                "created_at": f"2026-09-{day:02d}T00:00:00Z",
                "published_at": None if flags.get("draft") else f"2026-09-{day:02d}T00:00:00Z",
                "draft": flags.get("draft", False),
                "prerelease": flags.get("prerelease", False),
            }

        # The API lists drafts first; two of them must not cost published slots.
        values = [
            release("v0.121.0", 25, draft=True),
            release("v0.118.4", 5, draft=True),
            release("v0.120.0", 20),
            release("v0.119.0", 13, prerelease=True),
            release("v0.114.0", 3),
            release("v0.113.0", 2),
        ]
        client = MagicMock()
        client.pages.return_value = values
        items = release_items(client, ["nika"], 3, self.timeline, order_start=0)
        self.assertEqual(
            [item.ssot_id for item in items],
            [
                "github:release:supernovae-st/nika@v0.114.0",
                "github:release:supernovae-st/nika@v0.119.0",
                "github:release:supernovae-st/nika@v0.120.0",
            ],
        )


class GitHubClientTests(unittest.TestCase):
    def test_graphql_retries_a_secondary_rate_limit(self) -> None:
        throttled = urllib.error.HTTPError(
            "https://api.github.com/graphql",
            403,
            "Forbidden",
            {"Retry-After": "7"},
            io.BytesIO(
                b'{"message":"You have exceeded a secondary rate limit."}'
            ),
        )
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"data":{"viewer":{"login":"nika"}}}'
        )
        sleeps: list[float] = []
        client = GitHub("token", sleep=sleeps.append)
        with patch(
            "project.github.urllib.request.urlopen",
            side_effect=[throttled, response],
        ):
            result = client.graphql("query { viewer { login } }")
        self.assertEqual(result["viewer"]["login"], "nika")
        self.assertEqual(sleeps, [10])

    def test_graphql_paces_aliased_mutations_by_cost(self) -> None:
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"data":{"one":{},"two":{},"three":{},"four":{}}}'
        )
        sleeps: list[float] = []
        client = GitHub(
            "token",
            sleep=sleeps.append,
            mutation_interval=0.25,
        )
        with patch(
            "project.github.urllib.request.urlopen",
            return_value=response,
        ):
            client.graphql("mutation { one two three four }", mutation_cost=4)
        self.assertEqual(sleeps, [1.0])


if __name__ == "__main__":
    unittest.main()
