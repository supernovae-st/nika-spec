#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The judge is judged: a neutered assertion, a corrupted manifest and a weakened reference must all go red."""
import contextlib
import json
import shutil
import subprocess
import sys
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

    # ── a path is an identity, never a string that two nodes can share ───────

    def test_a_key_that_looks_like_a_nested_path_does_not_hide_the_nested_change(self):
        changes = judge.semantic_changes
        base = {"a": {"b": 1}, "a.b": 2}
        self.assertEqual(changes(base, {"a": {"b": 9}, "a.b": 2}), {"a.b"})
        self.assertEqual(changes(base, {"a": {"b": 1}, "a.b": 9}), {'["a.b"]'})
        self.assertEqual(changes(base, {"a": {"b": 9}, "a.b": 9}), {"a.b", '["a.b"]'})
        # The defect depended on which entry was written last; the fix may not.
        self.assertEqual(changes({"a.b": 2, "a": {"b": 1}}, {"a.b": 2, "a": {"b": 9}}), {"a.b"})

    def test_a_key_that_looks_like_an_index_does_not_hide_the_element_change(self):
        changes = judge.semantic_changes
        base = {"v": [1], "v[0]": 2}
        self.assertEqual(changes(base, {"v": [9], "v[0]": 2}), {"v[0]"})
        self.assertEqual(changes(base, {"v": [1], "v[0]": 9}), {'["v[0]"]'})
        self.assertEqual(changes({"v[0]": 2, "v": [1]}, {"v[0]": 2, "v": [9]}), {"v[0]"})
        # A sequence index, the string "0" and the integer 0 are three different places.
        self.assertEqual(changes({"v": {"0": 1}}, {"v": {"0": 9}}), {'v["0"]'})
        self.assertEqual(changes({"v": {0: 1}}, {"v": {0: 9}}), {"v[<int> 0]"})
        self.assertEqual(changes({"v": {0: 1, "0": 1}}, {"v": {0: 1, "0": 9}}), {'v["0"]'})

    def test_a_non_string_key_is_not_its_string_lookalike(self):
        changes = judge.semantic_changes
        for key, lookalike, rendered, rendered_lookalike in (
                (1, "1", "[<int> 1]", '["1"]'), (0, "0", "[<int> 0]", '["0"]'), (-1, "-1", "[<int> -1]", '["-1"]'),
                (True, "true", "[<bool> true]", "true"), (False, "false", "[<bool> false]", "false"),
                (None, "null", "[<null>]", "null"), (1.5, "1.5", "[<float> 1.5]", '["1.5"]')):
            with self.subTest(key=key):
                base = {key: "x", lookalike: "y"}
                self.assertEqual(changes(base, {key: "CHANGED", lookalike: "y"}), {rendered})
                self.assertEqual(changes(base, {key: "x", lookalike: "CHANGED"}), {rendered_lookalike})
        # Python calls the keys 1 and True equal. YAML does not, and neither does a path.
        self.assertEqual(changes({1: "x"}, {True: "x"}), {"[<int> 1]", "[<bool> true]"})
        self.assertEqual(changes({1: "x"}, {1.0: "x"}), {"[<int> 1]", "[<float> 1.0]"})

    def test_an_empty_key_and_punctuation_keys_have_their_own_identity(self):
        changes = judge.semantic_changes
        self.assertEqual(changes({"": 1}, {"": 2}), {'[""]'})
        self.assertEqual(changes({"": {"": 1}}, {"": {"": 2}}), {'[""][""]'})
        self.assertEqual(changes({"a": {"": 1}, "a.": 2}, {"a": {"": 9}, "a.": 2}), {'a[""]'})
        self.assertEqual(changes({"a": {"": 1}, "a.": 2}, {"a": {"": 1}, "a.": 9}), {'["a."]'})
        self.assertEqual(changes({".": 1, "": {"": 1}}, {".": 1, "": {"": 9}}), {'[""][""]'})
        for key, rendered in (("]", '["]"]'), ("[", '["["]'), ('"', '["\\""]'), ("\\", '["\\\\"]'),
                              ('a"]', '["a\\"]"]'), (" ", '[" "]'), ("a b", '["a b"]'), ("é", '["é"]'),
                              ("0abc", '["0abc"]'), ("a-b", '["a-b"]')):
            with self.subTest(key=key):
                self.assertEqual(changes({"p": {key: 1}}, {"p": {key: 2}}), {"p" + rendered})

    def test_mixed_nesting_reports_each_change_under_its_own_path(self):
        changes = judge.semantic_changes
        base = {"a.b": {"c": [{"d.e": 1}]}, "a": {"b": {"c": [{"d": {"e": 1}}]}}}
        flat = {"a.b": {"c": [{"d.e": 9}]}, "a": {"b": {"c": [{"d": {"e": 1}}]}}}
        nested = {"a.b": {"c": [{"d.e": 1}]}, "a": {"b": {"c": [{"d": {"e": 9}}]}}}
        self.assertEqual(changes(base, flat), {'["a.b"].c[0]["d.e"]'})
        self.assertEqual(changes(base, nested), {"a.b.c[0].d.e"})
        self.assertEqual(changes(flat, nested), {'["a.b"].c[0]["d.e"]', "a.b.c[0].d.e"})

    def test_no_two_places_share_a_rendered_path(self):
        keys = ["a", "b", "a.b", "b.c", "a.b.c", "a[0]", "[0]", "0", 0, "", ".", "..", "]", "[", '"', "\\", 'a"]',
                "a\\", True, "true", None, "null", 1, "1", 1.5, "1.5", "<int> 1", "[<int> 1]", '["a"]', " ", "a b",
                "é", -1, "-1", "c", "b.c[0]"]
        seen = {}
        for parent in keys:
            for child in keys:
                for shape, document in (("mapping", lambda v: {parent: {child: v}}),
                                        ("sequence", lambda v: {parent: [{child: v}]})):
                    paths = judge.semantic_changes(document(1), document(2))
                    self.assertEqual(len(paths), 1, (parent, child, shape, paths))
                    (path,) = paths
                    place = (repr(parent), repr(child), shape)
                    self.assertNotIn(path, seen, f"{place} and {seen.get(path)} both render as {path!r}")
                    seen[path] = place
        self.assertEqual(len(seen), 2 * len(keys) ** 2)

    def test_no_change_is_reported_exactly_when_two_documents_are_typed_equal(self):
        """A property, not a list of cases: an independent recursive oracle decides equality, and
        `semantic_changes` must be empty for exactly those pairs. Seeded, so a failure reproduces."""
        import copy
        import random
        rng = random.Random(20260918)
        keys = ["a", "b", "a.b", "b.a", "a[0]", "[0]", "0", 0, "", ".", "]", "[", '"', "\\", True, "true", None,
                "null", 1, "1", 1.5, "1.5", "a.b.a", "<int> 0"]
        leaves = [0, 1, True, False, None, "", "0", "1", 1.0, 0.0, "a.b", "true", [], {}]

        def document(depth):
            roll = rng.random()
            if depth == 0 or roll < 0.3:
                return copy.deepcopy(rng.choice(leaves))
            if roll < 0.7:
                return {key: document(depth - 1) for key in rng.sample(keys, rng.randint(0, 4))}
            return [document(depth - 1) for _ in range(rng.randint(0, 3))]

        def places(value, path=()):
            yield path
            children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
            for step, child in children:
                yield from places(child, path + (step,))

        def replaced(value, path, new):
            if not path:
                return new
            value = copy.copy(value)
            value[path[0]] = replaced(value[path[0]], path[1:], new)
            return value

        def typed_equal(a, b):
            if type(a) is not type(b):
                return False
            if isinstance(a, dict):
                left = {(type(k).__name__, k): v for k, v in a.items()}
                right = {(type(k).__name__, k): v for k, v in b.items()}
                return left.keys() == right.keys() and all(typed_equal(left[k], right[k]) for k in left)
            if isinstance(a, list):
                return len(a) == len(b) and all(map(typed_equal, a, b))
            return a == b

        equal = unequal = 0
        for _ in range(4000):
            first = document(3)
            if rng.random() < 0.25:
                second = copy.deepcopy(first)
            else:  # the same document with ONE place replaced: the pairs a last-wins index gets wrong
                second = replaced(first, rng.choice(list(places(first))), document(1))
            same = typed_equal(first, second)
            equal, unequal = equal + same, unequal + (not same)
            self.assertEqual(judge.semantic_changes(first, second) == set(), same, (first, second))
        self.assertGreater(min(equal, unequal), 500, "the generator must produce both kinds of pair")

    def test_a_collision_is_refused_loudly_and_never_overwritten(self):
        real = judge.render
        judge.render = lambda path: "one-name-for-everything"
        try:
            with self.red("render as"):
                judge.semantic_changes({"a": 1, "b": 2}, {"a": 1, "b": 3})
        finally:
            judge.render = real
        twice = (("key", "str", "a"),)
        with self.red("yielded twice"):
            judge.index_nodes([(twice, ("int", 1)), (twice, ("int", 2))])

    def test_simple_paths_render_exactly_as_before(self):
        import yaml
        base = yaml.safe_load((self.root / "workflows/x06/base.nika.yaml").read_text(encoding="utf-8"))
        edit = yaml.safe_load((self.root / "workflows/x06/edit-reference.nika.yaml").read_text(encoding="utf-8"))
        self.assertEqual(judge.semantic_changes(base, edit), {"secrets.webhook.key", "permits.net.http[0]"})

    def test_the_edit_assertion_sees_a_policy_change_hidden_behind_a_lookalike_key(self):
        import copy
        import yaml
        base = {"nika": "lookalike", "const": {"limits": {"refund_eur": 100}, "limits.refund_eur": 100},
                "tasks": {"rule": {"invoke": {"tool": "nika:jq", "args": {"input": 1, "expression": "."}}}}}
        (self.root / "workflows/x06/lookalike-base.nika.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
        params = {"base": "workflows/x06/lookalike-base.nika.yaml", "allowed": ["const.note"], "required": [],
                  "_root": self.root}
        raised = copy.deepcopy(base)
        raised["const"]["limits"]["refund_eur"] = 250
        self.assertEqual(judge.ASSERTIONS["edit_locality"](raised, params),
                         ["unrequested change at `const.limits.refund_eur`"])
        lookalike = copy.deepcopy(base)
        lookalike["const"]["limits.refund_eur"] = 250
        self.assertEqual(judge.ASSERTIONS["edit_locality"](lookalike, params),
                         ['unrequested change at `const["limits.refund_eur"]`'])

    # ── an ad hoc candidate is admitted by the reference oracle before it is judged ──

    REFERENCE = "workflows/x01/reference.nika.yaml"
    GOOD_WHEN = "    when: ${{ with.go == true }}\n"

    def cli(self, candidate, scenario="X01"):
        """The command a compiler's candidate would be judged with: exit code, parsed stdout, stderr."""
        result = subprocess.run([sys.executable, judge.__file__, "--scenario", scenario, "--candidate", str(candidate)],
                                capture_output=True, text=True, check=False)
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            report = None
        return result.returncode, report, result.stderr

    def candidate(self, name, text):
        path = self.root / "workflows/x01" / name
        path.write_text(text, encoding="utf-8")
        return path

    def reference_text(self):
        return (self.root / self.REFERENCE).read_text(encoding="utf-8")

    def passes_every_assertion_when_parsed_last_wins(self, text):
        """What the unguarded command judged: the document a last-wins YAML parser makes of this text."""
        import yaml
        assertions = self.scenario(judge.load(self.root), "X01")["assertions"]
        return not any(judge.judge(yaml.safe_load(text), assertions, self.root).values())

    def assert_refused_as_static_invalid(self, outcome, code):
        status, report, stderr = outcome
        self.assertEqual(status, 2, (report, stderr))
        self.assertIs(report["accepted"], False)
        self.assertEqual(report["refused"], "static-invalid")
        self.assertNotIn("violations", report, "a source that was refused was not judged")
        found = [error.get("code") or error.get("namespace") for error in report["static_errors"]]
        self.assertTrue(any(str(item).startswith(code) for item in found), found)

    def test_cli_accepts_a_valid_reference_exactly_as_before(self):
        status, report, _ = self.cli(self.root / self.REFERENCE)
        self.assertEqual((status, report), (0, {"scenario": "X01", "accepted": True, "violations": {}}))

    def test_cli_still_rejects_an_ordinary_semantic_near_miss(self):
        status, report, _ = self.cli(self.root / "workflows/x01/near-miss-gated-through-data-edge.nika.yaml")
        self.assertEqual(status, 1)
        self.assertIs(report["accepted"], False)
        self.assertEqual(list(report["violations"]), ["effects_gated"])
        self.assertNotIn("refused", report, "this source is statically valid: it was judged, and rejected on meaning")

    def test_cli_refuses_a_duplicate_key_even_though_the_last_value_would_pass(self):
        text = self.reference_text()
        self.assertEqual(text.count(self.GOOD_WHEN), 1)
        # `when: true` first, the correct condition last. A last-wins parser keeps the correct one and the
        # document is the reference; a first-wins reader would publish after a refusal; the engine refuses both.
        good_last = text.replace(self.GOOD_WHEN, "    when: true\n" + self.GOOD_WHEN)
        self.assertTrue(self.passes_every_assertion_when_parsed_last_wins(good_last),
                        "the trap: parsed last-wins, this candidate satisfies every assertion")
        self.assert_refused_as_static_invalid(self.cli(self.candidate("duplicate-good-last.nika.yaml", good_last)),
                                              "NIKA-PARSE-017")
        # The other order used to be rejected on meaning, by parser luck. It is the same defect.
        good_first = text.replace(self.GOOD_WHEN, self.GOOD_WHEN + "    when: true\n")
        self.assertFalse(self.passes_every_assertion_when_parsed_last_wins(good_first))
        self.assert_refused_as_static_invalid(self.cli(self.candidate("duplicate-good-first.nika.yaml", good_first)),
                                              "NIKA-PARSE-017")

    def test_cli_refuses_a_duplicate_top_level_block_that_hides_a_wider_boundary(self):
        text = self.reference_text()
        wide = 'permits:\n  tools: ["nika:*"]\n  fs:\n    write: ["./**"]\n\n'
        self.assertEqual(text.count("\npermits:\n"), 1)
        hidden = text.replace("\npermits:\n", "\n" + wide + "permits:\n", 1)
        self.assertTrue(self.passes_every_assertion_when_parsed_last_wins(hidden))
        self.assert_refused_as_static_invalid(self.cli(self.candidate("duplicate-permits.nika.yaml", hidden)),
                                              "NIKA-PARSE-017")

    def test_cli_refuses_a_malformed_schema_although_every_assertion_passes(self):
        text = self.reference_text()
        self.assertEqual(text.count("        type: object\n"), 1)
        malformed = text.replace("        type: object\n", "        type: objectt\n")
        self.assertTrue(self.passes_every_assertion_when_parsed_last_wins(malformed))
        self.assert_refused_as_static_invalid(self.cli(self.candidate("malformed-schema.nika.yaml", malformed)), "NIKA-")

    def test_cli_refuses_an_unknown_envelope_key_although_every_assertion_passes(self):
        unknown = self.reference_text() + "\npolicy:\n  refunds: allowed\n"
        self.assertTrue(self.passes_every_assertion_when_parsed_last_wins(unknown))
        self.assert_refused_as_static_invalid(self.cli(self.candidate("unknown-key.nika.yaml", unknown)), "NIKA-PARSE")

    def test_cli_refuses_text_that_is_not_yaml_with_a_verdict_not_a_crash(self):
        outcome = self.cli(self.candidate("not-yaml.nika.yaml", "nika: broken\ntasks: [\n"))
        self.assert_refused_as_static_invalid(outcome, "NIKA-PARSE-001")

    def test_cli_refuses_a_corpus_candidate_the_reference_oracle_refuses(self):
        outcome = self.cli(self.root / "workflows/x01/refused-ordering-only-gate.nika.yaml")
        self.assert_refused_as_static_invalid(outcome, "NIKA-SEC-014")

    def test_the_source_is_read_once_and_the_oracle_and_the_parser_see_those_bytes(self):
        folder = self.root / "workflows/x01"

        class RewrittenWhileJudged:
            """A file that says one thing on the first read and another afterwards."""

            def __init__(self, first, later):
                self.first, self.later, self.reads, self.parent, self.name = first, later, 0, folder, "candidate.nika.yaml"

            def read_bytes(self):
                self.reads += 1
                return (self.first if self.reads == 1 else self.later).encode("utf-8")

            def read_text(self, *args, **kwargs):
                return self.read_bytes().decode("utf-8")

        valid = self.reference_text()
        duplicate = valid.replace(self.GOOD_WHEN, "    when: true\n" + self.GOOD_WHEN)
        near_miss = (folder / "near-miss-gated-through-data-edge.nika.yaml").read_text(encoding="utf-8")

        refused_first = RewrittenWhileJudged(duplicate, valid)
        status, report = judge.judge_candidate("X01", refused_first, self.root)
        self.assertEqual((status, report["refused"], refused_first.reads), (2, "static-invalid", 1),
                         "the oracle must judge the bytes that were read, not a later, cleaner file")

        valid_first = RewrittenWhileJudged(valid, near_miss)
        status, report = judge.judge_candidate("X01", valid_first, self.root)
        self.assertEqual((status, report, valid_first.reads),
                         (0, {"scenario": "X01", "accepted": True, "violations": {}}, 1))

        near_miss_first = RewrittenWhileJudged(near_miss, valid)
        status, report = judge.judge_candidate("X01", near_miss_first, self.root)
        self.assertEqual((status, list(report["violations"]), near_miss_first.reads), (1, ["effects_gated"], 1))

    def test_a_usage_error_is_not_a_verdict(self):
        # argparse exits 2 on its own, the status a static-invalid refusal also uses. A verdict always
        # comes with a report on stdout; a misuse prints none, so a caller can tell the two apart.
        result = subprocess.run([sys.executable, judge.__file__, "--no-such-flag"], capture_output=True, text=True,
                                check=False)
        self.assertEqual((result.returncode, result.stdout), (2, ""))
        self.assertIn("usage:", result.stderr)

    def test_the_corpus_and_the_command_admit_through_the_same_door(self):
        import yaml
        path = self.root / "workflows/x01/refused-ordering-only-gate.nika.yaml"
        text, verdict = judge.admit(path)
        self.assertEqual(text, path.read_text(encoding="utf-8"))
        self.assertEqual([error["code"] for error in verdict["errors"]], ["NIKA-SEC-014"])
        text, verdict = judge.admit(self.root / self.REFERENCE)
        self.assertTrue(verdict["valid"])
        self.assertEqual(yaml.safe_load(text)["nika"], "x01-fanout-approve-publish")

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

    # ── a partly repaired gap: what remains stays, and a repair is proven ────

    KG01_WITNESS = "workflows/x01/near-miss-gated-through-data-edge.nika.yaml"
    CORE = "workflows/x13/refused-certain-skip-core.nika.yaml"
    COUSIN = "workflows/x13/refused-certain-skip-fan-out-stage.nika.yaml"
    CLOSED = "workflows/x13/variant-closed-by-a-success-edge-on-the-stage.nika.yaml"
    CONDITIONAL = "workflows/x13/near-miss-stage-also-reads-a-step-that-ran.nika.yaml"

    def gap(self, data, gid):
        return next(g for g in data["retained_gaps"] if g["id"] == gid)

    def row(self, data, file):
        return next(c for s in data["scenarios"] for c in s["candidates"] if c["file"] == file)

    def test_the_three_retained_gaps_keep_their_criterion(self):
        gaps = {g["id"]: g for g in judge.load(self.root)["retained_gaps"]}
        self.assertEqual(sorted(gaps), ["KG01", "KG02", "KG03"])
        probe = gaps["KG01"]["reproduce"]
        self.assertEqual((probe["kind"], probe["file"], probe["expect_code"], gaps["KG01"]["baseline"]),
                         ("engine_check", self.KG01_WITNESS, "NIKA-SEC-014", "expected_fail"))
        self.assertEqual(gaps["KG01"]["title"], "A route closed only by a skippable data edge fires on no")
        self.assertEqual(gaps["KG01"]["repaired_subcases"], [self.CORE, self.COUSIN])
        witness = self.row(judge.load(self.root), self.KG01_WITNESS)
        self.assertEqual((witness["role"], witness.get("spec_oracle", "valid"), witness.get("engine_check", "valid")),
                         ("near_miss", "valid", "valid"), "the original golden is still admitted by both oracles")

    def test_a_retained_gap_is_not_closed_by_editing_its_witness(self):
        path = self.root / self.KG01_WITNESS
        path.write_text(path.read_text(encoding="utf-8") + "# a comment no judge reads\n", encoding="utf-8")
        with self.red("KG01: its witness file changed"):
            judge.validate(self.root)

    def test_a_partly_repaired_gap_cannot_drop_its_pin(self):
        self.manifest(lambda d: self.gap(d, "KG01")["reproduce"].pop("sha256"))
        with self.red("KG01: a partly repaired gap pins the bytes"):
            judge.validate(self.root)

    def test_a_repair_is_a_refused_candidate_that_is_also_run_as_written(self):
        self.manifest(lambda d: self.row(d, self.CORE).pop("refused_run"))
        with self.red("KG01: a repaired sub-case is a refused candidate that is also run as written"):
            judge.validate(self.root)

    def test_a_correct_candidate_cannot_be_named_as_the_repair(self):
        self.manifest(lambda d: self.gap(d, "KG01").update(repaired_subcases=["workflows/x13/reference.nika.yaml"]))
        with self.red("KG01: a repaired sub-case is a refused candidate"):
            judge.validate(self.root)

    def test_only_a_refused_candidate_is_run_as_written(self):
        run = {"answers": {"human": False}, "expect": {"exit": 2, "tasks_started": [], "files_written": {}}}
        self.manifest(lambda d: self.row(d, "workflows/x13/reference.nika.yaml").update(refused_run=run))
        with self.red("only a refused candidate is run as written"):
            judge.validate(self.root)

    def test_a_refused_run_states_what_it_left_behind(self):
        self.manifest(lambda d: self.row(d, self.COUSIN)["refused_run"]["expect"].pop("files_written"))
        with self.red("a refused run states its exit, the tasks that started and the files it left"):
            judge.validate(self.root)

    def test_a_success_edge_on_the_same_stage_closes_the_repaired_core(self):
        """Closed: the same producer's success edge cancels what its value edge leaves open, so the
        refusal is not a blanket one. The manifest still declares a refusal, and that is what goes red."""
        self.rewrite(self.CORE, "  publish:\n    with:\n", "  publish:\n    after:\n      stage: success\n    with:\n")
        with self.red("refused-certain-skip-core.*must refuse with NIKA-SEC-014"):
            judge.validate(self.root)

    def oracle_verdicts(self):
        """The reference oracle's blocking verdict on every candidate of this corpus."""
        judge._VERDICTS.clear()
        verdicts = {}
        for scenario in judge.load(self.root)["scenarios"]:
            for row in scenario["candidates"]:
                _, verdict = judge.admit(self.root / row["file"])
                codes = sorted({error.get("code") for error in verdict["errors"]})
                verdicts[row["file"]] = "valid" if verdict["valid"] else "+".join(codes)
        return verdicts

    @contextlib.contextmanager
    def neutered(self, **guards):
        """The reference consent oracle with some of its guards replaced, restored on the way out."""
        judge.admit(self.root / self.CORE)  # the oracle is loaded on first use
        oracle = sys.modules["deep_static"]
        real = {name: getattr(oracle, name) for name in guards}
        for name, fake in guards.items():
            setattr(oracle, name, fake)
        judge._VERDICTS.clear()
        try:
            yield
        finally:
            for name, guard in real.items():
                setattr(oracle, name, guard)
            judge._VERDICTS.clear()

    def flips(self, **guards):
        before = self.oracle_verdicts()
        with self.neutered(**guards):
            after = self.oracle_verdicts()
        return {file: after[file] for file in before if before[file] != after[file]}

    def test_without_the_sure_skip_reading_exactly_the_repaired_subcases_are_admitted(self):
        """What the reference oracle said before it read a certain skip: both files valid. Nothing else moves."""
        blind = {"_consent_skip_witnesses": lambda gate, closed, by_id: []}
        self.assertEqual(self.flips(**blind), {self.CORE: "valid", self.COUSIN: "valid"})
        with self.neutered(**blind), self.red("refused-certain-skip-core.*must refuse with NIKA-SEC-014"):
            judge.validate(self.root)

    def test_an_oracle_that_refuses_what_it_cannot_prove_is_caught(self):
        """Every admission taken for certain: the conditional near-miss and the closed variant are refused,
        and ONLY they are. Both are declared valid here, so an over-claiming oracle turns this corpus red."""
        eager = {"_consent_admission": lambda task, gate, skipped: "certain"}
        self.assertEqual(self.flips(**eager), {self.CONDITIONAL: "NIKA-SEC-014", self.CLOSED: "NIKA-SEC-014"})
        with self.neutered(**eager), self.red("variant-closed-by-a-success-edge.*the reference oracle refuses it"):
            judge.validate(self.root)

    def test_the_original_witness_is_kept_admitted_by_two_independent_guards(self):
        """Why no oracle may refuse the original golden: its stage navigates into a value (the binding
        is not total) AND reads a step that merely ran (the admission is not certain). Either guard
        alone keeps it valid; only an oracle with neither would refuse it."""
        certain, total = (lambda task, gate, skipped: "certain"), (lambda value: True)
        self.assertNotIn(self.KG01_WITNESS, self.flips(_consent_admission=certain))
        self.assertNotIn(self.KG01_WITNESS, self.flips(_consent_total_binding=total))
        self.assertEqual(self.flips(_consent_admission=certain, _consent_total_binding=total).get(self.KG01_WITNESS),
                         "NIKA-SEC-014")

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
