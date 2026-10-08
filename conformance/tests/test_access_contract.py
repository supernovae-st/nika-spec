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
OBSERVED_KEYS = {"acp_config_before_first_prompt", "acp_prompts", "api_inference_requests",
                 "cli_invocations"}
RECEIPT_KEYS = {"access_via", "protocol", "requested_model", "requested_effort",
                "transmitted_model", "transmitted_effort", "configured_model",
                "configured_effort", "model_evidence", "responding_model"}


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
                        errors += closed(offer, {"effort"}, f"{via}.acp.models.{model}")
                        efforts = offer.get("effort") if isinstance(offer, dict) else None
                        if not isinstance(efforts, list) or any(
                                not isinstance(e, str) or not e for e in efforts):
                            errors.append(f"{via}.acp.models.{model}.effort must list nonempty strings")
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
            errors += closed(applied, {"model", "effort"}, "observed.acp_config_before_first_prompt")
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
    model, via, protocol = workflow.get("model"), access.get("via"), access.get("protocol")
    verbs = [verb for task in workflow["tasks"].values() for verb in VERBS if verb in task]
    model_tasks = sum(verb in {"infer", "agent"} for verb in verbs)
    route = run["access_routes"].get(via)
    if "access" in run and run["access"] != via:
        return "admission", {"reason": "a launch option contradicts the declared route"}
    if route is None:
        return "admission", {"reason": "the declared route is not staged"}
    if protocol == "api":
        if not route.get("api", {}).get("configured"):
            return "admission", {"reason": "the route does not speak api here"}
        return "run", {"protocol": "api", "via": via, "model": model, "effort": effort,
                       "responder": route["api"].get("responder"),
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
    if model not in acp["models"]:
        return "session", {"reason": "the session does not advertise the model"}
    if effort is not None and (acp["config"] == "legacy"
                               or effort not in acp["models"][model]["effort"]):
        return "session", {"reason": "the selected model is not offered this effort"}
    configured = acp["config"] == "options"
    if configured and acp.get("readback", "confirmed") == "unconfirmed":
        return "session", {"reason": "the read-back configuration does not hold the selection"}
    return "run", {
        "protocol": "acp", "via": via, "model": model, "effort": effort,
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
    if facts["protocol"] == "acp":
        applied = {"model": facts["model"], **({"effort": facts["effort"]} if facts["effort"] else {})}
        if observed.get("acp_config_before_first_prompt") != applied:
            diffs.append(f"the peer holds {applied} before its first prompt")
    elif "acp_config_before_first_prompt" in observed:
        diffs.append("an API run configures no ACP session")
    receipt = expected.get("receipt", {})
    want = {"access_via": facts["via"], "protocol": facts["protocol"],
            "requested_model": facts["model"], "requested_effort": facts["effort"],
            "transmitted_model": facts["model"], "responding_model": facts["responder"]}
    if facts["protocol"] == "acp":
        confirmed = facts["configured"]
        want.update({
            "transmitted_effort": facts["effort"],
            "configured_model": facts["model"] if confirmed else None,
            "configured_effort": facts["effort"] if confirmed else None,
            "model_evidence": "configured" if confirmed else "accepted_request",
        })
    for key, value in receipt.items():
        if key in want and value != want[key]:
            diffs.append(f"receipt.{key}: premises give {want[key]!r} · fixture claims {value!r}")
    if facts["protocol"] == "acp" and not facts.get("dies") and not {
            "configured_model", "model_evidence", "responding_model"} <= set(receipt):
        diffs.append("an ACP fixture keeps configured, evidence and responder facts apart")
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
        self.assertEqual(set(access["properties"]), {"via", "protocol", "fallback"})
        self.assertEqual(access["properties"]["protocol"]["enum"], ["api", "acp"])
        self.assertEqual(access["properties"]["fallback"]["enum"], ["none"])
        self.assertEqual(access["properties"]["via"]["pattern"], "^[a-z][a-z0-9-]*$")

    def test_reasoning_requires_a_native_effort_and_lists_none(self):
        reasoning = SCHEMA["properties"]["run"]["properties"]["reasoning"]
        self.assertIs(reasoning["additionalProperties"], False)
        self.assertEqual(reasoning["required"], ["effort"])
        effort = reasoning["properties"]["effort"]
        self.assertEqual(effort["type"], "string")
        # No universal scale: a value list here would be an invented catalog.
        self.assertFalse({"enum", "const", "examples", "default"} & set(effort))

    def test_selection_is_declared_only_under_run(self):
        places = []

        def walk(node, pointer):
            if isinstance(node, dict):
                for name in node.get("properties", {}):
                    if name in {"access", "reasoning"}:
                        places.append(f"{pointer}/properties/{name}")
                for key, child in node.items():
                    walk(child, f"{pointer}/{key}")
            elif isinstance(node, list):
                for index, child in enumerate(node):
                    walk(child, f"{pointer}/{index}")

        walk(SCHEMA, "")
        self.assertEqual(sorted(places), ["/properties/run/properties/access",
                                          "/properties/run/properties/reasoning"])


class StaticFixtures(unittest.TestCase):
    def setUp(self):
        from jsonschema import Draft202012Validator
        self.validator = Draft202012Validator(SCHEMA)
        self.canon = runner.load_canon()
        self.laws = laws()
        self.fixtures = sorted(d for d in ENVELOPE.iterdir()
                               if d.name[:3].isdigit() and int(d.name[:3]) >= FIRST_ACCESS_FIXTURE)

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


class TheJudgeHasTeeth(unittest.TestCase):
    """Each mutation is a plausible authoring or engine-shaped lie; all must be caught."""

    def setUp(self):
        self.base = load(HARNESS / "003-file-acp-selection-configured-before-prompt")

    def mutated(self, change):
        workflow, run, expected = copy.deepcopy(self.base)
        change(workflow, run, expected)
        return workflow, run, expected

    def caught(self, change):
        workflow, run, expected = self.mutated(change)
        return bool(judge(workflow, run, expected) or shape_errors(run, expected))

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
