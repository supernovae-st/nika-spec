#!/usr/bin/env python3
"""Verify the Project OS contract offline or against GitHub."""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from typing import Any

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from project_os.github import (  # noqa: E402
    GitHub,
    GitHubError,
    load_project,
    project_fields,
    views_snapshot,
)
from project_os.model import ITEM_GATE, timeline_items  # noqa: E402


VALID_WRITERS = {"projector", "timeline", "github", "human"}
RESERVED_FIELD_NAMES = {
    "Assignees",
    "Closed",
    "Created",
    "Labels",
    "Linked pull requests",
    "Milestone",
    "Parent issue",
    "Repository",
    "Reviewers",
    "Status",
    "Sub-issues progress",
    "Title",
    "Type",
    "Updated",
}
LAYOUTS = {
    "TABLE": "TABLE_LAYOUT",
    "BOARD": "BOARD_LAYOUT",
    "ROADMAP": "ROADMAP_LAYOUT",
}
SEMANTIC_SIGILS = {
    "📜",
    "🚪",
    "🧩",
    "🔀",
    "📦",
    "✅",
    "🛠",
    "🔍",
    "✧",
    "✎",
    "◆",
    "◇",
    "✓",
    "·",
    "○",
    "◌",
    "🧭",
    "⚙",
    "🌱",
    "✦",
    "🤝",
    "◈",
    "🧰",
    "📊",
    "●",
    "→",
    "⋯",
    "?",
    "△",
    "⛓",
    "⇢",
    "!",
    "✗",
    "🚨",
    "👀",
    "▶",
    "⏭",
}


