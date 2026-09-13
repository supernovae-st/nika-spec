# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("rehearsals", ROOT / "scripts/template-rehearsals.py")
rehearsals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearsals)


class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("canon/templates", "templates"):
            shutil.copytree(ROOT / name, self.root / name)
        self.path = self.root / "templates/rehearsals.yaml"
        self.rows = yaml.safe_load(self.path.read_text())

    def save(self):
        self.path.write_text(yaml.safe_dump(self.rows))

    def test_checked_in_outputs_match_their_sources(self):
        for path, text in rehearsals.render(ROOT).items():
            self.assertEqual(path.read_text(), text, path)

    def test_quoted_multiline_unicode_fill_keeps_structure(self):
        fill = 'A "quote": $HOME\nnext line\\path · é'
        self.rows["rehearsals"][0]["fill"] = fill
        self.save()
        out = rehearsals.render(self.root)
        body = yaml.safe_load(out[self.root / "examples/18-bounded-batch.nika.yaml"])
        self.assertEqual(body["const"]["brief"], fill)
        self.assertEqual(body["tasks"]["process"]["for_each"]["max_parallel"], 2)

    def test_unknown_template_and_traversal_are_refused(self):
        for key, value in (("template", "unknown"), ("example", "../../outside")):
            with self.subTest(key=key):
                self.rows = yaml.safe_load((ROOT / "templates/rehearsals.yaml").read_text())
                self.rows["rehearsals"][0][key] = value
                self.save()
                with self.assertRaises(ValueError):
                    rehearsals.render(self.root)

    def test_duplicate_destination_is_refused(self):
        self.rows["rehearsals"][1]["example"] = self.rows["rehearsals"][0]["example"]
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            rehearsals.render(self.root)

    def test_missing_or_extra_value_slot_is_refused(self):
        path = self.root / "templates/bounded-batch.nika.yaml"
        original = path.read_text()
        for body in (original.replace("<SLOT: the per-item instruction>", "filled"),
                     original.replace("first note", "'<SLOT: another value>'")):
            path.write_text(body)
            with self.assertRaisesRegex(ValueError, "one scalar value slot"):
                rehearsals.render(self.root)

    def test_template_logic_edit_changes_its_lesson(self):
        path = self.root / "templates/bounded-batch.nika.yaml"
        path.write_text(path.read_text().replace("max_parallel: 2", "max_parallel: 1"))
        out = rehearsals.render(self.root)
        self.assertIn("max_parallel: 1", out[self.root / "examples/18-bounded-batch.nika.yaml"])


if __name__ == "__main__":
    unittest.main()
