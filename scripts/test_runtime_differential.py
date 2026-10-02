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


UNSEALED = "UNSEALED — no run_sealed frame: the run was not signed"
WITNESS = runner.WITNESS + ": the\n  permit witness is absent (NEP-0007)"
SEALED = {"tier": "sealed", "key_id": "k1", "source": "a trusted signer"}
FORGED_SEAL = {"tier": "forged", "reason": "the run_sealed signature does not verify"}
ANCHORED = {"tier": "anchored", "log_index": "17", "tree_size": "42",
            "gen_time": "2026-10-01T00:00:00Z"}
GAP = {"tier": "gap", "reason": "the checkpoint does not cover the head"}
UNRECORDED = "COST-REPLAY — unrecorded · the boot frame pins no pricing table"
REFUSED = "COST-REPLAY — REFUSED · the pinned pricing table is not this engine's"
REPLAYED = ("COST-REPLAY — the pinned pricing table is this engine's (pin)\n"
            "  the budget verdict re-judged from the journaled dollars (re-pricing)")
BROKEN = ["BROKEN at line 4 — recorded chain 0123 · computed 4567",
          "  every line from here on is unverified"]
BURIED = ["TAMPERED — 9 events · chain intact · head 0123abcd",
          "  the chain covers every line, and one of them is a SEAL with lines after it",
          "SEAL BURIED — the journal carries a run_sealed frame at line 8 with 1 line after it"]
LINE_BOUND = ["line 2 is 1048890 bytes — beyond the verifier's line bound (1048576 bytes)",
              "  the DoS class, refused before any parse (F-P1)"]
ROWS = [{"index": 0, "item": "a", "status": "failed"},
        {"index": 1, "item": "b", "status": "cancelled"}]
CLAIMS = ["clean", "finding", "incomplete", "forged", "refused"]


def ladder(trace, lines=(UNSEALED,), code=0, headline="intact", liveness=None, tier="ok",
           seal=None, anchor=None, replay=None, **extra):
    """A verify v1 ladder report, shaped as the reference engine projects it."""
    document = {"verify_version": 1, "trace": trace, "tier": tier, "exit": code,
                "chain": {"events": 9, "head": "0123abcd", "headline": headline,
                          "liveness": liveness},
                "seal": seal or {"tier": "unsealed"},
                "anchor": anchor or {"tier": "not-present"},
                "replay": replay or {"tier": "not-asked"}, "lines": list(lines)}
    document.update(extra)
    return document


def finish(trace, tier, code, lines, **extra):
    """A verify v1 non-ladder report: the base fields only."""
    document = {"verify_version": 1, "trace": trace, "tier": tier, "exit": code,
                "lines": list(lines)}
    document.update(extra)
    return document


def file_bound(trace, size=268435457, bound=268435456):
    return (f"{trace}: {size} bytes — over the journal bound ({bound} bytes · NEP-0012 law 1 · "
            "a file beyond it is not a run this engine produced)")


def projection(trace, items=ROWS, version=2, **extra):
    """A `trace outputs --json` document whose task `fan` carries `items`."""
    document = {"outputs_version": version, "trace": trace, "state": "completed",
                "liveness": None,
                "tasks": [{"id": "fan", "verb": "invoke", "status": "ok", "cause": "normal",
                           "error_code": None, "error_message": None, "recovered_from": None,
                           "integrity_source": None, "warning": None, "items": items}]}
    document.update(extra)
    return document


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
        report = ladder(str((self.fixture / "trace.ndjson").resolve()))
        with patch.object(runner.subprocess, "run") as invoke:
            invoke.return_value = subprocess.CompletedProcess([], 0, json.dumps(report), "")
            self.assertEqual(runner.judge_trace("output-double", self.fixture), [])
            invoke.assert_called_once()


