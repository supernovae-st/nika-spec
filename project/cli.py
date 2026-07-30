"""Command line entry point for Nika Project OS."""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from typing import Any

import yaml

from .github import (
    GitHub,
    GitHubError,
    ensure_fields,
    ensure_repository_links,
    load_project,
    project_fields,
    reconcile,
    update_project_metadata,
)
from .sources import desired_from_sources


ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "project" / "project-os.yaml"
TIMELINE_PATH = ROOT / "timeline" / "timeline.yaml"


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def render_readme(manifest: dict[str, Any]) -> str:
    fields = manifest["fields"] + manifest.get("built_in_fields", [])
    views = manifest["views"]
    insights = manifest["insights"]
    sources = manifest["sources"]
    signal = next(field for field in fields if field["name"] == "Signal")
    lines = [
        "## 🦋 Nika Project OS",
        "",
        "**One public operating surface. Zero second backlog.** "
        "The record, issues, pull requests and releases stay authoritative in "
        "their own sources. Hand edits to projector-owned fields are repaired "
        "on the next reconciliation.",
        "",
        "### 🧬 The SSOT map",
        "",
        "| Source | Owns |",
        "|---|---|",
    ]
    for name, source in sources.items():
        owns = " · ".join(source["owns"])
        lines.append(f"| `{name}` | {owns} |")
    lines.extend(
        [
            "",
            "### 🪞 Eight lenses, one truth",
            "",
            "| Lens | Layout | Purpose |",
            "|---|---|---|",
        ]
    )
    for view in views:
        lines.append(
            f"| **{view['name']}** | {view['layout'].title()} | {view['purpose']} |"
        )
    lines.extend(
        [
            "",
            "### 📈 Pulse",
            "",
            "| Chart | X axis | Group |",
            "|---|---|---|",
        ]
    )
    for insight in insights:
        lines.append(
            f"| **{insight['name']}** | `{insight['x']}` | "
            f"`{insight.get('group_by', 'none')}` |"
        )
    lines.extend(
        [
            "",
            "### 🚨 Read Signal first",
            "",
            "`Signal` is derived attention. It never replaces the human-owned "
            "`Priority` or `Effort` fields.",
            "",
            "| Signal | Meaning |",
            "|---|---|",
        ]
    )
    for option in signal["options"]:
        lines.append(f"| **{option[0]}** | {option[2]} |")
    lines.extend(
        [
            "",
            "### 🎛 The field contract",
            "",
            "| Field | Writer |",
            "|---|---|",
        ]
    )
    for field in fields:
        lines.append(f"| **{field['name']}** | `{field['writer']}` |")
    lines.extend(
        [
            "",
            "### 🔒 Projection laws",
            "",
            "- Reconciliation is incremental. The projector never wipes the Project.",
            "- Unknown items are quarantined, not deleted.",
            "- Removed managed items are retained as orphans, preserving Insights history.",
            "- Gates carry conditions, never dates.",
            "- Every projector-owned classification carries one stable semantic sigil.",
            "- Priority and Effort remain explicit human decisions.",
            "- Views and Insights are browser-only GitHub state. Their exact recipe is versioned in [`project/project-os.yaml`](https://github.com/supernovae-st/nika-spec/blob/main/project/project-os.yaml).",
            "",
            "📜 Record: [`timeline/timeline.yaml`](https://github.com/supernovae-st/nika-spec/blob/main/timeline/timeline.yaml) · rendered timeline: https://nika.sh/timeline",
        ]
    )
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Reconcile Nika Project OS")
    mode = value.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="apply the incremental repair",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing (the default)",
    )
    return value


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    apply = arguments.apply
    token = os.environ.get("BOARD_PROJECT_TOKEN", "")
    if not token:
        print("BOARD_PROJECT_TOKEN is not set", file=sys.stderr)
        return 2

    manifest = load_yaml(MANIFEST_PATH)
    timeline = load_yaml(TIMELINE_PATH)
    project_definition = manifest["project"]
    field_definitions = (
        manifest["fields"] + manifest.get("built_in_fields", [])
    )
    client = GitHub(token)
    try:
        project = load_project(
            client,
            project_definition["organization"],
            project_definition["number"],
        )
        if project["title"] != project_definition["title"]:
            raise GitHubError(
                f"project title mismatch: {project['title']!r}, "
                f"expected {project_definition['title']!r}"
            )

        setup_actions: list[str] = []
        if apply:
            fields, field_actions = ensure_fields(
                client, project["id"], manifest["fields"]
            )
            setup_actions.extend(field_actions)
            setup_actions.extend(
                ensure_repository_links(
                    client,
                    project["id"],
                    project_definition["organization"],
                    project_definition["number"],
                    project_definition["repositories"],
                )
            )
            setup_actions.extend(
                update_project_metadata(
                    client,
                    project,
                    project_definition,
                    render_readme(manifest),
                )
            )
        else:
            fields = project_fields(client, project["id"])
            for definition in manifest["fields"]:
                if definition["name"] not in fields:
                    setup_actions.append(f"field missing: {definition['name']}")

        desired, source_actions = desired_from_sources(
            client,
            manifest,
            timeline,
            apply_gate_issues=apply,
        )
        item_actions = reconcile(
            client,
            project["id"],
            desired,
            fields,
            field_definitions,
            apply=apply,
        )
    except (GitHubError, OSError, ValueError) as error:
        print(f"project-os: {error}", file=sys.stderr)
        return 2

    actions = setup_actions + source_actions + item_actions
    if actions:
        verb = "applied" if apply else "drift"
        print(f"project-os · {verb} · {len(actions)} action(s)")
        for action in actions:
            print(f"  · {action}")
    else:
        print(f"project-os · quiet · {len(desired)} items already synced")
    return 0 if apply or not actions else 1


if __name__ == "__main__":
    raise SystemExit(main())
