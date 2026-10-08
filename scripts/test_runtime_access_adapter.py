#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Adversarial laws for the access-selection adapter (runtime_access_adapter.py).

ADAPTER TESTS, NOT ENGINE RESULTS. Every engine below is a scripted double
written by this file: a conformant one proves the stage can be satisfied, and
each deviant one proves the judge refuses a substitution, a selection applied
after the prompt, an unread-back configuration, a lost or repeated event or a
mislabelled receipt. None of this says what any real engine does.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("runtime_differential",
                                              HERE / "runtime-differential.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
adapter = runner.access_adapter
peers_spec = importlib.util.spec_from_file_location("runtime_access_peer",
                                                    HERE / "runtime_access_peer.py")
peers = importlib.util.module_from_spec(peers_spec)
peers_spec.loader.exec_module(peers)
HARNESS = HERE.parent / "conformance" / "tests" / "runtime" / "access-harness"
MODEL, OLD = "openai/gpt-5.5", "openai/gpt-5.4"
ZERO = {"acp_prompts": 0, "api_inference_requests": 0, "cli_invocations": 0}

# A scripted engine: argv `run input.nika --json …`, a PLAN of physical steps
# against whatever the stage put on PATH and in the environment, then the
# frames or the refusal the plan dictates. Standard library only.
ENGINE = r'''
import json, os, subprocess, sys
with open(os.path.splitext(os.path.abspath(__file__))[0] + ".plan.json", encoding="utf-8") as plan:
    PLAN = json.load(plan)


def emit(kind, fields):
    print(json.dumps({"kind": kind, "fields": [{"key": k, "value": v} for k, v in fields]}),
          flush=True)


class Acp:
    def __init__(self, command):
        self.proc = subprocess.Popen([command], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL)
        self.next = 0

    def call(self, method, params):
        self.next += 1
        line = json.dumps({"jsonrpc": "2.0", "id": self.next, "method": method, "params": params})
        try:
            self.proc.stdin.write((line + "\n").encode())
            self.proc.stdin.flush()
        except BrokenPipeError:
            return None
        while True:
            raw = self.proc.stdout.readline()
            if not raw:
                return None
            message = json.loads(raw)
            if message.get("id") == self.next:
                return message


def acp_step(step):
    acp = Acp(step.get("command", "codex-acp"))
    acp.call("initialize", {"protocolVersion": 1, "clientCapabilities": {}})
    if step.get("probe"):
        acp.proc.kill()
        acp.proc.wait(timeout=10)
        return
    sid = acp.call("session/new", {"cwd": os.getcwd(), "mcpServers": []})["result"]["sessionId"]
    for action, *value in step.get("actions", []):
        if action == "prompt":
            reply = acp.call("session/prompt", {"sessionId": sid,
                                                "prompt": [{"type": "text", "text": "Summarize."}]})
        elif action == "set_model":
            reply = acp.call("session/set_model", {"sessionId": sid, "modelId": value[0]})
        else:
            reply = acp.call("session/set_config_option",
                             {"sessionId": sid, "configId": action, "value": value[0]})
        if reply is None:
            break
    try:
        acp.proc.stdin.close()
    except BrokenPipeError:
        pass
    acp.proc.wait(timeout=10)


def api_step(step):
    import urllib.error, urllib.request  # lazily: ssl is slow to load
    body = step.get("body", {"model": "gpt-5.5", "stream": False,
                             "messages": [{"role": "user", "content": "Summarize."}]})
    url = os.environ["NIKA_OPENAI_BASE_URL"]
    if "path" in step:
        url = url.split("/v1/")[0] + step["path"]
    request = urllib.request.Request(url, method=step.get("method", "POST"),
                                     data=json.dumps(body).encode() if body else None,
                                     headers={"Content-Type": "application/json"})
    if os.environ.get("OPENAI_API_KEY"):
        request.add_header("Authorization", "Bearer " + os.environ["OPENAI_API_KEY"])
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            answer.read()
    except urllib.error.HTTPError:
        pass


def cli_step(step):
    subprocess.run([step.get("command", "codex"), *step["argv"]], input=b"Summarize.\n",
                   capture_output=True, timeout=10)


def main():
    argv = sys.argv[1:]
    if argv == ["--version"]:
        print("scripted engine (adapter test double)")
        return 0
    if "expect_argv" in PLAN and argv != PLAN["expect_argv"]:
        print(json.dumps({"error": {"code": "SCRIPTED-ARGV", "message": json.dumps(argv)}}))
        return 99
    # The interpreter itself may add its locale coercion; nothing else may appear.
    seen = sorted(set(os.environ) - {"LC_CTYPE", "__CF_USER_TEXT_ENCODING"})
    if "expect_env" in PLAN and seen != PLAN["expect_env"]:
        print(json.dumps({"error": {"code": "SCRIPTED-ENV", "message": json.dumps(seen)}}))
        return 99
    for step in PLAN.get("steps", []):
        {"acp": acp_step, "api": api_step, "cli": cli_step}[step["do"]](step)
    if "signal" in PLAN:
        os.kill(os.getpid(), PLAN["signal"])
    if "silent" in PLAN:
        return PLAN["silent"]
    if "refuse" in PLAN:
        # The reference engine settles a pre-run refusal as one run_settled frame.
        document = ({"kind": "run_settled", "cause": "refused", "status": "failed",
                     "error": PLAN["refuse"]} if PLAN.get("settled") else {"error": PLAN["refuse"]})
        print(json.dumps(document), flush=True)
        return PLAN.get("exit", 3)
    emit("workflow_started", [("workflow", "scripted")])
    for task, terminal in PLAN.get("tasks", {}).items():
        emit("task_started", [("task", task)])
        fields = [("task", task), ("outcome", json.dumps(terminal["outcome"]))]
        fields += [(key, value if isinstance(value, str) else json.dumps(value))
                   for key, value in terminal.get("fields", [])]
        for _ in range(terminal.get("repeat", 1)):
            emit(terminal.get("kind", "task_completed"), fields)
    state = PLAN.get("state", "success")
    emit("workflow_" + {"success": "completed", "failure": "failed"}[state], [("workflow", "scripted")])
    if PLAN.get("settle", True):
        print(json.dumps({"kind": "run_settled",
                          "status": {"success": "succeeded", "failure": "failed"}[state]}), flush=True)
    return {"success": 0, "failure": 1}[state]


sys.exit(main())
'''


def selection(protocol="acp", model=None, effort=None, responder=None, **extra):
    value = {"schema": adapter.SELECTION_SCHEMA, "protocol": protocol,
             "model": dict.fromkeys(adapter.VALUE_KEYS), "effort": dict.fromkeys(adapter.VALUE_KEYS),
             "responder": {"model": responder,
                           "evidence": "api_response" if responder else "unknown"}}
    value["model"].update(model or {})
    value["effort"].update(effort or {})
    value.update(extra)
    return value


def configured(model=MODEL, effort="high"):
    """The receipt of a selection applied through config options and read back."""
    facts = {"model": {"requested": MODEL, "option": "model", "transmitted": model,
                       "configured": model, "configured_source": "confirmed_selection"}}
    if effort:
        facts["effort"] = {"requested": effort, "option": "reasoning_effort",
                           "transmitted": effort, "configured": effort,
                           "configured_source": "confirmed_selection"}
    return selection(**facts)


def requirement(via="codex", protocol="acp", effort="high"):
    value = {"via": via, "protocol": protocol, "fallback": "none"}
    if effort:
        value["effort"] = effort
    return value


def success(fields, task="summarize"):
    return {task: {"outcome": {"class": "success", "payload": {"value": "ok", "attempts": 1}},
                   "fields": fields}}


def failure(code, task="summarize"):
    return {task: {"kind": "task_failed",
                   "outcome": {"class": "failure", "payload": {"error": {"code": code,
                                                                         "message": "refused"}}}}}


def receipt_fields(sel, req, via="codex"):
    return [("access_id", via), ("access_requirement", req), ("access_selection", sel)]


SIGN_IN = {"do": "cli", "argv": ["login", "status"]}
PROBE = {"do": "acp", "probe": True}


def session(*actions):
    return {"do": "acp", "actions": [list(action) for action in actions]}


def write_engine(directory: str, plan: dict) -> str:
    """One stable double per directory (its first exec is the costly one on some
    hosts); each judgment rewrites only the plan beside it."""
    path = pathlib.Path(directory) / "engine"
    if not path.exists():
        path.write_text(f"#!{sys.executable} -S\n" + ENGINE, encoding="utf-8")
        path.chmod(0o755)
    path.with_name("engine.plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return str(path)


def digest(directory: pathlib.Path) -> dict:
    return {path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file()}


class ScriptedEngineCase(unittest.TestCase):
    """One real fixture, one generated engine double, the differential's own judge."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="nika-access-engine-")
        cls.fixtures_before = digest(HARNESS)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def tearDown(self):
        # No judgment ever rewrites a fixture: the expectation bytes are the oracle.
        self.assertEqual(digest(HARNESS), self.fixtures_before)

    def engine(self, plan: dict) -> str:
        return write_engine(self.tmp.name, plan)

    def verdict(self, fixture, plan: dict) -> tuple[str, list[str]]:
        directory = fixture if isinstance(fixture, pathlib.Path) else next(HARNESS.glob(f"{fixture}-*"))
        try:
            diffs = runner.judge_run(self.engine(plan), directory)
        except runner.UnsupportedFixture as error:
            return "UNSUPPORTED", [str(error)]
        except RuntimeError as error:
            return "ENGINE-ERROR", [str(error)]
        return ("DIVERGE" if diffs else "AGREE"), list(diffs) + list(getattr(diffs, "notes", []))

    def assertVerdict(self, fixture, plan, wanted, *witnesses):
        got, lines = self.verdict(fixture, plan)
        self.assertEqual(got, wanted, "\n".join(lines))
        for witness in witnesses:
            self.assertTrue(any(witness in line for line in lines), f"{witness!r} not in {lines}")
        return lines


class AcpSelectionLaws(ScriptedEngineCase):
    """003 · 006: the selection is applied and read back before the one prompt."""

    def conformant(self, **overrides):
        plan = {"steps": [SIGN_IN, PROBE, session(("model", MODEL), ("reasoning_effort", "high"),
                                                  ("prompt",))],
                "tasks": success(receipt_fields(configured(), requirement()))}
        plan.update(overrides)
        return plan

    def test_a_conformant_double_agrees_and_probes_are_not_inference(self):
        lines = self.assertVerdict("003", self.conformant(), "AGREE")
        self.assertTrue(any("codex login status" in line and "direct invocations: none" in line
                            for line in lines), lines)
        self.assertVerdict("006", self.conformant(), "AGREE")

    def test_every_listed_discovery_form_stays_out_of_the_count(self):
        probes = [{"do": "cli", "argv": argv} for argv in (
            ["--version"], ["login", "status"], ["features", "list"],
            ["-c", "features.plugins=false", "mcp", "list", "--json"], ["mcp", "list"])]
        plan = self.conformant()
        plan["steps"] = probes + plan["steps"]
        self.assertVerdict("003", plan, "AGREE")

    def test_a_direct_or_near_miss_cli_invocation_is_counted(self):
        for argv in (["exec", "--json"], ["login", "status", "--json"], ["login status"], ["status"],
                     ["features", "list", "--all"], ["-c", "x=y"]):
            with self.subTest(argv=argv):
                plan = self.conformant()
                plan["steps"] = [{"do": "cli", "argv": argv}] + plan["steps"]
                self.assertVerdict("003", plan, "DIVERGE", "observed.cli_invocations: want 0 · got 1")

    def test_configuration_after_the_prompt_is_not_configuration_before_it(self):
        plan = self.conformant(steps=[SIGN_IN, session(("prompt",), ("model", MODEL),
                                                       ("reasoning_effort", "high"))])
        self.assertVerdict("003", plan, "DIVERGE", "observed.acp_config_before_first_prompt")

    def test_an_effort_judged_on_the_default_model_does_not_hold(self):
        # 006: the default model rejects `high`; selecting the model afterwards
        # leaves no applied effort when the prompt arrives.
        plan = self.conformant(steps=[session(("reasoning_effort", "high"), ("model", MODEL),
                                              ("prompt",))])
        self.assertVerdict("006", plan, "DIVERGE", "observed.acp_config_before_first_prompt")

    def test_a_second_prompt_is_counted(self):
        plan = self.conformant(steps=[session(("model", MODEL), ("reasoning_effort", "high"),
                                              ("prompt",), ("prompt",))])
        self.assertVerdict("003", plan, "DIVERGE", "observed.acp_prompts: want 1 · got 2")

    def test_receipt_lies_and_contradictions_never_agree(self):
        req = requirement()
        lies = {
            "an acknowledgement recorded as configured": selection(
                model={"requested": MODEL, "option": "model", "transmitted": MODEL,
                       "configured": MODEL, "configured_source": "accepted_request"},
                effort=configured()["effort"]),
            "a configured value without its source": selection(
                model={"requested": MODEL, "option": "model", "transmitted": MODEL,
                       "configured": MODEL}, effort=configured()["effort"]),
            "the request promoted to the responder": selection(
                model=configured()["model"], effort=configured()["effort"], responder=MODEL),
            "a translated effort": configured(effort="max"),
            "another protocol under a declared acp": dict(configured(), protocol="api"),
            "an unknown receipt key": dict(configured(), fallback_used="api"),
            "a responder with unknown evidence": dict(configured(),
                                                      responder={"model": "x", "evidence": "unknown"}),
            "a numeric fact": selection(model=dict(configured()["model"], transmitted=5),
                                        effort=configured()["effort"]),
        }
        for label, lie in lies.items():
            with self.subTest(lie=label):
                self.assertVerdict("003", self.conformant(tasks=success(receipt_fields(lie, req))),
                                   "DIVERGE")

    def test_the_requirement_restates_the_file_and_agrees_with_the_call(self):
        for label, req, via in [
            ("a dropped fallback", {"via": "codex", "protocol": "acp", "effort": "high"}, "codex"),
            ("another declared protocol", requirement(protocol="api"), "codex"),
            ("another effort", requirement(effort="max"), "codex"),
            ("a route substituted under the declared via", requirement(), "openai"),
            ("an unknown requirement key", dict(requirement(), alternatives="api"), "codex"),
        ]:
            with self.subTest(case=label):
                plan = self.conformant(tasks=success(receipt_fields(configured(), req, via)))
                self.assertVerdict("003", plan, "DIVERGE")

    def test_missing_malformed_or_repeated_records_never_agree(self):
        for label, fields in [
            ("no receipt at all", []),
            ("no requirement beside the selection", [("access_id", "codex"),
                                                     ("access_selection", configured())]),
            ("no access_id", [("access_requirement", requirement()),
                              ("access_selection", configured())]),
            ("a selection that is not JSON", receipt_fields("{", requirement())),
            ("a doubled selection field", receipt_fields(configured(), requirement())
             + [("access_selection", configured())]),
        ]:
            with self.subTest(case=label):
                self.assertVerdict("003", self.conformant(tasks=success(fields)), "DIVERGE")
        tasks = success(receipt_fields(configured(), requirement()))
        tasks["summarize"]["repeat"] = 2
        self.assertVerdict("003", self.conformant(tasks=tasks), "DIVERGE")
        self.assertVerdict("003", self.conformant(tasks={}), "DIVERGE", "no terminal event")
        self.assertVerdict("003", self.conformant(settle=False), "DIVERGE", "run_settled")

    def test_an_effort_the_file_never_asked_never_travels(self):
        # A copy of 003 without run.reasoning: an options session that offers
        # efforts, a file that asks none.
        source = next(HARNESS.glob("003-*"))
        fixture = pathlib.Path(self.tmp.name) / "no-effort"
        fixture.mkdir(exist_ok=True)
        (fixture / "input.nika").write_bytes((source / "input.nika").read_bytes().replace(
            b"  reasoning:\n    effort: high\n", b""))
        (fixture / "run.json").write_bytes((source / "run.json").read_bytes())
        (fixture / "expected-run.json").write_text(json.dumps({
            "admission": {"accepted": True}, "workflow_state": "success",
            "tasks": {"summarize": {"status": "success"}},
            "receipt": {"access_via": "codex", "protocol": "acp", "requested_model": MODEL,
                        "requested_effort": None, "transmitted_model": MODEL,
                        "configured_model": MODEL, "model_evidence": "configured",
                        "responding_model": None},
            "observed": {"acp_config_before_first_prompt": {"model": MODEL}, "acp_prompts": 1,
                         "api_inference_requests": 0, "cli_invocations": 0}}))
        receipt = selection(model=configured()["model"],
                            effort={"configured": "low", "configured_source": "session_config"})
        plan = {"steps": [session(("model", MODEL), ("prompt",))],
                "tasks": success(receipt_fields(receipt, requirement(effort=None)))}
        self.assertVerdict(fixture, plan, "AGREE")
        plan["steps"] = [session(("model", MODEL), ("reasoning_effort", "high"), ("prompt",))]
        self.assertVerdict(fixture, plan, "DIVERGE",
                           "receipt.transmitted_effort · the ACP peer received 'high'")

    def test_the_peer_record_binds_the_receipt_even_when_the_applied_state_matches(self):
        # The last value sent is the transmitted one, even when the peer refused it.
        plan = self.conformant(steps=[session(("model", MODEL), ("reasoning_effort", "high"),
                                              ("reasoning_effort", "xhigh"), ("prompt",))])
        self.assertVerdict("003", plan, "DIVERGE",
                           "receipt.transmitted_effort · the ACP peer received 'xhigh'")

    def test_another_receipt_schema_is_unsupported_unless_something_else_diverges(self):
        other = dict(configured(), schema="nika/access-selection@2")
        self.assertVerdict("003", self.conformant(tasks=success(receipt_fields(other, requirement()))),
                           "UNSUPPORTED", "nika/access-selection@2")
        plan = self.conformant(tasks=success(receipt_fields(other, requirement())))
        plan["steps"] = [{"do": "cli", "argv": ["exec"]}] + plan["steps"]
        self.assertVerdict("003", plan, "DIVERGE", "unsupported · receipt")


class LegacyAndRefusalLaws(ScriptedEngineCase):
    """004 · 008–011: an acknowledgement is not a configuration; a session refusal
    sends no prompt."""

    def test_an_acknowledged_model_is_accepted_request_evidence(self):
        legacy = selection(model={"requested": MODEL, "option": "session/set_model",
                                  "transmitted": MODEL, "configured_source": "accepted_request"})
        plan = {"steps": [SIGN_IN, session(("set_model", MODEL), ("prompt",))],
                "tasks": success(receipt_fields(legacy, requirement(effort=None)))}
        self.assertVerdict("004", plan, "AGREE")
        promoted = selection(model={"requested": MODEL, "option": "session/set_model",
                                    "transmitted": MODEL, "configured": MODEL,
                                    "configured_source": "confirmed_selection"})
        plan["tasks"] = success(receipt_fields(promoted, requirement(effort=None)))
        self.assertVerdict("004", plan, "DIVERGE", "receipt.configured_model", "receipt.model_evidence")
        # A legacy session exposes no configuration options at all.
        plan = {"steps": [session(("model", MODEL), ("prompt",))],
                "tasks": success(receipt_fields(legacy, requirement(effort=None)))}
        self.assertVerdict("004", plan, "DIVERGE", "observed.acp_config_before_first_prompt")

    def test_session_refusals_agree_only_with_zero_prompts(self):
        refused = {"state": "failure", "tasks": failure("NIKA-1805")}
        for fixture, actions in [("008", [("model", MODEL)]), ("009", [("model", MODEL)]),
                                 ("010", []), ("011", [("model", MODEL), ("reasoning_effort", "high")])]:
            with self.subTest(fixture=fixture):
                self.assertVerdict(fixture, dict(refused, steps=[SIGN_IN, session(*actions)]), "AGREE")
        for fixture, actions, why in [
            ("008", [("model", MODEL), ("reasoning_effort", "xhigh"), ("prompt",)],
             "an unoffered effort sent, then a prompt anyway"),
            ("008", [("model", MODEL), ("reasoning_effort", "high"), ("prompt",)],
             "the effort rounded to an offered one"),
            ("009", [("reasoning_effort", "xhigh"), ("model", MODEL), ("prompt",)],
             "the effort judged on the default model"),
            ("010", [("model", OLD), ("prompt",)], "the advertised neighbour served"),
            ("011", [("model", MODEL), ("reasoning_effort", "high"), ("prompt",)],
             "an unconfirmed read-back assumed applied"),
        ]:
            with self.subTest(case=why):
                self.assertVerdict(fixture, dict(refused, steps=[session(*actions)]), "DIVERGE",
                                   "observed.acp_prompts: want 0 · got 1")

    def test_a_premature_success_or_another_code_never_agrees(self):
        plan = {"steps": [session(("model", MODEL), ("reasoning_effort", "xhigh"))],
                "tasks": success(receipt_fields(configured(effort="xhigh"), requirement(effort="xhigh")))}
        self.assertVerdict("008", plan, "DIVERGE", "workflow_state: want failure")
        plan = {"state": "failure", "tasks": failure("NIKA-1804"), "steps": [session(("model", MODEL))]}
        self.assertVerdict("008", plan, "DIVERGE", "error_code: want NIKA-1805")


class AdmissionLaws(ScriptedEngineCase):
    """012 · 015–017: refused at admission with the exact code and witnesses, and
    nothing sent anywhere."""

    def refusal(self, code, message, steps=(SIGN_IN,), **plan):
        return dict({"steps": list(steps), "refuse": {"code": code, "message": message}}, **plan)

    def test_exact_admission_refusals_agree(self):
        self.assertVerdict("012", self.refusal("NIKA-1803", "codex is installed, but its ACP adapter is not"),
                           "AGREE")
        self.assertVerdict("016", self.refusal("NIKA-1802", "run.access.via: lighthouse is no route"),
                           "AGREE")
        self.assertVerdict("017", self.refusal("NIKA-1800", "run.access.protocol: api is not spoken"),
                           "AGREE")

    def test_a_settled_refusal_is_read_and_named(self):
        plan = self.refusal("NIKA-1803", "codex is installed, but its ACP adapter is not", settled=True)
        self.assertVerdict("012", plan, "AGREE",
                           "engine refused before any workflow or task event, at settlement "
                           "(cause refused): NIKA-1803")

    def test_the_launch_option_reaches_the_engine_verbatim(self):
        plan = self.refusal("NIKA-1801", "--access openai contradicts run.access.via: codex",
                            expect_argv=["run", "input.nika", "--json", "--access", "openai"])
        self.assertVerdict("015", plan, "AGREE")
        plan = self.refusal("NIKA-1801", "run.access.via", expect_argv=["run", "input.nika", "--json"])
        self.assertVerdict("015", plan, "DIVERGE", "SCRIPTED-ARGV")

    def test_a_refusal_after_a_substitution_never_agrees(self):
        for label, step, witness in [
            ("the direct CLI", {"do": "cli", "argv": ["exec", "--json"]}, "observed.cli_invocations"),
            ("the configured API", {"do": "api"}, "observed.api_inference_requests"),
        ]:
            with self.subTest(substitute=label):
                self.assertVerdict("012", self.refusal("NIKA-1803", "codex", [SIGN_IN, step]),
                                   "DIVERGE", witness)

    def test_a_wrong_code_a_missing_witness_or_an_execution_never_agrees(self):
        self.assertVerdict("012", self.refusal("NIKA-1800", "codex"), "DIVERGE", "admission.error_code")
        self.assertVerdict("016", self.refusal("NIKA-1802", "run.access.via is unknown"),
                           "DIVERGE", "missing witness 'lighthouse'")
        self.assertVerdict("017", self.refusal("NIKA-1800", "x", exit=0), "DIVERGE", "exited zero")
        served = {"steps": [SIGN_IN, session(("model", MODEL), ("reasoning_effort", "high"), ("prompt",))],
                  "tasks": success(receipt_fields(configured(), requirement(protocol="api")))}
        self.assertVerdict("017", served, "DIVERGE", "admission: execution events")

    def test_the_engine_sees_exactly_the_staged_environment(self):
        wanted = ["HOME", "NIKA_KEYCHAIN", "NIKA_OPENAI_BASE_URL", "OPENAI_API_KEY", "PATH", "TERM",
                  "TMPDIR"]
        plan = self.refusal("NIKA-1803", "codex", expect_env=wanted)
        lines = self.assertVerdict("012", plan, "AGREE")
        self.assertFalse(any("SCRIPTED-ENV" in line for line in lines), lines)


class ApiAndDeathLaws(ScriptedEngineCase):
    """005 · 007 · 013: the API route is exact, the responder verbatim, and a dying
    session is never re-routed."""

    def api(self, responder=None, transmitted=MODEL):
        sel = selection(protocol="api", responder=responder,
                        model={"requested": MODEL, "option": "model", "transmitted": transmitted})
        return {"steps": [{"do": "api"}],
                "tasks": success(receipt_fields(sel, requirement(via="openai", protocol="api",
                                                                 effort=None), via="openai"))}

    def test_the_api_selection_and_its_verbatim_responder(self):
        self.assertVerdict("005", self.api("gpt-5.5-2026-09-30"), "AGREE")
        self.assertVerdict("007", self.api(), "AGREE")
        self.assertVerdict("005", self.api(MODEL), "DIVERGE", "receipt.responding_model")
        self.assertVerdict("005", self.api(None), "DIVERGE", "receipt.responding_model")
        plan = self.api()
        plan["steps"] = [session(("model", MODEL), ("prompt",))]
        self.assertVerdict("007", plan, "DIVERGE", "observed.api_inference_requests: want 1 · got 0",
                           "observed.acp_prompts: want 0 · got 1")

    def test_the_physically_sent_model_binds_a_truthful_looking_receipt(self):
        # Review P1: the receipt is unchanged and correct; only the body differs.
        for fixture in ("005", "007"):
            for body_model in ("totally-different-model", "openai/gpt-5.5", "gpt-5.4"):
                with self.subTest(fixture=fixture, sent=body_model):
                    plan = self.api("gpt-5.5-2026-09-30" if fixture == "005" else None)
                    plan["steps"] = [{"do": "api", "body": {"model": body_model, "messages": [],
                                                            "stream": False}}]
                    self.assertVerdict(fixture, plan, "DIVERGE",
                                       f"the openai endpoint received model {body_model!r}")
        # The file declared no effort (`requested_effort: null`): none may travel.
        plan = self.api()
        plan["steps"] = [{"do": "api", "body": {"model": "gpt-5.5", "messages": [], "stream": False,
                                                "reasoning_effort": "high"}}]
        self.assertVerdict("007", plan, "DIVERGE",
                           "the openai endpoint received reasoning_effort 'high'")
        self.assertVerdict("007", self.api(), "AGREE")

    def test_a_model_listing_is_discovery_not_inference(self):
        plan = self.api()
        plan["steps"].insert(0, {"do": "api", "method": "GET", "body": {}, "path": "/v1/models"})
        self.assertVerdict("007", plan, "AGREE")

    def test_the_unpriced_stage_is_unsupported_only_when_nothing_was_sent(self):
        price = {"code": None, "message": "price unknown: this host cannot obtain a fresh one-time "
                                          "choice; use an interactive local `nika run`"}
        self.assertVerdict("005", {"refuse": price}, "UNSUPPORTED", "interactive one-time choice")
        https = {"code": None, "message": "unknown-cost admission requires an exact HTTPS route and model"}
        self.assertVerdict("007", {"refuse": https}, "UNSUPPORTED", "refuses that plain-HTTP route")
        self.assertVerdict("007", {"refuse": dict(https, code="NIKA-1800")}, "UNSUPPORTED")
        self.assertVerdict("005", {"refuse": https, "settled": True}, "UNSUPPORTED")
        # An inference sent before the refusal is an effect: never an unstaged premise.
        self.assertVerdict("007", {"refuse": price, "steps": [{"do": "api"}]}, "DIVERGE",
                           "admission: accepted run has no workflow_started",
                           "peers · api inference requests 1")
        other = {"code": None, "message": "price known: a different refusal"}
        self.assertVerdict("005", {"refuse": other}, "DIVERGE", "admission")

    def test_a_dead_session_fails_on_its_route_and_nowhere_else(self):
        died = {"state": "failure", "tasks": failure("NIKA-1804"),
                "steps": [SIGN_IN, session(("model", MODEL), ("reasoning_effort", "high"), ("prompt",))]}
        self.assertVerdict("013", died, "AGREE")
        for label, step, witness in [
            ("the configured API", {"do": "api"}, "observed.api_inference_requests: want 0 · got 1"),
            ("the direct CLI", {"do": "cli", "argv": ["exec", "--json"]}, "observed.cli_invocations"),
            ("a second session", session(("model", MODEL), ("reasoning_effort", "high"), ("prompt",)),
             "observed.acp_prompts: want 1 · got 2"),
        ]:
            with self.subTest(rerouted=label):
                self.assertVerdict("013", dict(died, steps=died["steps"] + [step]), "DIVERGE", witness)
        self.assertVerdict("013", dict(died, state="success", tasks=success(
            receipt_fields(configured(), requirement()))), "DIVERGE", "workflow_state")


class CrashLaws(ScriptedEngineCase):
    def test_no_evidence_is_loud_before_any_admission_comparison(self):
        # Review P2: an exit with nothing on stdout is no refusal and no run.
        for fixture in ("003", "012"):
            for code in (0, 1, 3):
                with self.subTest(fixture=fixture, exit=code):
                    self.assertVerdict(fixture, {"steps": [SIGN_IN], "silent": code}, "ENGINE-ERROR",
                                       f"no evidence on stdout (rc={code}")

    def test_a_killed_engine_is_loud_even_after_a_correct_prefix(self):
        plan = {"steps": [SIGN_IN, session(("model", MODEL), ("reasoning_effort", "high"), ("prompt",))],
                "signal": 9}
        self.assertVerdict("003", plan, "ENGINE-ERROR", "killed by signal 9")


class ContractLaws(unittest.TestCase):
    """Every declaration is validated whole before any process starts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nika-access-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.base = json.loads((HARNESS / "003-file-acp-selection-configured-before-prompt"
                                / "run.json").read_text())
        self.expected = json.loads((HARNESS / "003-file-acp-selection-configured-before-prompt"
                                    / "expected-run.json").read_text())
        self.workflow = (HARNESS / "003-file-acp-selection-configured-before-prompt"
                         / "input.nika").read_bytes()

    def classify(self, run=None, expected=None, workflow=None):
        directory = pathlib.Path(self.tmp.name) / f"case-{len(os.listdir(self.tmp.name))}"
        directory.mkdir()
        (directory / "input.nika").write_bytes(self.workflow if workflow is None else workflow)
        (directory / "run.json").write_text(json.dumps(self.base if run is None else run))
        (directory / "expected-run.json").write_text(
            json.dumps(self.expected if expected is None else expected))
        try:
            runner.load_run_contract(directory)
        except runner.InvalidFixture as error:
            return "FIXTURE-ERROR", str(error)
        except runner.UnsupportedFixture as error:
            return "UNSUPPORTED", str(error)
        return "CONTRACT", ""

    def acp(self, **change):
        run = json.loads(json.dumps(self.base))
        run["access_routes"]["codex"]["acp"].update(change)
        return run

    def test_the_corpus_classifies_as_declared(self):
        for directory in sorted(HARNESS.iterdir()):
            if not directory.is_dir():
                continue
            number = directory.name[:3]
            with self.subTest(fixture=directory.name):
                try:
                    runner.load_run_contract(directory)
                    got = "CONTRACT"
                except runner.UnsupportedFixture as error:
                    got = "UNSUPPORTED"
                    if number == "014":
                        self.assertIn("attestation", str(error))
                self.assertEqual(got, "UNSUPPORTED" if number in ("001", "002", "014") else "CONTRACT")

    def test_malformed_declarations_are_fixture_errors(self):
        run = json.loads(json.dumps(self.base))
        cases = {
            "an unknown route side": dict(run, access_routes={"codex": {"acpp": {}}}),
            "a non-kebab route": dict(run, access_routes={"Codex": {}}),
            "an empty world": dict(run, access_routes={}),
            "a string availability": self.acp(available="true"),
            "an unknown acp key": self.acp(effort_options=["high"]),
            "an unknown config kind": self.acp(config="both"),
            "a readback on a legacy session": self.acp(config="legacy", readback="confirmed",
                                                       models={MODEL: {"effort": []}}),
            "an effort on a legacy session": self.acp(config="legacy"),
            "an unknown readback": self.acp(readback="maybe"),
            "an unknown prompt behavior": self.acp(prompt="hangs"),
            "an empty model map": self.acp(models={}),
            "a repeated effort": self.acp(models={MODEL: {"effort": ["high", "high"]}}),
            "a padded effort": self.acp(models={MODEL: {"effort": [" high"]}}),
            "an unknown offer key": self.acp(models={MODEL: {"effort": [], "max": 1}}),
            "a session behind an unavailable adapter": {"access_routes": {"codex": {"acp": {
                "available": False, "config": "options"}}}},
            "a string cli flag": dict(run, access_routes={"codex": {"cli": {"available": 1}}}),
            "a responder without a credential": dict(run, access_routes={"openai": {"api": {
                "configured": False, "responder": "x"}}}),
            "an empty launch token": dict(run, access=""),
        }
        for label, invalid in cases.items():
            with self.subTest(case=label):
                self.assertEqual(self.classify(run=invalid)[0], "FIXTURE-ERROR")

    def test_malformed_expectations_are_fixture_errors(self):
        observed = self.expected["observed"]
        cases = {
            "no observed block": {k: v for k, v in self.expected.items() if k != "observed"},
            "a missing count": dict(self.expected, observed={k: v for k, v in observed.items()
                                                             if k != "cli_invocations"}),
            "a boolean count": dict(self.expected, observed=dict(observed, acp_prompts=True)),
            "a negative count": dict(self.expected, observed=dict(observed, cli_invocations=-1)),
            "an unknown observation": dict(self.expected, observed=dict(observed, probes=0)),
            "a configuration with no prompt": dict(self.expected, observed=dict(observed, acp_prompts=0)),
            "an unknown applied key": dict(self.expected, observed=dict(
                observed, acp_config_before_first_prompt={"model": MODEL, "mode": "x"})),
            "an unknown receipt key": dict(self.expected, receipt=dict(self.expected["receipt"],
                                                                       served_model=MODEL)),
            "an empty receipt": dict(self.expected, receipt={}),
            "an unknown evidence word": dict(self.expected, receipt={"model_evidence": "served"}),
            "an empty receipt fact": dict(self.expected, receipt={"configured_model": ""}),
            "a receipt on a refused admission": {"admission": {"accepted": False, "error_code": "NIKA-1803"},
                                                 "observed": ZERO, "receipt": {"protocol": "acp"}},
        }
        for label, invalid in cases.items():
            with self.subTest(case=label):
                self.assertEqual(self.classify(expected=invalid)[0], "FIXTURE-ERROR")
        self.assertEqual(self.classify(workflow=b"nika: x\nnika: y\n")[0], "FIXTURE-ERROR")
        self.assertEqual(self.classify(workflow=b"\xff")[0], "FIXTURE-ERROR")

    def test_the_declaration_is_read_as_the_literal_words_of_the_file(self):
        directory = pathlib.Path(self.tmp.name) / "literal"
        directory.mkdir()
        (directory / "input.nika").write_bytes(self.workflow.replace(b"effort: high", b"effort: on"))
        access = adapter.contract(directory, self.expected, self.base)
        self.assertEqual(access.declared, {"via": "codex", "protocol": "acp", "fallback": "none",
                                           "effort": "on"})

    def test_unstageable_premises_are_unsupported(self):
        infer = self.workflow.replace(b"    agent:", b"    infer:")
        self.assertEqual(self.classify(workflow=infer), ("UNSUPPORTED", adapter.ATTESTATION_GAP))
        cases = {
            "an env overlay": dict(self.base, env={"OPENAI_API_KEY": "x"}),
            "an unbound agent route": {"access_routes": {"lighthouse": {"cli": {"available": True}}}},
            "an unbound api route": {"access_routes": {"codex": {"api": {"configured": True}}}},
            "an unadvertised default": self.acp(default_model=OLD),
            "injected attestations": dict(self.base, harness_attestations={"codex": None}),
        }
        for label, run in cases.items():
            with self.subTest(case=label):
                self.assertEqual(self.classify(run=run)[0], "UNSUPPORTED")


class StageCase(unittest.TestCase):
    """The stage alone, driven directly: what it builds, and what its peers log."""

    def stage(self, routes, launch=None):
        access = adapter.Contract(routes, launch, dict(ZERO), None, (), {}, b"nika: x\n")
        stage = adapter.Stage(access)
        stage.__enter__()
        self.addCleanup(stage.__exit__, None, None, None)
        return stage

    def acp_world(self, **change):
        acp = {"available": True, "config": "options",
               "models": {OLD: {"effort": ["low", "medium", "xhigh"]}, MODEL: {"effort": ["low", "high"]}}}
        acp.update(change)
        return {"codex": {"acp": acp}}


class StageLaws(StageCase):
    def test_the_environment_is_explicit_and_holds_only_fake_keys(self):
        stage = self.stage({"codex": {"acp": {"available": True, "config": "options",
                                              "models": {MODEL: {"effort": []}}}},
                            "openai": {"api": {"configured": True}}})
        env = stage.env
        self.assertEqual(sorted(env), ["HOME", "NIKA_KEYCHAIN", "NIKA_OPENAI_BASE_URL",
                                       "OPENAI_API_KEY", "PATH", "TERM", "TMPDIR"])
        self.assertEqual(env["OPENAI_API_KEY"], adapter.FAKE_KEY)
        self.assertTrue(env["NIKA_OPENAI_BASE_URL"].startswith("http://127.0.0.1:"))
        for key in ("HOME", "TMPDIR"):
            self.assertTrue(env[key].startswith(str(stage.root)), key)
        self.assertEqual(env["PATH"].split(":"), [str(stage.dirs["bin"]), *adapter.SYSTEM_PATH])
        self.assertEqual(sorted(os.listdir(stage.dirs["bin"])), ["codex", "codex-acp"])
        self.assertEqual((stage.dirs["project"] / "input.nika").read_bytes(), b"nika: x\n")

    def test_absence_is_staged_as_absence(self):
        stage = self.stage({"codex": {"acp": {"available": False}, "cli": {"available": True}},
                            "openai": {"api": {"configured": False}}})
        self.assertEqual(os.listdir(stage.dirs["bin"]), ["codex"])
        self.assertNotIn("OPENAI_API_KEY", stage.env)
        self.assertIn("NIKA_OPENAI_BASE_URL", stage.env)
        empty = self.stage({"codex": {}})
        self.assertEqual(os.listdir(empty.dirs["bin"]), [])

    def test_a_host_registry_binary_on_the_system_path_refuses_the_stage(self):
        with tempfile.TemporaryDirectory() as system:
            pathlib.Path(system, "codex").write_text("")
            original = adapter.SYSTEM_PATH
            adapter.SYSTEM_PATH = (system,)
            try:
                with self.assertRaises(adapter.StageError):
                    with adapter.Stage(adapter.Contract({}, None, dict(ZERO), None, (), {}, b"")):
                        pass
            finally:
                adapter.SYSTEM_PATH = original

    def test_the_stage_removes_itself(self):
        stage = adapter.Stage(adapter.Contract({}, None, dict(ZERO), None, (), {}, b""))
        with stage:
            root = stage.root
            self.assertTrue(root.exists())
        self.assertFalse(root.exists())


class PeerLaws(StageCase):
    """The scripted ACP agent, spoken to over its pipes like any client would."""

    def start(self, stage, name="codex-acp"):
        proc = subprocess.Popen([str(stage.dirs["bin"] / name)], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=stage.env)
        self.addCleanup(lambda: (proc.kill(), proc.wait(), proc.stdout.close(), proc.stderr.close(),
                                 proc.stdin.close() if not proc.stdin.closed else None))
        return proc

    def call(self, proc, method, params, request_id=1):
        line = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        proc.stdin.write((json.dumps(line) + "\n").encode())
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    def open_session(self, proc):
        identity = self.call(proc, "initialize", {"protocolVersion": 1})["result"]
        answer = self.call(proc, "session/new", {"cwd": "/", "mcpServers": []}, 2)["result"]
        return identity, answer

    @staticmethod
    def current(options):
        return {option["category"]: option["currentValue"] for option in options}

    def test_identity_options_and_efforts_after_the_model_selection(self):
        stage = self.stage(self.acp_world(default_model=OLD))
        proc = self.start(stage)
        identity, answer = self.open_session(proc)
        self.assertEqual(identity["agentInfo"]["name"], "codex-acp")
        self.assertEqual(self.current(answer["configOptions"]), {"model": OLD, "thought_level": "low"})
        sid = answer["sessionId"]
        rejected = self.call(proc, "session/set_config_option",
                             {"sessionId": sid, "configId": "reasoning_effort", "value": "high"}, 3)
        self.assertEqual(rejected["error"]["code"], -32602)
        applied = self.call(proc, "session/set_config_option",
                            {"sessionId": sid, "configId": "model", "value": MODEL}, 4)["result"]
        efforts = [o for o in applied["configOptions"] if o["category"] == "thought_level"][0]
        self.assertEqual([v["value"] for v in efforts["options"]], ["low", "high"])
        self.call(proc, "session/set_config_option",
                  {"sessionId": sid, "configId": "reasoning_effort", "value": "high"}, 5)
        self.call(proc, "session/prompt", {"sessionId": sid, "prompt": []}, 6)
        proc.stdin.close()
        proc.wait(timeout=10)
        observation = stage.observe()
        self.assertEqual(observation.first_prompt()["applied"], {"model": MODEL, "effort": "high"})
        outcomes = [s["outcome"] for s in observation.acp[0]["selections"]]
        self.assertEqual(outcomes, ["rejected", "applied", "applied"])

    def test_a_model_change_drops_an_effort_it_does_not_offer(self):
        stage = self.stage(self.acp_world(default_model=OLD))
        proc = self.start(stage)
        sid = self.open_session(proc)[1]["sessionId"]
        self.call(proc, "session/set_config_option",
                  {"sessionId": sid, "configId": "reasoning_effort", "value": "xhigh"}, 3)
        answer = self.call(proc, "session/set_config_option",
                           {"sessionId": sid, "configId": "model", "value": MODEL}, 4)["result"]
        self.assertEqual(self.current(answer["configOptions"]), {"model": MODEL, "thought_level": "low"})
        self.call(proc, "session/prompt", {"sessionId": sid, "prompt": []}, 5)
        proc.stdin.close()
        proc.wait(timeout=10)
        self.assertEqual(stage.observe().first_prompt()["applied"], {"model": MODEL})

    def test_an_unconfirmed_read_back_returns_the_configuration_unchanged(self):
        stage = self.stage(self.acp_world(readback="unconfirmed"))
        proc = self.start(stage)
        before = self.open_session(proc)[1]
        sid = before["sessionId"]
        answer = self.call(proc, "session/set_config_option",
                           {"sessionId": sid, "configId": "model", "value": MODEL}, 3)["result"]
        self.assertEqual(answer["configOptions"], before["configOptions"])
        proc.stdin.close()
        proc.wait(timeout=10)
        self.assertEqual(stage.observe().acp[0]["selections"][0]["outcome"], "ignored")

    def test_a_legacy_session_only_acknowledges(self):
        stage = self.stage(self.acp_world(config="legacy", models={MODEL: {"effort": []}}))
        proc = self.start(stage)
        answer = self.open_session(proc)[1]
        self.assertNotIn("configOptions", answer)
        self.assertEqual(answer["models"]["availableModels"], [{"modelId": MODEL, "name": MODEL}])
        sid = answer["sessionId"]
        refused = self.call(proc, "session/set_config_option",
                            {"sessionId": sid, "configId": "model", "value": MODEL}, 3)
        self.assertEqual(refused["error"]["code"], -32601)
        self.assertEqual(self.call(proc, "session/set_model", {"sessionId": sid, "modelId": MODEL}, 4),
                         {"jsonrpc": "2.0", "id": 4, "result": {}})

    def test_a_dying_session_records_its_prompt_then_ends(self):
        stage = self.stage(self.acp_world(prompt="session_dies"))
        proc = self.start(stage)
        sid = self.open_session(proc)[1]["sessionId"]
        proc.stdin.write((json.dumps({"jsonrpc": "2.0", "id": 9, "method": "session/prompt",
                                      "params": {"sessionId": sid, "prompt": []}}) + "\n").encode())
        proc.stdin.flush()
        self.assertEqual(proc.stdout.readline(), b"")
        self.assertEqual(proc.wait(timeout=10), 70)
        observation = stage.observe()
        self.assertEqual(observation.counts()["acp_prompts"], 1)
        self.assertEqual(observation.acp[0]["exit"], "session_dies")

    def test_malformed_input_and_unknown_methods_are_answered_not_obeyed(self):
        stage = self.stage(self.acp_world())
        proc = self.start(stage)
        proc.stdin.write(b"{not json\n")
        proc.stdin.flush()
        self.assertEqual(json.loads(proc.stdout.readline())["error"]["code"], -32700)
        self.assertEqual(self.call(proc, "session/load", {}, 2)["error"]["code"], -32601)
        self.assertEqual(self.call(proc, "session/prompt", {"sessionId": "none"}, 3)["error"]["code"],
                         -32602)
        proc.stdin.close()
        proc.wait(timeout=10)
        self.assertEqual(stage.observe().counts()["acp_prompts"], 1)


class CliLaws(StageCase):
    def test_discovery_is_an_exact_argv(self):
        discovery = [{"argv": list(argv), "kind": kind}
                     for argv, kind in adapter.AGENT_ROUTES["codex"].discovery]
        for argv, kind in [(["login", "status"], "discovery:auth"), (["--version"], "discovery:version"),
                           (["-c", "a=b", "--config", "c=d", "features", "list"], "discovery:capability"),
                           (["login", "status", "--json"], "direct"), (["login status"], "direct"),
                           (["exec", "--json"], "direct"), (["-c"], "direct"), ([], "direct"),
                           (["features", "list", "-c", "x"], "direct")]:
            with self.subTest(argv=argv):
                self.assertEqual(peers.classify(argv, discovery), kind)

    def run_cli(self, stage, *argv):
        return subprocess.run([str(stage.dirs["bin"] / "codex"), *argv], input=b"Summarize.\n",
                              capture_output=True, env=stage.env, timeout=30)

    def test_the_direct_path_follows_the_premise_and_is_always_recorded(self):
        signed = self.stage({"codex": {"acp": {"available": True, "config": "options",
                                               "models": {MODEL: {"effort": []}}}}})
        self.assertEqual(self.run_cli(signed, "login", "status").returncode, 0)
        refused = self.run_cli(signed, "exec", "--json")
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(signed.observe().counts()["cli_invocations"], 1)
        direct = self.stage({"codex": {"cli": {"available": True}}})
        answered = self.run_cli(direct, "exec", "--json")
        self.assertEqual(answered.returncode, 0)
        self.assertIn(b"agent_message", answered.stdout)
        kinds = sorted(record["kind"] for record in direct.observe().cli)
        self.assertEqual(kinds, ["direct"])


class EndpointLaws(StageCase):
    def post(self, stage, body, method="POST", key=True, path=None):
        url = stage.env["NIKA_OPENAI_BASE_URL"]
        if path is not None:
            url = url.split("/v1/")[0] + path
        request = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                         method=method, headers={"Content-Type": "application/json"})
        if key:
            request.add_header("Authorization", f"Bearer {stage.env['OPENAI_API_KEY']}")
        try:
            with urllib.request.urlopen(request, timeout=10) as answer:
                return answer.status, answer.read()
        except urllib.error.HTTPError as error:
            with error:
                return error.code, error.read()

    def test_inference_is_counted_and_the_responder_is_verbatim_or_absent(self):
        named = self.stage({"openai": {"api": {"configured": True, "responder": "gpt-5.5-2026-09-30"}}})
        status, body = self.post(named, {"model": "gpt-5.5", "messages": [], "stream": False})
        self.assertEqual((status, json.loads(body)["model"]), (200, "gpt-5.5-2026-09-30"))
        status, body = self.post(named, {"model": "gpt-5.5", "messages": [], "stream": True})
        self.assertIn(b"gpt-5.5-2026-09-30", body)
        self.assertTrue(body.endswith(b"data: [DONE]\n\n"))
        status, _ = self.post(named, None, method="GET", path="/v1/models")
        self.assertEqual(status, 404)
        records = named.observe().api
        self.assertEqual([r["class"] for r in records], ["inference", "inference", "discovery"])
        self.assertEqual({r["authorization"] for r in records}, {"staged"})
        self.assertEqual(named.observe().counts()["api_inference_requests"], 2)
        anonymous = self.stage({"openai": {"api": {"configured": True}}})
        self.assertNotIn("model", json.loads(self.post(anonymous, {"messages": []})[1]))

    def test_an_unconfigured_route_answers_nothing_but_counts_the_attempt(self):
        stage = self.stage({"openai": {"api": {"configured": False}}})
        status, _ = self.post(stage, {"model": "gpt-5.5"}, key=False)
        self.assertEqual(status, 401)
        self.assertEqual(stage.observe().api[0]["authorization"], "absent")
        self.assertEqual(stage.observe().counts()["api_inference_requests"], 1)


class ReceiptDecoderLaws(unittest.TestCase):
    """The engine-shaped receipt reads exactly; everything else is named."""

    def test_the_engine_shapes_decode_and_project(self):
        acp = configured()
        got = adapter.project_receipt("codex", adapter.decode_selection(json.dumps(acp), runner.strict_json))
        self.assertEqual(got, {"access_via": "codex", "protocol": "acp", "requested_model": MODEL,
                               "requested_effort": "high", "transmitted_model": MODEL,
                               "transmitted_effort": "high", "configured_model": MODEL,
                               "configured_effort": "high", "model_evidence": "configured",
                               "responding_model": None})
        session_config = selection(model={"requested": None, "configured": "m",
                                          "configured_source": "session_config"})
        projected = adapter.project_receipt("codex", adapter.decode_selection(
            json.dumps(session_config), runner.strict_json))
        self.assertEqual(projected["model_evidence"], "session_config")
        moved = dict(acp, changed_mid_turn=["model=other"])
        adapter.decode_selection(json.dumps(moved), runner.strict_json)

    def test_ambiguous_or_foreign_receipts_never_read(self):
        text = json.dumps(configured())
        for raw in [text.replace('"schema"', '"schema": "x", "schema"'), "[]", "null", "{",
                    text.replace('"acp"', "NaN", 1), 5]:
            with self.subTest(raw=str(raw)[:40]):
                with self.assertRaises(adapter.InvalidEvidence):
                    adapter.decode_selection(raw, runner.strict_json)
        with self.assertRaises(adapter.Unsupported):
            adapter.decode_selection(json.dumps(dict(configured(), schema="nika/access-selection@9")),
                                     runner.strict_json)
        for raw in ['{"via":"codex","via":"x"}', '{}', '{"via":""}', '{"protocol":"cli"}',
                    '{"fallback":"api"}', '{"via":"codex","extra":"x"}', '{"effort":5}']:
            with self.subTest(requirement=raw):
                with self.assertRaises(adapter.InvalidEvidence):
                    adapter.decode_requirement(raw, runner.strict_json)


class SweepLaws(unittest.TestCase):
    """The sweep prints the adapter's notes, keeps private evidence on request and
    names the binary it judged."""

    def test_the_evidence_directory_holds_the_stage_and_an_index(self):
        engines = tempfile.TemporaryDirectory(prefix="nika-access-sweep-")
        self.addCleanup(engines.cleanup)
        engine = write_engine(engines.name, {"steps": [SIGN_IN], "refuse": {"code": "NIKA-1803",
                                                                           "message": "codex"}})
        with tempfile.TemporaryDirectory(prefix="nika-access-evidence-") as evidence:
            env = {runner.access_adapter.ENV_FILE: evidence, "NIKA_BIN": engine}
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(runner, "ACCESS_EVIDENCE", None), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                code = runner.main(["runner", "runtime/access-harness/012-file-acp-unavailable-not-substituted"])
            self.assertEqual(code, 0, output.getvalue())
            self.assertIn("note · peers · cli discovery/sign-in probes: codex login status",
                          output.getvalue())
            self.assertIn("access adapter · engine", output.getvalue())
            [run] = os.listdir(evidence)
            root = pathlib.Path(evidence, run)
            index = json.loads((root / "index.json").read_text())
            self.assertEqual(index["fixtures"][0]["verdict"], "AGREE")
            self.assertEqual(len(index["engines"][0]["sha256"]), 64)
            kept = root / "runtime" / "access-harness" / "012-file-acp-unavailable-not-substituted"
            record = json.loads((kept / "record.json").read_text())
            self.assertEqual(record["observation"]["counts"], ZERO)
            self.assertTrue(any(kept.joinpath("stage", "logs").iterdir()))
            self.assertTrue((kept / "stage" / "peers.py").is_file())


if __name__ == "__main__":
    unittest.main()
