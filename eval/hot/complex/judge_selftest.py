#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The judge is judged: a neutered assertion, a corrupted manifest and a weakened reference must all go red."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import judge


class TheJudgeCanFail(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="complex-goldens-")
        self.root = Path(self.temp.name) / "complex"
        shutil.copytree(judge.ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))
        self.addCleanup(self.temp.cleanup)

    def manifest(self, change):
        path = self.root / "scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def scenario(self, data, sid):
        return next(s for s in data["scenarios"] if s["id"] == sid)

    def rewrite(self, relative, old, new):
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, f"{relative}: the mutation must apply exactly once")
        path.write_text(text.replace(old, new), encoding="utf-8")

    def red(self, pattern):
        return self.assertRaisesRegex(judge.JudgeError, pattern)

    # ── the corpus as committed ──────────────────────────────────────────────

    def test_committed_corpus_is_green_and_promotes_nothing(self):
        report = judge.validate(self.root)
        self.assertFalse(report["hot_promotion"])
        self.assertGreaterEqual(report["negative_controls"], report["scenarios"])

    # ── every assertion is load-bearing, in both directions ──────────────────

    def test_an_assertion_that_accepts_everything_is_caught(self):
        for kind, real in list(judge.ASSERTIONS.items()):
            with self.subTest(kind=kind):
                judge.ASSERTIONS[kind] = lambda doc, params: []
                try:
                    with self.red("expected violations"):
                        judge.validate(self.root)
                finally:
                    judge.ASSERTIONS[kind] = real

    def test_an_assertion_that_rejects_everything_is_caught(self):
        for kind, real in list(judge.ASSERTIONS.items()):
            with self.subTest(kind=kind):
                judge.ASSERTIONS[kind] = lambda doc, params: ["always red"]
                try:
                    with self.red("expected violations"):
                        judge.validate(self.root)
                finally:
                    judge.ASSERTIONS[kind] = real

    # ── a correct candidate that is weakened stops being accepted ────────────

    def test_a_defaulted_gate_in_the_reference_is_rejected(self):
        self.rewrite("workflows/x01/reference.nika.yaml", 'Report: ${{ with.report }}"\n',
                     'Report: ${{ with.report }}"\n        default: true\n')
        with self.red("x01/reference.*gate_blocking"):
            judge.validate(self.root)

    def consent_verdict(self, condition):
        """This judge's own reading, independent of the reference oracle that refuses the same files first."""
        import yaml
        text = (self.root / "workflows/x01/reference.nika.yaml").read_text(encoding="utf-8")
        self.assertEqual(text.count("when: ${{ with.go == true }}"), 1)
        doc = yaml.safe_load(text.replace("when: ${{ with.go == true }}", f"when: {condition}"))
        assertions = self.scenario(judge.load(self.root), "X01")["assertions"]
        return judge.judge(doc, assertions, self.root)["effects_gated"]

    def test_consent_conditions_that_stay_open_on_a_refusal_are_rejected(self):
        self.assertEqual(self.consent_verdict("${{ with.go == true }}"), [])
        self.assertEqual(self.consent_verdict("${{ with.go != false }}"), [])
        self.assertEqual(self.consent_verdict("${{ with.go == true && with.report != null }}"), [])
        for open_on_refusal in ("${{ with.go == false }}", "${{ with.go == true || with.go == false }}",
                                "${{ with.go == true || with.report != null }}", "${{ !(with.go == true) }}", "true"):
            with self.subTest(condition=open_on_refusal):
                self.assertTrue(self.consent_verdict(open_on_refusal), "a refusal must close the write")

    def test_the_reference_oracle_and_this_judge_agree_on_an_inverted_condition(self):
        self.rewrite("workflows/x11/reference.nika.yaml", "when: ${{ with.go == true }}", "when: ${{ with.go == false }}")
        with self.red("x11/reference.*NIKA-SEC-014"):
            judge.validate(self.root)

    def test_a_destination_read_from_the_ticket_is_rejected(self):
        self.rewrite("workflows/x08/reference.nika.yaml", '        path: "${{ const.reply_path }}"',
                     '        path: "./out/${{ inputs.ticket }}"')
        with self.red("x08/reference.*control_positions_trusted"):
            judge.validate(self.root)

    def test_an_unrequested_policy_change_in_the_edit_is_rejected(self):
        self.rewrite("workflows/x06/edit-reference.nika.yaml", "  refund_limit_eur: 100", "  refund_limit_eur: 101")
        with self.red("x06/edit-reference.*edit_locality"):
            judge.validate(self.root)

    def test_a_fifth_class_without_a_branch_is_rejected(self):
        def widen(data):
            self.scenario(data, "X10")["assertions"][0]["params"]["domain"].append("fraud")
        self.manifest(widen)
        judge.validate(self.root)  # the negated fallback is total, so a new class still lands
        self.rewrite("workflows/x10/reference.nika.yaml", 'when: ${{ with.c.class != "billing" && with.c.class != "login" }}',
                     'when: ${{ with.c.class == "security" || with.c.class == "unknown" }}')
        with self.red("x10/reference.*branches_exclusive_total"):
            judge.validate(self.root)

    # ── locality is judged on typed nodes, containers included ───────────────

    def test_an_empty_container_that_appears_or_disappears_is_a_change(self):
        changes = judge.semantic_changes
        self.assertEqual(changes({"t": {"x": 1}}, {"t": {"x": 1, "on_error": {}}}), {"t.on_error"})
        self.assertEqual(changes({"t": {"x": 1}}, {"t": {"x": 1, "read": []}}), {"t.read"})
        self.assertEqual(changes({"t": {"x": 1, "retry": {}}}, {"t": {"x": 1}}), {"t.retry"})
        self.assertEqual(changes({"l": [1]}, {"l": [1, []]}), {"l[1]"})
        self.assertEqual(changes({"c": []}, {"c": {}}), {"c"})
        self.assertEqual(changes({"c": {}}, {"c": None}), {"c"})

    def test_a_value_that_changes_type_is_a_change_even_when_python_calls_it_equal(self):
        changes = judge.semantic_changes
        self.assertTrue(True == 1 and False == 0 and 1 == 1.0, "the trap this test exists for")  # noqa: E712
        for before, after in ((True, 1), (False, 0), (1, 1.0), (None, ""), (None, False), ("1", 1), (0, None)):
            with self.subTest(before=before, after=after):
                self.assertEqual(changes({"v": before}, {"v": after}), {"v"})
                self.assertEqual(changes({"v": after}, {"v": before}), {"v"})

    def test_formatting_is_not_a_change(self):
        import yaml
        block = yaml.safe_load("a: 1\nb:\n  c: [1, 2]\n  d: 'x'\n")
        flow = yaml.safe_load('# a comment\nb: {d: "x", c: [1, 2]}\na: 1\n')
        self.assertEqual(judge.semantic_changes(block, flow), set())

    def edited(self, mutate):
        """The X06 assertion applied to the reference edit after an in-memory mutation: no oracle is involved."""
        import yaml
        doc = yaml.safe_load((self.root / "workflows/x06/edit-reference.nika.yaml").read_text(encoding="utf-8"))
        mutate(doc)
        assertion = self.scenario(judge.load(self.root), "X06")["assertions"]
        return judge.judge(doc, assertion, self.root)["edit_locality"]

    def test_the_edit_assertion_sees_what_the_old_flattening_missed(self):
        self.assertEqual(self.edited(lambda doc: None), [])
        self.assertEqual(self.edited(lambda doc: doc["tasks"]["notify"].update(retry={})),
                         ["unrequested change at `tasks.notify.retry`"])
        self.assertEqual(self.edited(lambda doc: doc["permits"].update(fs={})),
                         ["unrequested change at `permits.fs`"])
        self.assertEqual(self.edited(lambda doc: doc["inputs"]["ticket"].update(required=1)),
                         ["unrequested change at `inputs.ticket.required`"])
        self.assertEqual(self.edited(lambda doc: doc["const"].update(refund_limit_eur=100.0)),
                         ["unrequested change at `const.refund_limit_eur`"])

    def test_the_documented_paths_of_the_edit_did_not_widen(self):
        params = self.scenario(judge.load(self.root), "X06")["assertions"][0]["params"]
        self.assertEqual(params["allowed"], ["secrets.webhook.key", "permits.net.http[[]0[]]"])
        self.assertEqual(params["required"], params["allowed"])

    # ── the manifest cannot claim more than it shows ─────────────────────────

    def test_a_near_miss_that_stops_declaring_its_violation_is_caught(self):
        self.manifest(lambda d: self.scenario(d, "X07")["candidates"][1].update(violates=[]))
        with self.red("a near-miss names the assertion or the behaviour"):
            judge.validate(self.root)

    def test_an_assertion_nothing_turns_red_is_caught(self):
        def add(data):
            self.scenario(data, "X09")["assertions"].append(
                {"id": "unproven", "kind": "outputs_contract", "params": {"required": ["selected"]},
                 "question": "Is it there?"})
        self.manifest(add)
        with self.red("no near-miss turns"):
            judge.validate(self.root)

    def test_a_near_miss_must_say_why_it_is_plausible(self):
        self.manifest(lambda d: self.scenario(d, "X02")["candidates"][1].pop("plausible_because"))
        with self.red("say why it is plausible"):
            judge.validate(self.root)

    def test_a_candidate_must_say_who_wrote_it(self):
        self.manifest(lambda d: self.scenario(d, "X05")["candidates"][0].pop("provenance"))
        with self.red("who wrote this candidate"):
            judge.validate(self.root)

    def test_hand_authored_candidates_are_never_counted_as_generated(self):
        report = judge.validate(self.root)["candidate_provenance"]
        self.assertEqual((report["compiler-generated"], report["model-generated"]), (0, 0))
        self.assertEqual(report["hand-authored"], sum(len(s["candidates"]) for s in judge.load(self.root)["scenarios"]))

    def test_a_scenario_without_a_law_is_caught(self):
        self.manifest(lambda d: self.scenario(d, "X03").update(laws=[]))
        with self.red("names its law and owner"):
            judge.validate(self.root)

    def test_a_product_contract_cannot_be_promoted_by_editing_its_status(self):
        self.manifest(lambda d: d["product_contracts"][0].update(status="STATIC_AND_BEHAVIOUR"))
        with self.red("PC01: status"):
            judge.validate(self.root)

    def test_a_product_contract_cannot_carry_a_static_proof(self):
        self.manifest(lambda d: d["product_contracts"][1].update(candidates=[]))
        with self.red("carries no static proof"):
            judge.validate(self.root)

    def test_a_retained_gap_cannot_be_declared_fixed_in_the_manifest(self):
        self.manifest(lambda d: d["retained_gaps"][0].update(baseline="pass"))
        with self.red("stays red until it is fixed"):
            judge.validate(self.root)

    def test_hot_promotion_cannot_be_switched_on(self):
        self.manifest(lambda d: d.update(hot_promotion=True))
        with self.red("no HOT promotion"):
            judge.validate(self.root)

    def test_a_refused_candidate_that_becomes_valid_is_caught(self):
        self.rewrite("workflows/x01/refused-ordering-only-gate.nika.yaml", "    after:\n      human: success\n    with:\n",
                     "    with:\n      go: ${{ tasks.human.output }}\n")
        self.rewrite("workflows/x01/refused-ordering-only-gate.nika.yaml",
                     "      report: ${{ tasks.merge.output.report }}\n    invoke:\n      tool: \"nika:write\"",
                     "      report: ${{ tasks.merge.output.report }}\n    when: ${{ with.go == true }}\n    invoke:\n      tool: \"nika:write\"")
        with self.red("must refuse with NIKA-SEC-014"):
            judge.validate(self.root)

    # ── the reading of `when:` everything above rests on ─────────────────────

    def test_three_valued_reading(self):
        gate = {"with.go": False}
        self.assertIs(judge.evaluate("with.go == true", gate), False)
        self.assertIs(judge.evaluate("with.go != false", gate), False)
        self.assertIs(judge.evaluate("with.go == true || with.go == false", gate), True)
        self.assertIs(judge.evaluate("with.go == true && with.other == 1", gate), False)
        self.assertIs(judge.evaluate("with.go == true || with.other == 1", gate), judge.UNKNOWN)
        self.assertIs(judge.evaluate("!(with.go == true)", gate), True)
        self.assertIs(judge.evaluate('with.c.class != "a" && with.c.class != "b"', {"with.c.class": "z"}), True)
        with self.assertRaises(judge.Undecidable):
            judge.evaluate("size(with.go) > 0", gate)

    def test_a_with_edge_does_not_close_a_route_and_an_after_success_edge_does(self):
        gate = {"invoke": {"tool": "nika:prompt", "args": {"message": "ok?"}}}
        gated = {"with": {"go": "${{ tasks.ask.output }}"}, "when": "${{ with.go == true }}",
                 "invoke": {"tool": "nika:jq", "args": {"input": 1, "expression": "."}}}
        write = {"invoke": {"tool": "nika:write", "args": {"path": "./o", "content": "x"}}}
        through_data = {"ask": gate, "stage": gated, "act": {**write, "with": {"v": "${{ tasks.stage.output }}"}}}
        through_state = {"ask": gate, "stage": gated, "act": {**write, "after": {"stage": "success"}}}
        on_terminal = {"ask": gate, "stage": gated, "act": {**write, "after": {"stage": "terminal"}}}
        self.assertIsNone(judge.closing_gate("act", through_data))
        self.assertEqual(judge.closing_gate("act", through_state), "ask")
        self.assertIsNone(judge.closing_gate("act", on_terminal))

    def test_an_input_choice_gate_is_not_consent(self):
        ask = {"invoke": {"tool": "nika:prompt", "args": {"mode": "input", "message": "type yes"}}}
        self.assertFalse(judge.is_confirm_gate(ask))


if __name__ == "__main__":
    unittest.main()
