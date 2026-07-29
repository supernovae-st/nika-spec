#!/usr/bin/env python3
# check-yaml-dup-keys.py — the second-key gate.
#
# A duplicate key in a YAML mapping is not an error to PyYAML: the last
# value silently wins. That silence has bitten three named times (a CI
# step swallowed by a plain-scalar continuation · a kit fold that doubled
# two permits blocks · an indent-eaten dependabot groups block) — the
# Surface-C threshold: discipline graduates to a gate.
#
# Scope · every tracked *.yml / *.yaml EXCEPT
#   *.nika.yaml           the engine parser refuses duplicates itself
#                         (NIKA-PARSE-017 · proven by mutation 2026-07-29)
#   conformance/tests/**  the torture corpus is deliberately malformed;
#                         its validity belongs to the harness
#
# A file that does not parse at all is SKIPped by name (validity is other
# gates' law); only a real duplicate key FAILs. The merge idiom
# (<<: *anchor + a local override) stays legal: only LITERAL twin keys
# inside one mapping fire.
#
#   python3 scripts/check-yaml-dup-keys.py             # sweep the repo
#   python3 scripts/check-yaml-dup-keys.py --selftest  # prove the teeth
from __future__ import annotations

import pathlib
import subprocess
import sys

import yaml

SPEC_ROOT = pathlib.Path(__file__).resolve().parent.parent
MERGE_TAG = "tag:yaml.org,2002:merge"


class DupKey(Exception):
    pass


class Loader(yaml.SafeLoader):
    """SafeLoader that refuses literal twin keys in one mapping.

    The scan runs on the RAW node pairs, before SafeLoader flattens
    merge keys — so `<<:` expansion never counts as a duplicate and the
    override idiom stays legal. Keys are compared as (resolved tag,
    scalar text): plain `yes` (bool) and quoted "yes" (str) stay two
    different keys, exactly as YAML resolves them.
    """

    def construct_mapping(self, node, deep=False):
        seen: dict[tuple[str, str], int] = {}
        for k_node, _v in node.value:
            if not isinstance(k_node, yaml.ScalarNode) or k_node.tag == MERGE_TAG:
                continue
            key = (k_node.tag, k_node.value)
            line = k_node.start_mark.line + 1
            if key in seen:
                raise DupKey(
                    f"duplicate key {k_node.value!r} "
                    f"(lines {seen[key]} and {line} · the second silently wins)"
                )
            seen[key] = line
        return super().construct_mapping(node, deep)


def judge(text: str) -> tuple[str, str | None]:
    """('ok', None) · ('dup', message) · ('noparse', first error line)."""
    try:
        for _ in yaml.load_all(text, Loader=Loader):
            pass
    except DupKey as e:
        return "dup", str(e)
    except yaml.YAMLError as e:
        return "noparse", str(e).splitlines()[0][:100]
    return "ok", None


def tracked_yaml() -> list[pathlib.Path]:
    rels = subprocess.run(
        ["git", "ls-files", "*.yml", "*.yaml"],
        cwd=SPEC_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    keep: list[pathlib.Path] = []
    for rel in rels:
        if rel.endswith(".nika.yaml") or rel.startswith("conformance/tests/"):
            continue
        keep.append(SPEC_ROOT / rel)
    return keep


def sweep() -> int:
    files = tracked_yaml()
    bad = 0
    skipped = 0
    for f in files:
        verdict, msg = judge(f.read_text(encoding="utf-8", errors="replace"))
        rel = f.relative_to(SPEC_ROOT)
        if verdict == "dup":
            print(f"FAIL  {rel} · {msg}")
            bad += 1
        elif verdict == "noparse":
            print(f"SKIP  {rel} · no-parse ({msg})")
            skipped += 1
    print(
        f"\nyaml-dup-keys · {len(files)} files · "
        f"{bad} duplicate(s) · {skipped} skipped"
    )
    return 1 if bad else 0


SELFTEST_CASES: list[tuple[str, str, str]] = [
    ("clean mapping", "a: 1\nb:\n  c: 2\n  d: 3\n", "ok"),
    ("root twin", "a: 1\nb: 2\na: 3\n", "dup"),
    ("nested twin", "a:\n  x: 1\n  y: 2\n  x: 3\n", "dup"),
    ("merge override stays legal", "base: &b\n  k: 1\nuse:\n  <<: *b\n  k: 2\n", "ok"),
    ("twin in the second document", "a: 1\n---\nb: 1\nb: 2\n", "dup"),
    ("bool-tagged twin (on/on)", "on: 1\non: 2\n", "dup"),
]


def selftest() -> int:
    bad = 0
    for name, text, want in SELFTEST_CASES:
        got, msg = judge(text)
        ok = got == want
        bad += 0 if ok else 1
        detail = f" · {msg}" if msg else ""
        print(f"{'ok  ' if ok else 'FAIL'}  {name}: want {want}, got {got}{detail}")
    print(f"selftest · {len(SELFTEST_CASES) - bad}/{len(SELFTEST_CASES)}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    return sweep()


if __name__ == "__main__":
    sys.exit(main())
