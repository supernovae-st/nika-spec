#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Refuse live retired Nika program suffixes in tracked paths and text.

Scans pathnames and UTF-8 text for ``.nika.yaml`` / ``.nika.yml``, plus
escaped regex / brace-glob aliases. Exceptions are bounded: path + match
+ category + reason + owner. Stale exceptions fail. Negative tests and
this ratchet's own pattern data must be listed explicitly — there is no
blanket tests/ or docs/ exemption.

    python3 scripts/check-old-suffix.py
    python3 scripts/check-old-suffix.py --selftest
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS_PATH = ROOT / "scripts" / "old-suffix-exceptions.yaml"
RETIRED = (".nika.yaml", ".nika.yml")
CATEGORIES = {
    "historical",
    "frozen",
    "negative",
    "ratchet",
}

# Path and content needles. Escaped/brace forms catch glob aliases that
# would otherwise keep teaching the retired suffixes.
CONTENT_NEEDLES = (
    ".nika.yaml",
    ".nika.yml",
    r"\.nika\.ya?ml",
    r"\.nika\.yaml",
    r"\.nika\.yml",
    "*.nika.yaml",
    "*.nika.yml",
    "*.nika.ya?ml",
    ".nika.{yaml,yml}",
    ".nika.{yml,yaml}",
)


def git_ls_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [p.decode() for p in out.split(b"\0") if p]


def load_exceptions() -> list[dict]:
    data = yaml.safe_load(EXCEPTIONS_PATH.read_text()) or {}
    rows = data.get("exceptions") or []
    seen = set()
    for row in rows:
        for key in ("path", "match", "category", "reason", "owner"):
            if not row.get(key):
                raise SystemExit(f"old-suffix exception missing {key}: {row}")
        if row["category"] not in CATEGORIES:
            raise SystemExit(f"unknown exception category: {row['category']}")
        ident = (row["path"], row["match"])
        if ident in seen:
            raise SystemExit(f"duplicate exception: {ident}")
        seen.add(ident)
    return rows


def matching_exceptions(rel: str, text: str, exceptions: list[dict]) -> list[dict]:
    found = []
    for row in exceptions:
        if rel == row["path"] or rel.startswith(row["path"].rstrip("/") + "/"):
            if row["category"] == "ratchet" or row["match"] in text or row["match"] in rel:
                found.append(row)
    return found


def content_hits(text: str) -> list[tuple[int, str]]:
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(needle in line for needle in CONTENT_NEEDLES):
            hits.append((i, line))
    return hits


def scan(exceptions: list[dict]) -> tuple[list[str], set[tuple[str, str]]]:
    failures: list[str] = []
    used: set[tuple[str, str]] = set()
    files = git_ls_files()
    for rel in files:
        if rel.endswith(RETIRED):
            rows = matching_exceptions(rel, rel, exceptions)
            if not rows:
                failures.append(f"path {rel} · retired program suffix")
            else:
                used.update((row["path"], row["match"]) for row in rows)
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, OSError):
            continue
        for lineno, line in content_hits(text):
            rows = matching_exceptions(rel, line, exceptions)
            if not rows:
                failures.append(f"{rel}:{lineno} · {line.strip()[:160]}")
            else:
                used.update((row["path"], row["match"]) for row in rows)
    declared = {(row["path"], row["match"]) for row in exceptions}
    stale = declared - used
    for path, match in sorted(stale):
        failures.append(f"stale exception · {path} · {match!r}")
    return failures, used


def selftest() -> int:
    """A reintroduced live old suffix must be detected; listed exceptions pass."""
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "live.nika.yaml").write_text("nika: x\ntasks: { t: { infer: { prompt: x } } }\n")
        (root / "ok.nika").write_text("nika: x\ntasks: { t: { infer: { prompt: x } } }\n")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check-old-suffix.py"),
             "--root", str(root), "--no-git"],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 or "live.nika.yaml" not in proc.stdout + proc.stderr:
            print("selftest: missed a live retired path", proc.stdout, proc.stderr)
            bad += 1
        else:
            print("selftest: reintroduced live.nika.yaml detected")
    # Real tree with exceptions must be invokable from --selftest only as
    # a smoke that the exception file parses. The main scan is CI.
    load_exceptions()
    print("selftest: exception file parses")
    return bad


def scan_root_no_git(root: Path) -> list[str]:
    failures = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.endswith(RETIRED):
            failures.append(f"path {rel} · retired program suffix")
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in content_hits(text):
            failures.append(f"{rel}:{lineno} · {line.strip()[:160]}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--no-git", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.no_git:
        root = args.root or ROOT
        failures = scan_root_no_git(root)
        for f in failures:
            print(f"✗ {f}", file=sys.stderr)
        print(f"old-suffix ratchet · {len(failures)} hit(s) (no-git)")
        return 1 if failures else 0
    failures, _used = scan(load_exceptions())
    for f in failures:
        print(f"✗ {f}", file=sys.stderr)
    if failures:
        print(f"old-suffix ratchet · {len(failures)} hit(s)", file=sys.stderr)
        return 1
    print("old-suffix ratchet · clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
