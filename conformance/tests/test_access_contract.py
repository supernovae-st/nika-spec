#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The access contract agrees with itself: schema, laws and fixtures.

spec/01-envelope.md §run (run.access · run.reasoning) · LAW-SURFACE-0503 ·
LAW-GRAMMAR-0502 · LAW-GRAMMAR-0503 · LAW-CONF-0501.

Offline and engine-free. This judges the CONTRACT's own consistency, never an
implementation: a runtime fixture that is consistent here stays UNSUPPORTED
until a qualified adapter executes it (runtime/access-harness/README.md).
The judge below derives each access-selection fixture's verdict from its own
premises, so a fixture can never claim an outcome its route world forbids.
"""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "conformance"))
import runner  # noqa: E402

SCHEMA = json.loads((ROOT / "schemas/workflow.schema.json").read_text(encoding="utf-8"))
ENVELOPE = ROOT / "conformance/tests/core/envelope"
HARNESS = ROOT / "conformance/tests/runtime/access-harness"
FIRST_ACCESS_FIXTURE = 33
# An access fixture is one whose document declares the `run:` block, an `access:` key or a
# `service_tier:` key wherever it was written (a misplaced one has no `run:` line): the
# envelope's later fixtures for other laws (the retired version tag, a withdrawn secret source)
# are not the access contract's to cite.
ACCESS_SUBJECT = re.compile(r"^\s*(run|access|service_tier):", re.M)
ENVELOPE_KEYS = {"nika", "model", "inputs", "const", "secrets", "permits", "run", "tasks", "outputs"}
ACCESS_LAWS = {"LAW-SURFACE-0503", "LAW-GRAMMAR-0502", "LAW-GRAMMAR-0503", "LAW-CONF-0501"}
# The reference engine's execution-access family (NIKA-1800..1849). A refusal
# fixture records the code the engine emits; it never mints one here.
ACCESS_CODE = re.compile(r"^NIKA-18[0-4][0-9]$")
KEBAB = re.compile(r"^[a-z][a-z0-9-]*$")
MODEL_ID = re.compile(r"^[a-z][a-z0-9-]*/\S+$")
VERBS = ("infer", "exec", "invoke", "agent")

ROUTE_KEYS = {"acp", "cli", "api"}
ACP_KEYS = {"available", "config", "readback", "default_model", "models", "prompt"}
OFFER_KEYS = {"effort", "service_tier"}
APPLIED_KEYS = {"model", "effort", "service_tier"}
OBSERVED_KEYS = {"acp_config_before_first_prompt", "acp_prompts", "api_inference_requests",
                 "cli_invocations"}
# A declared service tier keeps six facts apart: the language word requested, the native values
# the session offered, the native value sent, the one read back, and the two facts only a
# witness states (the tier carried on the turn, the tier the provider reports).
TIER_FACTS = {"requested_service_tier", "offered_service_tier", "transmitted_service_tier",
              "configured_service_tier", "turn_service_tier", "effective_service_tier"}
RECEIPT_KEYS = {"access_via", "protocol", "requested_model", "requested_effort",
                "transmitted_model", "transmitted_effort", "configured_model",
                "configured_effort", "model_evidence", "responding_model"} | TIER_FACTS
# The language's two words (01 §run), and the native value each route of the reference binding
# table gives them over ACP (runtime/access-harness/README.md): codex reads `fast` as its
# `fast-mode` option set to `on`, and `standard` as that option set to `off`. A route absent
# from this table binds no tier, and neither does any route over its inference API.
TIER_WORDS = ("standard", "fast")
TIER_BINDING = {"codex": {"standard": "off", "fast": "on"}}


def laws() -> dict:
    found = {}
    for name in ("model.yaml", "temporal.yaml"):
        document = yaml.safe_load((ROOT / "canon/laws" / name).read_text(encoding="utf-8"))
        found.update({law["id"]: law for law in document["laws"]})
    return found


def count(value) -> bool:
    return type(value) is int and value >= 0


def closed(value, allowed: set, label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} must be an object"]
    return [f"{label}: unknown key {key!r}" for key in sorted(set(value) - allowed)]


def access_fixtures() -> list[Path]:
    return sorted(d for d in HARNESS.iterdir()
                  if (d / "run.json").is_file()
                  and "access_routes" in json.loads((d / "run.json").read_text(encoding="utf-8")))


def load(directory: Path) -> tuple[dict, dict, dict]:
    workflow = yaml.safe_load((directory / "input.nika").read_text(encoding="utf-8"))
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    expected = json.loads((directory / "expected-run.json").read_text(encoding="utf-8"))
    return workflow, run, expected


def shape_errors(run: dict, expected: dict) -> list[str]:
    """The closed fixture extension documented in access-harness/README.md."""
    errors = []
    routes = run.get("access_routes")
    if not isinstance(routes, dict) or not routes:
        return ["access_routes must be a nonempty object"]
    for via, route in routes.items():
        if not KEBAB.match(via):
            errors.append(f"route id {via!r} is not kebab-case")
        errors += closed(route, ROUTE_KEYS, f"route {via}")
        if not isinstance(route, dict):
            continue
        acp = route.get("acp")
        if acp is not None:
            errors += closed(acp, ACP_KEYS, f"{via}.acp")
            if not isinstance(acp, dict) or type(acp.get("available")) is not bool:
                errors.append(f"{via}.acp.available must be a boolean")
            elif acp["available"]:
                if acp.get("config") not in {"options", "legacy"}:
                    errors.append(f"{via}.acp.config must be options or legacy")
                if "readback" in acp and (acp.get("config") != "options"
                                          or acp["readback"] not in {"confirmed", "unconfirmed"}):
                    errors.append(f"{via}.acp.readback is confirmed|unconfirmed, options only")
                models = acp.get("models")
                if not isinstance(models, dict) or not models:
                    errors.append(f"{via}.acp.models must be a nonempty object")
                else:
                    for model, offer in models.items():
                        if not MODEL_ID.match(model):
                            errors.append(f"{via}.acp.models: {model!r} is not <provider>/<name>")
                        errors += closed(offer, OFFER_KEYS, f"{via}.acp.models.{model}")
                        efforts = offer.get("effort") if isinstance(offer, dict) else None
                        if not isinstance(efforts, list) or any(
                                not isinstance(e, str) or not e for e in efforts):
                            errors.append(f"{via}.acp.models.{model}.effort must list nonempty strings")
                        tiers = offer.get("service_tier", []) if isinstance(offer, dict) else []
                        if (not isinstance(tiers, list) or any(t not in TIER_WORDS for t in tiers)
                                or len(set(tiers)) != len(tiers)):
                            errors.append(f"{via}.acp.models.{model}.service_tier lists standard, "
                                          "fast or both, once each")
                        elif tiers and acp.get("config") == "legacy":
                            errors.append(f"{via}.acp: a legacy session offers no service tier")
                if "default_model" in acp and not MODEL_ID.match(str(acp["default_model"])):
                    errors.append(f"{via}.acp.default_model is not <provider>/<name>")
                if acp.get("prompt", "completes") not in {"completes", "session_dies"}:
                    errors.append(f"{via}.acp.prompt must be completes or session_dies")
        for side, flag, extra in (("cli", "available", set()), ("api", "configured", {"responder"})):
            if side in route:
                errors += closed(route[side], {flag} | extra, f"{via}.{side}")
                if not isinstance(route[side], dict) or type(route[side].get(flag)) is not bool:
                    errors.append(f"{via}.{side}.{flag} must be a boolean")
        responder = route.get("api", {}).get("responder") if isinstance(route.get("api"), dict) else None
        if responder is not None and (not isinstance(responder, str) or not responder):
            errors.append(f"{via}.api.responder must be a nonempty string")
    observed = expected.get("observed")
    if not isinstance(observed, dict):
        errors.append("an access-selection fixture asserts observed")
    else:
        errors += closed(observed, OBSERVED_KEYS, "observed")
        for key in OBSERVED_KEYS - {"acp_config_before_first_prompt"}:
            if key not in observed or not count(observed[key]):
                errors.append(f"observed.{key} must be an exact nonnegative integer")
        applied = observed.get("acp_config_before_first_prompt")
        if applied is not None:
            errors += closed(applied, APPLIED_KEYS, "observed.acp_config_before_first_prompt")
            if isinstance(applied, dict) and applied.get("service_tier", "fast") not in TIER_WORDS:
                errors.append("observed.acp_config_before_first_prompt.service_tier is the "
                              "language word, never a route's own value")
    if "receipt" in expected:
        errors += closed(expected["receipt"], RECEIPT_KEYS, "receipt")
    return errors


def infer_grade(attestation) -> bool:
    return (isinstance(attestation, dict) and attestation.get("single_turn") is True
            and attestation.get("no_implicit_tools") is True
            and attestation.get("structured_output") in {"text", "json", "json_schema"}
            and isinstance(attestation.get("model_identity"), str))


def predict(workflow: dict, run: dict) -> tuple[str, dict]:
    """The contract's verdict for these premises (01 §run · LAW-CONF-0501).

    The plane is ``admission`` (the file and the probed routes decide it, no
    workflow event), ``session`` (only the live session reveals it: the task
    fails before its first prompt) or ``run`` (the selection is honored).
    """
    declared = workflow.get("run", {})
    access = declared.get("access", {})
    effort = declared.get("reasoning", {}).get("effort")
    tier = access.get("service_tier")
    model, via, protocol = workflow.get("model"), access.get("via"), access.get("protocol")
    verbs = [verb for task in workflow["tasks"].values() for verb in VERBS if verb in task]
    model_tasks = sum(verb in {"infer", "agent"} for verb in verbs)
    route = run["access_routes"].get(via)
    # The route's own values for the two words: a route fact, known before any session.
    binding = TIER_BINDING.get(via) if protocol == "acp" else None
    unbound = {"reason": "the route binds no service tier on this protocol"}
    if "access" in run and run["access"] != via:
        return "admission", {"reason": "a launch option contradicts the declared route"}
    if route is None:
        return "admission", {"reason": "the declared route is not staged"}
    if protocol == "api":
        if not route.get("api", {}).get("configured"):
            return "admission", {"reason": "the route does not speak api here"}
        if tier is not None:
            return "admission", unbound
        return "run", {"protocol": "api", "via": via, "model": model, "effort": effort,
                       "tier": None, "responder": route["api"].get("responder"),
                       "api": model_tasks, "acp": 0, "cli": 0}
    if protocol != "acp":
        raise ValueError("an access-selection fixture declares api or acp")
    acp = route.get("acp")
    if acp is None:
        return "admission", {"reason": "the route does not speak acp"}
    if not acp["available"]:
        return "admission", {"reason": "the ACP adapter is absent"}
    if "infer" in verbs and not infer_grade(run.get("harness_attestations", {}).get(via)):
        return "admission", {"reason": "infer: has no attested ACP one-shot on this route"}
    if tier is not None and binding is None:
        return "admission", unbound
    if model not in acp["models"]:
        return "session", {"reason": "the session does not advertise the model"}
    if effort is not None and (acp["config"] == "legacy"
                               or effort not in acp["models"][model]["effort"]):
        return "session", {"reason": "the selected model is not offered this effort"}
    # The tier is judged last, against what the SELECTED model offers. A session
    # that only acknowledges a model request exposes no option to apply one with.
    offered = acp["models"][model].get("service_tier", [])
    if tier is not None and acp["config"] == "legacy":
        return "session", {"reason": "a session that only acknowledges cannot apply a service tier"}
    if tier is not None and tier not in offered:
        return "session", {"reason": "the selected model is not offered this service tier"}
    configured = acp["config"] == "options"
    if configured and acp.get("readback", "confirmed") == "unconfirmed":
        return "session", {"reason": "the read-back configuration does not hold the selection"}
    return "run", {
        "protocol": "acp", "via": via, "model": model, "effort": effort,
        "tier": tier, "tier_offered": offered, "tier_values": binding or {},
        "configured": configured, "responder": None,  # an ACP session names no responder
        "dies": acp.get("prompt", "completes") == "session_dies",
        "api": 0, "acp": model_tasks, "cli": 0,
    }


def exact_counts(observed: dict, want: dict) -> list[str]:
    return [f"observed.{key}: premises give {value} · fixture claims {observed.get(key)}"
            for key, value in want.items()
            if not (count(observed.get(key)) and observed[key] == value)]


def failed_tasks(expected: dict) -> list[str]:
    """A failing run whose every asserted task failed with an access-family code."""
    tasks = expected.get("tasks", {})
    if expected.get("workflow_state") != "failure" or not tasks:
        return ["the run fails and names the failed task"]
    return [f"task {name} fails with an access-family code (NIKA-1800..1849)"
            for name, task in tasks.items()
            if task.get("status") != "failure" or not ACCESS_CODE.match(str(task.get("error_code")))]


def judge(workflow: dict, run: dict, expected: dict) -> list[str]:
    """Every claim the fixture makes must follow from its premises."""
    plane, facts = predict(workflow, run)
    observed = expected.get("observed", {})
    admission = expected.get("admission", {})
    zero = {"acp_prompts": 0, "api_inference_requests": 0, "cli_invocations": 0}
    diffs = []
    if plane == "admission":
        if admission.get("accepted") is not False:
            diffs.append(f"premises refuse at admission ({facts['reason']}) · fixture claims otherwise")
        elif not ACCESS_CODE.match(str(admission.get("error_code"))):
            diffs.append("an admission refusal records an access-family code (NIKA-1800..1849)")
        if set(expected) & {"workflow_state", "tasks", "receipt"}:
            diffs.append("an admission refusal asserts no execution and no receipt")
    elif plane == "session":
        if admission.get("accepted") is not True:
            diffs.append(f"only the live session refuses ({facts['reason']}) · the run was admitted")
        diffs += failed_tasks(expected)
    if plane in {"admission", "session"}:
        diffs += exact_counts(observed, zero)
        if "acp_config_before_first_prompt" in observed:
            diffs.append("no prompt arrived, so no configuration precedes one")
        return diffs
    if admission.get("accepted") is not True:
        diffs.append("premises admit the selection · fixture claims a refusal")
    if facts.get("dies"):
        diffs += failed_tasks(expected)
    elif expected.get("workflow_state") != "success" or any(
            task.get("status") != "success" for task in expected.get("tasks", {}).values()):
        diffs.append("the honored selection completes: success")
    diffs += exact_counts(observed, {"acp_prompts": facts["acp"],
                                     "api_inference_requests": facts["api"],
                                     "cli_invocations": facts["cli"]})
    tier = facts["tier"]
    if facts["protocol"] == "acp":
        # A declared tier is held in the language's word; a session default is never applied.
        applied = {"model": facts["model"],
                   **({"effort": facts["effort"]} if facts["effort"] else {}),
                   **({"service_tier": tier} if tier else {})}
        if observed.get("acp_config_before_first_prompt") != applied:
            diffs.append(f"the peer holds {applied} before its first prompt")
    elif "acp_config_before_first_prompt" in observed:
        diffs.append("an API run configures no ACP session")
    receipt = expected.get("receipt", {})
    # A run that declares no tier records none: every tier fact is unknown. The
    # scripted peer witnesses neither the turn nor the provider, so those two
    # stay unknown for a declared tier as well.
    want = {"access_via": facts["via"], "protocol": facts["protocol"],
            "requested_model": facts["model"], "requested_effort": facts["effort"],
            "transmitted_model": facts["model"], "responding_model": facts["responder"],
            **dict.fromkeys(TIER_FACTS), "requested_service_tier": tier}
    if facts["protocol"] == "acp":
        confirmed = facts["configured"]
        want.update({
            "transmitted_effort": facts["effort"],
            "configured_model": facts["model"] if confirmed else None,
            "configured_effort": facts["effort"] if confirmed else None,
            "model_evidence": "configured" if confirmed else "accepted_request",
        })
        if tier:
            # The route's native values, in the session's own order. A tier is honored only
            # through a configuration option, so its read-back is always the value sent.
            native = facts["tier_values"]
            want.update({
                "offered_service_tier": [native.get(word) for word in facts["tier_offered"]],
                "transmitted_service_tier": native.get(tier),
                "configured_service_tier": native.get(tier),
            })
    for key, value in receipt.items():
        if key in want and value != want[key]:
            diffs.append(f"receipt.{key}: premises give {want[key]!r} · fixture claims {value!r}")
    if facts["protocol"] == "acp" and not facts.get("dies"):
        if not {"configured_model", "model_evidence", "responding_model"} <= set(receipt):
            diffs.append("an ACP fixture keeps configured, evidence and responder facts apart")
        if tier and not TIER_FACTS <= set(receipt):
            diffs.append("a fixture that honors a declared tier keeps its six facts apart")
        if not tier and facts["tier_offered"] and not {
                "requested_service_tier", "transmitted_service_tier"} <= set(receipt):
            diffs.append("a tier offered and not declared: the receipt states that none was "
                         "requested and none travelled")
    return diffs


class SchemaShape(unittest.TestCase):
    def test_the_envelope_keeps_its_nine_keys(self):
        self.assertEqual(set(SCHEMA["properties"]), ENVELOPE_KEYS)
        self.assertIs(SCHEMA["additionalProperties"], False)

    def test_run_is_closed_over_four_optional_dimensions(self):
        run = SCHEMA["properties"]["run"]
        self.assertIs(run["additionalProperties"], False)
        self.assertEqual(set(run["properties"]), {"entropy", "clock", "access", "reasoning"})
        self.assertNotIn("required", run)

    def test_access_is_closed_nonempty_and_has_two_protocols(self):
        access = SCHEMA["properties"]["run"]["properties"]["access"]
        self.assertIs(access["additionalProperties"], False)
        self.assertEqual(access["minProperties"], 1)
        self.assertNotIn("required", access)
        self.assertEqual(set(access["properties"]), {"via", "protocol", "fallback", "service_tier"})
        self.assertEqual(access["properties"]["protocol"]["enum"], ["api", "acp"])
        self.assertEqual(access["properties"]["fallback"]["enum"], ["none"])
        self.assertEqual(access["properties"]["via"]["pattern"], "^[a-z][a-z0-9-]*(?![\\s\\S])")

    def test_the_service_tier_is_two_words_and_nothing_else(self):
        tier = SCHEMA["properties"]["run"]["properties"]["access"]["properties"]["service_tier"]
        self.assertEqual(tier["enum"], ["standard", "fast"])
        # A closed literal: the enum is the whole rule. A type, a pattern or a default would
        # let a route's own word, a boolean or an assumed tier through another door.
        self.assertFalse({"type", "pattern", "default", "const", "anyOf", "oneOf"} & set(tier))

    def test_reasoning_requires_a_native_effort_and_lists_none(self):
        reasoning = SCHEMA["properties"]["run"]["properties"]["reasoning"]
        self.assertIs(reasoning["additionalProperties"], False)
        self.assertEqual(reasoning["required"], ["effort"])
        effort = reasoning["properties"]["effort"]
        self.assertEqual(effort["type"], "string")
        # No universal scale: a value list here would be an invented catalog.
        self.assertFalse({"enum", "const", "examples", "default"} & set(effort))

    def test_literal_rules_hold_on_every_edge(self):
        """The schema implements the prose rules exactly, whatever a regex dialect does with $.

        via: ASCII kebab-case, nothing after it. effort: nonempty, no surrounding
        Unicode White_Space (inner characters kept), no template.
        """
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(SCHEMA)
        white_space = set(map(chr, [*range(0x09, 0x0E), 0x20, 0x85, 0xA0, 0x1680,
                                    *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F,
                                    0x3000]))

        def admitted(run):
            document = {"nika": "t", "tasks": {"a": {"infer": {"prompt": "hi"}}}, "run": run}
            return not list(validator.iter_errors(document))

        def kebab(text):
            return bool(re.fullmatch(r"[a-z][a-z0-9-]*", text, flags=re.ASCII))

        def verbatim(text):
            core = text.strip("".join(white_space))
            return bool(core) and core == text and "${{" not in text

        for via in ["codex", "claude-code", "c0", "codex-", "codex\n", "\ncodex", "Codex",
                    "co dex", "", "c\u00e9"]:
            with self.subTest(via=via):
                self.assertEqual(admitted({"access": {"via": via}}), kebab(via))
        for effort in ["high", "x", "extra high", "a\nb", "high\n", "\nhigh", " high", "high ",
                       "high\t", "high\u0085", "\u00a0high", "high\u3000", "high\u2029",
                       "\ufeffhigh", "high\x1c", "${{ inputs.e }}", "", " "]:
            with self.subTest(effort=effort):
                self.assertEqual(admitted({"reasoning": {"effort": effort}}), verbatim(effort))
        # The tier is two exact words: no case folding, no padding, no route-native word
        # (an on/off switch, an API's own tier names), no template, no other scalar type.
        for tier in ["standard", "fast", "Fast", "FAST", " fast", "fast ", "fast\n", "on", "off",
                     "priority", "flex", "default", "auto", "ultrafast", "",
                     "${{ inputs.tier }}"]:
            with self.subTest(tier=tier):
                self.assertEqual(admitted({"access": {"service_tier": tier}}),
                                 tier in ("standard", "fast"))
        for tier in [True, False, 1, None, ["fast"], {"fast": True}]:
            with self.subTest(tier=repr(tier)):
                self.assertFalse(admitted({"access": {"service_tier": tier}}))

    def test_selection_is_declared_only_under_run(self):
        places = []

        def walk(node, pointer):
            if isinstance(node, dict):
                for name in node.get("properties", {}):
                    if name in {"access", "reasoning", "service_tier"}:
                        places.append(f"{pointer}/properties/{name}")
                for key, child in node.items():
                    walk(child, f"{pointer}/{key}")
            elif isinstance(node, list):
                for index, child in enumerate(node):
                    walk(child, f"{pointer}/{index}")

        walk(SCHEMA, "")
        self.assertEqual(sorted(places), [
            "/properties/run/properties/access",
            "/properties/run/properties/access/properties/service_tier",
            "/properties/run/properties/reasoning"])


class StaticFixtures(unittest.TestCase):
    def setUp(self):
        from jsonschema import Draft202012Validator
        self.validator = Draft202012Validator(SCHEMA)
        self.canon = runner.load_canon()
        self.laws = laws()
        self.fixtures = sorted(
            d for d in ENVELOPE.iterdir()
            if d.name[:3].isdigit() and int(d.name[:3]) >= FIRST_ACCESS_FIXTURE
            and ACCESS_SUBJECT.search((d / "input.yaml").read_text(encoding="utf-8")))

    def test_every_access_fixture_meets_its_verdict(self):
        self.assertTrue(self.fixtures)
        for directory in self.fixtures:
            with self.subTest(fixture=directory.name):
                expected = json.loads((directory / "expected.json").read_text(encoding="utf-8"))
                verdict = runner.validate_text((directory / "input.yaml").read_text(encoding="utf-8"),
                                               self.validator, self.canon, base_dir=directory)
                self.assertEqual(verdict["valid"], expected["valid"], verdict["errors"])
                for error in expected.get("errors", []):
                    self.assertTrue(runner._matches(error, verdict["errors"]), verdict["errors"])

    def test_refusals_are_single_and_targeted(self):
        for directory in self.fixtures:
            expected = json.loads((directory / "expected.json").read_text(encoding="utf-8"))
            if expected["valid"]:
                continue
            with self.subTest(fixture=directory.name):
                verdict = runner.validate_text((directory / "input.yaml").read_text(encoding="utf-8"),
                                               self.validator, self.canon, base_dir=directory)
                self.assertEqual(len(verdict["errors"]), 1, verdict["errors"])

    def test_laws_cite_every_fixture_with_its_polarity(self):
        cited = {}
        for law_id in ACCESS_LAWS | {"LAW-TEMPORAL-0435"}:
            law = self.laws[law_id]
            for key, valid in (("fixtures", True), ("negative_fixtures", False)):
                for path in law.get(key, []):
                    cited.setdefault(path, set()).add(valid)
        for directory in self.fixtures:
            path = directory.relative_to(ROOT).as_posix()
            expected = json.loads((directory / "expected.json").read_text(encoding="utf-8"))
            with self.subTest(fixture=directory.name):
                self.assertEqual(cited.get(path), {expected["valid"]})

    def test_access_laws_cite_only_existing_fixtures(self):
        for law_id in ACCESS_LAWS:
            for key in ("fixtures", "negative_fixtures"):
                for path in self.laws[law_id].get(key, []):
                    with self.subTest(law=law_id, fixture=path):
                        self.assertTrue((ROOT / path).is_dir())


class RuntimeFixtures(unittest.TestCase):
    def setUp(self):
        from jsonschema import Draft202012Validator
        self.validator = Draft202012Validator(SCHEMA)
        self.canon = runner.load_canon()
        self.fixtures = access_fixtures()

    def test_the_extension_is_closed(self):
        self.assertTrue(self.fixtures)
        for directory in self.fixtures:
            workflow, run, expected = load(directory)
            with self.subTest(fixture=directory.name):
                self.assertEqual(shape_errors(run, expected), [])

    def test_inputs_are_statically_valid_and_declare_the_selection(self):
        for directory in self.fixtures:
            text = (directory / "input.nika").read_text(encoding="utf-8")
            with self.subTest(fixture=directory.name):
                verdict = runner.validate_text(text, self.validator, self.canon, base_dir=directory)
                self.assertTrue(verdict["valid"], verdict["errors"])
                self.assertIn("access", yaml.safe_load(text).get("run", {}))

    def test_every_claim_follows_from_the_premises(self):
        for directory in self.fixtures:
            with self.subTest(fixture=directory.name):
                self.assertEqual(judge(*load(directory)), [])

    def test_conf_law_cites_every_access_selection_fixture(self):
        law = laws()["LAW-CONF-0501"]
        for directory in self.fixtures:
            _, run, expected = load(directory)
            path = directory.relative_to(ROOT).as_posix()
            honored = (expected.get("admission", {}).get("accepted") is True
                       and expected.get("workflow_state") == "success")
            key = "fixtures" if honored else "negative_fixtures"
            with self.subTest(fixture=directory.name):
                self.assertIn(path, law.get(key, []))


def acknowledged_as_configured(workflow, run, expected):
    """A legacy session acknowledged the model; the only lie left is « configured »."""
    workflow["run"].pop("reasoning")
    run["access_routes"]["codex"]["acp"].update(config="legacy",
                                                models={"openai/gpt-5.5": {"effort": []}})
    expected["observed"]["acp_config_before_first_prompt"].pop("effort")
    expected["receipt"].update(requested_effort=None, transmitted_effort=None,
                               configured_effort=None)


def tier_acknowledged_as_configured(workflow, run, expected):
    """A legacy session acknowledged the model and exposes no option to apply a tier
    with. Everything else is restated truthfully; the tier is still claimed configured."""
    acknowledged_as_configured(workflow, run, expected)
    expected["receipt"].update(configured_model=None, model_evidence="accepted_request")


def tier_over_an_api(workflow, run, expected):
    """The same file on a route's inference API, where no route binds a tier."""
    workflow["run"]["access"].update(via="openai", protocol="api")
    run["access_routes"]["openai"] = {"api": {"configured": True}}


