#!/usr/bin/env python3
"""project-board.py · the GitHub Projects board as a PROJECTION.

The org board « Nika · the road » is derived from timeline/timeline.yaml
(the machine-verified SSOT): never curated by hand. The stale-board
anti-pattern (github/roadmap's own README rotted for years) comes from
hand-maintenance; a projection cannot rot: on every sync this script
makes the board equal to the SSOT, so hand edits are OVERWRITTEN by
construction. The board says so in its own readme.

Shape (one surface, the whole time story, GitHub-native):
  · one draft item per forward gate (rail order · body = the conditions)
    → Stage « gate · conditions open »
  · the last three releases from the record (body = the dated claim)
    → Stage « shipped · in the record »

Sync = compare desired vs current (title/body/stage, in order); on any
drift, wipe and recreate: deterministic order, deterministic board.
Quiet when equal (the weekly cron usually no-ops).

Env: BOARD_PROJECT_TOKEN: a fine-grained PAT with org-project write
(GITHUB_TOKEN cannot write org-level Projects v2). Run from repo root:
  BOARD_PROJECT_TOKEN=... python3 timeline/project-board.py
"""

from __future__ import annotations

import json
import re
import os
import sys
import urllib.request

import yaml

ORG = "supernovae-st"
TITLE = "Nika · the road (a projection)"
SHORT = "Projected from timeline/timeline.yaml: the whole record (every dated claim) plus the forward gates. Hand edits are overwritten."
README = (
    "## This board is a projection\n\n"
    "Derived from [`timeline/timeline.yaml`](https://github.com/supernovae-st/nika-spec/blob/main/timeline/timeline.yaml), "
    "the machine-verified SSOT whose provable claims are re-proven in CI "
    "(push, PR, weekly). **Hand edits are overwritten on the next sync**; "
    "to move the road, move the record (a NEP for normative changes, a PR for the rest).\n\n"
    "### The fields\n\n"
    "| Field | Meaning |\n|---|---|\n"
    "| **Stage** | gate (conditions open) or shipped (in the record) |\n"
    "| **Era** | ✧ exploration · ✎ brouillon · ◆ diamond · ◇ ahead |\n"
    "| **Kind** | release · milestone · gate |\n"
    "| **Proof** | ✓ proven (re-proven in CI) · recorded · ○ labeled (testimony, honestly) |\n"
    "| **When** | the dated past. Gates carry no date by law: on the roadmap view the future is literally unplaced |\n"
    "| **Order** | one sequence, oldest claim to farthest gate |\n\n"
    "### The views to save (60 seconds, once)\n\n"
    "1. **The rail** · Table · group by Stage · sort by Order · fields: Title, Kind, Era, Proof, When\n"
    "2. **The road** · Board · columns by Stage\n"
    "3. **The record** · Roadmap · date field When · the past sits on the axis, the gates deliberately do not\n"
    "4. **By proof** · Table · group by Proof: the honesty contract at a glance\n\n"
    "Gates carry **conditions, never dates**. When a gate flips, the record gains "
    "a dated, proven entry and its issue closes itself.\n\n"
    "Rendered for humans: https://nika.sh/timeline · the exhaustive ship log: "
    "https://nika.sh/changelog"
)

STAGE_FIELD = "Stage"
STAGE_GATE = "gate · conditions open"
STAGE_SHIPPED = "shipped · in the record"
SHIPPED_COUNT = 3

PROVEN_CLASSES = {"crates-io", "github-release", "github-commit", "github-pr", "git-tag"}
RECORDED_CLASSES = {"scorecard"}
ERA_LABEL = {"exploration": "✧ exploration", "brouillon": "✎ brouillon", "diamond": "◆ diamond"}
ERA_AHEAD = "◇ ahead"
FIELD_SELECTS = {
    "Era": [
        ("✧ exploration", "GRAY", "private prototypes, testimony class"),
        ("✎ brouillon", "ORANGE", "the named draft, 0.1 to 0.79.3"),
        ("◆ diamond", "BLUE", "rewritten from scratch, real semver"),
        ("◇ ahead", "PURPLE", "the gates: conditions, never dates"),
    ],
    "Kind": [
        ("release", "GREEN", "a tagged release"),
        ("milestone", "BLUE", "a dated claim of the record"),
        ("gate", "YELLOW", "a forward condition"),
    ],
    "Proof": [
        ("✓ proven", "GREEN", "re-proven in CI against a public source"),
        ("· recorded", "YELLOW", "a recorded reading"),
        ("○ labeled", "GRAY", "testimony or private archive, honestly labeled"),
    ],
}


