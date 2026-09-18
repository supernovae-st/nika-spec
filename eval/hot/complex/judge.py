#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Judge composed authoring candidates by meaning, never by bytes or by model output.

A candidate is a workflow somebody (a person, a compiler, a model) proposes for
a scenario. Static validity is necessary and proves nothing else: every
near-miss in this corpus is a workflow that reads well and is wrong. The
assertions below are properties of the derived graph, so a differently built
correct candidate passes and a plausible incorrect one does not.

    python3 eval/hot/complex/judge.py                      # the corpus judges itself
    python3 eval/hot/complex/judge.py --scenario X01 --candidate my.nika.yaml

No engine, no network, no model. Runtime behaviour is `behaviour.py`.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent.parent
STATUSES = {
    "STATIC_JUDGED",                 # assertions and their negative controls run in CI, no engine
    "STATIC_AND_BEHAVIOUR",          # also rehearsed offline on an explicitly supplied engine
    "UNQUALIFIED_PRODUCT_CONTRACT",  # acceptance case only: nothing here proves it
}
ROLES = {"reference", "variant", "near_miss", "refused"}
PURE_TOOLS = {"nika:jq", "nika:assert", "nika:validate", "nika:decide", "nika:json_diff",
              "nika:json_merge_patch", "nika:convert", "nika:hash", "nika:date"}
WRITE_TOOLS = {"nika:write", "nika:edit"}
NET_TOOLS = {"nika:fetch", "nika:notify"}
CONTROL_ARGS = {"path", "url", "target", "channel", "bundle"}
EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.S)
REFERENCE = re.compile(r"\b(inputs|const|secrets|with|tasks)\.([A-Za-z_][A-Za-z0-9_]*)|\b(item)\b")


class JudgeError(ValueError):
    """The corpus contradicts its own declarations."""


def require(condition: bool, message: str) -> None:
    # `assert` disappears under `python -O`; this gate must not.
    if not condition:
        raise JudgeError(message)


# ── the derived graph ────────────────────────────────────────────────────────

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def verb(task: dict) -> str | None:
    return next((name for name in ("infer", "exec", "invoke", "agent") if name in task), None)


def tool(task: dict) -> str | None:
    return task.get("invoke", {}).get("tool") if isinstance(task.get("invoke"), dict) else None


def sources(value, task: dict, _seen: frozenset = frozenset()) -> set[str]:
    """Where a value comes from: `inputs.x` · `const.y` · `secrets.z` · `tasks.t` · `item`.

    A `with.name` read resolves through the task's own bindings, because the
    binding is the edge; a task output is kept at task granularity.
    """
    found: set[str] = set()
    for text in strings(value):
        for body in EXPRESSION.findall(text):
            for space, name, item in REFERENCE.findall(body):
                if item:
                    found.add("item")
                elif space == "with":
                    if name not in _seen:
                        found |= sources(task.get("with", {}).get(name), task, _seen | {name})
                else:
                    found.add(f"{space}.{name}")
    return found


def task_sources(task: dict) -> set[str]:
    body = {key: value for key, value in task.items() if key != "with"}
    return sources(body, task) | sources(task.get("with", {}), task)


def effect_kind(task: dict) -> str | None:
    if "exec" in task:
        return "exec"
    if "agent" in task:
        granted = task["agent"].get("tools") or []
        egress = [t for t in granted if t not in PURE_TOOLS | {"nika:done", "nika:read", "nika:glob",
                                                              "nika:grep", "nika:log", "nika:prompt"}]
        return "agent" if egress else None
    name = tool(task)
    if name in WRITE_TOOLS:
        return "fs.write"
    if name in NET_TOOLS:
        return "net"
    if name and name.startswith("mcp:"):
        return "mcp"
    if isinstance(task.get("invoke"), dict) and "workflow" in task["invoke"]:
        return "workflow"
    return None


def is_confirm_gate(task: dict) -> bool:
    return tool(task) == "nika:prompt" and task["invoke"].get("args", {}).get("mode", "confirm") == "confirm"


