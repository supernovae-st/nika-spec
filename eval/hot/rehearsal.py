#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline wiring proofs on an explicitly supplied Nika engine, not HOT scores."""
import argparse
import copy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

from validate import ROOT, require


def local_only(doc):
    require(doc.get("model") == "mock/echo", "rehearsal requires mock/echo")
    permits = doc.get("permits", {})
    require(set(permits) <= {"tools", "fs"}, "rehearsal forbids network/exec permits")
    require(set(permits.get("fs", {})) <= {"read"}, "rehearsal forbids filesystem writes")
    require(set(permits.get("fs", {}).get("read", [])) <= {"./fixtures/customers.json"},
            "rehearsal reads fixture data only")
    for task in doc["tasks"].values():
        require("exec" not in task, "rehearsal forbids subprocess tasks")
        if "invoke" in task:
            require(task["invoke"].get("tool") in {"nika:jq", "nika:read", "nika:validate", "nika:assert"},
                    "rehearsal forbids external tools and child workflows")
        for verb in ("infer", "agent"):
            if verb in task:
                require(task[verb].get("model", "mock/echo") == "mock/echo", "non-mock task pin")
        if "agent" in task:
            require(task["agent"].get("tools") == ["nika:done"], "unexpected agent tools")


def run(engine, directory, doc, *, variables=(), events=False):
    local_only(doc)
    path = directory / "case.nika.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    checked = subprocess.run([engine, "check", "--json", "--native-strict", str(path)],
                             cwd=directory, capture_output=True, text=True, timeout=20)
    require(checked.returncode == 0, f"check failed: {checked.stdout}{checked.stderr}")
    command = [engine, "run", str(path), "--no-trace-file"]
    command += ["--json"] if events else ["--output", "json"]
    for key, value in variables:
        command += ["--var", f"{key}={value}"]
    return subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, help="Nika binary path or executable name")
    args = parser.parse_args()
    engine = shutil.which(args.engine)
    require(engine is not None, "engine unavailable; rehearsal was not executed")
    source = ROOT / "proposed-skeletons"
    docs = {p.stem.removesuffix(".nika"): yaml.safe_load(p.read_text()) for p in source.glob("*.nika.yaml")}
    checks = []
    with tempfile.TemporaryDirectory(prefix="nika-hot-rehearsal-") as temp:
        directory = Path(temp)
        shutil.copytree(source / "fixtures", directory / "fixtures")
        facts = docs["facts-to-draft"]
        result = run(engine, directory, facts)
        require(result.returncode == 0, f"facts-to-draft failed: {result.stderr}")
        output = json.loads(result.stdout)
        require(output["facts"] == facts["const"]["facts"] and "generated" in output,
                "generated prose changed or replaced the exact facts")
        checks.append("facts preserved separately from generated prose")

        lookup = docs["lookup-and-enrich"]
        customers = json.loads((directory / "fixtures/customers.json").read_text())
        for customer, expected in customers.items():
            result = run(engine, directory, lookup, variables=[("customer_id", customer)])
            require(result.returncode == 0 and json.loads(result.stdout)["facts"] == expected,
                    f"literal customer lookup failed: {result.stderr}")
        checks.append("exact lookup, including quotes and backslashes in the identifier")
        result = run(engine, directory, lookup, variables=[("customer_id", "absent")])
        require(result.returncode == 1 and json.loads(result.stdout).get("error", {}).get("code")
                == "NIKA-BUILTIN-ASSERT-001", "missing customer must fail, not fabricate facts")
        (directory / "fixtures/customers.json").write_text('{"CUST-1":{"name":42,"tier":"standard"}}')
        result = run(engine, directory, lookup)
        require(result.returncode == 1 and json.loads(result.stdout).get("error", {}).get("code")
                == "NIKA-BUILTIN-ASSERT-001", "invalid customer types must fail admission")
        (directory / "fixtures/customers.json").write_text("not JSON")
        result = run(engine, directory, lookup)
        require(result.returncode == 1 and "error" in json.loads(result.stdout),
                "malformed directory must fail parsing")
        (directory / "fixtures/customers.json").unlink()
        result = run(engine, directory, lookup)
        require(result.returncode == 1 and "error" in json.loads(result.stdout)
                and "facts" not in json.loads(result.stdout),
                "missing directory must fail, not recover invented facts")
        checks.append("missing customer, invalid customer types, malformed and missing directory refuse")

        for classification in ("billing", "login", "unknown"):
            doc = copy.deepcopy(docs["known-path-agent-fallback"])
            # Isolate the branch law from classifier quality. The actual branch
            # tasks and the actual mock agent remain exactly the candidate's.
            doc["tasks"]["classify"] = {"invoke": {"tool": "nika:jq", "args": {
                "input": {"class": classification}, "expression": "."}}}
            result = run(engine, directory, doc, events=True)
            require(result.returncode == 0, f"branch rehearsal failed: {result.stderr}")
            events = [json.loads(line) for line in result.stdout.splitlines()]
            started = [e for e in events if e.get("kind") == "task_started"
                       and {f["key"]: f["value"] for f in e.get("fields", [])}.get("task") == "investigate"]
            require(len(started) == int(classification == "unknown"), "agent ran on the wrong branch")
            settled = [e for e in events if e.get("kind") == "run_settled"][-1]
            require(settled["status"] == "succeeded", "branch did not settle successfully")
            require(settled["spend"]["unpriced_calls"] == int(classification == "unknown"),
                    "unexpected mock provider calls")
            checks.append(f"{classification}: agent calls={len(started)}")
    version = subprocess.check_output([engine, "--version"], text=True).strip()
    print(json.dumps({"engine": version, "checks": checks,
                      "qualification": "offline wiring only; classifier quality and HOT remain unmeasured"}, indent=2))


if __name__ == "__main__":
    main()