def tier_on_an_unbound_agent_route(workflow, run, expected):
    """The same file and session on an agent application the binding table does not know."""
    workflow["run"]["access"]["via"] = "another-agent"
    run["access_routes"]["another-agent"] = run["access_routes"].pop("codex")
    expected["receipt"]["access_via"] = "another-agent"


class TheJudgeHasTeeth(unittest.TestCase):
    """Each mutation is a plausible authoring or engine-shaped lie; all must be caught."""

    def setUp(self):
        self.base = load(HARNESS / "003-file-acp-selection-configured-before-prompt")

    def mutated(self, change, base=None):
        workflow, run, expected = copy.deepcopy(self.base if base is None else base)
        change(workflow, run, expected)
        return workflow, run, expected

    def caught(self, change, base=None):
        return bool(self.findings(change, base))

    def findings(self, change, base=None) -> list[str]:
        """Every difference the judge and the shape check name for a mutated fixture,
        with the reason the premises give when they are the ones that refuse."""
        workflow, run, expected = self.mutated(change, base)
        found = judge(workflow, run, expected) + shape_errors(run, expected)
        reason = predict(workflow, run)[1].get("reason")
        return found + ([f"premises refuse: {reason}"] if found and reason else [])

    def test_the_unmutated_fixture_is_clean(self):
        self.assertEqual(judge(*self.base), [])

    def test_mutations_are_caught(self):
        acp = lambda r: r["access_routes"]["codex"]["acp"]
        mutations = {
            "effort not offered yet admitted":
                lambda w, r, e: acp(r)["models"]["openai/gpt-5.5"].update(effort=["low"]),
            "effort judged on the default model":
                lambda w, r, e: (acp(r).update(default_model="openai/gpt-5.4"),
                                 acp(r)["models"].update({"openai/gpt-5.4": {"effort": ["high"]}}),
                                 acp(r)["models"]["openai/gpt-5.5"].update(effort=["low"])),
            "unavailable route yet admitted": lambda w, r, e: acp(r).update(available=False),
            "API substitutes for ACP":
                lambda w, r, e: e["observed"].update(acp_prompts=0, api_inference_requests=1),
            "direct CLI substitutes for ACP":
                lambda w, r, e: e["observed"].update(acp_prompts=0, cli_invocations=1),
            "config applied after the prompt":
                lambda w, r, e: e["observed"].pop("acp_config_before_first_prompt"),
            "effort translated":
                lambda w, r, e: e["observed"]["acp_config_before_first_prompt"].update(effort="max"),
            "effort over an acknowledge-only session admitted":
                lambda w, r, e: acp(r).update(config="legacy",
                                              models={"openai/gpt-5.5": {"effort": []}}),
            "acknowledgement promoted to configuration": acknowledged_as_configured,
            "request promoted to responder":
                lambda w, r, e: e["receipt"].update(responding_model="openai/gpt-5.5"),
            "unconfirmed readback admitted": lambda w, r, e: acp(r).update(readback="unconfirmed"),
            "launch option overrides the file": lambda w, r, e: r.update(access="openai"),
            "infer over an unattested ACP seat":
                lambda w, r, e: w["tasks"]["summarize"].update(
                    infer=w["tasks"]["summarize"].pop("agent")),
            "unknown route-world key": lambda w, r, e: acp(r).update(effort_options=["high"]),
            "boolean count": lambda w, r, e: e["observed"].update(acp_prompts=True),
        }
        for label, change in mutations.items():
            with self.subTest(mutation=label):
                self.assertTrue(self.caught(change), label)

    def test_service_tier_mutations_are_caught_for_their_own_reason(self):
        fast = load(HARNESS / "018-file-acp-service-tier-fast-configured-before-prompt")
        standard = load(HARNESS / "019-file-acp-service-tier-standard-configured-before-prompt")
        omitted = load(HARNESS / "020-file-acp-service-tier-omitted-sends-none")
        for base in (fast, standard, omitted):
            self.assertEqual(judge(*base) + shape_errors(base[1], base[2]), [])
        acp = lambda r: r["access_routes"]["codex"]["acp"]
        offer = lambda r: acp(r)["models"]["openai/gpt-5.5"]
        held = lambda e: e["observed"]["acp_config_before_first_prompt"]
        unoffered = "the selected model is not offered this service tier"
        mutations = {
            "fast served as standard on the wire": (
                fast, lambda w, r, e: held(e).update(service_tier="standard"), "the peer holds"),
            "fast served as standard in the receipt": (
                fast, lambda w, r, e: e["receipt"].update(transmitted_service_tier="off",
                                                          configured_service_tier="off"),
                "receipt.transmitted_service_tier: premises give 'on'"),
            "standard served as fast": (
                standard, lambda w, r, e: e["receipt"].update(transmitted_service_tier="on",
                                                              configured_service_tier="on"),
                "receipt.configured_service_tier: premises give 'off'"),
            "a tier admitted on a model that does not offer it": (
                fast, lambda w, r, e: offer(r).pop("service_tier"), unoffered),
            "standard assumed where only fast is offered": (
                standard, lambda w, r, e: offer(r).update(service_tier=["fast"]), unoffered),
            "a tier judged on the default model": (
                fast, lambda w, r, e: (
                    acp(r).update(default_model="openai/gpt-5.4"),
                    acp(r)["models"].update({"openai/gpt-5.4": {
                        "effort": ["high"], "service_tier": ["standard", "fast"]}}),
                    offer(r).pop("service_tier")), unoffered),
            "a tier applied after the prompt": (
                fast, lambda w, r, e: held(e).pop("service_tier"), "the peer holds"),
            "a tier recorded for a file that declared none": (
                omitted, lambda w, r, e: e["receipt"].update(configured_service_tier="on"),
                "receipt.configured_service_tier: premises give None"),
            "the session's offer recorded for a file that declared none": (
                omitted, lambda w, r, e: e["receipt"].update(offered_service_tier=["on", "off"]),
                "receipt.offered_service_tier: premises give None"),
            "the session default held as an applied tier": (
                omitted, lambda w, r, e: held(e).update(service_tier="fast"), "the peer holds"),
            "the declaration dropped from the file, the tier still claimed": (
                fast, lambda w, r, e: w["run"]["access"].pop("service_tier"),
                "receipt.requested_service_tier: premises give None"),
            "an acknowledged tier promoted to configured": (
                fast, tier_acknowledged_as_configured,
                "a session that only acknowledges cannot apply a service tier"),
            "an unconfirmed read-back admitted": (
                fast, lambda w, r, e: acp(r).update(readback="unconfirmed"),
                "the read-back configuration does not hold the selection"),
            "a tier admitted over an API": (
                fast, tier_over_an_api, "the route binds no service tier on this protocol"),
            "a tier admitted on an agent route that binds none": (
                fast, tier_on_an_unbound_agent_route,
                "the route binds no service tier on this protocol"),
            "the confirmed configuration relabelled as the tier that served": (
                fast, lambda w, r, e: e["receipt"].update(effective_service_tier="on"),
                "receipt.effective_service_tier: premises give None"),
            "the turn's tier claimed with no witness": (
                fast, lambda w, r, e: e["receipt"].update(turn_service_tier="on"),
                "receipt.turn_service_tier: premises give None"),
            "the language word recorded as the value sent": (
                fast, lambda w, r, e: e["receipt"].update(transmitted_service_tier="fast"),
                "receipt.transmitted_service_tier: premises give 'on'"),
            "the route's value held as the language word": (
                fast, lambda w, r, e: held(e).update(service_tier="on"),
                "service_tier is the language word"),
            "the offer reordered": (
                fast, lambda w, r, e: e["receipt"].update(offered_service_tier=["on", "off"]),
                "receipt.offered_service_tier: premises give ['off', 'on']"),
            "a tier fact left out of an honored tier": (
                fast, lambda w, r, e: e["receipt"].pop("turn_service_tier"),
                "keeps its six facts apart"),
            "an offered tier left unstated by the receipt": (
                omitted, lambda w, r, e: e["receipt"].pop("requested_service_tier"),
                "a tier offered and not declared"),
            "a word outside the language in the offer": (
                fast, lambda w, r, e: offer(r).update(service_tier=["fast", "priority"]),
                "service_tier lists standard, fast or both, once each"),
            "a tier offered by a legacy session": (
                fast, lambda w, r, e: acp(r).update(config="legacy"),
                "a legacy session offers no service tier"),
            "an unknown tier receipt key": (
                fast, lambda w, r, e: e["receipt"].update(served_service_tier="on"),
                "receipt: unknown key 'served_service_tier'"),
        }
        for label, (base, change, witness) in mutations.items():
            with self.subTest(mutation=label):
                found = self.findings(change, base)
                self.assertTrue(any(witness in line for line in found),
                                f"{witness!r} not in {found}")

    def test_tier_refusals_observe_zero_inference_on_their_plane(self):
        zero = {"acp_prompts": 0, "api_inference_requests": 0, "cli_invocations": 0}
        refusals = {number: load(next(HARNESS.glob(f"{number}-*")))
                    for number in ("021", "023", "024", "025", "026", "027")}
        for number, base in refusals.items():
            with self.subTest(fixture=number, case="clean"):
                self.assertEqual(judge(*base) + shape_errors(base[1], base[2]), [])
            for label, leak in {"a prompt was sent": {"acp_prompts": 1},
                                "the API was called": {"api_inference_requests": 1},
                                "the CLI was started": {"cli_invocations": 1}}.items():
                with self.subTest(fixture=number, leak=label):
                    self.assertTrue(self.caught(
                        lambda w, r, e, leak=leak: e["observed"].update(leak), base))
            with self.subTest(fixture=number, case="honored anyway"):
                self.assertTrue(self.caught(lambda w, r, e: (e.clear(), e.update(
                    {"admission": {"accepted": True}, "workflow_state": "success",
                     "tasks": {"summarize": {"status": "success"}},
                     "observed": dict(zero, acp_prompts=1)})), base))
        with self.subTest(case="a session refusal claimed at admission"):
            self.assertTrue(self.caught(lambda w, r, e: (e.clear(), e.update(
                {"admission": {"accepted": False, "error_code": "NIKA-1805"},
                 "observed": dict(zero)})), refusals["021"]))
        with self.subTest(case="an admission refusal claimed as a task failure"):
            self.assertTrue(self.caught(lambda w, r, e: (e.clear(), e.update(
                {"admission": {"accepted": True}, "workflow_state": "failure",
                 "tasks": {"summarize": {"status": "failure", "error_code": "NIKA-1800"}},
                 "observed": dict(zero)})), refusals["027"]))
        with self.subTest(case="the unbound route served at its own default tier"):
            self.assertTrue(self.caught(lambda w, r, e: (e.clear(), e.update(
                {"admission": {"accepted": True}, "workflow_state": "success",
                 "tasks": {"summarize": {"status": "success"}},
                 "observed": dict(zero, api_inference_requests=1)})), refusals["027"]))

    def test_refusals_observe_zero_inference_on_their_plane(self):
        zero = {"acp_prompts": 0, "api_inference_requests": 0, "cli_invocations": 0}

        def session_refusal(w, r, e):
            r["access_routes"]["codex"]["acp"]["models"]["openai/gpt-5.5"]["effort"] = ["low"]
            e.clear()
            e.update({"admission": {"accepted": True}, "workflow_state": "failure",
                      "tasks": {"summarize": {"status": "failure", "error_code": "NIKA-1805"}},
                      "observed": dict(zero)})

        def admission_refusal(w, r, e):
            r["access_routes"]["codex"]["acp"]["available"] = False
            e.clear()
            e.update({"admission": {"accepted": False, "error_code": "NIKA-1803"},
                      "observed": dict(zero)})

        for plane, refusal in {"session": session_refusal, "admission": admission_refusal}.items():
            with self.subTest(plane=plane, case="clean"):
                self.assertEqual(judge(*self.mutated(refusal)), [])
            for label, leak in {"a prompt was sent": {"acp_prompts": 1},
                                "the API was called": {"api_inference_requests": 1},
                                "the CLI was started": {"cli_invocations": 1}}.items():
                with self.subTest(plane=plane, leak=label):
                    self.assertTrue(self.caught(lambda w, r, e, refusal=refusal, leak=leak: (
                        refusal(w, r, e), e["observed"].update(leak))))
        with self.subTest(case="an invented code"):
            self.assertTrue(self.caught(lambda w, r, e: (
                admission_refusal(w, r, e), e["admission"].update(error_code="NIKA-ACCESS-001"))))
        with self.subTest(case="a session refusal claimed at admission"):
            self.assertTrue(self.caught(lambda w, r, e: (
                session_refusal(w, r, e), e.clear(), e.update(
                    {"admission": {"accepted": False, "error_code": "NIKA-1805"},
                     "observed": dict(zero)}))))
        with self.subTest(case="an admission refusal claimed as a task failure"):
            self.assertTrue(self.caught(lambda w, r, e: (
                admission_refusal(w, r, e), e.clear(), e.update(
                    {"admission": {"accepted": True}, "workflow_state": "failure",
                     "tasks": {"summarize": {"status": "failure", "error_code": "NIKA-1803"}},
                     "observed": dict(zero)}))))

    def test_an_api_responder_is_recorded_verbatim(self):
        workflow, run, expected = load(HARNESS / "005-file-api-attested-responder-recorded")
        self.assertEqual(judge(workflow, run, expected), [])
        for label, claim in {"rewritten into the request": "openai/gpt-5.5",
                             "dropped although attested": None}.items():
            with self.subTest(mutation=label):
                lie = copy.deepcopy(expected)
                lie["receipt"]["responding_model"] = claim
                self.assertTrue(judge(workflow, run, lie))

    def test_a_dying_session_fails_on_the_same_route(self):
        def dies(w, r, e):
            r["access_routes"]["codex"]["acp"]["prompt"] = "session_dies"
            r["access_routes"]["codex"]["cli"] = {"available": True}
            r["access_routes"]["openai"] = {"api": {"configured": True}}
            e["workflow_state"] = "failure"
            e["tasks"] = {"summarize": {"status": "failure", "error_code": "NIKA-1804"}}
        self.assertEqual(judge(*self.mutated(dies)), [])
        for label, reroute in {"re-routed to the API": {"api_inference_requests": 1},
                               "re-routed to the direct CLI": {"cli_invocations": 1},
                               "claimed success": None}.items():
            with self.subTest(mutation=label):
                def change(w, r, e, reroute=reroute):
                    dies(w, r, e)
                    if reroute is None:
                        e["workflow_state"] = "success"
                        e["tasks"] = {"summarize": {"status": "success"}}
                    else:
                        e["observed"].update(reroute)
                self.assertTrue(self.caught(change))

if __name__ == "__main__":
    unittest.main()
