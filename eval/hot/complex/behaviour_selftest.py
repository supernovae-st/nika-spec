#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The rehearsal can fail: a sabotaged reference, a silenced near-miss and a closed gap must each turn it red.

    NIKA_BIN=/path/to/nika python3 -O eval/hot/complex/behaviour_selftest.py

The rehearsal controls need an engine, so they are an offline proof and not a CI step; they skip, visibly,
when `NIKA_BIN` is unset. The comparison behind the licence-header gap needs none and always runs.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import judge

ENGINE = os.environ.get("NIKA_BIN")
HARNESS = Path(__file__).resolve().parent / "behaviour.py"


@unittest.skipUnless(ENGINE, "set NIKA_BIN to an engine binary; nothing was rehearsed")
class TheRehearsalCanFail(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="complex-behaviour-selftest-")
        self.root = Path(self.temp.name) / "complex"
        shutil.copytree(judge.ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))
        self.addCleanup(self.temp.cleanup)

    def only(self, *ids):
        """Keep the named scenarios so that one mutation costs seconds, not the whole corpus."""
        path = self.root / "scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["scenarios"] = [s for s in data["scenarios"] if s["id"] in ids]
        kept = {c["file"] for s in data["scenarios"] for c in s["candidates"]}
        kept_cases = {c["id"] for s in data["scenarios"] for c in s["behaviour"] + s.get("compile_door", [])}
        data["retained_gaps"] = [g for g in data["retained_gaps"]
                                 if g["reproduce"].get("file") in kept or g["reproduce"].get("candidate") in kept
                                 or g["reproduce"].get("case") in kept_cases and g["reproduce"]["kind"] == "compile_door"]
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def manifest(self, change):
        path = self.root / "scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def rewrite(self, relative, old, new):
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, f"{relative}: the mutation must apply exactly once")
        path.write_text(text.replace(old, new), encoding="utf-8")

    def rehearse(self):
        result = subprocess.run([sys.executable, str(HARNESS), "--engine", ENGINE, "--root", str(self.root)],
                                capture_output=True, text=True, check=False)
        return result.returncode, (json.loads(result.stdout) if result.stdout.strip().startswith("{") else
                                   {"failures": [result.stderr]})

    def test_the_kept_scenarios_are_green_as_committed(self):
        self.only("X10", "X12")
        code, summary = self.rehearse()
        self.assertEqual((code, summary["failures"]), (0, []))

    def test_a_reference_that_stops_withholding_the_total_is_rejected(self):
        self.only("X02")
        self.rewrite("workflows/x02/reference.nika.yaml", "(if .complete then ([$r.results[] | .cents] | add) else null end)",
                     "([$r.results[] | select(. != null) | .cents] | add)")
        code, summary = self.rehearse()
        self.assertEqual(code, 1)
        self.assertTrue(any("reference.nika.yaml: a correct candidate is rejected by ['X02-B1']" in f
                            for f in summary["failures"]), summary["failures"])

    def test_a_near_miss_that_is_no_longer_declared_rejected_is_caught(self):
        self.only("X12")
        self.manifest(lambda d: d["scenarios"][0]["candidates"][1].pop("caught_by_behaviour"))
        code, summary = self.rehearse()
        self.assertEqual(code, 1)
        self.assertTrue(any("expected rejection by [], observed ['X12-B2']" in f for f in summary["failures"]),
                        summary["failures"])

    def test_an_expectation_that_is_wrong_rejects_the_reference(self):
        self.only("X09")
        self.manifest(lambda d: d["scenarios"][0]["behaviour"][0]["expect"]["outputs_exact"].update(selected="quote-b"))
        code, summary = self.rehearse()
        self.assertEqual(code, 1)
        self.assertTrue(any("reference.nika.yaml: a correct candidate is rejected" in f for f in summary["failures"]))

    def test_an_engine_check_verdict_that_drifts_is_caught(self):
        self.only("X07")
        self.manifest(lambda d: d["scenarios"][0]["candidates"][3].update(engine_check="valid"))
        code, summary = self.rehearse()
        self.assertEqual(code, 1)
        self.assertTrue(any("engine check expected valid, observed NIKA-SEC-004" in f for f in summary["failures"]))

    def test_a_gap_that_closed_must_be_retired_not_left_as_expected_fail(self):
        self.only("X01")
        # Point the retained gap at a file the engine DOES refuse: the expected behaviour is then observed.
        self.manifest(lambda d: d["retained_gaps"][0]["reproduce"].update(
            file="workflows/x01/refused-ordering-only-gate.nika.yaml"))
        code, summary = self.rehearse()
        self.assertEqual(code, 1)
        self.assertTrue(any("KG01: the expected behaviour is now observed" in f for f in summary["failures"]))

    def test_a_candidate_that_needs_a_program_is_never_executed(self):
        self.only("X08")
        self.manifest(lambda d: d["scenarios"][0]["candidates"][3].update(behaviour=True))
        code, summary = self.rehearse()
        self.assertEqual(code, 1)
        self.assertTrue(any("declared runnable, and it declares ['exec'] authority" in f for f in summary["failures"]),
                        summary["failures"])


class TheHeaderGapIsJudgedAgainstTheBase(unittest.TestCase):
    """No engine needed: the comparison itself must be able to say both yes and no."""

    def test_the_gap_closes_only_when_the_edited_file_keeps_the_first_line_of_the_base(self):
        import behaviour
        corpus = judge.load()
        row = next(g for g in corpus["retained_gaps"] if g["id"] == "KG03")
        header = (judge.ROOT / row["reproduce"]["expect_first_line_of"]).read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(header.startswith("#"), "the base opens with its licence header")
        self.assertTrue(behaviour.gap(None, corpus, row, {"X06-C2": {"first_line": header}}, judge.ROOT))
        self.assertFalse(behaviour.gap(None, corpus, row, {"X06-C2": {"first_line": "const:"}}, judge.ROOT))
        self.assertFalse(behaviour.gap(None, corpus, row, {"X06-C2": {"first_line": None}}, judge.ROOT))


if __name__ == "__main__":
    unittest.main()
