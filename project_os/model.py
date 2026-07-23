"""Pure model and normalization functions for Nika Project OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


ORG = "supernovae-st"
MARKER_PREFIX = "nika-project-os:ssot:"
STAGE_GATE = "gate · conditions open"
STAGE_SHIPPED = "shipped · in the record"
STAGE_WORK = "work · active"
STAGE_REVIEW = "review · integrating"
STAGE_RELEASE = "release · published"
ERA_AHEAD = "◇ ahead"
ERA_LABEL = {
    "exploration": "✧ exploration",
    "brouillon": "✎ brouillon",
    "diamond": "◆ diamond",
}
PROVEN_CLASSES = {
    "crates-io",
    "github-release",
    "github-commit",
    "github-pr",
    "git-tag",
}
RECORDED_CLASSES = {"scorecard"}


@dataclass(frozen=True)
class DesiredItem:
    """One normalized Project item.

    `content_id` links a real Issue or Pull Request. A missing content id means
    the Project owns a draft item. Only draft items and projected gate issues
    have managed content.
    """

    ssot_id: str
    title: str
    body: str
    fields: dict[str, Any]
    content_id: str | None = None
    content_kind: str = "DraftIssue"
    source_url: str | None = None
    managed_content: bool = False
    legacy_titles: tuple[str, ...] = field(default_factory=tuple)


def marker(ssot_id: str) -> str:
    return f"<!-- {MARKER_PREFIX}{ssot_id} -->"


def extract_marker(body: str | None) -> str | None:
    if not body:
        return None
    needle = f"<!-- {MARKER_PREFIX}"
    start = body.find(needle)
    if start < 0:
        return None
    end = body.find(" -->", start)
    if end < 0:
        return None
    value = body[start + len(needle):end].strip()
    return value or None


def era_of(entry: dict[str, Any]) -> str:
    if entry.get("era"):
        return ERA_LABEL[entry["era"]]
    date = str(entry["date"])
    if date < "2026-01-01":
        return ERA_LABEL["exploration"]
    if date < "2026-04-13":
        return ERA_LABEL["brouillon"]
    return ERA_LABEL["diamond"]


def proof_of(entry: dict[str, Any]) -> str:
    evidence_class = (entry.get("evidence") or {}).get("class", "")
    if evidence_class in PROVEN_CLASSES:
        return "✓ proven"
    if evidence_class in RECORDED_CLASSES:
        return "· recorded"
    return "○ labeled"


def proof_url(entry: dict[str, Any]) -> str | None:
    evidence = entry.get("evidence") or {}
    repo = evidence.get("repo")
    evidence_class = evidence.get("class", "")
    if repo and evidence.get("tag"):
        return f"https://github.com/{repo}/releases/tag/{evidence['tag']}"
    if repo and evidence.get("sha"):
        return f"https://github.com/{repo}/commit/{evidence['sha']}"
    if repo and evidence.get("pr"):
        return f"https://github.com/{repo}/pull/{evidence['pr']}"
    if evidence_class == "crates-io" and entry.get("version"):
        return f"https://crates.io/crates/nika/{entry['version']}"
    return None


def when_of(entry: dict[str, Any]) -> str:
    date = str(entry["date"])
    return f"{date}-15" if len(date) == 7 else date


def title_of(entry: dict[str, Any]) -> str:
    if entry.get("title") and entry.get("version"):
        return f"v{entry['version']} · {entry['title']}"
    if entry.get("version"):
        return f"v{entry['version']}"
    return entry["title"]


def entry_body(entry: dict[str, Any], ssot_id: str) -> str:
    lines = [marker(ssot_id)]
    if entry.get("detail"):
        lines.extend(["", entry["detail"]])
    url = proof_url(entry)
    evidence_class = (entry.get("evidence") or {}).get("class", "evidence")
    proof = f"Proof class: {evidence_class}"
    proof += f" · {url}" if url else " (labeled, never dressed as proof)"
    lines.extend(["", proof])
    if entry.get("precision") == "month":
        lines.append("Date carries month precision; the roadmap seats it mid-month.")
    return "\n".join(lines).strip()


def gate_body(gate: dict[str, Any], ssot_id: str) -> str:
    lines = [
        f"<!-- projected:gate:{gate['id']} -->",
        marker(ssot_id),
        "**A forward gate of the record: conditions, never dates.**",
        "",
    ]
    lines.extend(f"- [ ] {condition}" for condition in gate.get("conditions", []))
    if gate.get("note"):
        lines.extend(["", f"_{gate['note']}_"])
    lines.extend(
        [
            "",
            "SSOT: [`timeline/timeline.yaml`](https://github.com/supernovae-st/nika-spec/blob/main/timeline/timeline.yaml) · rendered: https://nika.sh/timeline#gates",
            "",
            "_Projected from the record; hand edits are overwritten. When this gate flips, the record gains a dated proven entry and this issue closes itself._",
        ]
    )
    return "\n".join(lines)


def certainty_for_proof(proof: str) -> str:
    if proof == "✓ proven":
        return "Proven"
    if proof == "○ labeled":
        return "Unknown"
    return "Committed"


def timeline_items(doc: dict[str, Any]) -> list[DesiredItem]:
    items: list[DesiredItem] = []
    entries = sorted(doc.get("entries", []), key=lambda item: str(item["date"]))
    for order, entry in enumerate(entries, start=1):
        ssot_id = f"timeline:entry:{entry['id']}"
        title = title_of(entry)
        proof = proof_of(entry)
        when = when_of(entry)
        is_release = entry.get("type") == "release"
        fields = {
            "SSOT ID": ssot_id,
            "Item type": "Release" if is_release else "Record",
            "Stage": STAGE_SHIPPED,
            "Era": era_of(entry),
            "Kind": "release" if is_release else "milestone",
            "Proof": proof,
            "Status": "Done",
            "When": when,
            "Order": order,
            "Pole": "08 · chronicle" if entry.get("component") is None else "02 · engineering",
            "Horizon": "Record",
            "Certainty": certainty_for_proof(proof),
            "Start": when,
            "Target": when,
            "Release": f"v{entry['version']}" if entry.get("version") else None,
            "Block state": "Clear",
            "Projection state": "Synced",
            "Review state": "Not applicable",
            "CI state": "Not applicable",
        }
        items.append(
            DesiredItem(
                ssot_id=ssot_id,
                title=title,
                body=entry_body(entry, ssot_id),
                fields=fields,
                managed_content=True,
                legacy_titles=(title,),
            )
        )
    offset = len(items)
    for index, gate in enumerate(doc.get("gates", []), start=1):
        ssot_id = f"timeline:gate:{gate['id']}"
        title = f"gate · {gate['title']}"
        fields = {
            "SSOT ID": ssot_id,
            "Item type": "Gate",
            "Stage": STAGE_GATE,
            "Era": ERA_AHEAD,
            "Kind": "gate",
            "Proof": "◌ pending",
            "Status": "Todo",
            "Order": offset + index,
            "Pole": "01 · product",
            "Horizon": "Next" if index == 1 else "Later",
            "Certainty": "Committed",
            "Release": gate["title"].split(" · ", 1)[0],
            "Block state": "Clear",
            "Projection state": "Synced",
            "Review state": "Not applicable",
            "CI state": "Not applicable",
        }
        items.append(
            DesiredItem(
                ssot_id=ssot_id,
                title=title,
                body=gate_body(gate, ssot_id),
                fields=fields,
                content_kind="Issue",
                managed_content=True,
                legacy_titles=(title,),
            )
        )
    return items


def label_names(item: dict[str, Any]) -> set[str]:
    return {label["name"].lower() for label in item.get("labels", [])}


def pole_from_labels(labels: Iterable[str]) -> str:
    mapping = {
        "product": "01 · product",
        "engineering": "02 · engineering",
        "growth": "03 · growth",
        "identity": "04 · identity",
        "community": "05 · community",
        "revenue": "06 · revenue",
        "operations": "07 · operations",
        "chronicle": "08 · chronicle",
        "data": "09 · data",
    }
    for label in labels:
        if label.startswith("pole/") and label[5:] in mapping:
            return mapping[label[5:]]
    return "02 · engineering"


def accountable(item: dict[str, Any]) -> str | None:
    assignees = [actor["login"] for actor in item.get("assignees", [])]
    if assignees:
        return ", ".join(sorted(assignees))
    user = item.get("user") or {}
    return user.get("login")


def block_state(blocked_by: int | None, blocking: int | None) -> str:
    if blocked_by is None or blocking is None:
        return "Unknown"
    if blocked_by and blocking:
        return "Both"
    if blocked_by:
        return "Blocked"
    if blocking:
        return "Blocking"
    return "Clear"


def issue_item(
    repo: str,
    issue: dict[str, Any],
    blocked_by: int | None,
    blocking: int | None,
) -> DesiredItem:
    ssot_id = f"github:issue:{ORG}/{repo}#{issue['number']}"
    milestone = issue.get("milestone") or {}
    target = (milestone.get("due_on") or "")[:10] or None
    fields = {
        "SSOT ID": ssot_id,
        "Item type": "Issue",
        "Stage": STAGE_WORK,
        "Era": ERA_AHEAD,
        "Kind": "issue",
        "Proof": "◌ pending",
        "Status": "In progress" if issue.get("assignees") else "Todo",
        "Pole": pole_from_labels(label_names(issue)),
        "Horizon": "Now" if issue.get("assignees") else "Next",
        "Certainty": "Committed",
        "Start": issue.get("created_at", "")[:10] or None,
        "Target": target,
        "Release": milestone.get("title"),
        "Accountable": accountable(issue),
        "Block state": block_state(blocked_by, blocking),
        "Projection state": "Synced",
        "Review state": "Not applicable",
        "CI state": "Not applicable",
    }
    return DesiredItem(
        ssot_id=ssot_id,
        title=issue["title"],
        body=issue.get("body") or "",
        fields=fields,
        content_id=issue["node_id"],
        content_kind="Issue",
        source_url=issue["html_url"],
    )


def review_state(pull: dict[str, Any], reviews: list[dict[str, Any]]) -> str:
    if pull.get("draft"):
        return "Draft"
    latest: dict[str, str] = {}
    for review in reviews:
        user = (review.get("user") or {}).get("login")
        state = review.get("state")
        if user and state:
            latest[user] = state
    states = set(latest.values())
    if "CHANGES_REQUESTED" in states:
        return "Changes requested"
    if "APPROVED" in states:
        return "Approved"
    return "Review needed"


def ci_state(checks: list[dict[str, Any]] | None) -> str:
    if checks is None:
        return "Unknown"
    if not checks:
        return "Unknown"
    if any(check.get("status") != "completed" for check in checks):
        return "Pending"
    bad = {
        "action_required",
        "cancelled",
        "failure",
        "stale",
        "startup_failure",
        "timed_out",
    }
    if any(check.get("conclusion") in bad for check in checks):
        return "Red"
    return "Green"


def pull_request_item(
    repo: str,
    pull: dict[str, Any],
    reviews: list[dict[str, Any]],
    checks: list[dict[str, Any]] | None,
) -> DesiredItem:
    ssot_id = f"github:pr:{ORG}/{repo}#{pull['number']}"
    milestone = pull.get("milestone") or {}
    target = (milestone.get("due_on") or "")[:10] or None
    fields = {
        "SSOT ID": ssot_id,
        "Item type": "Pull request",
        "Stage": STAGE_REVIEW,
        "Era": ERA_AHEAD,
        "Kind": "pull-request",
        "Proof": "◌ pending",
        "Status": "In progress",
        "Pole": pole_from_labels(label_names(pull)),
        "Horizon": "Now",
        "Certainty": "Committed",
        "Start": pull.get("created_at", "")[:10] or None,
        "Target": target,
        "Release": milestone.get("title"),
        "Accountable": accountable(pull),
        "Block state": "Clear",
        "Projection state": "Synced",
        "Review state": review_state(pull, reviews),
        "CI state": ci_state(checks),
    }
    return DesiredItem(
        ssot_id=ssot_id,
        title=pull["title"],
        body=pull.get("body") or "",
        fields=fields,
        content_id=pull["node_id"],
        content_kind="PullRequest",
        source_url=pull["html_url"],
    )


def release_item(repo: str, release: dict[str, Any], order: int) -> DesiredItem:
    tag = release["tag_name"]
    ssot_id = f"github:release:{ORG}/{repo}@{tag}"
    published = (release.get("published_at") or release.get("created_at") or "")[:10]
    title = release.get("name") or tag
    body = "\n".join(
        [
            marker(ssot_id),
            "",
            f"Published release: {release['html_url']}",
            "",
            "_Projected from the GitHub release. Edit the release, never this card._",
        ]
    )
    fields = {
        "SSOT ID": ssot_id,
        "Item type": "Release",
        "Stage": STAGE_RELEASE,
        "Era": ERA_LABEL["diamond"],
        "Kind": "release",
        "Proof": "✓ proven",
        "Status": "Done",
        "When": published or None,
        "Order": order,
        "Pole": "02 · engineering",
        "Horizon": "Record",
        "Certainty": "Proven",
        "Start": published or None,
        "Target": published or None,
        "Release": tag,
        "Block state": "Clear",
        "Projection state": "Synced",
        "Review state": "Not applicable",
        "CI state": "Not applicable",
    }
    return DesiredItem(
        ssot_id=ssot_id,
        title=title,
        body=body,
        fields=fields,
        source_url=release["html_url"],
        managed_content=True,
        legacy_titles=(title,),
    )


def timeline_release_keys(doc: dict[str, Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for entry in doc.get("entries", []):
        evidence = entry.get("evidence") or {}
        repo = evidence.get("repo")
        tag = evidence.get("tag")
        if evidence.get("class") == "github-release" and repo and tag:
            keys.add((repo, tag))
    return keys


def published_sort_key(release: dict[str, Any]) -> datetime:
    value = release.get("published_at") or release.get("created_at")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
