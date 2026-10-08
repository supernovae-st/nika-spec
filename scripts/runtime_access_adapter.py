#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""The access-selection command adapter, invoked by runtime-differential.py for
`runtime/access-harness` fixtures that inject a route world
(`run.json.access_routes`), assert the adapter's own observations
(`expected-run.json.observed`) and may assert the run's receipt (`receipt`).

It serves the REFERENCE engine only: the route registry it stages against is
the closed binding table below. Another implementation needs its own admitted
adapter, never a fallback. One fixture is one isolated stage and one real
`nika run --json` of the unchanged workflow:

- stage: scripted ACP agents, each route's product CLI and a loopback inference
  endpoint, built from `access_routes` alone, in a private HOME, TMPDIR, project
  and PATH with an explicit environment and a fake key. No host binary, account
  store or provider is read or reached;
- observe: every peer's own log. ACP requests, selections, the configuration
  returned and the configuration held when a prompt arrived; product-CLI
  processes split into discovery or sign-in probes and direct invocations;
  endpoint requests split into model listings and inference requests;
- decode: the engine's task terminal frames, `access_id`, `access_requirement`
  and `access_selection` (`nika/access-selection@1`), strictly;
- judge: `observed` and `receipt` exactly as asserted, beside the run door's
  own admission and execution judgment.

No expected value is derived from the premises: the fixture's own bytes are the
only expectation. A premise this stage cannot realize is UNSUPPORTED with its
reason; a well-staged run that differs is a divergence.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field

PEERS = pathlib.Path(__file__).with_name("runtime_access_peer.py")
SELECTION_SCHEMA = "nika/access-selection@1"
FAKE_KEY = "sk-nika-conformance-scripted-never-valid"
ROUTE_ID = re.compile(r"[a-z][a-z0-9-]*")
ANSWER = "scripted answer"
COUNTS = ("acp_prompts", "api_inference_requests", "cli_invocations")
RECEIPT_KEYS = ("access_via", "protocol", "requested_model", "requested_effort",
                "transmitted_model", "transmitted_effort", "configured_model",
                "configured_effort", "model_evidence", "responding_model")
TERMINAL_KINDS = ("task_completed", "task_failed", "task_skipped", "task_cancelled")
VERBS = ("infer", "exec", "invoke", "agent")
ENV_FILE = "NIKA_ACCESS_EVIDENCE_DIR"


@dataclass(frozen=True)
class AgentRoute:
    """An agent-application route as the reference engine's registry reaches it."""
    acp_command: str      # the ACP speaker the registry spawns
    identity: dict        # an initialize self-report the registry admits (name, version pin)
    product_command: str  # the product CLI: PATH presence and the sign-in probe
    effort_option: str    # the session's reasoning option id (category thought_level)
    discovery: tuple      # exact product-CLI argv that discover, never infer


@dataclass(frozen=True)
class ApiRoute:
    """An inference API route as the reference engine composes it from its environment."""
    key_env: str          # the conventional key variable
    base_url_env: str     # the complete-endpoint override
    path: str             # the inference endpoint the engine posts to
    wire_prefix: str      # the route's own provider prefix, absent from its request body

    def wire_model(self, model: str) -> str | None:
        """A model id as this route's request body names it. The route is the
        provider, so its OpenAI-compatible body carries the provider's own name
        (`openai/gpt-5.5` travels as `gpt-5.5`); an id of another provider has no
        wire form here. Deliberate and route-bound: never applied to an ACP
        session, whose advertised values are compared verbatim."""
        return model[len(self.wire_prefix):] if model.startswith(self.wire_prefix) else None


# The reference engine's registry facts, never fixture premises: a route a
# fixture stages outside this table is UNSUPPORTED. The ACP identity is one its
# registry admits for the route (`agentInfo.name` and a version inside the pin);
# it is never the identity of an audited completion profile.
AGENT_ROUTES = {
    "codex": AgentRoute(
        acp_command="codex-acp",
        identity={"name": "codex-acp", "version": "0.16.2",
                  "title": "Scripted ACP peer (nika-spec access conformance)"},
        product_command="codex",
        effort_option="reasoning_effort",
        discovery=((("--version",), "discovery:version"),
                   (("login", "status"), "discovery:auth"),
                   (("features", "list"), "discovery:capability"),
                   (("mcp", "list"), "discovery:capability"),
                   (("mcp", "list", "--json"), "discovery:capability")),
    ),
}
API_ROUTES = {
    "openai": ApiRoute("OPENAI_API_KEY", "NIKA_OPENAI_BASE_URL", "/v1/chat/completions", "openai/"),
}
# Every product CLI and ACP speaker the reference engine's registry looks for on
# PATH: none may be reachable through the stage's system directories.
REGISTRY_BINARIES = ("gemini", "qwen", "kimi", "opencode", "codex", "codex-acp", "copilot",
                     "grok", "claude", "claude-agent-acp")
SYSTEM_PATH = ("/usr/bin", "/bin")
# The reference engine's machine refusals of a Run whose API route has no known
# USD price: its unknown-cost admission refuses a route it cannot review (the
# stage's plain-HTTP loopback endpoint is one), and a reviewable one still
# needs a fresh interactive choice the host may not offer. Recognized only to
# classify a run that did nothing: never read as agreement.
UNKNOWN_PRICE_REFUSALS = ("price unknown:", "unknown-cost admission")
ATTESTATION_GAP = (
    "an infer: task on an agent-application route rests on the subscription-harness "
    "attestation premise (02 §Subscription harness access); run.json states that premise "
    "only as injected harness_attestations (absent here, so none is attested), and the "
    "reference engine admits no injected attestation: its build attests its own routes "
    "(the ACP one-shot completion profiles), so no supported seam stages this premise")


