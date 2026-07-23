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
from project_os.model import timeline_items  # noqa: E402


VALID_WRITERS = {"projector", "timeline", "github", "human"}
LAYOUTS = {
    "TABLE": "TABLE_LAYOUT",
    "BOARD": "BOARD_LAYOUT",
    "ROADMAP": "ROADMAP_LAYOUT",
}


def load(path: pathlib.Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def offline_findings(
    manifest: dict[str, Any], timeline: dict[str, Any]
) -> list[str]:
    findings: list[str] = []
    if manifest.get("schema_version") != 2:
        findings.append("project-os schema_version must be 2")
    names = [field["name"] for field in manifest.get("fields", [])]
    if len(names) != len(set(names)):
        findings.append("Project field names must be unique")
    for field in manifest.get("fields", []):
        if field.get("writer") not in VALID_WRITERS:
            findings.append(f"{field.get('name')}: invalid writer")
        if field.get("type") == "SINGLE_SELECT":
            options = [option[0] for option in field.get("options", [])]
            if not options or len(options) != len(set(options)):
                findings.append(
                    f"{field.get('name')}: select options must be non-empty and unique"
                )
    views = manifest.get("views", [])
    view_names = [view["name"] for view in views]
    if len(views) > 8:
        findings.append("Project OS allows at most eight Project views plus Pulse")
    if len(view_names) != len(set(view_names)):
        findings.append("view names must be unique")
    for view in views:
        if view.get("layout") not in LAYOUTS:
            findings.append(f"{view.get('name')}: unsupported layout")
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
        if item.fields["Type"] == "Gate":
            for date_field in ("When", "Start", "Target"):
                if item.fields.get(date_field):
                    findings.append(
                        f"{item.ssot_id}: a gate cannot carry {date_field}"
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
    actual_views = views_snapshot(
        client, definition["organization"], definition["number"]
    )
    actual_pairs = [(view["name"], view["layout"]) for view in actual_views]
    expected_pairs = [
        (view["name"], LAYOUTS[view["layout"]]) for view in manifest["views"]
    ]
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
