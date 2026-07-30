"""Pure model and normalization functions for Nika Project OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


ORG = "supernovae-st"
MARKER_PREFIX = "nika-project-os:ssot:"
ITEM_RECORD = "📜 Record"
ITEM_GATE = "🚪 Gate"
ITEM_ISSUE = "🧩 Issue"
ITEM_PULL_REQUEST = "🔀 Pull request"
ITEM_RELEASE = "📦 Release"
STAGE_GATE = "🚪 gate · conditions open"
STAGE_SHIPPED = "✅ shipped · in the record"
STAGE_WORK = "🛠 work · active"
STAGE_REVIEW = "🔍 review · integrating"
STAGE_RELEASE = "📦 release · published"
ERA_AHEAD = "◇ ahead"
ERA_LABEL = {
    "exploration": "✧ exploration",
    "brouillon": "✎ brouillon",
    "diamond": "◆ diamond",
}
KIND_RELEASE = "📦 release"
KIND_MILESTONE = "◆ milestone"
KIND_GATE = "🚪 gate"
KIND_ISSUE = "🧩 issue"
KIND_PULL_REQUEST = "🔀 pull request"
POLE_PRODUCT = "01 · 🧭 product"
POLE_ENGINEERING = "02 · ⚙ engineering"
POLE_GROWTH = "03 · 🌱 growth"
POLE_IDENTITY = "04 · ✦ identity"
POLE_COMMUNITY = "05 · 🤝 community"
POLE_REVENUE = "06 · ◈ revenue"
POLE_OPERATIONS = "07 · 🧰 operations"
POLE_CHRONICLE = "08 · 📜 chronicle"
POLE_DATA = "09 · 📊 data"
HORIZON_NOW = "● now"
HORIZON_NEXT = "→ next"
HORIZON_LATER = "⋯ later"
HORIZON_RECORD = "✓ record"
CERTAINTY_PROVEN = "✓ proven"
CERTAINTY_COMMITTED = "◆ committed"
CERTAINTY_UNKNOWN = "? unknown"
BLOCK_CLEAR = "✓ clear"
BLOCK_BLOCKED = "⛓ blocked"
BLOCK_BLOCKING = "⇢ blocking"
BLOCK_BOTH = "⛓ both"
BLOCK_UNKNOWN = "? unknown"
PROJECTION_SYNCED = "✓ synced"
PROJECTION_DRIFTED = "△ drifted"
PROJECTION_ORPHANED = "◌ orphaned"
PROJECTION_QUARANTINED = "◇ quarantined"
REVIEW_NOT_APPLICABLE = "· not applicable"
REVIEW_DRAFT = "✎ draft"
REVIEW_NEEDED = "◌ review needed"
REVIEW_APPROVED = "✓ approved"
REVIEW_CHANGES_REQUESTED = "! changes requested"
CI_NOT_APPLICABLE = "· not applicable"
CI_PENDING = "◌ pending"
CI_GREEN = "✓ green"
CI_RED = "✗ red"
CI_UNKNOWN = "? unknown"
SIGNAL_ATTENTION = "🚨 attention"
SIGNAL_REVIEW = "👀 review"
SIGNAL_ACTIVE = "▶ active"
SIGNAL_QUEUED = "⏭ queued"
SIGNAL_READY = "✓ ready"
SIGNAL_SETTLED = "● settled"
STATUS_IN_PROGRESS = "In Progress"
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
        return CERTAINTY_PROVEN
    if proof == "○ labeled":
        return CERTAINTY_UNKNOWN
    return CERTAINTY_COMMITTED


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
            "Item type": ITEM_RELEASE if is_release else ITEM_RECORD,
            "Stage": STAGE_SHIPPED,
            "Era": era_of(entry),
            "Kind": KIND_RELEASE if is_release else KIND_MILESTONE,
            "Proof": proof,
            "Status": "Done",
            "When": when,
            "Order": order,
            "Pole": POLE_CHRONICLE if entry.get("component") is None else POLE_ENGINEERING,
            "Horizon": HORIZON_RECORD,
            "Certainty": certainty_for_proof(proof),
            "Start": when,
            "Target": when,
            "Release": f"v{entry['version']}" if entry.get("version") else None,
            "Block state": BLOCK_CLEAR,
            "Projection state": PROJECTION_SYNCED,
            "Review state": REVIEW_NOT_APPLICABLE,
            "CI state": CI_NOT_APPLICABLE,
            "Signal": SIGNAL_SETTLED,
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
            "Item type": ITEM_GATE,
            "Stage": STAGE_GATE,
            "Era": ERA_AHEAD,
            "Kind": KIND_GATE,
            "Proof": "◌ pending",
            "Status": "Todo",
            "Order": offset + index,
            "Pole": POLE_PRODUCT,
            "Horizon": HORIZON_NEXT if index == 1 else HORIZON_LATER,
            "Certainty": CERTAINTY_COMMITTED,
            "Release": gate["title"].split(" · ", 1)[0],
            "Block state": BLOCK_CLEAR,
            "Projection state": PROJECTION_SYNCED,
            "Review state": REVIEW_NOT_APPLICABLE,
            "CI state": CI_NOT_APPLICABLE,
            "Signal": SIGNAL_QUEUED,
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
        "product": POLE_PRODUCT,
        "engineering": POLE_ENGINEERING,
        "growth": POLE_GROWTH,
        "identity": POLE_IDENTITY,
        "community": POLE_COMMUNITY,
        "revenue": POLE_REVENUE,
        "operations": POLE_OPERATIONS,
        "chronicle": POLE_CHRONICLE,
        "data": POLE_DATA,
    }
    for label in labels:
        if label.startswith("pole/") and label[5:] in mapping:
            return mapping[label[5:]]
    return POLE_ENGINEERING


def accountable(
    item: dict[str, Any], *, include_author: bool = False
) -> str | None:
    assignees = [actor["login"] for actor in item.get("assignees", [])]
    if assignees:
        return ", ".join(sorted(assignees))
    if include_author:
        user = item.get("user") or {}
        return user.get("login")
    return None


def block_state(blocked_by: int | None, blocking: int | None) -> str:
    if blocked_by is None or blocking is None:
        return BLOCK_UNKNOWN
    if blocked_by and blocking:
        return BLOCK_BOTH
    if blocked_by:
        return BLOCK_BLOCKED
    if blocking:
        return BLOCK_BLOCKING
    return BLOCK_CLEAR


def issue_item(
    repo: str,
    issue: dict[str, Any],
    blocked_by: int | None,
    blocking: int | None,
) -> DesiredItem:
    ssot_id = f"github:issue:{ORG}/{repo}#{issue['number']}"
    milestone = issue.get("milestone") or {}
    target = (milestone.get("due_on") or "")[:10] or None
    dependency_state = block_state(blocked_by, blocking)
    has_owner = bool(issue.get("assignees"))
    fields = {
        "SSOT ID": ssot_id,
        "Item type": ITEM_ISSUE,
        "Stage": STAGE_WORK,
        "Era": ERA_AHEAD,
        "Kind": KIND_ISSUE,
        "Proof": "◌ pending",
        "Status": STATUS_IN_PROGRESS if has_owner else "Todo",
        "Pole": pole_from_labels(label_names(issue)),
        "Horizon": HORIZON_NOW if has_owner else HORIZON_NEXT,
        "Certainty": CERTAINTY_COMMITTED,
        "Start": issue.get("created_at", "")[:10] or None,
        "Target": target,
        "Release": milestone.get("title"),
        "Accountable": accountable(issue),
        "Block state": dependency_state,
        "Projection state": PROJECTION_SYNCED,
        "Review state": REVIEW_NOT_APPLICABLE,
        "CI state": CI_NOT_APPLICABLE,
        "Signal": (
            SIGNAL_ATTENTION
            if dependency_state in {BLOCK_BLOCKED, BLOCK_BOTH}
            else SIGNAL_ACTIVE if has_owner else SIGNAL_QUEUED
        ),
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
        return REVIEW_DRAFT
    latest: dict[str, str] = {}
    for review in reviews:
        user = (review.get("user") or {}).get("login")
        state = review.get("state")
        if user and state:
            latest[user] = state
    states = set(latest.values())
    if "CHANGES_REQUESTED" in states:
        return REVIEW_CHANGES_REQUESTED
    if "APPROVED" in states:
        return REVIEW_APPROVED
    return REVIEW_NEEDED


def ci_state(checks: list[dict[str, Any]] | None) -> str:
    if checks is None:
        return CI_UNKNOWN
    if not checks:
        return CI_UNKNOWN
    if any(check.get("status") != "completed" for check in checks):
        return CI_PENDING
    bad = {
        "action_required",
        "cancelled",
        "failure",
        "stale",
        "startup_failure",
        "timed_out",
    }
    if any(check.get("conclusion") in bad for check in checks):
        return CI_RED
    return CI_GREEN


def pull_request_signal(pull: dict[str, Any], review: str, ci: str) -> str:
    if review == REVIEW_CHANGES_REQUESTED or ci == CI_RED:
        return SIGNAL_ATTENTION
    if review == REVIEW_APPROVED and ci == CI_GREEN:
        return SIGNAL_READY
    if pull.get("draft"):
        return SIGNAL_ACTIVE
    return SIGNAL_REVIEW


def pull_request_item(
    repo: str,
    pull: dict[str, Any],
    reviews: list[dict[str, Any]],
    checks: list[dict[str, Any]] | None,
) -> DesiredItem:
    ssot_id = f"github:pr:{ORG}/{repo}#{pull['number']}"
    milestone = pull.get("milestone") or {}
    target = (milestone.get("due_on") or "")[:10] or None
    review = review_state(pull, reviews)
    ci = ci_state(checks)
    fields = {
        "SSOT ID": ssot_id,
        "Item type": ITEM_PULL_REQUEST,
        "Stage": STAGE_REVIEW,
        "Era": ERA_AHEAD,
        "Kind": KIND_PULL_REQUEST,
        "Proof": "◌ pending",
        "Status": STATUS_IN_PROGRESS,
        "Pole": pole_from_labels(label_names(pull)),
        "Horizon": HORIZON_NOW,
        "Certainty": CERTAINTY_COMMITTED,
        "Start": pull.get("created_at", "")[:10] or None,
        "Target": target,
        "Release": milestone.get("title"),
        "Accountable": accountable(pull, include_author=True),
        "Block state": BLOCK_CLEAR,
        "Projection state": PROJECTION_SYNCED,
        "Review state": review,
        "CI state": ci,
        "Signal": pull_request_signal(pull, review, ci),
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
        "Item type": ITEM_RELEASE,
        "Stage": STAGE_RELEASE,
        "Era": ERA_LABEL["diamond"],
        "Kind": KIND_RELEASE,
        "Proof": "✓ proven",
        "Status": "Done",
        "When": published or None,
        "Order": order,
        "Pole": POLE_ENGINEERING,
        "Horizon": HORIZON_RECORD,
        "Certainty": CERTAINTY_PROVEN,
        "Start": published or None,
        "Target": published or None,
        "Release": tag,
        "Block state": BLOCK_CLEAR,
        "Projection state": PROJECTION_SYNCED,
        "Review state": REVIEW_NOT_APPLICABLE,
        "CI state": CI_NOT_APPLICABLE,
        "Signal": SIGNAL_SETTLED,
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