class TraceDoorCase(unittest.TestCase):
    """One staged journal; every engine reply is an output double (no engine claim)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nika-trace-door-")
        self.addCleanup(self.tmp.cleanup)
        self.fixture = pathlib.Path(self.tmp.name) / "case"
        self.fixture.mkdir()
        self.journal = self.fixture / "trace.ndjson"
        self.journal.write_text('{"kind":"workflow_started","fields":[]}\n')
        self.trace = str(self.journal.resolve())
        self.calls = []

    def reply(self, code, stdout="", stderr=""):
        """A command's output double: a dict is one compact document, and a dict on
        stderr is wrapped in the exact ENV frame."""
        if isinstance(stdout, dict):
            stdout = json.dumps(stdout)
        if isinstance(stderr, dict):
            stderr = "nika: " + json.dumps(stderr)
        return subprocess.CompletedProcess([], code, stdout, stderr)

    def outcome(self, expected, *replies):
        """The runner's class for this fixture; the issued commands land in self.calls."""
        (self.fixture / "expected-verify.json").write_text(json.dumps(expected))
        with patch.object(runner.subprocess, "run", side_effect=list(replies)) as invoke:
            try:
                differences = runner.judge_trace("output-double", self.fixture)
                result = "DIVERGE" if differences else "AGREE"
            except runner.UnsupportedFixture:
                result = "UNSUPPORTED"
            finally:
                self.calls = [call.args[0] for call in invoke.call_args_list]
        return result

    def verdict(self, verdict, code, stdout="", stderr="", **expected):
        return self.outcome({"verdict": verdict, **expected}, self.reply(code, stdout, stderr))

    def framed(self, verdict, code, document, **expected):
        """The P1 frame for this exit: stdout for 0, 2 and 5; `nika: ` on stderr for 3."""
        if code == 3:
            return self.verdict(verdict, code, "", document, **expected)
        return self.verdict(verdict, code, document, **expected)


class VerifyFamilyLaws(TraceDoorCase):
    """Each admitted family agrees with its own verdict and with no other."""

    def assert_only(self, verdict, code, document):
        for claim in CLAIMS:
            with self.subTest(tier=document["tier"], claim=claim):
                self.assertEqual(self.framed(claim, code, document),
                                 "AGREE" if claim == verdict else "DIVERGE")

    def test_passing_ladders_are_clean_or_finding(self):
        t = self.trace
        sealed = ["SEALED — the run_sealed signature verifies · key k1 (trusted)",
                  "ANCHORED — no sidecar (`nika trace anchor` notarizes the head)",
                  "REPLAYED — not attempted (pass --replay <fresh.ndjson>)"]
        anchored = ["SEALED — the run_sealed signature verifies · key k1 (trusted)",
                    "ANCHORED — rekor index 17 · checkpoint + inclusion proof verified offline\n"
                    "  rfc3161 gen_time 2026-10-01T00:00:00Z (the trusted time)",
                    "REPLAYED — not attempted (pass --replay <fresh.ndjson>)"]
        self.assert_only("clean", 0, ladder(t))
        self.assert_only("clean", 0, ladder(t, sealed, tier="sealed", seal=SEALED))
        self.assert_only("clean", 0, ladder(t, anchored, tier="anchored", seal=SEALED,
                                            anchor=ANCHORED))
        self.assert_only("finding", 0, ladder(t, [UNSEALED, WITNESS, UNRECORDED]))

    def test_incomplete_has_its_own_exit_and_a_liveness(self):
        for liveness in ["alive", "dead", "unknown"]:
            self.assert_only("incomplete", 5, ladder(
                self.trace, [UNSEALED, "the writer lease is no longer held (recorded pid 7)"], 5,
                headline="incomplete", liveness=liveness))

    def test_positive_forgery_reports(self):
        t = self.trace
        for document in [
            ladder(t, ["SEAL FORGED — the signature does not verify"], 2, seal=FORGED_SEAL),
            ladder(t, ["SEAL FORGED — the signature does not verify", "no liveness record"], 2,
                   headline="incomplete", liveness="unknown", seal=FORGED_SEAL),
            ladder(t, ["SEALED — the run_sealed signature verifies · key k1 (trusted)",
                       "ANCHOR FORGED — the checkpoint does not cover the head",
                       "  reported tier: SEALED (the anchor vouches for nothing)"], 2,
                   tier="sealed", seal=SEALED, anchor=GAP),
            finish(t, "broken", 2, BROKEN),
            finish(t, "buried-seal", 2, BURIED),
        ]:
            self.assert_only("forged", 2, document)

    def test_decode_bound_refusals(self):
        self.assert_only("refused", 2, finish(self.trace, "line-over-long", 2, LINE_BOUND))
        self.assert_only("refused", 3, finish(self.trace, "refused", 3, [file_bound(self.trace)]))