# ── a three-valued reading of `when:` (the decidable fragment, nothing more) ──

TOKEN = re.compile(r"""\s*(?:(?P<op>==|!=|&&|\|\||!|\(|\))|(?P<str>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')"""
                   r"""|(?P<num>-?\d+(?:\.\d+)?)|(?P<name>[A-Za-z_][A-Za-z0-9_.]*))""")
UNKNOWN = object()


class Undecidable(ValueError):
    """The expression leaves the fragment this judge reads; it claims nothing."""


def tokenize(text: str) -> list[tuple[str, str]]:
    tokens, position = [], 0
    text = text.strip()
    while position < len(text):
        match = TOKEN.match(text, position)
        if not match or match.end() == position:
            raise Undecidable(text)
        position = match.end()
        kind = match.lastgroup
        tokens.append((kind, match.group(kind)))
    return tokens


def evaluate(text: str, env: dict):
    """Kleene evaluation: True · False · UNKNOWN. Unknown names stay unknown (sound, never a guess)."""
    tokens = tokenize(text)
    index = 0

    def peek():
        return tokens[index] if index < len(tokens) else (None, None)

    def take():
        nonlocal index
        index += 1
        return tokens[index - 1]

    def atom():
        kind, value = take() if index < len(tokens) else (None, None)
        if kind == "op" and value == "(":
            inner = disjunction()
            if take() != ("op", ")"):
                raise Undecidable(text)
            return inner
        if kind == "op" and value == "!":
            inner = atom()
            return UNKNOWN if inner is UNKNOWN else (not inner)
        if kind == "str":
            return value[1:-1]
        if kind == "num":
            return float(value)
        if kind == "name":
            if value in ("true", "false"):
                return value == "true"
            if value == "null":
                return None
            return env.get(value, UNKNOWN)
        raise Undecidable(text)

    def comparison():
        left = atom()
        kind, value = peek()
        if kind == "op" and value in ("==", "!="):
            take()
            right = atom()
            if left is UNKNOWN or right is UNKNOWN:
                return UNKNOWN
            return (left == right) if value == "==" else (left != right)
        return left

    def conjunction():
        result = comparison()
        while peek() == ("op", "&&"):
            take()
            right = comparison()
            if result is False or right is False:
                result = False
            elif result is UNKNOWN or right is UNKNOWN:
                result = UNKNOWN
            else:
                result = bool(result and right)
        return result

    def disjunction():
        result = conjunction()
        while peek() == ("op", "||"):
            take()
            right = conjunction()
            if result is True or right is True:
                result = True
            elif result is UNKNOWN or right is UNKNOWN:
                result = UNKNOWN
            else:
                result = bool(result or right)
        return result

    value = disjunction()
    if index != len(tokens):
        raise Undecidable(text)
    return value


def when_body(task: dict):
    condition = task.get("when")
    if condition is None or isinstance(condition, bool):
        return condition
    bodies = EXPRESSION.findall(str(condition))
    return bodies[0].strip() if len(bodies) == 1 else UNKNOWN


# ── consent: NO triggers exactly zero effects ────────────────────────────────

def gate_binding(task: dict, tasks: dict) -> tuple[str, str] | None:
    """(`with` name, gate id) when a binding carries a confirm gate's answer, and only that."""
    for name, value in (task.get("with") or {}).items():
        match = re.fullmatch(r"\s*\$\{\{\s*tasks\.([a-z0-9_]+)\.output\s*\}\}\s*", str(value))
        if match and match.group(1) in tasks and is_confirm_gate(tasks[match.group(1)]):
            return name, match.group(1)
    return None


def direct_gate(task: dict, tasks: dict) -> str | None:
    """The gate whose refusal provably closes this task, or None."""
    binding = gate_binding(task, tasks)
    body = when_body(task)
    if not binding or body in (None, True, False, UNKNOWN):
        return None
    try:
        refused = evaluate(body, {f"with.{binding[0]}": False})
        approved = evaluate(body, {f"with.{binding[0]}": True})
    except Undecidable:
        return None
    return binding[1] if refused is False and approved is not False else None


