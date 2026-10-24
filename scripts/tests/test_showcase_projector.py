# SPDX-License-Identifier: Apache-2.0
"""The showcase counts the docs print derive from each job's own header."""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("showcase", ROOT / "scripts/showcase-projector.py")
showcase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(showcase)


def snippet_counts(text: str) -> dict[str, int]:
    return {key: int(value) for key, value in re.findall(r"^  (\w+): (\d+),$", text, re.MULTILINE)}


class ShowcaseTierTests(unittest.TestCase):
    def test_every_shipped_job_lands_in_exactly_one_tier(self):
        workflows = showcase.load_showcase()
        counts = snippet_counts(showcase.render_showcase_snippet(workflows))
        self.assertEqual(counts["count"], len(workflows))
        tiers = [counts[f"t{n}"] for n in range(1, 5)]
        self.assertEqual(sum(tiers), counts["count"])
        for n, value in enumerate(tiers, start=1):
            with self.subTest(tier=n):
                self.assertGreater(value, 0)

    def test_tier_is_read_from_the_header_not_the_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            jobs = Path(temp)
            (jobs / "t4-looks-like-a-prefix.nika").write_text("# showcase · T1 starter · x\nnika: a\n")
            (jobs / "plain.nika").write_text("# showcase · T3 fan-out · y\nnika: b\n")
            with patch.object(showcase, "JOBS_DIR", jobs):
                counts = snippet_counts(showcase.render_showcase_snippet(
                    {"t4-looks-like-a-prefix.nika": "", "plain.nika": ""}))
        self.assertEqual(counts, {"count": 2, "t1": 1, "t2": 0, "t3": 1, "t4": 0})

    def test_a_job_without_a_tier_header_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            jobs = Path(temp)
            (jobs / "untiered.nika").write_text("# a job with no tier line\nnika: c\n")
            with patch.object(showcase, "JOBS_DIR", jobs), \
                 contextlib.redirect_stderr(io.StringIO()) as message, \
                 self.assertRaises(SystemExit) as stop:
                showcase.render_showcase_snippet({"untiered.nika": ""})
        self.assertEqual(stop.exception.code, 2)
        self.assertIn("untiered.nika", message.getvalue())


if __name__ == "__main__":
    unittest.main()
