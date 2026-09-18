#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Refuse live retired Nika program suffixes in tracked paths and text.

Exceptions are exact paths only — never a directory prefix. Frozen
evidence pins the whole-file digest. Teaching and negative files pin
the exact hit-count and the hash of the matching lines, so a new
``nika run foo.nika.yaml`` in an allowlisted chapter fails.

    python3 scripts/check-old-suffix.py
    python3 scripts/check-old-suffix.py --selftest
    python3 scripts/check-old-suffix.py --dump-pins
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS_PATH = ROOT / "scripts" / "old-suffix-exceptions.yaml"
RETIRED = (".nika.yaml", ".nika.yml")
CATEGORIES = {"historical", "frozen", "negative", "ratchet"}
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


def sha256_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def lines_sha256(lines: list[str]) -> str:
    return sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


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
    seen: set[str] = set()
    for row in rows:
        for key in ("path", "category", "reason", "owner"):
            if not row.get(key):
                raise SystemExit(f"old-suffix exception missing {key}: {row}")
        path = row["path"]
        if path.endswith("/") or "*" in path or path.endswith("\\"):
            raise SystemExit(f"exception path must be an exact file, not a prefix/glob: {path}")
        if row["category"] not in CATEGORIES:
            raise SystemExit(f"unknown exception category: {row['category']}")
        if path in seen:
            raise SystemExit(f"duplicate exception path: {path}")
        seen.add(path)
        if row["category"] == "frozen":
            if not row.get("digest"):
                raise SystemExit(f"frozen exception missing digest: {path}")
        else:
            if "count" not in row or not row.get("lines_sha256"):
                raise SystemExit(f"content exception missing count/lines_sha256: {path}")
    return rows


def content_hit_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if any(n in line for n in CONTENT_NEEDLES)]


def read_rel(rel: str, overlay: dict[str, str] | None) -> tuple[bytes, str] | None:
    if overlay is not None and rel in overlay:
        text = overlay[rel]
        return text.encode("utf-8"), text
    path = ROOT / rel
    try:
        raw = path.read_bytes()
        return raw, raw.decode("utf-8")
    except (UnicodeDecodeError, IsADirectoryError, OSError):
        return None


def scan(
    exceptions: list[dict],
    *,
    overlay: dict[str, str] | None = None,
    extra_paths: list[str] | None = None,
) -> list[str]:
    by_path = {row["path"]: row for row in exceptions}
    files = git_ls_files()
    if extra_paths:
        files = list(dict.fromkeys([*files, *extra_paths]))
    failures: list[str] = []
    used: set[str] = set()
    for rel in files:
        row = by_path.get(rel)
        loaded = read_rel(rel, overlay)
        retired_path = rel.endswith(RETIRED)
        if loaded is None:
            if retired_path and row is None:
                failures.append(f"path {rel} · retired program suffix")
            continue
        raw, text = loaded
        hits = content_hit_lines(text)
        if retired_path:
            if row is None or row["category"] != "frozen":
                failures.append(f"path {rel} · retired program suffix")
            elif sha256_bytes(raw) != row["digest"]:
                failures.append(f"{rel} · frozen digest mismatch")
            else:
                used.add(rel)
            continue
        if not hits:
            continue
        if row is None:
            for i, line in enumerate(text.splitlines(), 1):
                if any(n in line for n in CONTENT_NEEDLES):
                    failures.append(f"{rel}:{i} · {line.strip()[:160]}")
            continue
        used.add(rel)
        digest = sha256_bytes(raw)
        if row["category"] == "frozen":
            if digest != row["digest"]:
                failures.append(f"{rel} · frozen digest mismatch")
            continue
        if len(hits) != row["count"]:
            failures.append(
                f"{rel} · hit count {len(hits)} != pinned {row['count']}"
            )
        actual = lines_sha256(hits)
        if actual != row["lines_sha256"]:
            failures.append(f"{rel} · matching-lines hash mismatch")
    for row in exceptions:
        if row["path"] not in used:
            failures.append(f"stale exception · {row['path']}")
    return failures


def dump_pins() -> int:
    exceptions = load_exceptions()
    files = set(git_ls_files())
    for row in exceptions:
        rel = row["path"]
        loaded = read_rel(rel, None)
        if loaded is None:
            print(f"# missing {rel}", file=sys.stderr)
            continue
        raw, text = loaded
        hits = content_hit_lines(text)
        print(f"{rel}")
        print(f"  digest: {sha256_bytes(raw)}")
        print(f"  count: {len(hits)}")
        print(f"  lines_sha256: {lines_sha256(hits)}")
        if rel not in files:
            print("  # not in git ls-files", file=sys.stderr)
    return 0


def selftest() -> int:
    bad = 0
    exceptions = load_exceptions()
    clean = scan(exceptions)
    if clean:
        print("selftest: live tree should be clean, got:")
        for item in clean:
            print(f"  {item}")
        bad += 1
    else:
        print("selftest: live tree clean")

    env = "spec/01-envelope.md"
    orig = (ROOT / env).read_text(encoding="utf-8")
    injected = orig.rstrip() + "\n\n`nika run foo.nika.yaml`\n"
    chapter_fail = scan(exceptions, overlay={env: injected})
    if not any(env in item for item in chapter_fail):
        print("selftest: missed injection into allowlisted chapter", chapter_fail)
        bad += 1
    else:
        print("selftest: injection into spec/01-envelope.md detected")

    proof = "proofs/_ratchet-injection.nika.yaml"
    proof_fail = scan(
        exceptions,
        extra_paths=[proof],
        overlay={proof: "nika: inject\ntasks: { t: { infer: { prompt: x } } }\n"},
    )
    if not any(proof in item for item in proof_fail):
        print("selftest: missed new proofs/ retired path", proof_fail)
        bad += 1
    else:
        print("selftest: new proofs/_ratchet-injection.nika.yaml detected")

    if not any("retired program suffix" in item for item in proof_fail):
        print("selftest: new proofs file should fail as a retired path")
        bad += 1

    again = scan(exceptions)
    if again:
        print("selftest: overlay leaked into live scan", again)
        bad += 1
    else:
        print("selftest: legitimate history and negative tests still pass")
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--dump-pins", action="store_true")
    args = parser.parse_args()
    if args.dump_pins:
        return dump_pins()
    if args.selftest:
        return selftest()
    failures = scan(load_exceptions())
    for item in failures:
        print(f"✗ {item}", file=sys.stderr)
    if failures:
        print(f"old-suffix ratchet · {len(failures)} hit(s)", file=sys.stderr)
        return 1
    print("old-suffix ratchet · clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