def closing_gate(task_id: str, tasks: dict, _seen: frozenset = frozenset()) -> str | None:
    """A refusal reaches this task as a skip only through its own `when:` or an `after: success` edge.

    A `with:` edge does not close anything: a skipped producer hands null and the
    consumer still runs. That asymmetry is the counterexample `X01` retains.
    """
    task = tasks[task_id]
    gate = direct_gate(task, tasks)
    if gate:
        return gate
    for upstream, state in (task.get("after") or {}).items():
        if state == "success" and upstream in tasks and upstream not in _seen:
            gate = closing_gate(upstream, tasks, _seen | {task_id})
            if gate:
                return gate
    return None


def selected_effects(tasks: dict, params: dict) -> list[str]:
    kinds = set(params.get("kinds", ["fs.write", "net", "exec", "mcp", "agent", "workflow"]))
    exempt = set(params.get("exempt_tasks_writing", []))
    chosen = []
    for task_id, task in tasks.items():
        if effect_kind(task) not in kinds:
            continue
        path = str(task.get("invoke", {}).get("args", {}).get("path", "")) if "invoke" in task else ""
        if path and path in exempt:
            continue
        chosen.append(task_id)
    return chosen


def a_effects_gated(doc, params):
    tasks = doc["tasks"]
    effects = selected_effects(tasks, params)
    if not effects:
        return ["no effect task to judge: the requested effect is missing"]
    return [f"`{t}` can run after a refusal: no `when:` on the gate's answer and no `after: success` "
            f"edge from a task that has one" for t in effects if not closing_gate(t, tasks)]


def a_gate_blocking(doc, params):
    tasks = doc["tasks"]
    gates = {closing_gate(t, tasks) for t in selected_effects(tasks, params)} - {None}
    return [f"gate `{g}` declares `default:` and answers itself when nobody is there"
            for g in sorted(gates) if "default" in tasks[g]["invoke"].get("args", {})]


def a_gate_binds_effect_facts(doc, params):
    """What the person is shown must name every fact the effect consumes.

    The engine binds an answer to the content that was shown. A question that
    shows nothing binds nothing, and the answer then authorises any later value.
    """
    tasks, ignore, problems = doc["tasks"], set(params.get("ignore", [])), []
    for effect in selected_effects(tasks, params):
        gate = closing_gate(effect, tasks)
        if not gate:
            continue
        verb_body = tasks[effect][verb(tasks[effect])]
        binding = gate_binding(tasks[effect], tasks)
        facts = sources(verb_body, tasks[effect]) - {f"tasks.{gate}"} - ignore
        if binding:
            facts -= {f"with.{binding[0]}"}
        shown = sources(tasks[gate]["invoke"].get("args", {}).get("message", ""), tasks[gate])
        missing = sorted(facts - shown)
        if missing:
            problems.append(f"gate `{gate}` does not show {missing}, which `{effect}` consumes")
    return problems


# ── authority, intent fidelity, untrusted data ───────────────────────────────

def permit_entries(doc) -> dict[str, list]:
    permits = doc.get("permits")
    if not isinstance(permits, dict):
        return {}
    exec_grant = permits.get("exec", [])
    return {
        "tools": list(permits.get("tools", []) or []),
        "net.http": list((permits.get("net") or {}).get("http", []) or []),
        "fs.read": list((permits.get("fs") or {}).get("read", []) or []),
        "fs.write": list((permits.get("fs") or {}).get("write", []) or []),
        "exec": ["<any program>"] if exec_grant is True else list(exec_grant or []),
        "env": list(permits.get("env", []) or []),
    }


def normal(path: str) -> str:
    return path[2:] if path.startswith("./") else path