class EnvControlLaws(TraceDoorCase):
    """Known missing or unusable evidence agrees with no fixture verdict."""

    def test_env_classes_are_never_forged_or_refused(self):
        t = self.trace
        for document in [
            finish(t, "refused", 3, ["no trusted key: the keyring is unreadable"]),
            finish(t, "refused", 3, [file_bound(t, 10, 20)]),
            finish(t, "refused", 3, [file_bound("/elsewhere/trace.ndjson")]),
            finish(t, "refused", 3, [file_bound(t), "  a second line"]),
            finish(t, "unchained", 3, [f"unchained — {t} predates the chain (pre-0.96 journal)"]),
            finish(t, "empty", 3, [f"{t}: no events"]),
            finish(t, "unreadable", 3, [f"{t}:1: not a journal — the line is not valid JSON"]),
            ladder(t, ["SEAL UNATTRIBUTABLE — no trusted key"], 3,
                   seal={"tier": "unattributable", "reason": "no trusted key"}),
        ]:
            for claim in CLAIMS:
                with self.subTest(tier=document["tier"], lines=document["lines"], claim=claim):
                    self.assertEqual(self.framed(claim, 3, document), "DIVERGE")


class TransportLaws(TraceDoorCase):
    """One report in the frame its exit selects; nothing else is evidence."""

    def test_no_single_framed_report_is_never_a_verdict(self):
        report = json.dumps(finish(self.trace, "broken", 2, BROKEN))
        self.assertEqual(self.verdict("forged", 2, report), "AGREE")
        for code, stdout, stderr in [
            (2, "", ""), (2, " \n", ""), (2, "error: unexpected argument '--json'", ""),
            (2, "\n".join(BROKEN), ""), (2, report + report, ""), (2, report + "\ntrailer", ""),
            (2, "", report), (2, "", "nika: " + report), (2, report, "warning: a newer engine"),
            (2, "log: start\n" + report, ""), (1, report, ""), (4, report, ""),
            (139, report, ""),
        ]:
            with self.subTest(code=code, stdout=stdout[:30], stderr=stderr[:30]):
                self.assertEqual(self.verdict("forged", code, stdout, stderr), "DIVERGE")

    def test_the_env_frame_is_exact(self):
        report = json.dumps(finish(self.trace, "refused", 3, [file_bound(self.trace)]))
        for stdout, stderr in [("", "nika: " + report), ("", "nika: " + report + "\n\n"),
                               ("\n", "nika: " + report)]:
            with self.subTest(stdout=stdout, stderr=stderr[:20]):
                self.assertEqual(self.verdict("refused", 3, stdout, stderr), "AGREE")
        for stdout, stderr in [("", report), ("", "nika:" + report),
                               ("", "nika: nika: " + report), ("", " nika: " + report),
                               ("", "NIKA: " + report), ("", "warning\nnika: " + report),
                               ("", "nika: " + report + " tail"), (report, ""),
                               (report, "nika: " + report)]:
            with self.subTest(stdout=stdout[:20], stderr=stderr[:20]):
                self.assertEqual(self.verdict("refused", 3, stdout, stderr), "DIVERGE")

    def test_outer_whitespace_is_not_a_second_document(self):
        self.assertEqual(self.verdict("clean", 0, "\n " + json.dumps(ladder(self.trace)) + "\n\n"),
                         "AGREE")

    def test_signals_and_missing_engines_are_engine_errors(self):
        with self.assertRaises(RuntimeError):
            self.verdict("forged", -9, json.dumps(finish(self.trace, "broken", 2, BROKEN)))
        (self.fixture / "expected-verify.json").write_text('{"verdict":"clean"}')
        for failure in [FileNotFoundError("nika"), subprocess.TimeoutExpired(["nika"], 120)]:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(runner.subprocess, "run", side_effect=failure):
                    with self.assertRaises(type(failure)):
                        runner.judge_trace("output-double", self.fixture)