def era_of(entry: dict) -> str:
    if entry.get("era"):
        return ERA_LABEL[entry["era"]]
    d = str(entry["date"])
    if d < "2026-01-01":
        return ERA_LABEL["exploration"]
    if d < "2026-04-13":
        return ERA_LABEL["brouillon"]
    return ERA_LABEL["diamond"]


def proof_of(entry: dict) -> str:
    cls = (entry.get("evidence") or {}).get("class", "")
    if cls in PROVEN_CLASSES:
        return "✓ proven"
    if cls in RECORDED_CLASSES:
        return "· recorded"
    return "○ labeled"


def proof_url(entry: dict) -> str | None:
    ev = entry.get("evidence") or {}
    repo, cls = ev.get("repo"), ev.get("class", "")
    if repo and ev.get("tag"):
        return f"https://github.com/{repo}/releases/tag/{ev['tag']}"
    if repo and ev.get("sha"):
        return f"https://github.com/{repo}/commit/{ev['sha']}"
    if repo and ev.get("pr"):
        return f"https://github.com/{repo}/pull/{ev['pr']}"
    if cls == "crates-io" and entry.get("version"):
        return f"https://crates.io/crates/nika/{entry['version']}"
    return None


def when_of(entry: dict) -> str:
    d = str(entry["date"])
    return f"{d}-15" if len(d) == 7 else d


API = "https://api.github.com/graphql"


def gql(token: str, query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "nika-board-projection",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read())
    if out.get("errors"):
        raise SystemExit(f"graphql: {json.dumps(out['errors'])[:800]}")
    return out["data"]


def desired_items(doc: dict) -> list[dict]:
    """The WHOLE record (every dated entry) plus the gates, in time order.
    Each item carries the field set the views slice on: Stage, Era, Kind,
    Proof, Status, When (past only: the future has no date by law), Order.
    Entry details are SSOT citations and keep their own punctuation."""
    items: list[dict] = []
    for e in sorted(doc.get("entries", []), key=lambda e: str(e["date"])):
        rel = e.get("type") == "release"
        if e.get("title") and e.get("version"):
            title = f"v{e['version']} · {e['title']}"
        elif e.get("version"):
            title = f"v{e['version']}"
        else:
            title = e["title"]
        lines = []
        if e.get("detail"):
            lines.append(e["detail"])
        url = proof_url(e)
        cls = (e.get("evidence") or {}).get("class", "evidence")
        lines.append("")
        lines.append(f"Proof class: {cls}" + (f" · {url}" if url else " (labeled, never dressed as proof)"))
        if e.get("precision") == "month":
            lines.append("Date carries month precision; the roadmap seats it mid-month.")
        items.append(
            {
                "title": title,
                "body": "\n".join(lines).strip(),
                "stage": STAGE_SHIPPED,
                "era": era_of(e),
                "kind": "release" if rel else "milestone",
                "proof": proof_of(e),
                "status": "Done",
                "when": when_of(e),
            }
        )
    for gate in doc.get("gates", []):
        items.append(
            {
                "title": f"gate · {gate['title']}",
                "body": gate_body(gate["id"], gate),
                "stage": STAGE_GATE,
                "era": ERA_AHEAD,
                "kind": "gate",
                "proof": None,
                "status": "Todo",
                "when": None,
                "gate_id": gate["id"],
            }
        )
    for i, it in enumerate(items, start=1):
        it["order"] = i
    return items


# ── v2 · the gates as REAL tracking issues (the Rust project-goals law) ──────
# One issue per gate, in the repo that carries its milestone, attached to
# it, labeled `gate`, body projected from the SSOT (a marker pins identity).
# A gate that leaves the SSOT (it flipped) closes its issue: the milestone
# completes by itself. The board then carries these REAL issues.

REPOS = ["nika", "nika-spec"]
LABEL = {"name": "gate", "color": "f0b429", "description": "a forward gate of the record · conditions, never dates"}


def rest(token: str, method: str, path: str, body: dict | None = None) -> dict | list:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "nika-board-projection",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else {}


def slug_match(gate_title: str, milestone_title: str) -> bool:
    """Exact match first (case-insensitive, the `gate · ` prefix stripped):
    the prefix heuristic alone seated `1.0.0` on the `1.0.0-rc.N`
    milestone (substring collision, caught on the first live run)."""
    ms = milestone_title.lower().removeprefix("gate · ").strip()
    if ms == gate_title.strip().lower():
        return True
    head = gate_title.split("·")[0].strip().lower()
    return head[:18] in ms and not ms.startswith(head + "-")