def a_authority_bounded(doc, params):
    if not isinstance(doc.get("permits"), dict):
        return ["no `permits:` block: the candidate declares no boundary at all"]
    problems = []
    for category, granted in permit_entries(doc).items():
        ceiling = params.get(category)
        for entry in granted:
            bare = normal(str(entry))
            if category == "tools" and (bare in PURE_TOOLS | {"nika:done", "nika:prompt", "nika:log"}):
                continue
            if bare in ("*", "**", "<any program>") or (category == "tools" and bare.endswith(":*")) \
                    or (category == "net.http" and "*" in bare):
                problems.append(f"`{category}` grants the wildcard `{entry}`")
            elif ceiling is None or bare not in {normal(str(c)) for c in ceiling}:
                problems.append(f"`{category}` grants `{entry}`, which the request does not need")
    return problems


def a_required_effects_present(doc, params):
    problems = []
    for need in params["effects"]:
        hits = [t for t in doc["tasks"].values() if tool(t) == need["tool"]]
        if "arg" in need:
            hits = [t for t in hits
                    if need["source"] in sources(t["invoke"].get("args", {}).get(need["arg"], ""), t)
                    or t["invoke"].get("args", {}).get(need["arg"]) == need["source"]]
        if not hits:
            problems.append(f"the requested `{need['tool']}` effect is absent: the intent was weakened, not served")
    return problems


def a_control_positions_trusted(doc, params):
    """Untrusted content may be read, quoted and judged. It may not choose a tool, a path, a host or a program."""
    tasks = doc["tasks"]
    tainted = set(params["untrusted"])
    changed = True
    while changed:
        changed = False
        for task_id, task in tasks.items():
            if f"tasks.{task_id}" not in tainted and (
                    task_sources(task) & tainted or tool(task) in set(params.get("untrusted_tools", []))):
                tainted.add(f"tasks.{task_id}")
                changed = True
    problems = []
    for task_id, task in tasks.items():
        positions = {"model": task.get("model")}
        if "exec" in task:
            positions.update({f"exec.{k}": task["exec"].get(k) for k in ("command", "shell", "cwd", "env")})
        if "agent" in task:
            positions.update({f"agent.{k}": task["agent"].get(k) for k in ("tools", "skills", "model")})
        if "infer" in task:
            positions["infer.model"] = task["infer"].get("model")
        if "invoke" in task:
            positions.update({"invoke.tool": task["invoke"].get("tool"),
                              "invoke.workflow": task["invoke"].get("workflow")})
            positions.update({f"args.{k}": v for k, v in (task["invoke"].get("args") or {}).items()
                              if k in CONTROL_ARGS})
        for position, value in positions.items():
            reached = sorted(sources(value, task) & tainted)
            if reached:
                problems.append(f"`{task_id}.{position}` is chosen by untrusted {reached}")
    return problems


# ── bounds, determinism, contracts ───────────────────────────────────────────

def a_bounded(doc, params):
    problems, model_tasks = [], 0
    for task_id, task in doc["tasks"].items():
        if "infer" in task:
            model_tasks += 1
            if not isinstance(task["infer"].get("max_tokens"), int):
                problems.append(f"`{task_id}` has no `max_tokens` ceiling")
        if "agent" in task:
            model_tasks += 1
            for bound in ("max_turns", "max_tokens_total"):
                if not isinstance(task["agent"].get(bound), int):
                    problems.append(f"`{task_id}` is an agent loop with no `{bound}`")
        if "for_each" in task and not isinstance(task["for_each"].get("max_parallel"), int):
            problems.append(f"`{task_id}` fans out with no `max_parallel`")
        attempts = (task.get("retry") or {}).get("max_attempts", 1)
        if attempts > params.get("max_retry_attempts", 5):
            problems.append(f"`{task_id}` retries {attempts} times")
    if model_tasks > params["max_model_tasks"]:
        problems.append(f"{model_tasks} model tasks exceed the declared budget of {params['max_model_tasks']}")
    return problems


def output_task(doc, name):
    match = re.search(r"tasks\.([a-z0-9_]+)", str((doc.get("outputs") or {}).get(name, "")))
    return match.group(1) if match else None


