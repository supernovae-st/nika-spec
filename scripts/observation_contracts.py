# SPDX-License-Identifier: Apache-2.0
"""Pure admission of adapter-dependent conformance data; never an engine verdict.

These closed contracts describe observations at four doors. This module has no
process, socket, provider or engine imports. Valid data still needs an adapter.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

DOORS = {
    "expected-approval.json": "approval-session-v1",
    "expected-http.json": "http-transport-v1",
    "expected-compose.json": "compose-intrinsic-v1",
    "expected-export.json": "secret-export-v1",
}
LAWS = {
    "approval-session-v1": "spec/10-authority.md#the-two-judges-that-remain",
    "http-transport-v1": "stdlib/builtins-v0.1.md#nikafetch",
    "compose-intrinsic-v1": "stdlib/builtins-v0.1.md#nikacompose--self-check-a-drafted-workflow-agent-loops-only",
    "secret-export-v1": "spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification",
}
SURFACES = ["stdout", "stderr", "journal", "trace-outputs"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, required, optional=()):
    require(type(value) is dict, "expected an object")
    require(set(required) <= value.keys(), "missing required fields")
    require(value.keys() <= set(required) | set(optional), "unknown fields")


def choice(value, allowed):
    require(type(value) is str and value in allowed, "unknown enum value")


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, "expected a bounded integer")
    require(value <= 1_000_000, "integer exceeds fixture bound")


def boolean(value):
    require(type(value) is bool, "expected a boolean")


def text(value):
    require(type(value) is str and bool(value), "expected nonempty text")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON member")
        result[key] = value
    return result


def invalid_number(value):
    raise ValueError("non-integer or non-JSON number in observation contract")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                      parse_float=invalid_number, parse_constant=invalid_number)


def fixture_file(directory, name):
    text(name)
    path = PurePosixPath(name)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in name,
            "fixture paths must be portable and confined")
    require(str(path) == name and name not in {".", ""}, "noncanonical fixture path")
    resolved = directory / name
    require(not any((directory / Path(*path.parts[:i])).is_symlink()
                    for i in range(1, len(path.parts) + 1)), "symlink fixture path")
    require(resolved.is_file(), "missing fixture input")
    require(bool(resolved.read_text(encoding="utf-8").strip()), "empty fixture input")


def approval(given, observed):
    fields(given, {"decision", "operator_store", "project", "lineage", "answer",
                   "now_ms", "expires_ms", "effect_path"})
    choice(given["decision"], {"consumed", "unproven", "fresh"})
    choice(given["operator_store"], {"same", "other"})
    choice(given["project"], {"same", "relocated"})
    choice(given["lineage"], {"verified", "waived", "historical-unbound"})
    choice(given["answer"], {"none", "affirmative", "denied"})
    integer(given["now_ms"]); integer(given["expires_ms"])
    require(given["now_ms"] < given["expires_ms"], "these cases require an unexpired ticket")
    require(given["effect_path"] == "out/approved.txt", "unknown effect target")
    fields(observed, {"reuse", "fresh_ticket_required", "new_decisions", "gated_effects"})
    choice(observed["reuse"], {"refused", "not-requested"})
    boolean(observed["fresh_ticket_required"])
    integer(observed["new_decisions"]); integer(observed["gated_effects"])
    if given["decision"] in {"consumed", "unproven"}:
        require(given["answer"] == "none", "reuse case must supply no fresh decision")
        require(observed == {"reuse": "refused", "fresh_ticket_required": True,
                             "new_decisions": 0, "gated_effects": 0},
                "a consumed or unproven decision grants no effect")
    else:
        require(given["lineage"] == "verified" and given["answer"] != "none",
                "fresh control needs a bound ticket and an explicit answer")
        require(observed == {"reuse": "not-requested", "fresh_ticket_required": False,
                             "new_decisions": 1,
                             "gated_effects": int(given["answer"] == "affirmative")},
                "fresh approval and denial must be distinguished")


def policy_valid(policy):
    if type(policy) is not dict or set(policy) != {"accept"}:
        return False
    values = policy["accept"]
    return (type(values) is list and 1 <= len(values) <= 16
            and all(type(v) is int and 200 <= v <= 599 for v in values)
            and len(set(values)) == len(values))


def route(value):
    if value is None:
        return None
    text(value)
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.hostname in {"example.test", "final.example.test"},
            "transport fixture routes must use reserved mock HTTPS hosts")
    require(parsed.port is None, "fixture route has no host port")
    return urlunsplit((parsed.scheme, parsed.hostname, parsed.path, "", ""))


def http(given, observed):
    fields(given, {"method", "via", "response", "mode", "retry", "keyed", "fault",
                   "responses", "sibling"})
    choice(given["method"], {"GET", "HEAD", "POST"})
    choice(given["via"], {"workflow", "agent"})
    choice(given["mode"], {"raw", "jq"})
    integer(given["retry"]); require(given["retry"] <= 2, "unbounded retry fixture")
    boolean(given["keyed"]); boolean(given["sibling"])
    choice(given["fault"], {"none", "invalid-policy", "transport", "permission", "ssrf",
                            "tls", "redirect-limit", "body-limit", "extraction"})
    policy = given["response"]
    if given["fault"] == "invalid-policy":
        require(not policy_valid(policy), "invalid-policy case contains a valid policy")
    else:
        require(policy is None or policy_valid(policy), "invalid response policy")
    replies = given["responses"]
    require(type(replies) is list and len(replies) <= 3, "invalid mock response sequence")
    for response in replies:
        fields(response, {"status", "final_url", "body", "headers"})
        integer(response["status"]); require(200 <= response["status"] <= 599, "invalid HTTP status")
        route(response["final_url"])
        require(type(response["body"]) is str, "mock body must be text")
        require(type(response["headers"]) is dict and all(type(k) is str and type(v) is str
                for k, v in response["headers"].items()), "invalid mock headers")
    require(all(300 <= response["status"] <= 399 for response in replies[:-1]),
            "only redirect responses precede the final response")
    fields(observed, {"outcome", "requests", "attempts", "output", "error", "sibling"})
    choice(observed["outcome"], {"success", "failure", "refused"})
    integer(observed["requests"])
    if observed["attempts"] is not None:
        integer(observed["attempts"])
    choice(observed["sibling"], {"retained", "quarantined", "not-requested"})
    if not given["sibling"]:
        require(observed["sibling"] == "not-requested", "sibling assertion without a sibling")
    fault = given["fault"]
    if fault in {"invalid-policy", "permission", "ssrf"}:
        require(not replies and observed["requests"] == 0, "pre-transport refusal sends no request")
        require(observed["outcome"] == "refused" and observed["attempts"] is None,
                "pre-transport refusal makes no invocation-attempt assertion")
    else:
        require(observed["requests"] == (len(replies) or 1) and observed["attempts"] == 1,
                "these bounded cases observe one attempt and every mock transport request")
    if fault in {"none", "extraction"}:
        require(bool(replies), "status case needs a received response")
    else:
        require(not replies, "fault case must not fabricate a received status")
    final = replies[-1] if replies else None
    accepted = final is not None and ((200 <= final["status"] <= 299) if policy is None
                                     else final["status"] in policy["accept"])
    success = fault == "none" and accepted
    if success:
        require(given["mode"] == "raw", "successful extraction is raw in this contract version")
        require(observed["outcome"] == "success" and observed["error"] is None,
                "accepted status is success, never a recovered error")
        if policy is None:
            require(observed["output"] == final["body"], "legacy raw body shape changed")
        else:
            fields(observed["output"], {"status_code", "url", "body"})
            require(observed["output"]["status_code"] == final["status"], "wrong observed status")
            require(type(observed["output"]["status_code"]) is int, "status must be an integer")
            require(observed["output"]["url"] == route(final["final_url"]),
                    "unknown or final route was replaced or disclosed")
            require(given["mode"] == "raw", "successful jq extraction needs a separate contract extension")
            require(observed["output"]["body"] == final["body"], "wrong extracted body")
        if given["sibling"]:
            require(observed["sibling"] == "retained", "successful sibling was quarantined")
    else:
        require(observed["outcome"] != "success" and observed["output"] is None,
                "failure cannot become an observation")
        if fault not in {"invalid-policy", "permission", "ssrf"}:
            require(observed["outcome"] == "failure", "received failure is not a pre-transport refusal")
        fields(observed["error"], {"code", "status_code", "accepted", "transient"})
        require(observed["error"]["code"] == ("NIKA-BUILTIN-FETCH-001" if fault in {"none", "extraction"} else None),
                "received status and extraction failures keep their diagnostic")
        require(observed["error"]["status_code"] == (final["status"] if final else None),
                "missing received status or fabricated transport status")
        expected_accept = policy["accept"] if policy_valid(policy) and final else None
        require(observed["error"]["accepted"] == expected_accept, "wrong accepted-status evidence")
        transient = observed["error"]["transient"]
        require(transient is None or type(transient) is bool, "invalid transient observation")
        if given["method"] == "POST" and not given["keyed"]:
            require((transient is None or transient is False) and given["retry"] == 0,
                    "keyless effects cannot be blindly retried")
        elif fault == "none" and final is not None and 400 <= final["status"] <= 599:
            status_transient = final["status"] >= 500 or final["status"] in {408, 429}
            require(transient is None or transient is status_transient,
                    "status transient assertion contradicts the normative table")
        if given["sibling"]:
            require(observed["sibling"] == "quarantined", "unhandled failure retains quarantine")
    if fault == "extraction":
        require(given["mode"] == "jq" and accepted, "extraction pair needs an accepted status")


def compose(given, observed):
    fields(given, {"case", "child"})
    choice(given["case"], {"pure", "core-invalid", "missing-child", "effectful", "secret-flow", "capability-escape"})
    require(given["child"] == ("absent-child.nika" if given["case"] == "missing-child" else None),
            "unexpected child fixture")
    fields(observed, {"valid", "child_reads", "draft_effects", "secret_findings", "capability_escapes",
                      "certificate", "saved_check"})
    boolean(observed["valid"]); boolean(observed["certificate"])
    integer(observed["child_reads"]); integer(observed["draft_effects"])
    choice(observed["secret_findings"], {"zero", "positive"})
    choice(observed["capability_escapes"], {"zero", "positive"})
    choice(observed["saved_check"], {"not-requested", "NIKA-COMP-001"})
    require(observed["valid"] == (given["case"] != "core-invalid"), "valid means parsing and Core only")
    require(observed["child_reads"] == observed["draft_effects"] == 0,
            "self-check neither resolves children nor executes drafts")
    require(observed["secret_findings"] == ("positive" if given["case"] == "secret-flow" else "zero"),
            "secret report must remain separate from valid")
    require(observed["capability_escapes"] == ("positive" if given["case"] == "capability-escape" else "zero"),
            "capability report must remain separate from valid")
    require(observed["certificate"], "certificate summary must be observed")
    require(observed["saved_check"] == ("NIKA-COMP-001" if given["case"] == "missing-child" else "not-requested"),
            "in-memory and file-aware doors must remain distinct")


def export(given, observed):
    fields(given, {"case", "secret", "public_sentinel"})
    choice(given["case"], {"derived", "identity", "direct"})
    require(given["secret"] == "synthetic-conformance-secret-7f29", "only the declared synthetic secret is allowed")
    require(given["public_sentinel"] == "public-control", "missing public control")
    fields(observed, {"allowed_outcomes", "derived_value", "secret_occurrences", "surfaces", "public_sentinel", "refusal_code"})
    require(observed["allowed_outcomes"] == (["delivered"] if given["case"] == "derived" else ["refused"] if given["case"] == "direct" else ["redacted", "refused"]),
            "derived value must cross; the secret's identity must not")
    require(observed["derived_value"] is (True if given["case"] == "derived" else None),
            "the derived export is the JSON boolean, not a string")
    require(type(observed["secret_occurrences"]) is int and observed["secret_occurrences"] == 0,
            "secret bytes are forbidden")
    require(observed["surfaces"] == SURFACES, "every named export surface must be observed")
    require(observed["public_sentinel"] == given["public_sentinel"], "masking may not erase the public control")
    require(observed["refusal_code"] == ("NIKA-SEC-007" if given["case"] == "direct" else None),
            "direct secret export keeps its check refusal")


def validate(directory: Path, claim: str) -> str:
    """Validate the entire new contract, then return its missing adapter capability.

    Does not validate Nika Core or assert an engine result. A caller must report
    UNSUPPORTED, never AGREE, until a command adapter observes this contract.
    """
    require(not directory.is_symlink(), "symlink fixture directory")
    # The caller selects the fixture root; canonicalize its deployment ancestors.
    # Every path below this admitted root is checked before its contents are read.
    directory = directory.resolve(strict=True)
    require(directory.is_dir(), "fixture root is not a directory")
    require(claim in DOORS, "unknown observation door")
    fixture_file(directory, claim)
    document = load(directory / claim)
    fields(document, {"contract_version", "law", "input", "given", "observations"}, {"note"})
    require(type(document["contract_version"]) is int and document["contract_version"] == 1,
            "unsupported observation contract version")
    capability = DOORS[claim]
    require(document["law"] == LAWS[capability], "missing or unknown owning law")
    if "note" in document:
        text(document["note"])
    expected_input = "draft.nika" if claim == "expected-compose.json" else "input.nika"
    require(document["input"] == expected_input, "wrong input for this door")
    fixture_file(directory, document["input"])
    require(not (directory / "run.json").exists(), "an observation fixture cannot also request a run")
    handlers = {"expected-approval.json": approval, "expected-http.json": http,
                "expected-compose.json": compose, "expected-export.json": export}
    handlers[claim](document["given"], document["observations"])
    if claim == "expected-compose.json" and document["given"]["case"] == "missing-child":
        require(not (directory / "absent-child.nika").exists(), "missing-child premise is false")
    return capability
