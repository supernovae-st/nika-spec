#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Coverage matrix ratchet: every fixture path conformance/coverage-matrix.tsv cites exists.

A row's covered_by is a path (conformance/...), or prose that names paths (EMPTY / covered under /
DECLARED-UNQUALIFIED / partial / N/A-BY-DESIGN). Every path-shaped token, resolved from the repository
root or from conformance/, must exist: a row that cites a deleted fixture claims coverage nobody runs.

Usage: python3 scripts/check-coverage-matrix.py [--selftest]
"""
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX = ROOT / "conformance/coverage-matrix.tsv"
TOKEN = re.compile(r"(?:conformance/)?[a-z0-9_-]+(?:/[A-Za-z0-9_.-]+)+")


def cited(cell):
    """The path-shaped tokens of one covered_by cell."""
    for token in TOKEN.findall(cell):
        if token.endswith(".nika") or token.startswith("conformance/"):
            yield token


def missing(rows, root):
    out = []
    for number, row in enumerate(rows, start=2):
        for token in cited(row["covered_by"]):
            if not ((root / token).exists() or (root / "conformance" / token).exists()):
                out.append((number, token))
    return out


def load(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def selftest():
    rows = load(MATRIX)
    assert not missing(rows, ROOT), "the live matrix must pass before the selftest plants"
    planted = rows + [{"pillar": "dag", "namespace": "NIKA-DAG", "stage": "check-reject",
                       "covered_by": "conformance/dag/no-such-fixture.nika"}]
    found = missing(planted, ROOT)
    assert found and found[-1][1] == "conformance/dag/no-such-fixture.nika", found
    prose = rows + [{"pillar": "verbs", "namespace": "NIKA-X", "stage": "run-fail",
                     "covered_by": "covered under errors pillar (errors/no-such-witness.nika)"}]
    assert missing(prose, ROOT)[-1][1] == "errors/no-such-witness.nika"
    print("coverage-matrix selftest · 2/2 planted paths refused")


def main():
    if "--selftest" in sys.argv:
        selftest()
        return 0
    rows = load(MATRIX)
    bad = missing(rows, ROOT)
    for number, token in bad:
        print(f"FAIL  coverage-matrix.tsv:{number} cites {token}, which does not exist")
    if bad:
        return 1
    count = sum(1 for row in rows for _ in cited(row["covered_by"]))
    print(f"coverage-matrix · {len(rows)} rows · {count} cited paths exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
