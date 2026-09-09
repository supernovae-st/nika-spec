#!/usr/bin/env python3
"""Public verifier for the generated Estate projection at tools/estate/.

Reads provenance.json and checks the checkout against that declaration:
exact inventory, safe relative paths, sha256, git blob id and git file
mode. Missing, extra or symlink entries are refused. An altered digest
or mode is drift.

This checker does not regenerate the projection from Lab, does not
reach the network or any private path, and does not authenticate a
signature — none exists; provenance.json is a declaration.

    python3 scripts/check-estate-projection.py           # tools/estate
    python3 scripts/check-estate-projection.py DIR

    exit 0  inventory, paths, hashes and modes match
    exit 2  bad usage
    exit 3  missing, extra, symlink, or invalid provenance
    exit 5  digest, git-blob or mode drift
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = SPEC_ROOT / "tools" / "estate"

PROJECTION_SCHEMA = "nika-lab/estate-public-verifier/v1"
SOURCE_REPOSITORY = "supernovae-st/nika-estate"
# Historical Estate pin this generated projection carries. Declared here
# so a swapped-in foreign projection is refused; not a Lab regeneration.
EXPECTED_SOURCE_COMMIT = "247deb86220035bed9b276606ce4a2957c5a8d57"
EXPECTED_SOURCE_TREE = "895a18cc0bfed9b0bb6dd66a4e7616cb09c0e039"

PUBLIC_FILES = (
    "LICENSE",
    "SCHEMA.md",
    "OPEN_DEFECTS.md",
    "scripts/estate.py",
    "scripts/selftest.py",
)
GENERATED_FILES = ("README.md",)
MANIFEST_FILE = "provenance.json"
OWNED_FILES = PUBLIC_FILES + GENERATED_FILES + (MANIFEST_FILE,)
OWNED_DIRS = ("scripts",)

MODES = ("100644", "100755")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

MANIFEST_KEYS = (
    "schema",
    "kind",
    "editable_implementation",
    "source_repository",
    "source_commit",
    "source_tree",
    "license",
    "requires",
    "does_not_require",
    "files",
    "generated",
    "manifest",
)
FILE_ROW_KEYS = ("path", "sha256", "git_blob", "mode")
GENERATED_ROW_KEYS = ("path", "sha256")


class CheckError(Exception):
    """Structural refusal (exit 3) or drift (exit 5)."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def file_mode(path: Path) -> str:
    return "100755" if os.lstat(path).st_mode & stat.S_IXUSR else "100644"


def entry_kind(path: Path) -> str:
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "dir"
    return "other"


def walk(root: Path, cur: Path | None = None):
    """Pre-order ``(rel, kind, path)``. Symlinks are reported, never followed."""
    cur = cur or root
    for name in sorted(os.listdir(cur)):
        path = cur / name
        kind = entry_kind(path)
        yield path.relative_to(root).as_posix(), kind, path
        if kind == "dir":
            yield from walk(root, path)


def _pairs_without_duplicates(pairs: list) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate key {key!r}")
        obj[key] = value
    return obj


def strict_json_loads(data: bytes):
    """json.loads that refuses a repeated key at any nesting level."""
    return json.loads(data, object_pairs_hook=_pairs_without_duplicates)


def _hex(value: object, width: int, what: str) -> str:
    pattern = HEX40 if width == 40 else HEX64
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise CheckError(3, f"{what} is not a {width}-hex digest: {value!r}")
    return value


