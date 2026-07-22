#!/usr/bin/env python3
"""project-board.py · the GitHub Projects board as a PROJECTION.

The org board « Nika · the road » is derived from timeline/timeline.yaml
(the machine-verified SSOT) — never curated by hand. The stale-board
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
drift, wipe and recreate — deterministic order, deterministic board.
Quiet when equal (the weekly cron usually no-ops).

Env: BOARD_PROJECT_TOKEN — a fine-grained PAT with org-project write
(GITHUB_TOKEN cannot write org-level Projects v2). Run from repo root:
  BOARD_PROJECT_TOKEN=... python3 timeline/project-board.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

import yaml

ORG = "supernovae-st"
TITLE = "Nika · the road (a projection)"
SHORT = "Projected from timeline/timeline.yaml — gates carry conditions, never dates. Hand edits are overwritten."
README = (
    "## This board is a projection\n\n"
    "Derived from [`timeline/timeline.yaml`](https://github.com/supernovae-st/nika-spec/blob/main/timeline/timeline.yaml) "
    "— the machine-verified SSOT whose provable claims are re-proven in CI "
    "(push · PR · weekly). **Hand edits are overwritten on the next sync**; "
    "to move the road, move the record (a NEP for normative changes, a PR for the rest).\n\n"
    "Gates carry **conditions, never dates**. When a gate flips, the record gains "
    "a dated, proven entry — and the item here moves to shipped.\n\n"
    "Rendered for humans: https://nika.sh/timeline · the exhaustive ship log: "
    "https://nika.sh/changelog"
)
STAGE_FIELD = "Stage"
STAGE_GATE = "gate · conditions open"
STAGE_SHIPPED = "shipped · in the record"
SHIPPED_COUNT = 3

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
    items: list[dict] = []
    for i, gate in enumerate(doc.get("gates", []), start=1):
        lines = [f"- {c}" for c in gate.get("conditions", [])]
        if gate.get("note"):
            lines += ["", f"_{gate['note']}_"]
        lines += ["", "SSOT: `timeline/timeline.yaml` · rendered: https://nika.sh/timeline#gates"]
        items.append(
            {
                "title": f"{i:02d} · {gate['title']}",
                "body": "\n".join(lines),
                "stage": STAGE_GATE,
            }
        )
    # entries live TOP-LEVEL in the SSOT (each carries its era: field);
    # the website's vendor script is what groups them under eras. Release
    # rows carry no prose by design (the verifier proves them against the
    # API; the story lives in the changelog) — the item derives its whole
    # body from the evidence.
    releases = [e for e in doc.get("entries", []) if e.get("type") == "release"]
    for e in sorted(releases, key=lambda e: str(e["date"]))[-SHIPPED_COUNT:]:
        ev = e.get("evidence") or {}
        proof = (
            f"https://github.com/{ev['repo']}/releases/tag/{ev['tag']}"
            if ev.get("repo") and ev.get("tag")
            else "https://nika.sh/changelog"
        )
        items.append(
            {
                "title": f"v{e['version']} · shipped {e['date']}",
                "body": f"A dated, machine-proven claim of the record ({ev.get('class', 'evidence')}).\n\n"
                f"Proof: {proof}\nThe story: https://nika.sh/changelog",
                "stage": STAGE_SHIPPED,
            }
        )
    return items


def main() -> None:
    token = os.environ.get("BOARD_PROJECT_TOKEN", "")
    if not token:
        raise SystemExit("BOARD_PROJECT_TOKEN is not set")
    doc = yaml.safe_load(open("timeline/timeline.yaml", encoding="utf-8"))
    desired = desired_items(doc)

    org = gql(token, '{organization(login:"%s"){id}}' % ORG)["organization"]["id"]

    # find-or-create the project by exact title
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
    gql(
        token,
        "mutation($p:ID!,$s:String!,$r:String!){updateProjectV2(input:{projectId:$p,public:true,shortDescription:$s,readme:$r}){projectV2{id}}}",
        {"p": pid, "s": SHORT, "r": README},
    )

    # ensure the Stage single-select field
    fields = gql(
        token,
        "query($p:ID!){node(id:$p){... on ProjectV2{fields(first:30){nodes{... on ProjectV2SingleSelectField{id name options{id name}}}}}}}",
        {"p": pid},
    )["node"]["fields"]["nodes"]
    stage = next((f for f in fields if f and f.get("name") == STAGE_FIELD), None)
    if stage is None:
        stage = gql(
            token,
            'mutation($p:ID!){createProjectV2Field(input:{projectId:$p,dataType:SINGLE_SELECT,name:"%s",'
            'singleSelectOptions:[{name:"%s",color:YELLOW,description:"the future, as conditions"},'
            '{name:"%s",color:GREEN,description:"flipped — a dated, proven entry"}]})'
            "{projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}"
            % (STAGE_FIELD, STAGE_GATE, STAGE_SHIPPED),
            {"p": pid},
        )["createProjectV2Field"]["projectV2Field"]
    option_id = {o["name"]: o["id"] for o in stage["options"]}

    # current items (drafts only — anything else is a hand edit, wiped)
    current = gql(
        token,
        "query($p:ID!){node(id:$p){... on ProjectV2{items(first:100){nodes{id fieldValues(first:10){nodes{"
        "... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2SingleSelectField{name}}}}}"
        "content{... on DraftIssue{title body}}}}}}}",
        {"p": pid},
    )["node"]["items"]["nodes"]

    def snapshot(node: dict) -> dict | None:
        c = node.get("content") or {}
        if "title" not in c:
            return None  # non-draft content = a hand edit
        st = next(
            (
                v.get("name")
                for v in node["fieldValues"]["nodes"]
                if v and (v.get("field") or {}).get("name") == STAGE_FIELD
            ),
            None,
        )
        return {"title": c["title"], "body": (c.get("body") or "").strip(), "stage": st}

    snaps = [snapshot(n) for n in current]
    same = len(snaps) == len(desired) and all(
        s is not None
        and s["title"] == d["title"]
        and s["body"] == d["body"].strip()
        and s["stage"] == d["stage"]
        for s, d in zip(snaps, desired)
    )
    if same:
        print(f"board already equals the record · {len(desired)} items · quiet")
        return

    for node in current:
        gql(
            token,
            "mutation($p:ID!,$i:ID!){deleteProjectV2Item(input:{projectId:$p,itemId:$i}){deletedItemId}}",
            {"p": pid, "i": node["id"]},
        )
    for d in desired:
        item = gql(
            token,
            "mutation($p:ID!,$t:String!,$b:String!){addProjectV2DraftIssue(input:{projectId:$p,title:$t,body:$b}){projectItem{id}}}",
            {"p": pid, "t": d["title"], "b": d["body"]},
        )["addProjectV2DraftIssue"]["projectItem"]
        gql(
            token,
            "mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue("
            "input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){projectV2Item{id}}}",
            {"p": pid, "i": item["id"], "f": stage["id"], "o": option_id[d["stage"]]},
        )
    print(f"board projected · {len(desired)} items ({len(desired) - SHIPPED_COUNT} gates + {SHIPPED_COUNT} shipped)")


if __name__ == "__main__":
    sys.exit(main())