class JsonEvidenceLaws(TraceDoorCase):
    """Strict JSON: one object, unique members at every depth, finite numbers, UTF-8."""

    def test_ambiguous_or_non_object_documents_never_agree(self):
        clean = json.dumps(ladder(self.trace))
        for stdout in [
            clean.replace('"tier": "ok"', '"tier": "broken", "tier": "ok"'),
            clean.replace('"headline": "intact"', '"headline": "torn", "headline": "intact"'),
            "[" + clean + "]", '"clean"', "null", "1",
            clean.replace('"events": 9', '"events": NaN'),
            clean.replace('"events": 9', '"events": Infinity'),
            clean.replace('"events": 9', '"events": 1e999'),
            clean.replace('"verify_version": 1', '"verify_version": true'),
            clean.replace('"verify_version": 1', '"verify_version": 1.0'),
            clean.replace('"verify_version": 1', '"verify_version": "1"'),
        ]:
            with self.subTest(stdout=stdout[:60]):
                self.assertEqual(self.verdict("clean", 0, stdout), "DIVERGE")
        for raw in [clean.encode() + b"\xff", b"\xef\xbb\xbf" + clean.encode()]:
            with self.subTest(raw=raw[:8]):
                self.assertEqual(self.verdict("clean", 0, raw), "DIVERGE")

    def test_another_version_is_unsupported_and_new_fields_are_additive(self):
        t = self.trace
        self.assertEqual(self.verdict("clean", 0, ladder(t, verify_version=2)), "UNSUPPORTED")
        self.assertEqual(self.verdict("clean", 0, ladder(t, producer={"build": "x"})), "AGREE")
        chain = {**ladder(t)["chain"], "head_full": "0123abcd" * 8}
        self.assertEqual(self.verdict("clean", 0, ladder(t, chain=chain)), "AGREE")


class IdentityAndTypeLaws(TraceDoorCase):
    """The report binds this journal and this exit, with every known field typed."""

    def test_subject_exit_and_fields_are_bound(self):
        t = self.trace
        base = ladder(t)
        other = str(pathlib.Path(self.tmp.name) / "other" / "trace.ndjson")
        for label, document in [
            ("same basename, another journal", ladder(other)),
            ("relative subject", ladder("trace.ndjson")),
            ("absent subject", {k: v for k, v in base.items() if k != "trace"}),
            ("boolean exit", ladder(t, code=False)),
            ("decimal exit", {**base, "exit": 0.0}),
            ("string exit", ladder(t, code="0")),
            ("another exit", ladder(t, code=2)),
            ("empty tier", ladder(t, tier="")),
            ("missing chain", {k: v for k, v in base.items() if k != "chain"}),
            ("missing seal", {k: v for k, v in base.items() if k != "seal"}),
            ("boolean events", {**base, "chain": {**base["chain"], "events": True}}),
            ("negative events", {**base, "chain": {**base["chain"], "events": -1}}),
            ("empty head", {**base, "chain": {**base["chain"], "head": ""}}),
            ("liveness on an intact chain", ladder(t, liveness="alive")),
            ("missing liveness", {**base, "chain": {k: v for k, v in base["chain"].items()
                                                    if k != "liveness"}}),
            ("scalar line", ladder(t, [UNSEALED, 1])),
            ("string lines", {**base, "lines": UNSEALED}),
            ("numeric tree size", ladder(t, tier="anchored", seal=SEALED,
                                         anchor={**ANCHORED, "tree_size": 42})),
            ("untyped seal key", ladder(t, tier="sealed",
                                        seal={"tier": "sealed", "key_id": 1, "source": "x"})),
        ]:
            with self.subTest(label=label):
                self.assertEqual(self.framed("clean", 0, document), "DIVERGE")