def _safe_relative(value: object, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise CheckError(3, f"{what} must be a non-empty string")
    parts = value.split("/")
    if value.startswith("/") or "\\" in value or any(p in ("", ".", "..") for p in parts):
        raise CheckError(3, f"{what} is not a safe relative path: {value!r}")
    return value


def _closed_mapping(row: object, keys: tuple[str, ...], what: str) -> dict:
    if not isinstance(row, dict):
        raise CheckError(3, f"{what} is not an object")
    extra = set(row) - set(keys)
    missing = [k for k in keys if k not in row]
    if extra or missing:
        raise CheckError(
            3,
            f"{what} fields differ (missing {missing or '[]'}, extra {sorted(extra) or '[]'})",
        )
    return row


def _load_manifest(path: Path) -> dict:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CheckError(3, f"provenance.json unreadable ({exc.strerror})") from None
    try:
        payload = strict_json_loads(raw)
    except ValueError as exc:
        raise CheckError(3, f"provenance.json is not JSON ({exc})") from None
    except json.JSONDecodeError as exc:
        raise CheckError(3, f"provenance.json is not JSON ({exc})") from None
    if not isinstance(payload, dict):
        raise CheckError(3, "provenance.json is not an object")
    extra = set(payload) - set(MANIFEST_KEYS)
    missing = [k for k in MANIFEST_KEYS if k not in payload]
    if extra or missing:
        raise CheckError(
            3,
            "provenance.json fields differ "
            f"(missing {missing or '[]'}, extra {sorted(extra) or '[]'})",
        )
    if payload["schema"] != PROJECTION_SCHEMA:
        raise CheckError(3, f"provenance.json schema mismatch: {payload['schema']!r}")
    if payload["kind"] != "generated-projection":
        raise CheckError(3, f"kind is not generated-projection: {payload['kind']!r}")
    if payload["editable_implementation"] is not False:
        raise CheckError(3, "editable_implementation must be false")
    if payload["source_repository"] != SOURCE_REPOSITORY:
        raise CheckError(
            3, f"source_repository mismatch: {payload['source_repository']!r}"
        )
    commit = _hex(payload["source_commit"], 40, "source_commit")
    tree = _hex(payload["source_tree"], 40, "source_tree")
    if commit != EXPECTED_SOURCE_COMMIT:
        raise CheckError(
            5,
            f"source_commit mismatch: projection says {commit}, "
            f"expected {EXPECTED_SOURCE_COMMIT}",
        )
    if tree != EXPECTED_SOURCE_TREE:
        raise CheckError(
            5,
            f"source_tree mismatch: projection says {tree}, "
            f"expected {EXPECTED_SOURCE_TREE}",
        )
    if payload["license"] != "Apache-2.0":
        raise CheckError(3, f"license mismatch: {payload['license']!r}")
    if payload["requires"] != ["python3"]:
        raise CheckError(3, f"requires mismatch: {payload['requires']!r}")
    if payload["does_not_require"] != [
        "nika-lab",
        "nika-engine",
        "nika-spec",
        "nika-docs",
    ]:
        raise CheckError(3, f"does_not_require mismatch: {payload['does_not_require']!r}")
    if payload["manifest"] != MANIFEST_FILE:
        raise CheckError(3, f"manifest field mismatch: {payload['manifest']!r}")
    return payload


def _load_file_rows(payload: dict) -> list[dict]:
    files = payload["files"]
    if not isinstance(files, list) or len(files) != len(PUBLIC_FILES):
        raise CheckError(3, "files inventory length differs from the owned source set")
    rows = []
    seen: set[str] = set()
    for i, raw in enumerate(files):
        row = _closed_mapping(raw, FILE_ROW_KEYS, f"files[{i}]")
        rel = _safe_relative(row["path"], f"files[{i}].path")
        if rel != PUBLIC_FILES[i]:
            raise CheckError(
                3, f"files[{i}].path is {rel!r}, expected {PUBLIC_FILES[i]!r}"
            )
        if rel in seen:
            raise CheckError(3, f"files lists {rel} twice")
        seen.add(rel)
        _hex(row["sha256"], 64, f"files[{rel}].sha256")
        _hex(row["git_blob"], 40, f"files[{rel}].git_blob")
        if row["mode"] not in MODES:
            raise CheckError(3, f"files[{rel}].mode is not a git file mode: {row['mode']!r}")
        rows.append(row)
    return rows


def _load_generated_rows(payload: dict) -> list[dict]:
    generated = payload["generated"]
    if not isinstance(generated, list) or len(generated) != len(GENERATED_FILES):
        raise CheckError(3, "generated inventory length differs from the owned generated set")
    rows = []
    for i, raw in enumerate(generated):
        row = _closed_mapping(raw, GENERATED_ROW_KEYS, f"generated[{i}]")
        rel = _safe_relative(row["path"], f"generated[{i}].path")
        if rel != GENERATED_FILES[i]:
            raise CheckError(
                3, f"generated[{i}].path is {rel!r}, expected {GENERATED_FILES[i]!r}"
            )
        _hex(row["sha256"], 64, f"generated[{rel}].sha256")
        rows.append(row)
    return rows


def inspect_tree(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for rel, kind, path in walk(root):
        if kind == "dir" and rel in OWNED_DIRS:
            continue
        if kind == "symlink":
            raise CheckError(3, f"symlink not allowed {rel}")
        if kind == "file" and rel in OWNED_FILES:
            found[rel] = path
            continue
        raise CheckError(3, f"unexpected path {rel}")
    missing = [rel for rel in OWNED_FILES if rel not in found]
    if missing:
        raise CheckError(3, f"missing {missing[0]}")
    return found


def verify_bytes(found: dict[str, Path], file_rows: list[dict], generated_rows: list[dict]) -> None:
    declared = {row["path"]: row for row in file_rows}
    for rel in PUBLIC_FILES:
        path = found[rel]
        if entry_kind(path) != "file":
            raise CheckError(3, f"{rel} is not a regular file")
        body = path.read_bytes()
        row = declared[rel]
        actual_sha = sha256_bytes(body)
        actual_blob = git_blob_sha1(body)
        actual_mode = file_mode(path)
        if actual_sha != row["sha256"]:
            raise CheckError(5, f"digest drift {rel}")
        if actual_blob != row["git_blob"]:
            raise CheckError(5, f"git blob drift {rel}")
        if actual_mode != row["mode"]:
            raise CheckError(5, f"mode drift {rel}: {actual_mode} (expected {row['mode']})")
    for row in generated_rows:
        rel = row["path"]
        path = found[rel]
        if entry_kind(path) != "file":
            raise CheckError(3, f"{rel} is not a regular file")
        body = path.read_bytes()
        if sha256_bytes(body) != row["sha256"]:
            raise CheckError(5, f"digest drift {rel}")
        if file_mode(path) != "100644":
            raise CheckError(5, f"mode drift {rel}: {file_mode(path)} (expected 100644)")
    manifest_path = found[MANIFEST_FILE]
    if entry_kind(manifest_path) != "file":
        raise CheckError(3, f"{MANIFEST_FILE} is not a regular file")
    if file_mode(manifest_path) != "100644":
        raise CheckError(
            5, f"mode drift {MANIFEST_FILE}: {file_mode(manifest_path)} (expected 100644)"
        )


def check(root: Path) -> int:
    given = Path(root)
    try:
        if given.is_symlink():
            raise CheckError(3, f"destination {given} is a symlink; refusing to read through it")
        if not given.exists():
            raise CheckError(3, f"missing {given}")
        if not given.is_dir():
            raise CheckError(3, f"not a directory {given}")
        found = inspect_tree(given)
        payload = _load_manifest(found[MANIFEST_FILE])
        file_rows = _load_file_rows(payload)
        generated_rows = _load_generated_rows(payload)
        verify_bytes(found, file_rows, generated_rows)
    except CheckError as exc:
        print(f"estate-projection: {exc.message}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"estate-projection: {exc}", file=sys.stderr)
        return 3
    print(
        f"✓ public estate projection · pin {EXPECTED_SOURCE_COMMIT} · "
        f"tree {EXPECTED_SOURCE_TREE} · {given}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: python3 scripts/check-estate-projection.py [DIR]", file=sys.stderr)
        return 2
    target = Path(args[0]) if args else DEFAULT_ROOT
    return check(target)


if __name__ == "__main__":
    raise SystemExit(main())