def gate_body(gid: str, gate: dict) -> str:
    """One writer for the tracking-issue body: sync_issues posts it and
    desired_items fingerprints it. Two writers drifted on the marker and
    the sync recreated the whole board every run (caught live)."""
    lines = [f"<!-- projected:gate:{gid} -->",
             "**A forward gate of the record: conditions, never dates.**", ""]
    lines += [f"- [ ] {c}" for c in gate.get("conditions", [])]
    if gate.get("note"):
        lines += ["", f"_{gate['note']}_"]
    lines += ["", "SSOT: [`timeline/timeline.yaml`](https://github.com/supernovae-st/nika-spec/blob/main/timeline/timeline.yaml) · rendered: https://nika.sh/timeline#gates",
              "", "_Projected from the record; hand edits are overwritten. When this gate flips, the record gains a dated proven entry and this issue closes itself._"]
    return "\n".join(lines)


def sync_issues(token: str, doc: dict) -> dict[str, dict]:
    """Project one tracking issue per gate; close leftovers. Returns
    gate id -> {node_id, html_url} for the board layer."""
    by_gate: dict[str, dict] = {}
    milestones = {
        repo: rest(token, "GET", f"/repos/{ORG}/{repo}/milestones?state=open&per_page=50")
        for repo in REPOS
    }
    existing: dict[str, tuple[str, dict]] = {}
    for repo in REPOS:
        try:
            rest(token, "POST", f"/repos/{ORG}/{repo}/labels", LABEL)
        except Exception:
            pass  # exists
        for it in rest(token, "GET", f"/repos/{ORG}/{repo}/issues?labels=gate&state=open&per_page=100"):
            m = re.search(r"<!-- projected:gate:([a-z0-9-]+) -->", it.get("body") or "")
            if m:
                existing[m.group(1)] = (repo, it)

    for gate in doc.get("gates", []):
        gid, title = gate["id"], f"gate · {gate['title']}"
        seat = next(
            ((repo, ms) for repo in REPOS for ms in milestones[repo] if slug_match(gate["title"], ms["title"])),
            (REPOS[0], None),
        )
        repo, ms = seat
        body = gate_body(gid, gate)
        if gid in existing:
            erepo, it = existing.pop(gid)
            if it["title"] != title or (it.get("body") or "") != body or (ms and (it.get("milestone") or {}).get("number") != ms["number"]):
                patch: dict = {"title": title, "body": body}
                if ms and erepo == repo:
                    patch["milestone"] = ms["number"]
                it = rest(token, "PATCH", f"/repos/{ORG}/{erepo}/issues/{it['number']}", patch)
            by_gate[gid] = {"node_id": it["node_id"], "html_url": it["html_url"]}
        else:
            payload: dict = {"title": title, "body": body, "labels": ["gate"]}
            if ms:
                payload["milestone"] = ms["number"]
            it = rest(token, "POST", f"/repos/{ORG}/{repo}/issues", payload)
            print(f"issue opened: {it['html_url']}")
            by_gate[gid] = {"node_id": it["node_id"], "html_url": it["html_url"]}

    for gid, (erepo, it) in existing.items():
        rest(token, "POST", f"/repos/{ORG}/{erepo}/issues/{it['number']}/comments",
             {"body": "The gate flipped: the record gained its dated, proven entry. Closing the projection."})
        rest(token, "PATCH", f"/repos/{ORG}/{erepo}/issues/{it['number']}", {"state": "closed"})
        print(f"issue closed (gate flipped): {erepo}#{it['number']}")
    return by_gate


def link_repos(token: str, project_id: str) -> None:
    """Loud by law: the first live run swallowed a link failure and the
    repo Projects tabs stayed empty with a green run. Every repo prints
    its verdict; 'already linked' is the only quiet success."""
    for repo in REPOS:
        rid = gql(token, 'query($n:String!){repository(owner:"%s",name:$n){id}}' % ORG, {"n": repo})["repository"]["id"]
        try:
            gql(token, "mutation($p:ID!,$r:ID!){linkProjectV2ToRepository(input:{projectId:$p,repositoryId:$r}){repository{id}}}",
                {"p": project_id, "r": rid})
            print(f"linked project to {repo}")
        except SystemExit as err:
            msg = str(err)
            if "already linked" in msg.lower():
                print(f"already linked: {repo}")
            else:
                print(f"::warning::link to {repo} FAILED: {msg[:300]}")


FIELDS_QUERY = (
    "query($p:ID!){node(id:$p){... on ProjectV2{fields(first:50){nodes{"
    "... on ProjectV2Field{id name dataType}"
    "... on ProjectV2SingleSelectField{id name dataType options{id name}}}}}}}"
)