class ContradictionLaws(TraceDoorCase):
    """Typed legs, exit and owned lines must tell one story."""

    def test_contradictory_reports_never_agree(self):
        t = self.trace
        for label, code, document in [
            ("intact chain at exit 5", 5, ladder(t, code=5)),
            ("incomplete chain at exit 0", 0, ladder(t, headline="incomplete", liveness="dead")),
            ("incomplete sealed chain", 5, ladder(t, code=5, headline="incomplete",
                                                  liveness="dead", tier="sealed", seal=SEALED)),
            ("forged leg at exit 0", 0, ladder(t, ["SEAL FORGED — x"], seal=FORGED_SEAL)),
            ("forged leg without its line", 2, ladder(t, [UNSEALED], 2, seal=FORGED_SEAL)),
            ("refusing line beside a clean ladder", 0, ladder(t, [UNSEALED, "ANCHOR FORGED — x"])),
            ("headline line in a ladder", 0, ladder(t, [UNSEALED, "OK — 9 events · chain intact"])),
            ("bound report in a ladder", 0, ladder(t, [LINE_BOUND[0]])),
            ("attained tier above its seal", 0, ladder(t, tier="sealed")),
            ("required anchor", 3, ladder(t, code=3, tier="sealed", seal=SEALED,
                                          anchor={"tier": "required"})),
            ("replayed without --replay", 0, ladder(t, replay={"tier": "replayed"})),
            ("diverged without --replay", 2, ladder(t, code=2,
                                                    replay={"tier": "diverged", "reason": "x"})),
            ("not attempted without --replay", 0,
             ladder(t, replay={"tier": "not-attempted", "reason": "x"})),
            ("replayed top tier", 0, ladder(t, tier="replayed")),
            ("buried leg in a ladder", 2, ladder(t, ["SEAL BURIED — x"], 2,
                                                 seal={"tier": "buried", "line": 8, "trailing": 1})),
            ("broken report with a ladder", 2, finish(t, "broken", 2, BROKEN,
                                                      chain=ladder(t)["chain"])),
            ("broken report with an OK line", 2,
             finish(t, "broken", 2, BROKEN + ["OK — 9 events · chain intact"])),
            ("tampered report as an OK headline", 2,
             finish(t, "buried-seal", 2, ["OK — 9 events · chain intact", *BURIED[1:]])),
            ("buried report without its seal line", 2, finish(t, "buried-seal", 2, BURIED[:2])),
            ("broken family at exit 0", 0, finish(t, "broken", 0, BROKEN)),
            ("line bound within its bound", 2, finish(
                t, "line-over-long", 2,
                ["line 2 is 10 bytes — beyond the verifier's line bound (20 bytes)"])),
        ]:
            for claim in CLAIMS:
                with self.subTest(label=label, claim=claim):
                    self.assertEqual(self.framed(claim, code, document), "DIVERGE")

    def test_unknown_values_are_unsupported_never_guessed(self):
        t = self.trace
        for code, document in [
            (3, finish(t, "unknown", 3, [f"{t}: unknown verdict class"])),
            (3, finish(t, "a-newer-class", 3, ["?"])),
            (0, ladder(t, tier="unknown")),
            (0, ladder(t, replay={"tier": "unknown"})),
            (0, ladder(t, headline="frayed")),
            (5, ladder(t, code=5, headline="incomplete", liveness="dormant")),
            (0, ladder(t, seal={"tier": "half-sealed"})),
        ]:
            with self.subTest(document=document):
                self.assertEqual(self.framed("clean", code, document), "UNSUPPORTED")


class TornLaws(TraceDoorCase):
    """A torn tail is a valid observation that attests no lifecycle end."""

    def test_torn_never_discharges_a_lifecycle_claim(self):
        torn = ladder(self.trace, headline="torn")
        for journal in ['{"kind":"workflow_started"}\n{"kind":"workflow_completed"}\n{"kind":"ta',
                        '{"kind":"workflow_started"}\n{"kind":"ta']:
            self.journal.write_text(journal)
            for claim in CLAIMS:
                with self.subTest(journal=journal[-30:], claim=claim):
                    self.assertEqual(self.framed(claim, 0, torn),
                                     "UNSUPPORTED" if claim in ("clean", "finding", "incomplete")
                                     else "DIVERGE")

    def test_a_forged_seal_on_a_torn_chain_is_forged(self):
        self.assertEqual(self.framed("forged", 2, ladder(
            self.trace, ["SEAL FORGED — x"], 2, headline="torn", seal=FORGED_SEAL)), "AGREE")


class FindingLaws(TraceDoorCase):
    """The witness finding is a whole physical line of the report's own lines."""

    def test_finding_markers(self):
        t = self.trace
        for claim, code, document, stderr, result in [
            ("clean", 0, ladder(t), "", "AGREE"),
            ("finding", 0, ladder(t), "", "DIVERGE"),
            ("finding", 0, ladder(t, [UNSEALED, WITNESS]), "", "AGREE"),
            ("clean", 0, ladder(t, [UNSEALED, WITNESS]), "", "DIVERGE"),
            ("finding", 0, ladder(t, [UNSEALED + " · FINDING — inside"]), "", "DIVERGE"),
            ("clean", 0, ladder(t, [UNSEALED + " · FINDING — inside"]), "", "AGREE"),
            ("finding", 0, ladder(t), WITNESS, "DIVERGE"),
            ("finding", 0, ladder(t, [WITNESS, WITNESS]), "", "DIVERGE"),
            ("clean", 0, ladder(t, [UNSEALED, "FINDING — a newer requirement"]), "",
             "UNSUPPORTED"),
            ("forged", 2, ladder(t, ["SEAL FORGED — x", WITNESS], 2, seal=FORGED_SEAL), "",
             "AGREE"),
        ]:
            with self.subTest(claim=claim, lines=document["lines"], stderr=stderr[:10]):
                self.assertEqual(self.verdict(claim, code, document, stderr), result)


