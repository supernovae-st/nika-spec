#!/usr/bin/env python3
# timeline/verify.py · re-proves every provable claim in timeline.yaml
# SPDX-License-Identifier: Apache-2.0
#
# The timeline's honesty contract, mechanized: entries whose evidence
# class is provable (git-tag · github-release · github-commit ·
# github-pr · crates-io) are verified against their source of truth.
# Unprovable classes (testimony · private-archive) are counted and
# reported, never verified, never failed. The `scorecard` class records
# a dated reading — the entry is checked for shape, not re-fetched
# (the live score moves weekly by design).
#
# Usage ·
#   python3 timeline/verify.py            # verify (network for public APIs)
#   python3 timeline/verify.py --offline  # shape + local checks only
#
# Exit 0 = every provable claim proved (or skipped offline) · exit 1 =
# a provable claim failed to resolve · exit 2 = harness error.

import json
import pathlib
import re
import subprocess
import sys
import urllib.request

try:
    import yaml
except ImportError:
    print("verify: pyyaml required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "nika-timeline-verify (https://github.com/supernovae-st/nika-spec)"}

PROVABLE = {"git-tag", "github-release", "github-commit", "github-pr", "crates-io"}
UNPROVABLE = {"testimony", "private-archive"}
RECORDED = {"scorecard"}
STABLE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def http_ok(url: str) -> bool:
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def check(entry: dict, offline: bool) -> tuple[str, str]:
    """Returns (verdict, detail) · verdict ∈ PROVED · FAILED · RECORDED ·
    UNPROVABLE · SKIPPED-OFFLINE · BAD-SHAPE."""
    ev = entry.get("evidence") or {}
    cls = ev.get("class")
    if cls in UNPROVABLE:
        return "UNPROVABLE", cls
    if cls in RECORDED:
        return ("RECORDED", cls) if ev.get("reading") or ev.get("repo") else ("BAD-SHAPE", "scorecard needs reading/repo")
    if cls not in PROVABLE:
        return "BAD-SHAPE", f"unknown evidence class {cls!r}"
    if cls == "git-tag":
        tag = ev.get("tag")
        if not tag:
            return "BAD-SHAPE", "git-tag needs tag"
        rc = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet",
                             f"refs/tags/{tag}"], capture_output=True)
        return ("PROVED", tag) if rc.returncode == 0 else ("FAILED", f"tag {tag} not in this repo")
    if offline:
        return "SKIPPED-OFFLINE", cls
    if cls == "crates-io":
        crate, ver = ev.get("crate"), ev.get("version")
        if not (crate and ver):
            return "BAD-SHAPE", "crates-io needs crate+version"
        try:
            d = fetch_json(f"https://crates.io/api/v1/crates/{crate}")
        except Exception as e:
            return "FAILED", f"crates.io unreachable: {e}"
        hit = next((v for v in d.get("versions", []) if v["num"] == ver), None)
        if not hit:
            return "FAILED", f"{crate}@{ver} not on crates.io"
        pub = hit["created_at"][:10]
        want = str(entry.get("date", ""))[:10]
        if want and pub != want:
            return "FAILED", f"{crate}@{ver} published {pub}, entry says {want}"
        return "PROVED", f"{crate}@{ver} · {pub}" + (" · yanked (listed forever)" if hit.get("yanked") else "")
    if cls == "github-release":
        repo, tag = ev.get("repo"), ev.get("tag")
        if not (repo and tag):
            return "BAD-SHAPE", "github-release needs repo+tag"
        ok = http_ok(f"https://api.github.com/repos/{repo}/releases/tags/{tag}")
        return ("PROVED", f"{repo}@{tag}") if ok else ("FAILED", f"release {tag} not on {repo}")
    if cls == "github-commit":
        repo, sha = ev.get("repo"), ev.get("sha")
        if not repo:
            return "BAD-SHAPE", "github-commit needs repo"
        if not sha:
            return "RECORDED", ev.get("note", "commit noted without sha")
        ok = http_ok(f"https://api.github.com/repos/{repo}/commits/{sha}")
        return ("PROVED", f"{repo}@{sha[:9]}") if ok else ("FAILED", f"commit {sha[:9]} not on {repo}")
    if cls == "github-pr":
        repo, pr = ev.get("repo"), ev.get("pr")
        if not (repo and pr):
            return "BAD-SHAPE", "github-pr needs repo+pr"
        try:
            d = fetch_json(f"https://api.github.com/repos/{repo}/pulls/{pr}")
        except Exception as e:
            return "FAILED", f"PR #{pr} unreachable on {repo}: {e}"
        if not d.get("merged_at"):
            return "FAILED", f"PR #{pr} on {repo} is not merged"
        return "PROVED", f"{repo}#{pr} merged {d['merged_at'][:10]}"
    return "BAD-SHAPE", f"unhandled class {cls}"


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    doc = yaml.safe_load((ROOT / "timeline" / "timeline.yaml").read_text())
    declared = set(doc.get("evidence_classes", {}))
    rows = []
    seen_ids: set[str] = set()
    for section in ("eras", "entries"):
        for e in doc.get(section, []):
            stable_id = e.get("id")
            if not stable_id or not STABLE_ID.fullmatch(stable_id):
                rows.append(("BAD-SHAPE", e.get("title", "?"),
                             f"{section} item needs a stable kebab-case id"))
                continue
            if stable_id in seen_ids:
                rows.append(("BAD-SHAPE", stable_id, "stable id is duplicated"))
                continue
            seen_ids.add(stable_id)
            cls = (e.get("evidence") or {}).get("class")
            if cls not in declared:
                rows.append(("BAD-SHAPE", e.get("title", e.get("id", "?")),
                             f"class {cls!r} not in evidence_classes"))
                continue
            v, d = check(e, offline)
            rows.append((v, e.get("title") or e.get("id") or e.get("version", "?"), d))
    for g in doc.get("gates", []):
        stable_id = g.get("id")
        if not stable_id or not STABLE_ID.fullmatch(stable_id):
            rows.append(("BAD-SHAPE", str(stable_id or "?"),
                         "gate needs a stable kebab-case id"))
        elif stable_id in seen_ids:
            rows.append(("BAD-SHAPE", stable_id, "stable id is duplicated"))
        else:
            seen_ids.add(stable_id)
        if "date" in g:
            rows.append(("BAD-SHAPE", g.get("id", "?"), "a gate carries a DATE — the future has conditions, never dates"))
        if not g.get("conditions"):
            rows.append(("BAD-SHAPE", g.get("id", "?"), "a gate needs conditions"))
    counts: dict[str, int] = {}
    failed = 0
    for v, title, detail in rows:
        counts[v] = counts.get(v, 0) + 1
        mark = {"PROVED": "✓", "RECORDED": "·", "UNPROVABLE": "○",
                "SKIPPED-OFFLINE": "~"}.get(v, "✗")
        print(f"{mark} {v:16} {title[:58]:58} {detail}")
        if v in ("FAILED", "BAD-SHAPE"):
            failed += 1
    total = len(rows)
    print(f"\ntimeline · {total} claims · " + " · ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if failed:
        print(f"✗ {failed} provable claim(s) failed — the timeline never carries a broken proof", file=sys.stderr)
        return 1
    print("✓ every provable claim holds · unprovable claims are labeled, never counted as proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
