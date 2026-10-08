#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Scripted route peers for the access-selection adapter (runtime_access_adapter.py).

Each staged binary is a `/bin/sh` wrapper that runs this file in isolated mode
(`python3 -I -B -S`) with an absolute configuration file and log directory baked
in. An engine may hand its route processes a filtered environment, so nothing
here is read from the environment. Standard library only.

    acp <config.json> <log-dir>           one ACP agent process over stdio
    cli <config.json> <log-dir> <argv...> one invocation of a route's product CLI

Every process appends its own JSON-lines log (one file per process, flushed
line by line): what it physically received, what it answered, each selection's
outcome, the configuration it returned and the configuration it held when a
prompt arrived. The adapter judges these logs, never the engine's account of
them. The peers are deliberately plain: no model, no tool, no network.
"""
from __future__ import annotations

import json
import os
import select
import sys
import time

PROTOCOL_VERSION = 1
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS = -32700, -32600, -32601, -32602
MAX_LINE = 4 * 1024 * 1024
ANSWER = "scripted answer"


class Log:
    """One process, one append-only JSON-lines file; every record is flushed."""

    def __init__(self, directory: str, kind: str, route: str):
        self.seq = 0
        name = f"{kind}-{route}-{time.time_ns()}-{os.getpid()}.jsonl"
        self.handle = open(os.path.join(directory, name), "a", encoding="utf-8")

    def write(self, event: str, **fields) -> None:
        self.seq += 1
        record = {"t": time.time_ns(), "seq": self.seq, "pid": os.getpid(), "event": event}
        record.update(fields)
        self.handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.handle.flush()


class Session:
    """One ACP session's state: what is current, and what a client selection applied."""

    def __init__(self, world: dict, sid: str):
        self.sid = sid
        self.models = world["models"]
        self.legacy = world["config"] == "legacy"
        self.model = world.get("default_model") or next(iter(self.models))
        efforts = self.efforts()
        # ACP requires a current value for every option: the first offered one.
        self.effort = efforts[0] if efforts and not self.legacy else None
        # Only values a client selection set, and that still hold.
        self.applied: dict[str, str] = {}

    def efforts(self) -> list[str]:
        return [] if self.legacy else list(self.models[self.model]["effort"])

    def current(self) -> dict:
        return {"model": self.model, "effort": self.effort}

    def options(self, effort_id: str) -> list[dict]:
        """The complete configuration, as session/new and every answer report it."""
        def select_option(option_id, category, current, values):
            return {"id": option_id, "name": option_id, "category": category, "type": "select",
                    "currentValue": current,
                    "options": [{"value": value, "name": value} for value in values]}
        options = [select_option("model", "model", self.model, list(self.models))]
        if self.efforts():
            options.append(select_option(effort_id, "thought_level", self.effort, self.efforts()))
        return options

    def select_model(self, model: str) -> None:
        self.model = model
        self.applied["model"] = model
        if self.legacy:
            return
        efforts = self.efforts()
        if self.effort not in efforts:
            # The previous effort is not offered for this model: the session
            # resets it, and no client selection holds it any more.
            self.effort = efforts[0] if efforts else None
            self.applied.pop("effort", None)

    def select_effort(self, effort: str) -> None:
        self.effort = effort
        self.applied["effort"] = effort


