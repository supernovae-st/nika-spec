"""Source adapters for timeline, GitHub Issues, pull requests and releases."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from .github import GitHub
from .model import (
    DesiredItem,
    ORG,
    gate_body,
    issue_item,
    published_sort_key,
    pull_request_item,
    release_item,
    timeline_items,
    timeline_release_keys,
)


GATE_LABEL = {
    "name": "gate",
    "color": "f0b429",
    "description": "a forward gate of the record · conditions, never dates",
}


def slug_match(gate_title: str, milestone_title: str) -> bool:
    normalized = milestone_title.lower().removeprefix("gate · ").strip()
    if normalized == gate_title.strip().lower():
        return True
    head = gate_title.split("·")[0].strip().lower()
    return head[:18] in normalized and not normalized.startswith(head + "-")


def _gate_marker(body: str | None) -> str | None:
    match = re.search(r"<!-- projected:gate:([a-z0-9-]+) -->", body or "")
    return match.group(1) if match else None


def sync_gate_issues(
    client: GitHub,
    timeline: dict[str, Any],
    repositories: list[str],
    *,
    apply: bool,
) -> tuple[dict[str, str], list[str]]:
    """Return gate id to GitHub node id and optionally repair gate issues."""
    milestones = {
        repo: client.pages(f"/repos/{ORG}/{repo}/milestones?state=open") or []
        for repo in repositories
    }
    existing: dict[str, tuple[str, dict[str, Any]]] = {}
    changes: list[str] = []
    for repo in repositories:
        if apply:
            created = client.rest(
                "POST",
                f"/repos/{ORG}/{repo}/labels",
                GATE_LABEL,
                optional=True,
            )
            if created:
                changes.append(f"gate label created: {repo}")
        issues = client.pages(
            f"/repos/{ORG}/{repo}/issues?labels=gate&state=open"
        ) or []
        for issue in issues:
            gate_id = _gate_marker(issue.get("body"))
            if gate_id:
                existing[gate_id] = (repo, issue)

    nodes: dict[str, str] = {}
    for gate in timeline.get("gates", []):
        gate_id = gate["id"]
        ssot_id = f"timeline:gate:{gate_id}"
        title = f"gate · {gate['title']}"
        body = gate_body(gate, ssot_id)
        seat_repo, milestone = next(
            (
                (repo, candidate)
                for repo in repositories
                for candidate in milestones[repo]
                if slug_match(gate["title"], candidate["title"])
            ),
            (repositories[0], None),
        )
        current = existing.pop(gate_id, None)
        if current:
            repo, issue = current
            nodes[gate_id] = issue["node_id"]
            patch: dict[str, Any] = {}
            if issue["title"] != title:
                patch["title"] = title
            if (issue.get("body") or "") != body:
                patch["body"] = body
            if (
                milestone
                and repo == seat_repo
                and (issue.get("milestone") or {}).get("number")
                != milestone["number"]
            ):
                patch["milestone"] = milestone["number"]
            if patch:
                changes.append(f"gate issue update: {repo}#{issue['number']}")
                if apply:
                    updated = client.rest(
                        "PATCH",
                        f"/repos/{ORG}/{repo}/issues/{issue['number']}",
                        patch,
                    )
                    nodes[gate_id] = updated["node_id"]
            continue

        changes.append(f"gate issue open: {seat_repo} · {gate_id}")
        if not apply:
            continue
        payload: dict[str, Any] = {
            "title": title,
            "body": body,
            "labels": ["gate"],
        }
        if milestone:
            payload["milestone"] = milestone["number"]
        created = client.rest(
            "POST", f"/repos/{ORG}/{seat_repo}/issues", payload
        )
        nodes[gate_id] = created["node_id"]

    for gate_id, (repo, issue) in existing.items():
        changes.append(f"gate issue close: {repo}#{issue['number']} · {gate_id}")
        if not apply:
            continue
        client.rest(
            "POST",
            f"/repos/{ORG}/{repo}/issues/{issue['number']}/comments",
            {
                "body": "The gate flipped: the record gained its dated, proven entry. Closing the projection."
            },
        )
        client.rest(
            "PATCH",
            f"/repos/{ORG}/{repo}/issues/{issue['number']}",
            {"state": "closed"},
        )
    return nodes, changes


def _dependency_count(
    client: GitHub,
    repo: str,
    issue_number: int,
    direction: str,
) -> int | None:
    values = client.pages(
        f"/repos/{ORG}/{repo}/issues/{issue_number}/dependencies/{direction}",
        optional=True,
    )
    if values is None:
        return None
    return sum(1 for value in values if value.get("state") == "open")


def issue_items(
    client: GitHub,
    repositories: list[str],
    excluded_labels: set[str],
) -> list[DesiredItem]:
    output: list[DesiredItem] = []
    for repo in repositories:
        issues = client.pages(f"/repos/{ORG}/{repo}/issues?state=open") or []
        for issue in issues:
            if "pull_request" in issue:
                continue
            labels = {label["name"].lower() for label in issue.get("labels", [])}
            if labels & excluded_labels:
                continue
            blocked_by = _dependency_count(
                client, repo, issue["number"], "blocked_by"
            )
            blocking = _dependency_count(
                client, repo, issue["number"], "blocking"
            )
            output.append(issue_item(repo, issue, blocked_by, blocking))
    return output


def pull_request_items(
    client: GitHub, repositories: list[str]
) -> list[DesiredItem]:
    output: list[DesiredItem] = []
    for repo in repositories:
        pulls = client.pages(f"/repos/{ORG}/{repo}/pulls?state=open") or []
        for pull in pulls:
            reviews = client.pages(
                f"/repos/{ORG}/{repo}/pulls/{pull['number']}/reviews",
                optional=True,
            )
            checks_response = client.rest(
                "GET",
                f"/repos/{ORG}/{repo}/commits/{pull['head']['sha']}/check-runs?per_page=100",
                optional=True,
            )
            checks = (
                checks_response.get("check_runs", [])
                if checks_response is not None
                else None
            )
            output.append(
                pull_request_item(repo, pull, reviews or [], checks)
            )
    return output


def release_items(
    client: GitHub,
    repositories: list[str],
    limit_per_repository: int,
    timeline: dict[str, Any],
    order_start: int,
) -> list[DesiredItem]:
    represented = timeline_release_keys(timeline)
    releases: list[tuple[str, dict[str, Any]]] = []
    for repo in repositories:
        values = client.pages(f"/repos/{ORG}/{repo}/releases") or []
        for release in values[:limit_per_repository]:
            if release.get("draft"):
                continue
            if (f"{ORG}/{repo}", release["tag_name"]) in represented:
                continue
            releases.append((repo, release))
    releases.sort(key=lambda value: published_sort_key(value[1]))
    return [
        release_item(repo, release, order_start + index)
        for index, (repo, release) in enumerate(releases, start=1)
    ]


def desired_from_sources(
    client: GitHub,
    manifest: dict[str, Any],
    timeline: dict[str, Any],
    *,
    apply_gate_issues: bool,
) -> tuple[list[DesiredItem], list[str]]:
    project_repositories = manifest["project"]["repositories"]
    gate_nodes, gate_actions = sync_gate_issues(
        client,
        timeline,
        project_repositories,
        apply=apply_gate_issues,
    )
    desired = []
    for item in timeline_items(timeline):
        if item.ssot_id.startswith("timeline:gate:"):
            gate_id = item.ssot_id.rsplit(":", 1)[1]
            item = replace(item, content_id=gate_nodes.get(gate_id))
        desired.append(item)

    issue_source = manifest["sources"]["github_issues"]
    desired.extend(
        issue_items(
            client,
            issue_source["repositories"],
            {value.lower() for value in issue_source.get("exclude_labels", [])},
        )
    )
    pull_source = manifest["sources"]["github_pull_requests"]
    desired.extend(pull_request_items(client, pull_source["repositories"]))
    release_source = manifest["sources"]["github_releases"]
    desired.extend(
        release_items(
            client,
            release_source["repositories"],
            release_source["limit_per_repository"],
            timeline,
            order_start=len(desired) + 100,
        )
    )
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in desired:
        if item.ssot_id in seen:
            duplicates.append(item.ssot_id)
        seen.add(item.ssot_id)
    if duplicates:
        raise ValueError(f"duplicate normalized SSOT IDs: {sorted(duplicates)}")
    return desired, gate_actions