def load(path: pathlib.Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def offline_findings(
    manifest: dict[str, Any], timeline: dict[str, Any]
) -> list[str]:
    findings: list[str] = []
    if manifest.get("schema_version") != 3:
        findings.append("project-os schema_version must be 3")
    grammar = manifest.get("visual_grammar", {})
    for key in ("law", "density", "signal"):
        if not grammar.get(key):
            findings.append(f"visual_grammar.{key} must be declared")
    names = [field["name"] for field in manifest.get("fields", [])]
    if len(names) != len(set(names)):
        findings.append("Project field names must be unique")
    collisions = sorted(set(names) & RESERVED_FIELD_NAMES)
    if collisions:
        findings.append(
            f"custom fields collide with GitHub reserved names: {collisions}"
        )
    for field in manifest.get("fields", []):
        if field.get("writer") not in VALID_WRITERS:
            findings.append(f"{field.get('name')}: invalid writer")
        if field.get("type") == "SINGLE_SELECT":
            options = [option[0] for option in field.get("options", [])]
            if not options or len(options) != len(set(options)):
                findings.append(
                    f"{field.get('name')}: select options must be non-empty and unique"
                )
            if field.get("writer") != "human":
                for option in options:
                    if not any(sigil in option for sigil in SEMANTIC_SIGILS):
                        findings.append(
                            f"{field.get('name')}: {option!r} lacks a semantic sigil"
                        )
    field_definitions = {
        field["name"]: field for field in manifest.get("fields", [])
    }
    signal = field_definitions.get("Signal")
    if not signal or signal.get("writer") != "projector":
        findings.append("Signal must exist as a projector-owned field")

    views = manifest.get("views", [])
    view_names = [view["name"] for view in views]
    if len(views) != 8:
        findings.append("Project OS must expose exactly eight views plus Pulse")
    if len(view_names) != len(set(view_names)):
        findings.append("view names must be unique")
    available_fields = set(names) | RESERVED_FIELD_NAMES
    for view in views:
        if view.get("layout") not in LAYOUTS:
            findings.append(f"{view.get('name')}: unsupported layout")
        visible = view.get("fields", [])
        if len(visible) != len(set(visible)):
            findings.append(f"{view.get('name')}: visible fields must be unique")
        references = list(visible)
        references.extend(
            value
            for key in ("group_by", "column_by", "start", "target")
            if (value := view.get(key))
        )
        markers = view.get("markers")
        if isinstance(markers, str):
            references.append(markers)
        elif isinstance(markers, list):
            references.extend(markers)
        for sort in view.get("sort", []):
            references.append(sort.get("field"))
            if sort.get("direction") not in {"asc", "desc"}:
                findings.append(
                    f"{view.get('name')}: invalid sort direction"
                )
        missing = sorted(
            {
                reference
                for reference in references
                if reference and reference not in available_fields
            }
        )
        if missing:
            findings.append(
                f"{view.get('name')}: unknown field references {missing}"
            )
    insights = manifest.get("insights", [])
    insight_names = [insight["name"] for insight in insights]
    if len(insights) > 5:
        findings.append("Pulse allows at most five focused Insights charts")
    if len(insight_names) != len(set(insight_names)):
        findings.append("Insight names must be unique")
    for insight in insights:
        if insight.get("chart") != "BAR":
            findings.append(f"{insight.get('name')}: unsupported chart")
        references = [
            insight.get("x"),
            insight.get("group_by"),
        ]
        missing = sorted(
            {
                reference
                for reference in references
                if reference and reference not in available_fields
            }
        )
        if missing:
            findings.append(
                f"{insight.get('name')}: unknown field references {missing}"
            )
    if manifest.get("identity", {}).get("destructive_rebuild") != "forbidden":
        findings.append("destructive rebuild must be forbidden")
    if manifest.get("identity", {}).get("unknown_items") != "quarantine":
        findings.append("unknown items must be quarantined")

    try:
        normalized = timeline_items(timeline)
    except (KeyError, TypeError, ValueError) as error:
        findings.append(f"timeline normalization failed: {error}")
        normalized = []
    identities = [item.ssot_id for item in normalized]
    if len(identities) != len(set(identities)):
        findings.append("normalized SSOT IDs must be unique")
    for item in normalized:
        if item.fields["Item type"] == ITEM_GATE:
            for date_field in ("When", "Start", "Target"):
                if item.fields.get(date_field):
                    findings.append(
                        f"{item.ssot_id}: a gate cannot carry {date_field}"
                    )
        for field_name, value in item.fields.items():
            definition = field_definitions.get(field_name)
            if not definition or definition.get("type") != "SINGLE_SELECT":
                continue
            options = {
                option[0] for option in definition.get("options", [])
            }
            if value not in options:
                findings.append(
                    f"{item.ssot_id}: {field_name} value {value!r} "
                    "is absent from the manifest"
                )
    return findings


def live_findings(
    client: GitHub, manifest: dict[str, Any]
) -> list[str]:
    definition = manifest["project"]
    project = load_project(
        client, definition["organization"], definition["number"]
    )
    findings: list[str] = []
    if project["title"] != definition["title"]:
        findings.append("live project title differs from the contract")
    live_fields = project_fields(client, project["id"])
    for field in manifest["fields"]:
        current = live_fields.get(field["name"])
        if current is None:
            findings.append(f"live field missing: {field['name']}")
            continue
        if current.get("dataType") != field["type"]:
            findings.append(
                f"live field type drift: {field['name']} "
                f"{current.get('dataType')} != {field['type']}"
            )
        if (
            field["type"] == "SINGLE_SELECT"
            and field.get("writer") != "human"
        ):
            expected_options = [
                option[0] for option in field.get("options", [])
            ]
            actual_options = [
                option["name"] for option in current.get("options", [])
            ]
            if actual_options != expected_options:
                findings.append(
                    f"live field options drift: {field['name']} "
                    f"{actual_options} != {expected_options}"
                )
    actual_views = views_snapshot(
        client, definition["organization"], definition["number"]
    )
    # GitHub returns views in creation order, not their saved tab order. The
    # public API therefore proves membership and layout, while browser QA owns
    # the visual ordering contract.
    actual_pairs = sorted(
        (view["name"], view["layout"]) for view in actual_views
    )
    expected_pairs = sorted(
        (view["name"], LAYOUTS[view["layout"]]) for view in manifest["views"]
    )
    if actual_pairs != expected_pairs:
        findings.append(
            f"live views differ: expected {expected_pairs}, found {actual_pairs}"
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    arguments = argparse.ArgumentParser()
    arguments.add_argument(
        "--offline",
        action="store_true",
        help="verify files only, without GitHub",
    )
    values = arguments.parse_args(argv)
    manifest = load(ROOT / "project" / "project-os.yaml")
    timeline = load(ROOT / "timeline" / "timeline.yaml")
    findings = offline_findings(manifest, timeline)
    if not values.offline:
        token = os.environ.get("BOARD_PROJECT_TOKEN", "")
        if not token:
            print("project verify: BOARD_PROJECT_TOKEN is not set", file=sys.stderr)
            return 2
        try:
            findings.extend(live_findings(GitHub(token), manifest))
        except GitHubError as error:
            print(f"project verify: {error}", file=sys.stderr)
            return 2
    if findings:
        for finding in findings:
            print(f"✗ {finding}")
        return 1
    scope = "offline contract" if values.offline else "contract and live Project"
    print(f"✓ Nika Project OS · {scope} · clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