def ensure_fields(token: str, pid: str) -> dict:
    """Find or create the custom fields; realign select options on drift.
    Returns {name: {id, opts?}} including the built-in Status field."""
    have = {
        f["name"]: f
        for f in gql(token, FIELDS_QUERY, {"p": pid})["node"]["fields"]["nodes"]
        if f
    }
    out: dict[str, dict] = {}
    for name, opts in FIELD_SELECTS.items():
        want = [{"name": n, "color": c, "description": d} for n, c, d in opts]
        f = have.get(name)
        if f is None:
            f = gql(
                token,
                "mutation($p:ID!,$n:String!,$o:[ProjectV2SingleSelectFieldOptionInput!]!)"
                "{createProjectV2Field(input:{projectId:$p,dataType:SINGLE_SELECT,name:$n,singleSelectOptions:$o})"
                "{projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}",
                {"p": pid, "n": name, "o": want},
            )["createProjectV2Field"]["projectV2Field"]
            print(f"field created: {name}")
        elif [o["name"] for o in f.get("options", [])] != [o[0] for o in opts]:
            f = gql(
                token,
                "mutation($f:ID!,$o:[ProjectV2SingleSelectFieldOptionInput!]!)"
                "{updateProjectV2Field(input:{fieldId:$f,singleSelectOptions:$o})"
                "{projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}",
                {"f": f["id"], "o": want},
            )["updateProjectV2Field"]["projectV2Field"]
            print(f"field realigned: {name}")
        out[name] = {"id": f["id"], "opts": {o["name"]: o["id"] for o in f["options"]}}
    for name, dtype in (("When", "DATE"), ("Order", "NUMBER")):
        f = have.get(name)
        if f is None:
            f = gql(
                token,
                "mutation($p:ID!,$n:String!){createProjectV2Field(input:{projectId:$p,dataType:%s,name:$n})"
                "{projectV2Field{... on ProjectV2Field{id name}}}}" % dtype,
                {"p": pid, "n": name},
            )["createProjectV2Field"]["projectV2Field"]
            print(f"field created: {name}")
        out[name] = {"id": f["id"]}
    status = have.get("Status")
    if status and status.get("options"):
        out["Status"] = {"id": status["id"], "opts": {o["name"]: o["id"] for o in status["options"]}}
    stage = have.get(STAGE_FIELD)
    if stage and stage.get("options"):
        out[STAGE_FIELD] = {"id": stage["id"], "opts": {o["name"]: o["id"] for o in stage["options"]}}
    return out


def set_value(token: str, pid: str, item_id: str, field: dict, value: dict) -> None:
    gql(
        token,
        "mutation($p:ID!,$i:ID!,$f:ID!,$v:ProjectV2FieldValue!)"
        "{updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:$v}){projectV2Item{id}}}",
        {"p": pid, "i": item_id, "f": field["id"], "v": value},
    )


def apply_fields(token: str, pid: str, item_id: str, d: dict, fields: dict) -> None:
    plan = [
        (STAGE_FIELD, d["stage"]),
        ("Era", d["era"]),
        ("Kind", d["kind"]),
        ("Proof", d.get("proof")),
        ("Status", d.get("status")),
    ]
    for fname, val in plan:
        f = fields.get(fname)
        if f and val and val in f.get("opts", {}):
            set_value(token, pid, item_id, f, {"singleSelectOptionId": f["opts"][val]})
    if d.get("when") and "When" in fields:
        set_value(token, pid, item_id, fields["When"], {"date": d["when"]})
    if d.get("order") is not None and "Order" in fields:
        set_value(token, pid, item_id, fields["Order"], {"number": d["order"]})


ITEMS_QUERY = (
    "query($p:ID!){node(id:$p){... on ProjectV2{items(first:60){nodes{id "
    "fieldValues(first:20){nodes{"
    "... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2SingleSelectField{name}}}"
    "... on ProjectV2ItemFieldDateValue{date field{... on ProjectV2Field{name}}}"
    "... on ProjectV2ItemFieldNumberValue{number field{... on ProjectV2Field{name}}}}}"
    "content{... on DraftIssue{title body} ... on Issue{title body}}}}}}}"
)


def snapshot_items(token: str, pid: str) -> list[dict]:
    nodes = gql(token, ITEMS_QUERY, {"p": pid})["node"]["items"]["nodes"]
    out = []
    for node in nodes:
        c = node.get("content") or {}
        vals: dict = {}
        for v in node["fieldValues"]["nodes"]:
            if not v or "field" not in v:
                continue
            fname = (v.get("field") or {}).get("name")
            if "name" in v and fname:
                vals[fname] = v["name"]
            elif "date" in v and fname:
                vals[fname] = str(v["date"])
            elif "number" in v and fname:
                vals[fname] = int(v["number"])
        out.append(
            {
                "id": node["id"],
                "title": c.get("title"),
                "body": (c.get("body") or "").strip(),
                "vals": vals,
            }
        )
    return out