class CostReplayLaws(TraceDoorCase):
    """The budget leg is one marker of the report's own lines, its continuation in the
    same entry."""

    def test_three_classes_agree_only_with_themselves(self):
        legs = {"unrecorded": UNRECORDED, "refused": REFUSED, "replayed": REPLAYED}
        for wanted in legs:
            for actual, line in legs.items():
                with self.subTest(wanted=wanted, actual=actual):
                    self.assertEqual(self.framed("clean", 0, ladder(self.trace, [UNSEALED, line]),
                                                 cost_replay=wanted),
                                     "AGREE" if wanted == actual else "DIVERGE")

    def test_broken_or_foreign_cost_evidence_never_agrees(self):
        marker, phrase = REPLAYED.split("\n")
        for lines in [[UNSEALED], [marker], [marker, phrase], [marker + "\n\n" + phrase],
                      [phrase + "\n" + marker], [REPLAYED, REFUSED], [REPLAYED, REPLAYED],
                      ["COST-REPLAY — a newer class"], ["  " + REPLAYED],
                      [marker + "\n" + phrase.strip()]]:
            with self.subTest(lines=lines):
                self.assertEqual(self.framed("clean", 0, ladder(self.trace, lines),
                                             cost_replay="replayed"), "DIVERGE")
        self.assertEqual(self.verdict("clean", 0, ladder(self.trace, [UNSEALED, marker]), phrase,
                                      cost_replay="replayed"), "DIVERGE")
        self.assertEqual(self.framed("forged", 2, finish(self.trace, "broken", 2, BROKEN),
                                     cost_replay="unrecorded"), "DIVERGE")

    def test_a_refused_cost_leg_leaves_a_clean_chain_clean(self):
        self.assertEqual(self.framed("clean", 0, ladder(self.trace, [UNSEALED, REFUSED]),
                                     cost_replay="refused"), "AGREE")


class ItemProjectionLaws(TraceDoorCase):
    """Item tables come from `trace outputs` version 2; only `id` and `items` are read."""

    def judge_items(self, wanted, reply):
        return self.outcome({"verdict": "clean", "items": {"fan": wanted}},
                            self.reply(0, ladder(self.trace)), reply)

    def test_exact_rows_and_tables(self):
        t = self.trace
        swapped = [{"status": row["status"], "item": row["item"], "index": row["index"]}
                   for row in ROWS]
        for wanted, items in [(ROWS, ROWS), (None, None), ([], []), (ROWS, swapped)]:
            with self.subTest(wanted=wanted, items=items):
                self.assertEqual(self.judge_items(wanted, self.reply(0, projection(t, items))),
                                 "AGREE")
        for label, wanted, items in [
            ("an empty table is not an unrecorded one", None, []),
            ("an unrecorded table is not an empty one", [], None),
            ("a dropped row", ROWS, ROWS[:1]),
            ("reordered rows", ROWS, ROWS[::-1]),
            ("a boolean index", ROWS, [{**ROWS[0], "index": False}, ROWS[1]]),
            ("a string index", ROWS, [{**ROWS[0], "index": "0"}, ROWS[1]]),
            ("a relabelled status", ROWS, [ROWS[0], {**ROWS[1], "status": "never_started"}]),
        ]:
            with self.subTest(label=label):
                self.assertEqual(self.judge_items(wanted, self.reply(0, projection(t, items))),
                                 "DIVERGE")

    def test_only_a_bound_version_2_projection_is_read(self):
        t = self.trace
        self.assertEqual(self.judge_items(ROWS, self.reply(0, projection(t, version=1))),
                         "UNSUPPORTED")
        absent = projection(t)
        del absent["tasks"][0]["items"]
        doubled = projection(t)
        doubled["tasks"] = doubled["tasks"] * 2
        for label, wanted, reply in [
            ("a boolean version", ROWS, self.reply(0, projection(t, version=True))),
            ("a string version", ROWS, self.reply(0, projection(t, version="2"))),
            ("another journal", ROWS, self.reply(0, projection(self.tmp.name + "/trace.ndjson"))),
            ("a nonzero exit", ROWS, self.reply(3, "", "nika: cannot read the trace")),
            ("a warning beside it", ROWS, self.reply(0, projection(t), "warning: x")),
            ("a duplicate task", ROWS, self.reply(0, doubled)),
            ("an absent item field", None, self.reply(0, absent)),
            ("an absent task", ROWS, self.reply(0, projection(t, tasks=[]))),
            ("a scalar projection", ROWS, self.reply(0, "[]")),
        ]:
            with self.subTest(label=label):
                self.assertEqual(self.judge_items(wanted, reply), "DIVERGE")