class AcpPeer:
    """One scripted ACP agent process, driven by the route world the adapter staged."""

    def __init__(self, config: dict, log: Log):
        self.config = config
        self.world = config["acp"]
        self.legacy = self.world["config"] == "legacy"
        self.confirms = self.world.get("readback", "confirmed") == "confirmed"
        self.behavior = self.world.get("prompt", "completes")
        self.effort_id = config["effort_option"]
        self.sessions: dict[str, Session] = {}
        self.log = log

    def send(self, message: dict) -> None:
        line = json.dumps(message, separators=(",", ":"))
        self.log.write("sent", message=message)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def reply(self, request_id, result: dict) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def error(self, request_id, code: int, message: str) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})

    def serve(self) -> None:
        stream = sys.stdin.buffer
        while True:
            raw = stream.readline(MAX_LINE + 1)
            if not raw:
                self.log.write("exit", reason="eof")
                return
            if len(raw) > MAX_LINE:
                self.log.write("received", valid=False, reason="line over the peer's bound")
                self.error(None, PARSE_ERROR, "line over the peer's bound")
                return
            self.handle(raw)

    def handle(self, raw: bytes) -> None:
        try:
            message = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as problem:
            self.log.write("received", valid=False, raw=raw[:2048].decode("utf-8", "replace"),
                           reason=str(problem))
            self.error(None, PARSE_ERROR, "not one JSON document")
            return
        self.log.write("received", valid=True, message=message)
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            self.error(message.get("id") if isinstance(message, dict) else None,
                       INVALID_REQUEST, "not a JSON-RPC 2.0 message")
            return
        method = message.get("method")
        if not isinstance(method, str) or "id" not in message:
            return  # a notification (session/cancel …) or a stray answer: observed only
        params = message.get("params")
        params = params if isinstance(params, dict) else {}
        handler = {
            "initialize": self.initialize,
            "session/new": self.new_session,
            "session/set_config_option": self.set_config_option,
            "session/set_model": self.set_model,
            "session/prompt": self.prompt,
        }.get(method)
        if handler is None:
            self.error(message["id"], METHOD_NOT_FOUND, f"{method} is not offered by this peer")
            return
        handler(message["id"], params)

    def initialize(self, request_id, params: dict) -> None:
        identity = self.config["identity"]
        self.reply(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "agentCapabilities": {"loadSession": False, "promptCapabilities": {
                "image": False, "audio": False, "embeddedContext": False}},
            "authMethods": [],
            "agentInfo": {"name": identity["name"], "title": identity["title"],
                          "version": identity["version"]},
        })

    def new_session(self, request_id, params: dict) -> None:
        sid = f"scripted-{len(self.sessions) + 1}"
        session = Session(self.world, sid)
        self.sessions[sid] = session
        result = {"sessionId": sid}
        if self.legacy:
            # A legacy session advertises a model list and only acknowledges a choice.
            result["models"] = {"currentModelId": session.model, "availableModels": [
                {"modelId": model, "name": model} for model in session.models]}
        else:
            result["configOptions"] = session.options(self.effort_id)
        self.log.write("session", session=sid, cwd=params.get("cwd"), current=session.current())
        self.reply(request_id, result)

    def session_for(self, request_id, params: dict):
        session = self.sessions.get(params.get("sessionId"))
        if session is None:
            self.error(request_id, INVALID_PARAMS, "unknown sessionId")
        return session

    def set_config_option(self, request_id, params: dict) -> None:
        if self.legacy:
            self.error(request_id, METHOD_NOT_FOUND, "this session exposes no configuration options")
            return
        session = self.session_for(request_id, params)
        if session is None:
            return
        config_id, value = params.get("configId"), params.get("value")
        offers = {"model": list(session.models), self.effort_id: session.efforts()}
        offered = offers.get(config_id) if isinstance(config_id, str) else None
        record = {"session": session.sid, "method": "session/set_config_option",
                  "config_id": config_id, "value": value}
        if not offered or not isinstance(value, str) or value not in offered:
            self.log.write("selection", outcome="rejected", offered=offered, **record)
            self.error(request_id, INVALID_PARAMS,
                       f"{value!r} is not an offered value of option {config_id!r}")
            return
        if self.confirms:
            (session.select_model if config_id == "model" else session.select_effort)(value)
            self.log.write("selection", outcome="applied", **record)
        else:
            # An unconfirmed read-back: the answer carries the configuration as it was.
            self.log.write("selection", outcome="ignored", **record)
        options = session.options(self.effort_id)
        self.log.write("readback", session=session.sid, configOptions=options)
        self.reply(request_id, {"configOptions": options})

    def set_model(self, request_id, params: dict) -> None:
        if not self.legacy:
            self.error(request_id, METHOD_NOT_FOUND, "this session selects through config options")
            return
        session = self.session_for(request_id, params)
        if session is None:
            return
        model = params.get("modelId")
        record = {"session": session.sid, "method": "session/set_model", "value": model}
        if not isinstance(model, str) or model not in session.models:
            self.log.write("selection", outcome="rejected", offered=list(session.models), **record)
            self.error(request_id, INVALID_PARAMS, f"{model!r} is not an advertised model")
            return
        session.select_model(model)
        self.log.write("selection", outcome="acknowledged", **record)
        self.reply(request_id, {})

    def prompt(self, request_id, params: dict) -> None:
        session = self.sessions.get(params.get("sessionId"))
        self.log.write("prompt", session=params.get("sessionId"), session_known=session is not None,
                       applied=dict(session.applied) if session else {},
                       current=session.current() if session else None, behavior=self.behavior)
        if session is None:
            self.error(request_id, INVALID_PARAMS, "unknown sessionId")
            return
        if self.behavior == "session_dies":
            self.log.write("exit", reason="session_dies")
            sys.stdout.flush()
            os._exit(70)
        self.send({"jsonrpc": "2.0", "method": "session/update", "params": {
            "sessionId": session.sid,
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": ANSWER}}}})
        self.reply(request_id, {"stopReason": "end_turn"})


def classify(argv: list[str], discovery: list[dict]) -> str:
    """A product-CLI invocation is discovery only in an exact listed argv (after
    leading `-c <override>` pairs); anything else is a direct invocation. Fail
    closed: an unknown or merely similar form is never read as a probe."""
    words = list(argv)
    while len(words) >= 2 and words[0] in ("-c", "--config"):
        words = words[2:]
    return next((row["kind"] for row in discovery if row["argv"] == words), "direct")


def read_prompt(limit: float = 2.0) -> bytes:
    """The prompt a direct one-shot writes on stdin, read without waiting for EOF."""
    stream, data, deadline = sys.stdin.buffer, b"", time.monotonic() + limit
    while time.monotonic() < deadline and len(data) < MAX_LINE:
        ready, _, _ = select.select([stream], [], [], max(0.0, deadline - time.monotonic()))
        if not ready:
            break
        chunk = os.read(stream.fileno(), 65536)
        if not chunk:
            break
        data += chunk
        if b"\n" in chunk:
            break
    return data


def run_cli(config: dict, log: Log, argv: list[str]) -> int:
    kind = classify(argv, config["discovery"])
    log.write("invocation", argv=argv, kind=kind)
    if kind == "discovery:version":
        print(config["version_line"])
        return 0
    if kind == "discovery:auth":
        return 0 if config["signed_in"] else 1
    if kind.startswith("discovery:"):
        print(f"scripted {config['route']}: `{' '.join(argv)}` is not modeled by this route world",
              file=sys.stderr)
        return 2
    if not config["direct"]:
        log.write("refused", reason="no direct CLI path in this route world")
        print(f"scripted {config['route']}: no direct CLI path in this route world", file=sys.stderr)
        return 1
    prompt = read_prompt()
    log.write("direct", prompt_bytes=len(prompt))
    for line in ({"type": "thread.started", "thread_id": "scripted"}, {"type": "turn.started"},
                 {"type": "item.completed", "item": {"id": "scripted", "type": "agent_message",
                                                     "text": ANSWER}},
                 {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}):
        print(json.dumps(line), flush=True)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[1] not in ("acp", "cli"):
        print("usage: runtime_access_peer.py acp|cli <config.json> <log-dir> [argv...]",
              file=sys.stderr)
        return 64
    with open(argv[2], encoding="utf-8") as handle:
        config = json.load(handle)
    log = Log(argv[3], argv[1], config["route"])
    log.write("start", argv=argv[4:], kind=argv[1], route=config["route"])
    if argv[1] == "cli":
        return run_cli(config, log, argv[4:])
    AcpPeer(config, log).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