def a_decision_deterministic(doc, params):
    problems = []
    for name in params["outputs"]:
        task_id = output_task(doc, name)
        task = doc["tasks"].get(task_id) if task_id else None
        if task is None:
            problems.append(f"output `{name}` is not produced by a task")
        elif tool(task) not in PURE_TOOLS:
            problems.append(f"output `{name}` is decided by `{verb(task)}`, not by a deterministic rule")
        elif not any(s.startswith("tasks.") for s in task_sources(task)):
            problems.append(f"output `{name}` reads no evidence: a constant cannot be a verdict")
    return problems


def a_outputs_contract(doc, params):
    declared = set(doc.get("outputs") or {})
    return [f"output `{name}` is missing" for name in params["required"] if name not in declared]


def a_inputs_contract(doc, params):
    declared, problems = doc.get("inputs") or {}, []
    for name in params.get("must_supply", []):
        entry = declared.get(name)
        if not isinstance(entry, dict) or entry.get("required") is not True:
            problems.append(f"input `{name}` must be `required: true`: nobody may guess it")
        elif "default" in entry:
            problems.append(f"input `{name}` carries a `default:`: a forgotten value becomes an invented one")
    for name, default in params.get("defaults", {}).items():
        entry = declared.get(name)
        if not isinstance(entry, dict) or entry.get("default", UNKNOWN) != default:
            problems.append(f"input `{name}` must default to {default!r}")
    for name in params.get("nullable", []):
        kind = (declared.get(name) or {}).get("type")
        members = kind.get("union", []) if isinstance(kind, dict) else []
        if not any(member in (None, "null") for member in members):
            problems.append(f"input `{name}` must admit null as a value distinct from an empty string")
    return problems


def a_recover_narrow(doc, params):
    allowed, problems = set(params["allowed_codes"]), []
    for task_id, task in doc["tasks"].items():
        handler = task.get("on_error") or {}
        if tool(task) in params["tools"] and "recover" in handler:
            codes = set(handler.get("on_codes") or [])
            if not codes:
                problems.append(f"`{task_id}` recovers from every failure, so a corrupt or forbidden source reads as absent")
            elif not codes <= allowed:
                problems.append(f"`{task_id}` recovers from {sorted(codes - allowed)}")
    return problems


def a_fanout_isolated(doc, params):
    problems = []
    for task_id, task in doc["tasks"].items():
        if "for_each" in task:
            if task["for_each"].get("fail_fast") is not False:
                problems.append(f"`{task_id}` lets one bad item sink the batch (`fail_fast` is not false)")
            if not task.get("on_error"):
                problems.append(f"`{task_id}` has no per-item failure route")
    return problems


def a_branches_exclusive_total(doc, params):
    """For every value the classifier may return, exactly one branch is open."""
    field, problems = params["field"], []
    branches = {t: when_body(task) for t, task in doc["tasks"].items()
                if isinstance(when_body(task), str) and re.search(rf"\.{re.escape(field)}\b", when_body(task))}
    if not branches:
        return [f"no branch reads `.{field}`"]
    for value in params["domain"]:
        open_branches = []
        for task_id, body in branches.items():
            names = {n for kind, n in tokenize(body) if kind == "name" and n.endswith(f".{field}")}
            try:
                verdict = evaluate(body, {name: value for name in names})
            except Undecidable:
                verdict = UNKNOWN
            if verdict is UNKNOWN:
                problems.append(f"`{task_id}` cannot be decided for {field}={value!r}")
            elif verdict:
                open_branches.append(task_id)
        if len(open_branches) != 1:
            problems.append(f"{field}={value!r} opens {sorted(open_branches) or 'no branch'}; exactly one must run")
    return problems