class SecondaryAssertionLaws(TraceDoorCase):
    """Independent assertions keep their own failures; none hides another."""

    def test_a_divergence_keeps_its_unsupported_notes(self):
        expected = {"verdict": "forged", "items": {"fan": ROWS}}
        (self.fixture / "expected-verify.json").write_text(json.dumps(expected))
        replies = [self.reply(0, ladder(self.trace)), self.reply(0, projection(self.trace,
                                                                               version=1))]
        with patch.object(runner.subprocess, "run", side_effect=replies):
            differences = runner.judge_trace("output-double", self.fixture)
        self.assertTrue(any(line.startswith("verdict:") for line in differences), differences)
        self.assertTrue(any(line.startswith("unsupported · items") for line in differences),
                        differences)

    def test_the_prologue_reads_the_frozen_journal(self):
        boot = {"kind": "workflow_started",
                "fields": [{"key": "inputs", "value": '{"qui":"cli-operator"}'}]}
        self.journal.write_text(json.dumps(boot) + "\n")
        report = self.reply(0, ladder(self.trace))
        for origins, result in [({"qui": "cli-operator"}, "AGREE"),
                                ({"qui": "api-caller"}, "DIVERGE")]:
            with self.subTest(origins=origins):
                self.assertEqual(self.outcome({"verdict": "clean",
                                               "prologue": {"input_origins": origins}}, report),
                                 result)


class InvocationLaws(TraceDoorCase):
    """Fixture errors issue no command; the doors are exactly the two JSON commands."""

    def test_invalid_expectations_issue_no_command(self):
        for raw in ['{"verdict":"clean","verdict":"forged"}', '{"verdict":"torn"}',
                    '{"verdict":"clean","items":{}}', '{"verdict":"clean","cost_replay":"maybe"}']:
            (self.fixture / "expected-verify.json").write_text(raw)
            with self.subTest(raw=raw), patch.object(runner.subprocess, "run") as invoke:
                with self.assertRaises(runner.InvalidFixture):
                    runner.judge_trace("output-double", self.fixture)
                invoke.assert_not_called()

    def test_exact_argv_on_one_canonical_path(self):
        t = self.trace
        self.assertTrue(pathlib.Path(t).is_absolute())
        self.assertEqual(self.outcome({"verdict": "clean"}, self.reply(0, ladder(t))), "AGREE")
        self.assertEqual(self.calls,
                         [["output-double", "trace", "verify", t, "--json", "--color", "never"]])
        self.assertEqual(self.outcome({"verdict": "clean", "items": {"fan": ROWS}},
                                      self.reply(0, ladder(t)), self.reply(0, projection(t))),
                         "AGREE")
        self.assertEqual(self.calls[1],
                         ["output-double", "trace", "outputs", t, "--json", "--color", "never"])


class MeasurementIntegrityLaws(TraceDoorCase):
    """Observations are joined only over the journal bytes they all read."""

    def changing(self, action):
        def double(argv, **kwargs):
            action()
            return self.reply(0, ladder(self.trace))
        return double

    def test_a_journal_changed_or_removed_is_no_measurement(self):
        (self.fixture / "expected-verify.json").write_text('{"verdict":"clean"}')
        for action in [lambda: self.journal.write_text('{"kind":"workflow_started"}\n{}\n'),
                       lambda: self.journal.unlink()]:
            self.journal.write_text('{"kind":"workflow_started","fields":[]}\n')
            with self.subTest(action=action), \
                    patch.object(runner.subprocess, "run", side_effect=self.changing(action)):
                with self.assertRaises(runner.InvalidMeasurement):
                    runner.judge_trace("output-double", self.fixture)

    def test_the_sweep_reports_an_invalid_measurement_loudly(self):
        (self.fixture / "expected-verify.json").write_text('{"verdict":"clean"}')
        rewrite = self.changing(lambda: self.journal.write_text("{}\n{}\n"))
        with patch.object(runner, "RUNTIME", self.fixture.parent), \
                patch.object(runner.subprocess, "run", side_effect=rewrite), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(runner.main(["runner"]), 1)
        self.assertIn("ENGINE-ERROR", output.getvalue())
        self.assertIn("changed", output.getvalue())