class FixtureError(ValueError):
    """The access declaration or its expectation cannot be evaluated."""


class Unsupported(ValueError):
    """A valid premise or engine reply this adapter has no admitted seam or reading for."""


class InvalidEvidence(ValueError):
    """An engine record that is not one well-typed receipt."""


class StageError(RuntimeError):
    """The stage itself failed (isolation, endpoint, peer log): no measurement."""


# ---------------------------------------------------------------- the contract

@dataclass
class Contract:
    """One access fixture, validated whole before any process starts."""
    routes: dict
    launch: str | None
    observed: dict
    receipt: dict | None
    tasks: tuple
    declared: dict
    workflow: bytes


def _closed(value, allowed, label, required=()):
    if not isinstance(value, dict):
        raise FixtureError(f"{label} must be an object")
    unknown = set(value) - set(allowed)
    if unknown:
        raise FixtureError(f"unknown {label} keys: {', '.join(sorted(unknown))}")
    missing = [key for key in required if key not in value]
    if missing:
        raise FixtureError(f"{label} requires {', '.join(missing)}")


def _word(value, label):
    if not isinstance(value, str) or not value or value != value.strip():
        raise FixtureError(f"{label} must be a nonempty string without surrounding whitespace")
    return value


def _flag(value, label):
    if type(value) is not bool:
        raise FixtureError(f"{label} must be a boolean")
    return value


def _acp(acp, via):
    label = f"{via}.acp"
    _closed(acp, ("available", "config", "readback", "default_model", "models", "prompt"), label,
            ("available",))
    if not _flag(acp["available"], f"{label}.available"):
        if set(acp) != {"available"}:
            raise FixtureError(f"{label}: an unavailable adapter declares no session")
        return
    _closed(acp, acp.keys(), label, ("config", "models"))
    if acp["config"] not in ("options", "legacy"):
        raise FixtureError(f"{label}.config must be options or legacy")
    if "readback" in acp and (acp["config"] != "options"
                              or acp["readback"] not in ("confirmed", "unconfirmed")):
        raise FixtureError(f"{label}.readback is confirmed or unconfirmed, options only")
    if acp.get("prompt", "completes") not in ("completes", "session_dies"):
        raise FixtureError(f"{label}.prompt must be completes or session_dies")
    models = acp["models"]
    if not isinstance(models, dict) or not models:
        raise FixtureError(f"{label}.models must be a nonempty object")
    for model, offer in models.items():
        _word(model, f"{label}.models key")
        _closed(offer, ("effort",), f"{label}.models.{model}", ("effort",))
        efforts = offer["effort"]
        if not isinstance(efforts, list):
            raise FixtureError(f"{label}.models.{model}.effort must be an array")
        for effort in efforts:
            _word(effort, f"{label}.models.{model}.effort value")
        if len(set(efforts)) != len(efforts):
            raise FixtureError(f"{label}.models.{model}.effort repeats a value")
        if acp["config"] == "legacy" and efforts:
            raise FixtureError(f"{label}: a legacy session offers no effort option")
    if "default_model" in acp:
        _word(acp["default_model"], f"{label}.default_model")


def _routes(routes):
    if not isinstance(routes, dict) or not routes:
        raise FixtureError("access_routes must be a nonempty object")
    for via, route in routes.items():
        if not ROUTE_ID.fullmatch(via):
            raise FixtureError(f"route id {via!r} is not kebab-case")
        _closed(route, ("acp", "cli", "api"), f"route {via}")
        if "acp" in route:
            _acp(route["acp"], via)
        if "cli" in route:
            _closed(route["cli"], ("available",), f"{via}.cli", ("available",))
            _flag(route["cli"]["available"], f"{via}.cli.available")
        if "api" in route:
            api = route["api"]
            _closed(api, ("configured", "responder"), f"{via}.api", ("configured",))
            if "responder" in api:
                _word(api["responder"], f"{via}.api.responder")
                if not _flag(api["configured"], f"{via}.api.configured"):
                    raise FixtureError(f"{via}.api: an unconfigured endpoint names no responder")
            _flag(api["configured"], f"{via}.api.configured")
    return routes


def _observed(value):
    if value is None:
        raise FixtureError("an access fixture asserts observed: the adapter's own exact counts")
    _closed(value, COUNTS + ("acp_config_before_first_prompt",), "observed", COUNTS)
    for key in COUNTS:
        if type(value[key]) is not int or value[key] < 0:
            raise FixtureError(f"observed.{key} must be an exact nonnegative integer")
    if "acp_config_before_first_prompt" in value:
        applied = value["acp_config_before_first_prompt"]
        _closed(applied, ("model", "effort"), "observed.acp_config_before_first_prompt")
        for key, word in applied.items():
            _word(word, f"observed.acp_config_before_first_prompt.{key}")
        if value["acp_prompts"] == 0:
            raise FixtureError("no prompt arrives, so no configuration precedes one")
    return value


def _receipt(value):
    _closed(value, RECEIPT_KEYS, "receipt")
    if not value:
        raise FixtureError("receipt asserts nothing")
    for key, word in value.items():
        if key == "access_via":
            _word(word, "receipt.access_via")
        elif key == "protocol":
            if word not in ("api", "acp", None):
                raise FixtureError("receipt.protocol must be api, acp or null")
        elif key == "model_evidence":
            if word not in ("configured", "accepted_request", None):
                raise FixtureError("receipt.model_evidence must be configured, accepted_request or null")
        elif word is not None:
            _word(word, f"receipt.{key}")
    return value


