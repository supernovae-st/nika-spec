#!/usr/bin/env python3
"""Bounded regression: scripts/estate.py matches the qualified public projection.

The published source is nika-spec@f14f6872:tools/estate/scripts/estate.py
(historical nika-estate 247deb86, upgrade from 74287c75). This checker
does not fetch the network and does not rebuild tools/estate.

    python3 scripts/test-estate-mirror.py

    exit 0  mirror, pin and provenance agree
    exit 2  bad usage
    exit 3  missing path, symlink, or invalid pin declaration
    exit 5  byte, mode, pin or source drift
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent
HEX40 = re.compile(r"^[0-9a-f]{40}$")

EXPECTED_SPEC_COMMIT = "f14f6872a0d9d3ba12c196810082336c963d2765"
EXPECTED_ESTATE_SOURCE = "247deb86220035bed9b276606ce4a2957c5a8d57"
EXPECTED_PREVIOUS_PIN = "74287c75f3d52ee5cd328b6faaa5fb7eacf171f6"
EXPECTED_SHA256 = "da4e737e27fb5a8d92bfc3d5e7e707f84825556d0c8c2c4af989bc10939123c1"
EXPECTED_MODE = "100755"
PROJECTION_REL = "tools/estate/scripts/estate.py"
MIRROR_REL = "scripts/estate.py"
PIN_REL = "ESTATE_PIN"
PROVENANCE_REL = "tools/estate/provenance.json"


class CheckError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def require_file(root: Path, rel: str) -> Path:
    path = root / rel
    if path.is_symlink():
        raise CheckError(3, f"symlink not allowed {rel}")
    if not path.exists():
        raise CheckError(3, f"missing {rel}")
    if entry_kind(path) != "file":
        raise CheckError(3, f"{rel} is not a regular file")
    return path


def parse_pin(text: str) -> str:
    pin = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if pin is not None:
            raise CheckError(3, "ESTATE_PIN has more than one non-comment line")
        pin = line
    if pin is None:
        raise CheckError(3, "ESTATE_PIN names no revision")
    if not HEX40.fullmatch(pin):
        raise CheckError(3, f"ESTATE_PIN is not a 40-hex digest: {pin!r}")
    return pin


def check_root(root: Path) -> int:
    try:
        pin_path = require_file(root, PIN_REL)
        mirror = require_file(root, MIRROR_REL)
        projection = require_file(root, PROJECTION_REL)
        provenance_path = require_file(root, PROVENANCE_REL)
        pin_text = pin_path.read_text(encoding="utf-8")
        pin = parse_pin(pin_text)
        if pin != EXPECTED_SPEC_COMMIT:
            raise CheckError(
                5,
                f"ESTATE_PIN names {pin}, expected published nika-spec {EXPECTED_SPEC_COMMIT}",
            )
        if EXPECTED_ESTATE_SOURCE not in pin_text:
            raise CheckError(3, "ESTATE_PIN does not record historical nika-estate 247deb86")
        if EXPECTED_PREVIOUS_PIN not in pin_text:
            raise CheckError(3, "ESTATE_PIN does not record the 74287c75 → 247deb86 upgrade")
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CheckError(3, f"provenance.json is not JSON ({exc})") from None
        if provenance.get("source_commit") != EXPECTED_ESTATE_SOURCE:
            raise CheckError(
                5,
                f"projection source_commit is {provenance.get('source_commit')!r}, "
                f"expected {EXPECTED_ESTATE_SOURCE}",
            )
        rows = {row["path"]: row for row in provenance.get("files", []) if isinstance(row, dict)}
        row = rows.get("scripts/estate.py")
        if not row:
            raise CheckError(3, "provenance.json has no scripts/estate.py row")
        if row.get("sha256") != EXPECTED_SHA256 or row.get("mode") != EXPECTED_MODE:
            raise CheckError(5, "provenance scripts/estate.py digest or mode drifted")
        mirror_sha = sha256_file(mirror)
        projection_sha = sha256_file(projection)
        if projection_sha != EXPECTED_SHA256:
            raise CheckError(5, f"digest drift {PROJECTION_REL}")
        if mirror_sha != projection_sha:
            raise CheckError(5, f"digest drift {MIRROR_REL}")
        if file_mode(projection) != EXPECTED_MODE:
            raise CheckError(5, f"mode drift {PROJECTION_REL}: {file_mode(projection)}")
        if file_mode(mirror) != EXPECTED_MODE:
            raise CheckError(5, f"mode drift {MIRROR_REL}: {file_mode(mirror)}")
        if mirror.read_bytes() != projection.read_bytes():
            raise CheckError(5, f"byte mismatch {MIRROR_REL}")
    except CheckError as exc:
        print(f"estate-mirror: {exc.message}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"estate-mirror: {exc}", file=sys.stderr)
        return 3
    print(
        f"✓ scripts/estate.py equals {PROJECTION_REL} · "
        f"nika-spec@{EXPECTED_SPEC_COMMIT} · source {EXPECTED_ESTATE_SOURCE}"
    )
    return 0


def layout_from(root: Path, dest: Path) -> Path:
    for rel in (PIN_REL, MIRROR_REL, PROJECTION_REL, PROVENANCE_REL):
        src = root / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dest


class EstateMirrorTests(unittest.TestCase):
    def test_real_tree_passes(self):
        self.assertEqual(check_root(SPEC_ROOT), 0)

    def test_positive_temp_copy(self):
        with tempfile.TemporaryDirectory(prefix="estate-mirror-ok-") as tmp:
            layout_from(SPEC_ROOT, Path(tmp))
            self.assertEqual(check_root(Path(tmp)), 0)

    def test_byte_mismatch_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-mirror-bytes-") as tmp:
            root = layout_from(SPEC_ROOT, Path(tmp))
            path = root / MIRROR_REL
            path.write_bytes(path.read_bytes() + b"\n")
            self.assertEqual(check_root(root), 5)

    def test_mode_mismatch_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-mirror-mode-") as tmp:
            root = layout_from(SPEC_ROOT, Path(tmp))
            path = root / MIRROR_REL
            os.chmod(path, 0o644)
            self.assertEqual(check_root(root), 5)

    def test_stale_nika_estate_pin_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-mirror-pin-") as tmp:
            root = layout_from(SPEC_ROOT, Path(tmp))
            (root / PIN_REL).write_text(
                "# Bump deliberately: edit this\n"
                f"{EXPECTED_PREVIOUS_PIN}\n"
            )
            self.assertEqual(check_root(root), 5)

    def test_missing_historical_source_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-mirror-hist-") as tmp:
            root = layout_from(SPEC_ROOT, Path(tmp))
            (root / PIN_REL).write_text(
                "# Bump deliberately: edit this\n"
                f"# previous {EXPECTED_PREVIOUS_PIN}\n"
                f"{EXPECTED_SPEC_COMMIT}\n"
            )
            self.assertEqual(check_root(root), 3)

    def test_symlink_mirror_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-mirror-slink-") as tmp:
            root = layout_from(SPEC_ROOT, Path(tmp))
            path = root / MIRROR_REL
            path.unlink()
            os.symlink("estate.py.bak", path)
            self.assertEqual(check_root(root), 3)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--check"]:
        return check_root(SPEC_ROOT)
    if args in ([], ["--test"]):
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    print("usage: python3 scripts/test-estate-mirror.py [--check|--test]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
