#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Adversarial command-runner laws, using output doubles (no engine claim)."""
import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "runtime_differential", pathlib.Path(__file__).with_name("runtime-differential.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def event(kind, **fields):
    return {"kind": kind, "fields": [{"key": k, "value": v} for k, v in fields.items()]}


def stream(value=1, attempts=1, status="success"):
    return [event("workflow_started"), event("task_completed" if status == "success" else "task_failed",
            task="a", outcome=json.dumps({"class": status, "payload": {
                "value": value, "attempts": attempts}})),
            event("workflow_completed" if status == "success" else "workflow_failed"),
            {"kind": "run_settled", "status": "succeeded" if status == "success" else "failed"}]


class RunJudgeLaws(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nika-judge-law-")
        self.addCleanup(self.tmp.cleanup)
        self.fixture = pathlib.Path(self.tmp.name) / "case"
        self.fixture.mkdir()
        (self.fixture / "input.nika").write_text("nika: judge-law\n")

    def judge(self, output, expected=None, code=0):
        expected = expected or {"workflow_state": "success", "tasks": {
            "a": {"status": "success", "output": 1}}}
        (self.fixture / "expected-run.json").write_text(json.dumps(expected))
        raw = output if isinstance(output, str) else "\n".join(json.dumps(e) for e in output)
        with patch.object(runner.subprocess, "run") as invoke:
            invoke.return_value = subprocess.CompletedProcess([], code, raw, "")
            return runner.judge_run("output-double", self.fixture)

    def assert_rejected(self, *args, **kwargs):
        try:
            differences = self.judge(*args, **kwargs)
        except (ValueError, RuntimeError):
            return
        self.assertTrue(differences, "ambiguous or contradictory evidence agreed")

    def test_typed_json_equality_and_numeric_equivalence(self):
        for wanted, actual in [(1, True), (0, False), ({"x": [1]}, {"x": [True]}),
                               ([1, 2], [2, 1]), ("1", 1)]:
            with self.subTest(wanted=wanted, actual=actual):
                self.assert_rejected(stream(actual), {"tasks": {"a": {
                    "status": "success", "output": wanted}}})
        for wanted, actual in [(1, 1.0), ({"x": 1, "y": [2]}, {"y": [2.0], "x": 1.0})]:
            self.assertEqual(self.judge(stream(actual), {"tasks": {"a": {
                "status": "success", "output": wanted}}}), [])

    def test_attempts_are_integer_counts(self):
        for attempts in [True, 1.0, "1", -1]:
            with self.subTest(attempts=attempts):
                self.assert_rejected(stream(attempts=attempts), {"tasks": {
                    "a": {"status": "success", "attempts": 1}}})
        self.assertEqual(self.judge(stream(attempts=1)), [])

    def test_decimal_comparison_does_not_round_the_evidence(self):
        rows = stream()
        rows[1]["fields"][1]["value"] = (
            '{"class":"success","payload":{"value":1.00000000000000001,"attempts":1}}')
        self.assert_rejected(rows)
        for a, b in [("1.00000000000000001", "1"), ("1e-999", "0")]:
            self.assertFalse(runner.json_equal(runner.strict_json(a), runner.strict_json(b)))
        self.assertEqual(runner.json_text(runner.strict_json('{"x":[1.00000000000000001]}')),
                         '{"x":[1.00000000000000001]}')

    def test_contains_uses_json_for_non_strings(self):
        for value, text in [(True, "true"), ({"ok": True}, '"ok":true'), ([None], "null")]:
            self.assertEqual(self.judge(stream(value), {"tasks": {
                "a": {"status": "success", "output_contains": text}}}), [])
        self.assert_rejected(stream(True), {"tasks": {
            "a": {"status": "success", "output_contains": "True"}}})
        self.assertEqual(self.judge(stream("True"), {"tasks": {
            "a": {"status": "success", "output_contains": "True"}}}), [])

    def test_ambiguous_json_and_event_fields_never_overwrite(self):
        raw = "\n".join(json.dumps(e) for e in stream())
        for altered in [raw.replace('"kind": "task_completed"',
                                    '"kind": "task_failed", "kind": "task_completed"'),
                        raw + '\n{"kind":', raw + '\nnot-json',
                        raw.replace('"value": "a"', '"value": "b", "value": "a"')]:
            with self.subTest(raw=altered):
                self.assert_rejected(altered)
        for outcome in ['{"class":"failure","class":"success","payload":{"value":1}}',
                        '{"class":"success","payload":{"value":NaN}}',
                        '{"class":"success","payload":{"value":1e999}}', "{"]:
            rows = stream()
            rows[1]["fields"][1]["value"] = outcome
            self.assert_rejected(rows)
        rows = stream()
        rows[1]["fields"].insert(0, {"key": "task", "value": "other"})
        self.assert_rejected(rows)

    def test_terminal_claims_cannot_conflict_or_repeat(self):
        for index in [1, 2, 3]:
            rows = stream()
            rows.insert(index, rows[index])
            self.assert_rejected(rows)
        rows = stream()
        rows[1]["kind"] = "task_failed"
        self.assert_rejected(rows)
        rows = stream()
        rows[-1]["status"] = "failed"
        self.assert_rejected(rows)
        rows = stream()
        rows[1], rows[2] = rows[2], rows[1]
        self.assert_rejected(rows)
        self.assert_rejected(stream() + [{"error": {"code": "NIKA-X"}}])

    def test_exit_and_settlement_are_part_of_the_claim(self):
        for code in [-9, 139, 1]:
            self.assert_rejected(stream(), code=code)
        self.assert_rejected(stream()[:-1])
        self.assert_rejected(stream()[1:])
        failure = {"workflow_state": "failure", "tasks": {"a": {"status": "failure"}}}
        self.assert_rejected(stream(status="failure"), failure, code=0)
        self.assertEqual(self.judge(stream(status="failure"), failure, code=1), [])

    def test_invalid_layout_is_rejected_before_engine_call(self):
        (self.fixture / "expected-run.json").write_text('{"workflow_state":"success"}')
        for missing_input in [False, True]:
            extra = self.fixture / "expected-verify.json"
            if missing_input:
                extra.unlink()
                (self.fixture / "input.nika").unlink()
            else:
                extra.write_text('{"verdict":"forged"}')
            with patch.object(runner.subprocess, "run") as invoke:
                with self.assertRaises(runner.InvalidFixture):
                    runner.judge_run("output-double", self.fixture)
                invoke.assert_not_called()

    def test_misnamed_fixture_does_not_disappear_beside_valid_fixture(self):
        (self.fixture / "expected-run.json").write_text('{"workflow_state":"success"}')
        broken = self.fixture.parent / "misspelled"
        broken.mkdir()
        (broken / "input.nika").write_text("nika: misspelled\n")
        (broken / "expected-runs.json").write_text('{"workflow_state":"success"}')
        with patch.object(runner, "RUNTIME", self.fixture.parent), \
                patch.object(runner, "judge_run", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(runner.main(["runner"]), 1)
        self.assertIn("FIXTURE-ERROR", output.getvalue())
        self.assertIn("misspelled", output.getvalue())

    def test_trace_assertion_names_cannot_be_silently_ignored(self):
        (self.fixture / "trace.ndjson").write_text("{}\n")
        for key, value in [("prolouge", {"absent": ["inputs"]}),
                           ("costReplay", "refused"), ("item", {"fan": []}),
                           ("route_identity", "unsupported-claim")]:
            with self.subTest(key=key):
                (self.fixture / "expected-verify.json").write_text(
                    json.dumps({"verdict": "clean", key: value}))
                with patch.object(runner.subprocess, "run") as invoke:
                    invoke.return_value = subprocess.CompletedProcess([], 0, "OK", "")
                    with self.assertRaises(runner.InvalidFixture):
                        runner.judge_trace("output-double", self.fixture)
                    invoke.assert_not_called()
        expected = {"verdict": "clean", "note": "descriptive only"}
        (self.fixture / "expected-verify.json").write_text(json.dumps(expected))
        with patch.object(runner.subprocess, "run") as invoke:
            invoke.return_value = subprocess.CompletedProcess([], 0, "OK", "")
            self.assertEqual(runner.judge_trace("output-double", self.fixture), [])
            invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