def flatten(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from flatten(item, f"{prefix}[{index}]")
    else:
        yield prefix, value


def semantic_changes(base: dict, candidate: dict) -> set[str]:
    before, after = dict(flatten(base)), dict(flatten(candidate))
    return {path for path in before.keys() | after.keys() if before.get(path, UNKNOWN) != after.get(path, UNKNOWN)}


def a_edit_locality(doc, params):
    base = yaml.safe_load((params.get("_root", ROOT) / params["base"]).read_text(encoding="utf-8"))
    changed, problems = semantic_changes(base, doc), []
    for path in sorted(changed):
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in params["allowed"]):
            problems.append(f"unrequested change at `{path}`")
    for pattern in params["required"]:
        if not any(fnmatch.fnmatchcase(path, pattern) for path in changed):
            problems.append(f"requested change `{pattern}` did not happen")
    if set(base["tasks"]) != set(doc["tasks"]):
        problems.append(f"task identities changed: {sorted(set(base['tasks']) ^ set(doc['tasks']))}")
    return problems


ASSERTIONS = {
    "effects_gated": a_effects_gated,
    "gate_blocking": a_gate_blocking,
    "gate_binds_effect_facts": a_gate_binds_effect_facts,
    "authority_bounded": a_authority_bounded,
    "required_effects_present": a_required_effects_present,
    "control_positions_trusted": a_control_positions_trusted,
    "bounded": a_bounded,
    "decision_deterministic": a_decision_deterministic,
    "outputs_contract": a_outputs_contract,
    "inputs_contract": a_inputs_contract,
    "recover_narrow": a_recover_narrow,
    "fanout_isolated": a_fanout_isolated,
    "branches_exclusive_total": a_branches_exclusive_total,
    "edit_locality": a_edit_locality,
}


def judge(doc: dict, assertions: list[dict], root: Path = ROOT) -> dict[str, list[str]]:
    """assertion id → violations; an empty list is a pass."""
    require(isinstance(doc, dict) and isinstance(doc.get("tasks"), dict), "candidate is not a workflow")
    return {a["id"]: ASSERTIONS[a["kind"]](doc, {**a.get("params", {}), "_root": root}) for a in assertions}


# ── the corpus judges itself ─────────────────────────────────────────────────

SCENARIO_FIELDS = {"id", "title", "status", "owner", "laws", "intent", "facts", "expected_outcome",
                   "must_not_guess", "socratic", "assertions", "candidates", "validation"}
CONTRACT_FIELDS = {"id", "title", "status", "owner", "given", "when", "then", "must_never", "why_unqualified"}


_ORACLE: dict[str, dict] = {}


def spec_oracle(path: Path) -> dict:
    """The reference static oracle, by command. Keyed by content: the verdict is a function of the bytes."""
    key = hashlib.sha256(path.read_bytes()).hexdigest()
    if key not in _ORACLE:
        result = subprocess.run([sys.executable, str(REPO / "conformance/runner.py"), "validate", str(path)],
                                capture_output=True, text=True, check=False)
        _ORACLE[key] = json.loads(result.stdout)
    return _ORACLE[key]


def load(root: Path = ROOT) -> dict:
    return json.loads((root / "scenarios.json").read_text(encoding="utf-8"))