def fingerprint(d: dict) -> tuple:
    return (
        d["title"],
        d["body"].strip(),
        d["stage"],
        d["era"],
        d["kind"],
        d.get("proof"),
        d.get("status"),
        d.get("when"),
        d.get("order"),
    )


def current_fingerprint(snap: dict) -> tuple:
    v = snap["vals"]
    return (
        snap["title"],
        snap["body"],
        v.get(STAGE_FIELD),
        v.get("Era"),
        v.get("Kind"),
        v.get("Proof"),
        v.get("Status"),
        v.get("When"),
        v.get("Order"),
    )



def main() -> None:
    token = os.environ.get("BOARD_PROJECT_TOKEN", "")
    if not token:
        raise SystemExit("BOARD_PROJECT_TOKEN is not set")
    doc = yaml.safe_load(open("timeline/timeline.yaml", encoding="utf-8"))
    desired = desired_items(doc)
    gate_issues = sync_issues(token, doc)

    org = gql(token, '{organization(login:"%s"){id}}' % ORG)["organization"]["id"]
    found = gql(
        token,
        'query($q:String!){organization(login:"%s"){projectsV2(first:20,query:$q){nodes{id title number}}}}'
        % ORG,
        {"q": TITLE},
    )["organization"]["projectsV2"]["nodes"]
    project = next((p for p in found if p["title"] == TITLE), None)
    if project is None:
        project = gql(
            token,
            "mutation($o:ID!,$t:String!){createProjectV2(input:{ownerId:$o,title:$t}){projectV2{id title number}}}",
            {"o": org, "t": TITLE},
        )["createProjectV2"]["projectV2"]
        print(f"created project #{project['number']}")
    pid = project["id"]
    link_repos(token, pid)
    gql(
        token,
        "mutation($p:ID!,$s:String!,$r:String!){updateProjectV2(input:{projectId:$p,public:true,shortDescription:$s,readme:$r}){projectV2{id}}}",
        {"p": pid, "s": SHORT, "r": README},
    )
    fields = ensure_fields(token, pid)

    snaps = snapshot_items(token, pid)
    if len(snaps) == len(desired) and all(
        current_fingerprint(s) == fingerprint(d) for s, d in zip(snaps, desired)
    ):
        print(f"board already equals the record · {len(desired)} items · quiet")
        return

    for snap in snaps:
        gql(
            token,
            "mutation($p:ID!,$i:ID!){deleteProjectV2Item(input:{projectId:$p,itemId:$i}){deletedItemId}}",
            {"p": pid, "i": snap["id"]},
        )
    for d in desired:
        node = gate_issues.get(d.get("gate_id", ""))
        if node:
            item = gql(
                token,
                "mutation($p:ID!,$c:ID!){addProjectV2ItemById(input:{projectId:$p,contentId:$c}){item{id}}}",
                {"p": pid, "c": node["node_id"]},
            )["addProjectV2ItemById"]["item"]
        else:
            item = gql(
                token,
                "mutation($p:ID!,$t:String!,$b:String!){addProjectV2DraftIssue(input:{projectId:$p,title:$t,body:$b}){projectItem{id}}}",
                {"p": pid, "t": d["title"], "b": d["body"]},
            )["addProjectV2DraftIssue"]["projectItem"]
        apply_fields(token, pid, item["id"], d, fields)

    gates_n = sum(1 for d in desired if d["kind"] == "gate")
    proven_n = sum(1 for d in desired if d.get("proof") == "✓ proven")
    try:
        gql(
            token,
            "mutation($p:ID!,$b:String!){createProjectV2StatusUpdate(input:{projectId:$p,status:ON_TRACK,body:$b}){statusUpdate{id}}}",
            {
                "p": pid,
                "b": f"Re-projected from the record: {len(desired) - gates_n} dated claims ({proven_n} proven in CI) and {gates_n} gates ahead. v1 is the culmination; gates carry conditions, never dates.",
            },
        )
    except SystemExit as err:
        print(f"::warning::status update FAILED: {str(err)[:200]}")
    print(
        f"board projected · {len(desired)} items ({gates_n} gates + {len(desired) - gates_n} record claims, {proven_n} proven)"
    )


if __name__ == "__main__":
    sys.exit(main())