def _unique_keys(node, seen_nodes=None) -> None:
    """No mapping of the composed document repeats a scalar key (the engine refuses one)."""
    import yaml
    seen_nodes = set() if seen_nodes is None else seen_nodes
    if id(node) in seen_nodes:
        return
    seen_nodes.add(id(node))
    if isinstance(node, yaml.MappingNode):
        keys = set()
        for key, value in node.value:
            if isinstance(key, yaml.ScalarNode):
                if key.value in keys:
                    raise FixtureError(f"input.nika repeats the key {key.value!r}")
                keys.add(key.value)
            _unique_keys(key, seen_nodes)
            _unique_keys(value, seen_nodes)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _unique_keys(item, seen_nodes)


def _workflow(raw: bytes):
    """The workflow's composed YAML nodes: one mapping, no repeated key. Nodes,
    not resolved values, so a declaration is read as the literal words it wrote."""
    import yaml
    try:
        root = yaml.compose(raw.decode("utf-8"), Loader=yaml.SafeLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise FixtureError(f"input.nika is not readable YAML: {error}") from error
    if not isinstance(root, yaml.MappingNode):
        raise FixtureError("input.nika must be a YAML mapping")
    _unique_keys(root)
    return root


def _entries(node) -> dict:
    """A mapping node's children by their literal scalar key; anything else has none."""
    import yaml
    if not isinstance(node, yaml.MappingNode):
        return {}
    return {key.value: value for key, value in node.value if isinstance(key, yaml.ScalarNode)}


def _declaration(root) -> tuple[dict, set]:
    """The file's literal run.access / run.reasoning words, and the verbs its tasks use."""
    import yaml
    run = _entries(_entries(root).get("run"))
    declared = {}
    for section, keys in (("access", ("via", "protocol", "fallback")), ("reasoning", ("effort",))):
        entries = _entries(run.get(section))
        for key in keys:
            if key in entries:
                node = entries[key]
                declared[key] = node.value if isinstance(node, yaml.ScalarNode) else None
    verbs = set()
    for task in _entries(_entries(root).get("tasks")).values():
        verbs |= set(_entries(task)) & set(VERBS)
    return declared, verbs


def contract(directory: pathlib.Path, expected: dict, run: dict) -> Contract:
    """Validate the whole access contract before any process starts.

    Malformed declarations are FixtureError; a well-formed premise the stage
    cannot realize on the reference engine is Unsupported (checked after)."""
    routes = _routes(run.get("access_routes"))
    launch = run.get("access")
    if launch is not None:
        _word(launch, "access (the launch access option)")
    observed = _observed(expected.get("observed"))
    receipt = _receipt(expected["receipt"]) if "receipt" in expected else None
    admission = expected.get("admission") or {}
    if receipt is not None and admission.get("accepted") is False:
        raise FixtureError("a refused admission has no task terminal to carry a receipt")
    tasks = tuple(expected.get("tasks") or ())
    if receipt is not None and not tasks:
        raise FixtureError("a receipt is read on the terminal frames of the asserted tasks")
    try:
        workflow = (directory / "input.nika").read_bytes()
    except OSError as error:
        raise FixtureError(f"cannot read input.nika: {error}") from error
    declared, verbs = _declaration(_workflow(workflow))
    if "env" in run:
        raise Unsupported("an env overlay beside an injected route world has no defined "
                          "precedence: the stage's environment is the route world alone")
    for via, route in routes.items():
        if ({"acp", "cli"} & set(route)) and via not in AGENT_ROUTES:
            raise Unsupported(f"route {via}: the reference engine's registry binds no agent "
                              "application this stage can script")
        if "api" in route and via not in API_ROUTES:
            raise Unsupported(f"route {via}: the reference engine has no API binding this stage "
                              "can serve")
        acp = route.get("acp") or {}
        if acp.get("available") and acp.get("default_model", next(iter(acp["models"]))) not in \
                acp["models"]:
            raise Unsupported(f"route {via}: an unadvertised default_model cannot be the current "
                              "value of an ACP select option")
    if "infer" in verbs and (declared.get("via") in AGENT_ROUTES or declared.get("protocol") == "acp"):
        raise Unsupported(ATTESTATION_GAP)
    return Contract(routes, launch, observed, receipt, tasks, declared, workflow)


# ------------------------------------------------------------------- the stage

class Stage:
    """One fixture's private world (bin · home · tmp · project · logs); removed on exit."""

    def __init__(self, access: Contract):
        self.access = access
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="nika-access-")).resolve()
        self.dirs = {name: self.root / name for name in
                     ("bin", "home", "tmp", "project", "logs", "config")}
        self.servers: list[http.server.ThreadingHTTPServer] = []
        self.api_records: list[dict] = []
        self.lock = threading.Lock()
        self.env: dict[str, str] = {}
        self.staged: list[str] = []

    def __enter__(self):
        try:
            self.build()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        self.servers = []
        shutil.rmtree(self.root, ignore_errors=True)

    def build(self):
        for directory in SYSTEM_PATH:
            for name in REGISTRY_BINARIES:
                if os.path.lexists(os.path.join(directory, name)):
                    raise StageError(f"{directory}/{name} would be visible on the stage PATH")
        for directory in self.dirs.values():
            directory.mkdir()
        shutil.copy2(PEERS, self.root / "peers.py")
        workflow = self.dirs["project"] / "input.nika"
        workflow.write_bytes(self.access.workflow)
        if workflow.read_bytes() != self.access.workflow:
            raise StageError("the staged workflow is not byte-exact")
        self.env = {"PATH": ":".join((str(self.dirs["bin"]), *SYSTEM_PATH)),
                    "HOME": str(self.dirs["home"]), "TMPDIR": str(self.dirs["tmp"]),
                    "TERM": "dumb", "NIKA_KEYCHAIN": "off"}
        for via, route in self.access.routes.items():
            acp = route.get("acp") or {}
            acp_ready = bool(acp.get("available"))
            cli_ready = bool((route.get("cli") or {}).get("available"))
            agent = AGENT_ROUTES.get(via)
            if agent is not None and (acp_ready or cli_ready):
                # The product CLI is present and signed in whenever the route has a
                # path: the reference engine's ACP route asks it for its sign-in.
                # Only `cli.available` opens its direct invocation.
                self.peer(agent.product_command, "cli", {
                    "route": via, "signed_in": True, "direct": cli_ready,
                    "version_line": f"{agent.product_command} 0.0.0 (scripted conformance double)",
                    "discovery": [{"argv": list(argv), "kind": kind}
                                  for argv, kind in agent.discovery]})
            if agent is not None and acp_ready:
                self.peer(agent.acp_command, "acp", {
                    "route": via, "acp": acp, "identity": agent.identity,
                    "effort_option": agent.effort_option})
            if "api" in route:
                binding = API_ROUTES[via]
                port = self.serve(via, route["api"])
                # The override always points at the loopback endpoint (any request
                # is observed); only a configured route also holds a (fake) key.
                self.env[binding.base_url_env] = f"http://127.0.0.1:{port}{binding.path}"
                if route["api"]["configured"]:
                    self.env[binding.key_env] = FAKE_KEY

    def peer(self, name: str, kind: str, config: dict):
        path = self.dirs["config"] / f"{kind}-{name}.json"
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        command = [sys.executable, "-I", "-B", "-S", str(self.root / "peers.py"), kind, str(path),
                   str(self.dirs["logs"])]
        wrapper = self.dirs["bin"] / name
        wrapper.write_text("#!/bin/sh\nexec " + " ".join(map(shlex.quote, command)) + ' "$@"\n',
                           encoding="utf-8")
        wrapper.chmod(0o755)
        self.staged.append(f"{name} ({kind})")

    def serve(self, route: str, api: dict) -> int:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), endpoint(route, api, self.record))
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05},
                         daemon=True).start()
        self.servers.append(server)
        self.staged.append(f"{route} endpoint (127.0.0.1:{server.server_address[1]})")
        return server.server_address[1]

    def record(self, entry: dict):
        with self.lock:
            self.api_records.append(entry)
            with open(self.dirs["logs"] / f"api-{entry['route']}.jsonl", "a", encoding="utf-8") as log:
                log.write(json.dumps(entry, sort_keys=True) + "\n")

    def run(self, engine: str, args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
        argv = [engine, "run", "input.nika", "--json", *args]
        return subprocess.run(argv, cwd=self.dirs["project"], env=self.env,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)

    def observe(self) -> Observation:
        return observe(self.dirs["logs"], list(self.api_records))

    def keep(self, target: pathlib.Path):
        """Copy the whole stage (wrappers, peer code, configs, logs, engine traces)."""
        shutil.copytree(self.root, target, symlinks=True, dirs_exist_ok=True)


def endpoint(route: str, api: dict, record):
    """A loopback inference endpoint: every request observed, answers scripted."""
    responder, configured = api.get("responder"), api["configured"]

    class Endpoint(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def body(self) -> bytes:
            if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
                data = b""
                while True:
                    size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                    if size == 0:
                        self.rfile.readline()
                        return data
                    data += self.rfile.read(size)
                    self.rfile.readline()
            length = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(length) if length > 0 else b""

        def answer(self, status: int, content_type: str, payload: bytes):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)

        def handle_any(self):
            try:
                raw = self.body()
            except (ValueError, OSError):
                raw = b""  # a malformed body is still a request: recorded, never lost
            path = self.path.split("?", 1)[0]
            listing = self.command in ("GET", "HEAD") and (path == "/v1/models"
                                                           or path.startswith("/v1/models/"))
            try:
                payload = json.loads(raw) if raw else None
            except ValueError:
                payload = None
            body = payload if isinstance(payload, dict) else {}
            auth = self.headers.get("Authorization")
            record({"t": time.time_ns(), "route": route, "method": self.command, "path": path,
                    "class": "discovery" if listing else "inference",
                    "authorization": ("absent" if auth is None
                                      else "staged" if auth == f"Bearer {FAKE_KEY}" else "other"),
                    "model": body.get("model"), "stream": body.get("stream"),
                    "reasoning_effort": body.get("reasoning_effort"), "body_bytes": len(raw),
                    "body": payload if payload is not None else raw[:2048].decode("utf-8", "replace")})
            if listing:
                self.answer(404, "application/json",
                            json.dumps({"error": {"message": "model listing is not modeled"}}).encode())
            elif not configured:
                self.answer(401, "application/json",
                            json.dumps({"error": {"message": "no credential is configured"}}).encode())
            elif body.get("stream") is True:
                head = {"id": "chatcmpl-scripted", "object": "chat.completion.chunk", "created": 0}
                if responder is not None:
                    head["model"] = responder
                chunks = [dict(head, choices=[{"index": 0, "finish_reason": None,
                                               "delta": {"role": "assistant", "content": ANSWER}}]),
                          dict(head, choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                               usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})]
                text = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
                self.answer(200, "text/event-stream", text.encode())
            else:
                answer = {"id": "chatcmpl-scripted", "object": "chat.completion", "created": 0,
                          "choices": [{"index": 0, "finish_reason": "stop",
                                       "message": {"role": "assistant", "content": ANSWER}}],
                          "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
                if responder is not None:
                    answer["model"] = responder  # verbatim; absent names none
                self.answer(200, "application/json", json.dumps(answer).encode())

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = handle_any

    return Endpoint


# ------------------------------------------------------------- the observation

@dataclass
class Observation:
    """What the peers themselves recorded, in their own terms."""
    prompts: list = field(default_factory=list)
    acp: list = field(default_factory=list)
    sessions: list = field(default_factory=list)
    cli: list = field(default_factory=list)
    api: list = field(default_factory=list)

    def counts(self) -> dict:
        return {"acp_prompts": len(self.prompts),
                "api_inference_requests": sum(r["class"] == "inference" for r in self.api),
                "cli_invocations": sum(r["kind"] == "direct" for r in self.cli)}

    def first_prompt(self):
        return min(self.prompts, key=lambda prompt: (prompt["t"], prompt["seq"]), default=None)

    def summary(self) -> dict:
        return {"counts": self.counts(), "first_prompt": self.first_prompt(),
                "acp_processes": self.acp, "cli_invocations": self.cli, "api_requests": self.api}


def _records(path: pathlib.Path) -> list[dict]:
    """A peer's own log; a final line cut by a kill is dropped, any other damage is fatal."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    complete, tail = lines[:-1], lines[-1]
    records = []
    for number, line in enumerate(complete, 1):
        try:
            records.append(json.loads(line))
        except ValueError as error:
            raise StageError(f"{path.name}:{number}: unreadable peer log ({error})") from error
    if tail.strip():
        records.append({"event": "truncated"})
    return records


def observe(logs: pathlib.Path, api: list[dict]) -> Observation:
    observation = Observation(api=api)
    for path in sorted(logs.iterdir()):
        if path.name.startswith("api-"):
            continue
        records = _records(path)
        if not records or records[0].get("event") != "start":
            raise StageError(f"{path.name}: a peer log without its start record")
        start = records[0]
        route = start["route"]
        if start["kind"] == "cli":
            invocation = next((r for r in records if r.get("event") == "invocation"), None)
            if invocation is None:
                raise StageError(f"{path.name}: a CLI process that recorded no invocation")
            observation.cli.append({"route": route, "argv": invocation["argv"],
                                    "kind": invocation["kind"], "t": invocation["t"]})
            continue
        methods = [r["message"].get("method") for r in records
                   if r.get("event") == "received" and isinstance(r.get("message"), dict)
                   and "method" in r["message"]]
        prompts = [r for r in records if r.get("event") == "prompt"]
        observation.prompts += [dict(prompt, route=route) for prompt in prompts]
        for opened in (r for r in records if r.get("event") == "session"):
            mine = [r for r in records if r.get("session") == opened["session"]]
            observation.sessions.append({
                "route": route, "pid": start["pid"], "session": opened["session"], "t": opened["t"],
                "selections": [{key: r.get(key) for key in ("method", "config_id", "value", "outcome")}
                               for r in mine if r.get("event") == "selection"],
                "readbacks": [r["configOptions"] for r in mine if r.get("event") == "readback"]})
        observation.acp.append({
            "route": route, "pid": start["pid"], "methods": methods,
            "selections": [{key: r.get(key) for key in ("method", "config_id", "value", "outcome")}
                           for r in records if r.get("event") == "selection"],
            "readbacks": [r["configOptions"] for r in records if r.get("event") == "readback"],
            "prompts": len(prompts),
            "exit": next((r["reason"] for r in records if r.get("event") == "exit"), "killed"),
        })
    return observation


def diff_observed(expected: dict, observation: Observation) -> list[str]:
    """The adapter's own counts and the configuration held at the first prompt, exactly."""
    diffs = []
    counts = observation.counts()
    for key in COUNTS:
        if counts[key] != expected[key]:
            diffs.append(f"observed.{key}: want {expected[key]} · got {counts[key]}")
    if "acp_config_before_first_prompt" in expected:
        want, first = expected["acp_config_before_first_prompt"], observation.first_prompt()
        if first is None:
            diffs.append(f"observed.acp_config_before_first_prompt: want {want} · no prompt arrived")
        elif first["applied"] != want:
            diffs.append(f"observed.acp_config_before_first_prompt: want {want} · "
                         f"got {first['applied']} (the session held {first['current']})")
    return diffs


def acp_facts(observation: Observation) -> dict | None:
    """What the route's ACP peer itself received and confirmed, in the receipt's
    terms: the session its first prompt reached, else the last one opened. A
    transmitted value is the last one sent for that dimension, accepted or not; a
    configured value is the peer's own read-back of a dimension that was sent."""
    first = observation.first_prompt()
    if first is not None:
        chosen = [s for s in observation.sessions
                  if (s["pid"], s["session"]) == (first["pid"], first["session"])]
    else:
        chosen = sorted(observation.sessions, key=lambda s: s["t"])[-1:]
    if not chosen:
        return None
    session, binding = chosen[0], AGENT_ROUTES.get(chosen[0]["route"])
    sent = {"model": [s["value"] for s in session["selections"]
                      if s["method"] == "session/set_model" or s["config_id"] == "model"],
            "effort": [s["value"] for s in session["selections"]
                       if binding is not None and s["config_id"] == binding.effort_option]}
    readback = {option.get("category"): option.get("currentValue")
                for option in (session["readbacks"][-1] if session["readbacks"] else [])}
    facts = {}
    for dimension, category in (("model", "model"), ("effort", "thought_level")):
        facts[f"transmitted_{dimension}"] = sent[dimension][-1] if sent[dimension] else None
        facts[f"configured_{dimension}"] = readback.get(category) if sent[dimension] else None
    return facts


def diff_physical(expected: dict, observation: Observation) -> list[str]:
    """An asserted transmission or configuration is judged on what the routes
    themselves recorded, not only on the engine's account of it: the ACP peer's
    selections and read-backs verbatim, an API endpoint's request body in its
    route's wire form."""
    expected = dict(expected)
    if expected.get("requested_effort", "") is None:
        # No effort was asked: none may travel (01 §run · omitted keeps the route's default).
        expected.setdefault("transmitted_effort", None)
    keys = [key for key in ("transmitted_model", "transmitted_effort", "configured_model",
                            "configured_effort") if key in expected]
    if not keys:
        return []
    diffs = []
    inference = [r for r in observation.api if r["class"] == "inference"]
    acp = acp_facts(observation)
    protocol = expected.get("protocol")
    if protocol in ("acp", None) and (acp is not None or protocol == "acp"):
        for key in keys:
            got = None if acp is None else acp[key]
            if got != expected[key]:
                verb = "received" if key.startswith("transmitted") else "read back"
                diffs.append(f"receipt.{key} · the ACP peer {verb} {got!r} · the receipt asserts "
                             f"{expected[key]!r}")
    if protocol in ("api", None) and (inference or protocol == "api"):
        if not inference:
            diffs.append("receipt · no API endpoint received an inference request")
        for record in inference:
            binding = API_ROUTES[record["route"]]
            for key, field_name, wire in (("transmitted_model", "model", binding.wire_model),
                                          ("transmitted_effort", "reasoning_effort", str)):
                if key not in expected:
                    continue
                want = None if expected[key] is None else wire(expected[key])
                if record[field_name] != want:
                    diffs.append(f"receipt.{key} · the {record['route']} endpoint received "
                                 f"{field_name} {record[field_name]!r} · the receipt asserts "
                                 f"{expected[key]!r}, sent on this route as {want!r}")
            for key in ("configured_model", "configured_effort"):
                if key in expected and expected[key] is not None:
                    diffs.append(f"receipt.{key} · an API route reads back no configuration")
    return diffs


# ----------------------------------------------------------------- the receipt

SELECTION_KEYS = {"schema", "protocol", "model", "effort", "responder", "changed_mid_turn"}
VALUE_KEYS = {"requested", "option", "transmitted", "configured", "configured_source"}
SOURCES = {"session_config", "confirmed_selection", "accepted_request"}
RESPONDER_EVIDENCE = {"unknown", "api_response", "cli_reported"}
EVIDENCE_WORDS = {"confirmed_selection": "configured", "accepted_request": "accepted_request"}


def _text(value) -> bool:
    return isinstance(value, str) and bool(value)


def decode_requirement(raw, strict_json) -> dict:
    """`access_requirement`: the author's words, one compact JSON object."""
    if not isinstance(raw, str):
        raise InvalidEvidence("access_requirement is not a JSON text")
    try:
        value = strict_json(raw)
    except ValueError as error:
        raise InvalidEvidence(f"access_requirement is not one JSON object ({error})") from error
    if not isinstance(value, dict) or not value or set(value) - {"via", "protocol", "fallback", "effort"}:
        raise InvalidEvidence("access_requirement is not a closed nonempty requirement")
    if not all(_text(word) for word in value.values()):
        raise InvalidEvidence("access_requirement holds a non-string or empty word")
    if value.get("protocol", "acp") not in ("acp", "api") or value.get("fallback", "none") != "none":
        raise InvalidEvidence("access_requirement names a protocol or fallback the language lacks")
    return value


def decode_selection(raw, strict_json) -> dict:
    """`access_selection` under `nika/access-selection@1`: that name pins the closed
    shape and vocabulary; another schema name has no admitted reading here."""
    if not isinstance(raw, str):
        raise InvalidEvidence("access_selection is not a JSON text")
    try:
        value = strict_json(raw)
    except ValueError as error:
        raise InvalidEvidence(f"access_selection is not one JSON object ({error})") from error
    if not isinstance(value, dict):
        raise InvalidEvidence("access_selection is not an object")
    if value.get("schema") != SELECTION_SCHEMA:
        if _text(value.get("schema")):
            raise Unsupported(f"access_selection schema {value['schema']!r} has no admitted reading")
        raise InvalidEvidence("access_selection names no schema")
    if set(value) - SELECTION_KEYS or {"protocol", "model", "effort", "responder"} - set(value):
        raise InvalidEvidence("access_selection keys are not the schema's: "
                              + ", ".join(sorted(set(value) ^ SELECTION_KEYS)))
    if value["protocol"] not in ("api", "acp", None):
        raise InvalidEvidence(f"access_selection protocol {value['protocol']!r} is not api, acp or null")
    for dimension in ("model", "effort"):
        entry = value[dimension]
        if not isinstance(entry, dict) or set(entry) != VALUE_KEYS:
            raise InvalidEvidence(f"access_selection.{dimension} is not the five facts")
        if any(word is not None and not _text(word) for word in entry.values()):
            raise InvalidEvidence(f"access_selection.{dimension} holds a non-string or empty fact")
        source, configured = entry["configured_source"], entry["configured"]
        if source is not None and source not in SOURCES:
            raise InvalidEvidence(f"access_selection.{dimension} source {source!r} is not the schema's")
        # The four facts stay apart: an acknowledgement is never a configuration,
        # and a configured value always says how it was learned.
        if source == "accepted_request" and configured is not None:
            raise InvalidEvidence(f"access_selection.{dimension}: an acknowledged request is "
                                  "recorded as configured")
        if (configured is None) != (source in (None, "accepted_request")):
            raise InvalidEvidence(f"access_selection.{dimension}: configured value and source disagree")
    responder = value["responder"]
    if not isinstance(responder, dict) or set(responder) != {"model", "evidence"}:
        raise InvalidEvidence("access_selection.responder is not {model, evidence}")
    if responder["evidence"] not in RESPONDER_EVIDENCE:
        raise InvalidEvidence(f"responder evidence {responder['evidence']!r} is not the schema's")
    if responder["model"] is not None and not _text(responder["model"]):
        raise InvalidEvidence("responder model is neither a name nor null")
    if (responder["model"] is None) != (responder["evidence"] == "unknown"):
        raise InvalidEvidence("responder model and its evidence disagree")
    changes = value.get("changed_mid_turn", [])
    if not isinstance(changes, list) or not all(_text(change) for change in changes):
        raise InvalidEvidence("changed_mid_turn is not a list of changes")
    return value


def project_receipt(access_id: str, selection: dict) -> dict:
    """The engine's record in the fixture's vocabulary (access-harness/README.md)."""
    model, effort = selection["model"], selection["effort"]
    source = model["configured_source"]
    return {
        "access_via": access_id,
        "protocol": selection["protocol"],
        "requested_model": model["requested"],
        "requested_effort": effort["requested"],
        "transmitted_model": model["transmitted"],
        "transmitted_effort": effort["transmitted"],
        "configured_model": model["configured"],
        "configured_effort": effort["configured"],
        "model_evidence": None if source is None else EVIDENCE_WORDS.get(source, source),
        "responding_model": selection["responder"]["model"],
    }


def judge_receipts(access: Contract, events: list[dict], event_fields, strict_json
                   ) -> tuple[list[str], list[str], dict]:
    """Differences, unsupported readings and the decoded receipts per asserted task."""
    diffs, unsupported, decoded = [], [], {}
    terminals: dict[str, list[dict]] = {}
    for event in events:
        if event.get("kind") in TERMINAL_KINDS:
            try:
                fields = event_fields(event)
            except ValueError as error:
                diffs.append(f"receipt: invalid terminal frame ({error})")
                continue
            terminals.setdefault(fields.get("task"), []).append(fields)
    for task in access.tasks:
        frames = terminals.get(task, [])
        if len(frames) != 1:
            diffs.append(f"receipt: task {task} has {len(frames)} terminal frames, not one")
            continue
        fields = frames[0]
        if "access_selection" not in fields:
            diffs.append(f"receipt: task {task} carries no access_selection (missing receipt)")
            continue
        try:
            selection = decode_selection(fields["access_selection"], strict_json)
            if "access_requirement" not in fields:
                raise InvalidEvidence("no access_requirement beside the selection")
            requirement = decode_requirement(fields["access_requirement"], strict_json)
            if not _text(fields.get("access_id")):
                raise InvalidEvidence("no access_id names the route that served")
        except InvalidEvidence as error:
            diffs.append(f"receipt: task {task}: invalid evidence ({error})")
            continue
        except Unsupported as error:
            unsupported.append(f"receipt: task {task}: {error}")
            continue
        got = project_receipt(fields["access_id"], selection)
        decoded[task] = {"access_requirement": requirement, "access_selection": selection,
                         "projected": got}
        # The run's two records of one selection must tell one story, and the
        # requirement must restate the file (01 §run · four facts).
        if requirement != access.declared:
            diffs.append(f"receipt: task {task}: access_requirement {requirement} does not restate "
                         f"the file's {access.declared}")
        if requirement.get("effort") != selection["effort"]["requested"]:
            diffs.append(f"receipt: task {task}: the requirement and the selection request "
                         "different efforts")
        if "protocol" in requirement and selection["protocol"] != requirement["protocol"]:
            diffs.append(f"receipt: task {task}: travelled {selection['protocol']} under a declared "
                         f"protocol {requirement['protocol']}")
        if "via" in requirement and fields["access_id"] != requirement["via"]:
            diffs.append(f"receipt: task {task}: rode {fields['access_id']} under a declared via "
                         f"{requirement['via']}")
        for key, want in access.receipt.items():
            if got[key] != want:
                diffs.append(f"receipt.{key}: want {want!r} · got {got[key]!r}")
    return diffs, unsupported, decoded


def _executed(events: list[dict]) -> bool:
    return any(str(event.get("kind", "")).startswith(("workflow_", "task_")) for event in events)


def pre_run_error(stdout: str, events: list[dict] | None, strict_json) -> tuple[dict | None, str]:
    """The engine's own refusal before any workflow or task event: a bare machine
    error document, or the error a lone settlement carries."""
    if events is None or _executed(events):
        return None, ""
    for event in events:
        if event.get("kind") == "run_settled" and isinstance(event.get("error"), dict):
            return event["error"], f"at settlement (cause {event.get('cause')})"
    try:
        document = strict_json(stdout)
    except ValueError:
        return None, ""
    if isinstance(document, dict) and isinstance(document.get("error"), dict):
        return document["error"], "as a bare error document"
    return None, ""


def unstaged_premise(expected: dict, stdout: str, events: list[dict] | None,
                     observation: Observation, strict_json) -> str | None:
    """A run the fixture wanted, refused before any workflow or task event because
    the stage's unpriced endpoint meets the engine's unknown-cost admission, with
    nothing physically sent anywhere: the requirement was never exercised. Any
    effect keeps the divergence."""
    if (expected.get("admission") or {}).get("accepted") is not True \
            or any(observation.counts().values()):
        return None
    error, _ = pre_run_error(stdout, events, strict_json)
    message = error.get("message") if isinstance(error, dict) else None
    if not isinstance(message, str) or not (message.startswith(UNKNOWN_PRICE_REFUSALS[0])
                                            or UNKNOWN_PRICE_REFUSALS[1] in message):
        return None
    return ("the staged loopback endpoint has no known USD price for the reference engine: its "
            "unknown-cost admission refuses that plain-HTTP route, and a reviewable route would "
            "still need a fresh interactive one-time choice; this noninteractive adapter declares "
            "none and never answers or bypasses that review, so the selection was not exercised "
            f"(engine: {message})")


# ----------------------------------------------------------- notes · evidence

def refusal_witness(stdout: str, events: list[dict] | None, event_fields, strict_json) -> list[str]:
    """Where and why the engine refused, in its own words (informational)."""
    error, where = pre_run_error(stdout, events, strict_json)
    if error is not None:
        return [f"engine refused before any workflow or task event, {where}: {error.get('code')} · "
                f"{str(error.get('message'))[:240]}"]
    if not events:
        try:
            document = strict_json(stdout)
        except ValueError:
            return []
        if isinstance(document, dict) and "clean" in document:
            return [f"engine's embedded check answered before any event (clean="
                    f"{document['clean']}): {stdout.strip()[:240]}"]
        return []
    notes = []
    for event in events:
        if event.get("kind") != "task_failed":
            continue
        try:
            fields = event_fields(event)
            outcome = strict_json(fields.get("outcome", "{}"))
            error = outcome.get("payload", {}).get("error") or {}
        except (ValueError, AttributeError):
            continue
        message = error.get("message") or fields.get("detail")
        notes.append(f"task {fields.get('task')} failed: {error.get('code')} · {str(message)[:240]}")
    return notes


def notes(stage: Stage, proc, observation: Observation) -> list[str]:
    counts = observation.counts()
    sessions = [process for process in observation.acp if "session/new" in process["methods"]]
    lines = [f"stage · {', '.join(stage.staged) or 'nothing'} · exit {proc.returncode}",
             f"peers · acp {len(observation.acp)} process(es), {len(sessions)} with a session, "
             f"{counts['acp_prompts']} prompt(s) · selections "
             + (", ".join(f"{s['config_id'] or s['method']}={s['value']}:{s['outcome']}"
                          for process in observation.acp for s in process["selections"]) or "none")]
    probes = [f"{record['route']} {' '.join(record['argv'])}" for record in observation.cli
              if record["kind"] != "direct"]
    direct = [f"{record['route']} {' '.join(record['argv'])}" for record in observation.cli
              if record["kind"] == "direct"]
    lines.append(f"peers · cli discovery/sign-in probes: {'; '.join(probes) or 'none'}"
                 f" · direct invocations: {'; '.join(direct) or 'none'}")
    listings = sum(record["class"] == "discovery" for record in observation.api)
    bodies = [f"{record['route']}:{record['model']}" for record in observation.api
              if record["class"] == "inference"]
    lines.append(f"peers · api inference requests {counts['api_inference_requests']}"
                 f" ({', '.join(map(str, bodies)) or 'no body model'}) · model listings {listings}")
    facts = acp_facts(observation)
    if facts is not None:
        lines.append("peers · acp session facts · " + ", ".join(f"{key}={value!r}"
                                                                for key, value in facts.items()))
    return lines


def engine_identity(engine: str) -> dict:
    """The exact binary judged: its path, SHA-256 and own version report."""
    path = pathlib.Path(engine)
    digest = hashlib.sha256()
    with open(path, "rb") as binary:
        for chunk in iter(lambda: binary.read(1 << 20), b""):
            digest.update(chunk)
    with tempfile.TemporaryDirectory(prefix="nika-access-identity-") as home:
        version = subprocess.run([engine, "--version"], capture_output=True, text=True, timeout=60,
                                 env={"PATH": ":".join(SYSTEM_PATH), "HOME": home, "TERM": "dumb",
                                      "NIKA_KEYCHAIN": "off"}, cwd=home, stdin=subprocess.DEVNULL)
    return {"path": str(path), "sha256": digest.hexdigest(), "version_exit": version.returncode,
            "version": version.stdout.strip() or version.stderr.strip()}


def resolve_engine(engine: str) -> str:
    """An absolute engine path: the stage runs it from its own project directory."""
    found = engine if os.sep in engine else shutil.which(engine)
    if not found or not os.path.isfile(found):
        raise FileNotFoundError(f"engine {engine!r} not found")
    return os.path.abspath(found)