def validate(root: Path = ROOT) -> dict:
    root = root.resolve()  # a symlinked temp dir must not defeat the containment check below
    corpus = load(root)
    scenarios, contracts, gaps = corpus["scenarios"], corpus["product_contracts"], corpus["retained_gaps"]
    ids = [row["id"] for row in scenarios + contracts + gaps]
    require(len(ids) == len(set(ids)), "duplicate id")
    require(corpus["byte_equality"] is False, "this corpus judges meaning, never bytes")
    require(corpus["hot_promotion"] is False, "no HOT promotion follows from these cases")
    judged = refused = controls = 0
    for scenario in scenarios:
        sid = scenario["id"]
        require(not SCENARIO_FIELDS - scenario.keys(), f"{sid}: missing {sorted(SCENARIO_FIELDS - scenario.keys())}")
        require(scenario["status"] in STATUSES - {"UNQUALIFIED_PRODUCT_CONTRACT"}, f"{sid}: status")
        require(bool(scenario["laws"]) and bool(scenario["owner"]), f"{sid}: a fixture names its law and owner")
        known = {a["id"] for a in scenario["assertions"]}
        require(len(known) == len(scenario["assertions"]), f"{sid}: duplicate assertion id")
        for assertion in scenario["assertions"]:
            require(assertion["kind"] in ASSERTIONS, f"{sid}: unknown assertion kind {assertion['kind']}")
            require(bool(assertion.get("question")), f"{sid}/{assertion['id']}: which question does it answer?")
        roles = [c["role"] for c in scenario["candidates"]]
        require("reference" in roles and "near_miss" in roles, f"{sid}: needs a reference and a near-miss")
        exercised: set[str] = set()
        for candidate in scenario["candidates"]:
            label = f"{sid}/{candidate['file']}"
            require(candidate["role"] in ROLES, f"{label}: role")
            path = (root / candidate["file"]).resolve()
            require(path.is_relative_to(root) and path.is_file(), f"{label}: missing file")
            verdict = spec_oracle(path)
            expected_code = candidate.get("spec_oracle", "valid")
            if expected_code == "valid":
                require(verdict["valid"], f"{label}: the reference oracle refuses it: {verdict['errors']}")
            else:
                require(not verdict["valid"] and any(e.get("code") == expected_code for e in verdict["errors"]),
                        f"{label}: the reference oracle must refuse with {expected_code}, got {verdict}")
                refused += 1
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            failed = {aid for aid, problems in judge(doc, scenario["assertions"], root).items() if problems}
            declared = set(candidate.get("violates", []))
            require(declared <= known, f"{label}: violates an unknown assertion")
            if candidate["role"] in ("reference", "variant"):
                require(not declared, f"{label}: a correct candidate declares no violation")
            if candidate["role"] == "near_miss":
                require(bool(candidate.get("plausible_because")), f"{label}: say why it is plausible")
                require(bool(declared) or bool(candidate.get("caught_by_behaviour")),
                        f"{label}: a near-miss names the assertion or the behaviour that rejects it")
            # Red where declared, green everywhere else: a judge that rejects
            # everything is as useless as one that accepts everything.
            require(failed == declared, f"{label}: expected violations {sorted(declared)}, judged {sorted(failed)}")
            exercised |= declared
            judged += 1
            controls += len(declared)
        unproven = known - exercised
        require(not unproven, f"{sid}: no near-miss turns {sorted(unproven)} red, so nothing shows it can fail")
    for contract in contracts:
        require(not CONTRACT_FIELDS - contract.keys(), f"{contract['id']}: missing fields")
        require(contract["status"] == "UNQUALIFIED_PRODUCT_CONTRACT", f"{contract['id']}: status")
        require("candidates" not in contract and "assertions" not in contract,
                f"{contract['id']}: an unqualified contract carries no static proof")
    for gap in gaps:
        require({"id", "title", "owner", "law", "expected", "observed", "reproduce", "baseline"} <= gap.keys(),
                f"{gap['id']}: missing fields")
        require(gap["baseline"] == "expected_fail", f"{gap['id']}: a retained gap stays red until it is fixed")
    return {"scenarios": len(scenarios), "candidates_judged": judged, "negative_controls": controls,
            "refused_by_reference_oracle": refused, "product_contracts_unqualified": len(contracts),
            "retained_gaps": len(gaps), "hot_promotion": False,
            "qualification": "static meaning only; no engine ran, no model was called, nothing here is a runtime proof"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario")
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    try:
        if args.candidate:
            require(bool(args.scenario), "--candidate needs --scenario")
            scenario = next(s for s in load()["scenarios"] if s["id"] == args.scenario)
            verdict = judge(yaml.safe_load(args.candidate.read_text(encoding="utf-8")), scenario["assertions"])
            print(json.dumps({"scenario": args.scenario, "accepted": not any(verdict.values()),
                              "violations": {k: v for k, v in verdict.items() if v}}, indent=2, ensure_ascii=False))
            return 1 if any(verdict.values()) else 0
        print(json.dumps(validate(), indent=2))
        return 0
    except (JudgeError, KeyError, TypeError, OSError, StopIteration, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"complex goldens FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
