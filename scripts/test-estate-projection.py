#!/usr/bin/env python3
"""Refusal and positive-control tests for the public Estate projection.

The checker is exercised through its CLI on temporary copies. The stock
selftest of the real committed bundle is also required to pass. Nothing
here reaches Lab, the network, or private paths.

    python3 scripts/test-estate-projection.py
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent
CHECK = SPEC_ROOT / "scripts" / "check-estate-projection.py"
BUNDLE = SPEC_ROOT / "tools" / "estate"
SELFTEST = BUNDLE / "scripts" / "selftest.py"


def run_check(target: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECK), str(target)],
        cwd=SPEC_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def copy_bundle(tmp: Path) -> Path:
    dest = tmp / "bundle"
    shutil.copytree(BUNDLE, dest, symlinks=False)
    return dest


def dump_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


class EstateProjectionTests(unittest.TestCase):
    def test_real_bundle_passes_check(self):
        proc = run_check(BUNDLE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("247deb86220035bed9b276606ce4a2957c5a8d57", proc.stdout)
        self.assertIn("895a18cc0bfed9b0bb6dd66a4e7616cb09c0e039", proc.stdout)
        self.assertEqual(proc.stderr, "")

    def test_real_bundle_stock_selftest(self):
        env = os.environ.copy()
        env["NO_COLOR"] = "1"
        proc = subprocess.run(
            [sys.executable, str(SELFTEST)],
            cwd=BUNDLE,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("17/17", proc.stdout)

    def test_positive_control_on_temp_copy(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-ok-") as tmp:
            bundle = copy_bundle(Path(tmp))
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stderr, "")

    def test_missing_file_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-missing-") as tmp:
            bundle = copy_bundle(Path(tmp))
            (bundle / "LICENSE").unlink()
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("missing LICENSE", proc.stderr)

    def test_extra_file_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-extra-") as tmp:
            bundle = copy_bundle(Path(tmp))
            (bundle / "extra.txt").write_text("no\n")
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("unexpected path extra.txt", proc.stderr)

    def test_symlink_owned_path_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-slink-") as tmp:
            bundle = copy_bundle(Path(tmp))
            target = bundle / "SCHEMA.md"
            owned = bundle / "LICENSE"
            owned.unlink()
            os.symlink(target.name, owned)
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("symlink not allowed LICENSE", proc.stderr)

    def test_symlink_extra_path_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-slink-extra-") as tmp:
            bundle = copy_bundle(Path(tmp))
            os.symlink("LICENSE", bundle / "alias")
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("symlink not allowed alias", proc.stderr)

    def test_altered_digest_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-digest-") as tmp:
            bundle = copy_bundle(Path(tmp))
            path = bundle / "SCHEMA.md"
            path.write_bytes(path.read_bytes() + b"\n")
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 5, proc.stdout + proc.stderr)
            self.assertIn("digest drift SCHEMA.md", proc.stderr)

    def test_mode_drift_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-mode-") as tmp:
            bundle = copy_bundle(Path(tmp))
            path = bundle / "scripts" / "estate.py"
            os.chmod(path, 0o644)
            self.assertFalse(os.lstat(path).st_mode & stat.S_IXUSR)
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 5, proc.stdout + proc.stderr)
            self.assertIn("mode drift scripts/estate.py", proc.stderr)

    def test_duplicate_key_in_provenance_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-dup-") as tmp:
            bundle = copy_bundle(Path(tmp))
            original = (bundle / "provenance.json").read_text()
            # Repeat a key at the root. json.dumps cannot emit this.
            doubled = original.replace(
                '"kind": "generated-projection"',
                '"kind": "generated-projection",\n  "kind": "hand-edit"',
                1,
            )
            self.assertNotEqual(doubled, original)
            (bundle / "provenance.json").write_text(doubled)
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("duplicate key 'kind'", proc.stderr)

    def test_source_commit_trailing_newline_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-nl-") as tmp:
            bundle = copy_bundle(Path(tmp))
            payload = json.loads((bundle / "provenance.json").read_text())
            payload["source_commit"] = payload["source_commit"] + "\n"
            dump_json(bundle / "provenance.json", payload)
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("source_commit is not a 40-hex digest", proc.stderr)

    def test_git_blob_declaration_drift_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-blob-") as tmp:
            bundle = copy_bundle(Path(tmp))
            payload = json.loads((bundle / "provenance.json").read_text())
            payload["files"][0]["git_blob"] = "0" * 40
            dump_json(bundle / "provenance.json", payload)
            proc = run_check(bundle)
            self.assertEqual(proc.returncode, 5, proc.stdout + proc.stderr)
            self.assertIn("git blob drift LICENSE", proc.stderr)

    def test_destination_symlink_refused(self):
        with tempfile.TemporaryDirectory(prefix="estate-proj-destlink-") as tmp:
            root = Path(tmp)
            real = copy_bundle(root)
            link = root / "alias"
            os.symlink(real.name, link)
            proc = run_check(link)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("is a symlink", proc.stderr)

    def test_checker_has_no_lab_or_network_surface(self):
        text = CHECK.read_text()
        self.assertNotIn("estate/imported", text)
        self.assertNotIn("nika-lab-migration", text)
        self.assertNotIn("urllib", text)
        self.assertNotIn("requests", text)
        self.assertNotIn("socket", text)
        self.assertNotIn("http://", text)
        self.assertNotIn("https://", text)


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
