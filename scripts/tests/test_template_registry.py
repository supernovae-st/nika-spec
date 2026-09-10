# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("registry", ROOT / "scripts/template-registry.py")
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "canon/templates").mkdir(parents=True)
        (self.root / "templates").mkdir()
        (self.root / "templates/example.nika.yaml").write_text("nika: example\n")
        self.path = self.root / "canon/templates/registry.yaml"
        self.path.write_text("# Preserve this comment\ntemplates:\n  - id: example\n    source_path: templates/example.nika.yaml\n    source_digest: sha256:old\n    notes: keep\n")
    def test_detects_and_repairs_hash_without_changing_metadata(self):
        result, changes = registry.project(self.root)
        self.assertEqual(len(changes), 1)
        self.assertIn("# Preserve this comment", result)
        self.assertIn("notes: keep", result)
        self.assertIn("sha256:old", self.path.read_text())
        self.path.write_text(result)
        self.assertEqual(registry.project(self.root)[1], [])
    def test_new_unregistered_template_refused(self):
        (self.root / "templates/unknown.nika.yaml").write_text("nika: unknown")
        with self.assertRaisesRegex(ValueError, "inventory"):
            registry.project(self.root)
    def test_duplicate_refused(self):
        self.path.write_text(self.path.read_text() + self.path.read_text().split("templates:\n")[1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            registry.project(self.root)
    def test_escaped_path_refused(self):
        self.path.write_text(self.path.read_text().replace("templates/example.nika.yaml", "../outside"))
        with self.assertRaisesRegex(ValueError, "Invalid template"):
            registry.project(self.root)
    def test_missing_file_refused_before_write(self):
        before = self.path.read_bytes()
        (self.root / "templates/example.nika.yaml").unlink()
        with self.assertRaises(FileNotFoundError):
            registry.project(self.root)
        self.assertEqual(self.path.read_bytes(), before)

if __name__ == "__main__":
    unittest.main()