class LegMarkerLaws(TraceDoorCase):
    """A line that begins with a leg marker states that leg: it agrees with the typed leg, and a
    finish family states no leg but a buried seal's own."""

    def test_a_stated_leg_agrees_with_its_typed_leg(self):
        t = self.trace
        sealed = ["SEALED — the run_sealed signature verifies · key k1 (trusted)",
                  "ANCHORED — no sidecar (`nika trace anchor` notarizes the head)",
                  "REPLAYED — not attempted (pass --replay <fresh.ndjson>)"]
        for document in [
            ladder(t, ["SEALED — the run_sealed signature verifies · key k1 (trusted)"]),
            ladder(t, [UNSEALED, *sealed[1:]], tier="sealed", seal=SEALED),
            ladder(t, [sealed[0], "ANCHORED — rekor index 17 · checkpoint verified offline"],
                   tier="sealed", seal=SEALED),
            ladder(t, [UNSEALED, "REPLAYED — the journal re-executes identically"]),
            ladder(t, [UNSEALED, "ANCHORED — REQUIRED but no <trace>.anchor.json sidecar exists"]),
        ]:
            with self.subTest(lines=document["lines"]):
                self.assertEqual(self.framed("clean", 0, document), "DIVERGE")
        for document in [
            ladder(t),
            ladder(t, sealed, tier="sealed", seal=SEALED),
            ladder(t, [UNSEALED, "REPLAYED — not attempted (pass --replay <fresh.ndjson>)"]),
            ladder(t, []),
        ]:
            with self.subTest(lines=document["lines"]):
                self.assertEqual(self.framed("clean", 0, document), "AGREE")

    def test_a_finish_family_states_no_leg_but_its_own(self):
        t = self.trace
        for claim, document in [
            ("forged", finish(t, "broken", 2, [*BROKEN, "ANCHOR FORGED — contradictory diagnostic"])),
            ("forged", finish(t, "broken", 2, [*BROKEN, UNSEALED])),
            ("forged", finish(t, "buried-seal", 2, [*BURIED, "ANCHOR FORGED — x"])),
            ("forged", finish(t, "buried-seal", 2, [*BURIED, BURIED[2]])),
            ("refused", finish(t, "line-over-long", 2, [*LINE_BOUND, "SEAL FORGED — x"])),
        ]:
            with self.subTest(tier=document["tier"], lines=document["lines"]):
                self.assertEqual(self.framed(claim, 2, document), "DIVERGE")
        self.assertEqual(self.framed("forged", 2, finish(t, "broken", 2, BROKEN)), "AGREE")
        self.assertEqual(self.framed("forged", 2, finish(t, "buried-seal", 2, BURIED)), "AGREE")


class SeparateDoorLaws(unittest.TestCase):
    """Resume, receipt-explanation and energy expectations are validated as JSON
    before they are recognized as unsupported."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nika-door-law-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.cases = 0

    def fixture(self, claim, text):
        # One fresh directory per case: an empty text must not reuse a parent.
        self.cases += 1
        directory = self.root / f"case-{self.cases:02d}"
        directory.mkdir()
        (directory / claim).write_text(text)
        return directory

    def test_malformed_expectations_are_fixture_errors(self):
        for claim in ["expected-resume.json", "expected-explain.json", "expected-energy.json"]:
            for text in ["{", '{"a": 1, "a": 2}', "[1]", '"text"', '{"x": NaN}', ""]:
                with self.subTest(claim=claim, text=text):
                    with self.assertRaises(runner.InvalidFixture):
                        runner.fixture_door(self.fixture(claim, text))

    def test_well_formed_expectations_are_unsupported_not_agreement(self):
        for claim in ["expected-resume.json", "expected-explain.json", "expected-energy.json"]:
            with self.subTest(claim=claim):
                with self.assertRaises(runner.UnsupportedFixture):
                    runner.fixture_door(self.fixture(claim, '{"note": "well-formed"}'))

    def test_the_sweep_reports_the_two_classes_apart(self):
        self.fixture("expected-resume.json", "{")
        self.fixture("expected-energy.json", "{}")
        with patch.object(runner, "RUNTIME", self.root), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(runner.main(["runner"]), 1)
        report = output.getvalue()
        self.assertIn("FIXTURE-ERROR", report)
        self.assertIn("UNSUPPORTED", report)


if __name__ == "__main__":
    unittest.main()
