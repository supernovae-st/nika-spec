#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Rehearse the composed goldens offline on an explicitly supplied Nika engine.

Exact inputs go in; outputs AND effects are judged: which tasks started, which
files exist afterwards, the exit code and the refusal code. A correct final
answer with a stray write in an unchosen branch is a failure here.

    python3 eval/hot/complex/behaviour.py --engine /path/to/nika [--receipt out.json]

What this proves: the deterministic membrane each workflow draws around its
model calls, on that one engine build. What it does not prove: model quality
(model tasks are replaced by stated outputs, including hostile ones), any other
engine, live connectors, or anything listed under `product_contracts`.

Nothing here reaches a network, a provider or a program: a candidate that needs
one is judged statically and its engine check is recorded, and it is never run.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from judge import ROOT, JudgeError, load, require, semantic_changes

CORPUS = ROOT  # `--root` points a selftest at a corrupted copy

SAFE_TOOLS = {"nika:jq", "nika:assert", "nika:validate", "nika:read", "nika:write", "nika:prompt", "nika:decide"}
TIMEOUT = 60


def isolated_env(home: Path) -> dict:
    # No inherited variable: no provider key, no webhook, no ambient model seat.
    return {"HOME": str(home), "NIKA_KEYCHAIN": "off", "PATH": "/usr/bin:/bin"}


def local_only(doc: dict) -> str | None:
    """Why this candidate may not be executed here, or None when it is safe to run."""
    if doc.get("model") != "mock/echo":
        return "the envelope model is not mock/echo"
    if doc.get("secrets"):
        return "it reads a secret"
    permits = doc.get("permits") or {}
    if set(permits) - {"tools", "fs"}:
        return f"it declares {sorted(set(permits) - {'tools', 'fs'})} authority"
    for kind, prefix in (("read", "./fixtures/"), ("write", "./out/")):
        for entry in (permits.get("fs") or {}).get(kind, []) or []:
            if not str(entry).startswith(prefix) or ".." in str(entry):
                return f"fs.{kind} `{entry}` leaves {prefix}"
    for task_id, task in doc["tasks"].items():
        if "exec" in task:
            return f"`{task_id}` runs a program"
        if "invoke" in task and task["invoke"].get("tool") not in SAFE_TOOLS:
            return f"`{task_id}` invokes {task['invoke'].get('tool') or 'a child workflow'}"
        for verb in ("infer", "agent"):
            if verb in task and task[verb].get("model", "mock/echo") != "mock/echo":
                return f"`{task_id}` pins a non-mock model"
        if "agent" in task and set(task["agent"].get("tools") or []) - {"nika:done"}:
            return f"`{task_id}` grants tools to an agent"
    return None


def with_stubs(doc: dict, stubs: dict) -> dict:
    """Replace a model task by its stated output. Every edge, guard and failure route stays the candidate's."""
    doc = copy.deepcopy(doc)
    for task_id, value in stubs.items():
        task = doc["tasks"].get(task_id)
        if task is None:
            continue  # a differently built candidate has no such task; its own mock output stands
        for verb in ("infer", "agent"):
            task.pop(verb, None)
        task.pop("exec", None)
        task["invoke"] = {"tool": "nika:jq", "args": {"input": value, "expression": "."}}
    return doc


class Engine:
    def __init__(self, path: str):
        resolved = shutil.which(path)
        require(resolved is not None, "engine unavailable; nothing was rehearsed")
        self.path = resolved
        self.version = subprocess.check_output([resolved, "--version"], text=True, timeout=TIMEOUT).strip()
        self.sha256 = hashlib.sha256(Path(resolved).read_bytes()).hexdigest()

    def call(self, argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
        home = cwd / ".home"
        home.mkdir(exist_ok=True)
        return subprocess.run([self.path, *argv], cwd=cwd, env=isolated_env(home), capture_output=True,
                              text=True, timeout=TIMEOUT, check=False)

    def check_report(self, path: Path) -> dict:
        """{"verdict": `valid` or the refusal codes joined by `+`, "hints": the advisory kinds}.

        An advisory is not a verdict: the file is still admitted and still runs. It is recorded because a
        candidate the engine can only WARN about is a different fact from one it says nothing about.
        """
        with tempfile.TemporaryDirectory(prefix="complex-check-") as temp:
            shutil.copy(path, Path(temp) / path.name)
            result = self.call(["check", "--json", "--native-strict", path.name], Path(temp))
        report = json.loads(result.stdout)
        codes = sorted({f["code"] for f in report["findings"] if f.get("severity") == "error"})
        return {"verdict": "valid" if report["verdicts"]["valid"] else "+".join(codes),
                "hints": sorted({h["kind"] for h in report.get("hints", []) if h.get("kind")})}

    def check(self, path: Path) -> str:
        return self.check_report(path)["verdict"]


def frames(stdout: str) -> list[dict]:
    rows = []
    for line in stdout.splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"kind": "unparsed", "text": line[:200]})
    return rows


def observe(result: subprocess.CompletedProcess, directory: Path, before: set[Path]) -> dict:
    events = frames(result.stdout)
    settled = next((e for e in reversed(events) if e.get("kind") == "run_settled"), {})
    refusal = next((e for e in events if "kind" not in e and "error" in e), {})
    started = [field["value"] for e in events if e.get("kind") == "task_started"
               for field in e.get("fields", []) if field["key"] == "task"]
    written = {}
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if path.is_file() and path not in before and relative.parts[0] not in (".nika", ".home"):
            written[str(relative)] = path.read_text(encoding="utf-8", errors="replace")
    return {"exit": result.returncode, "status": settled.get("status"), "outputs": settled.get("outputs") or {},
            "error_code": (settled.get("error") or refusal.get("error") or {}).get("code"),
            "tasks_started": sorted(set(started)), "files_written": written}


def compare(expect: dict, seen: dict, rename: dict) -> list[str]:
    """Every way the observation departs from the contract; an empty list is a pass."""
    name = lambda task: rename.get(task, task)  # noqa: E731
    problems = []
    for key in ("exit", "status", "error_code"):
        if key in expect and seen[key] != expect[key]:
            problems.append(f"{key}: expected {expect[key]!r}, observed {seen[key]!r}")
    for key, value in expect.get("outputs", {}).items():
        if seen["outputs"].get(key, "<absent>") != value:
            problems.append(f"output `{key}`: expected {value!r}, observed {seen['outputs'].get(key, '<absent>')!r}")
    for key, allowed in expect.get("outputs_in", {}).items():
        if seen["outputs"].get(key, "<absent>") not in allowed:
            problems.append(f"output `{key}`: expected one of {allowed!r}, observed {seen['outputs'].get(key, '<absent>')!r}")
    if "outputs_exact" in expect and seen["outputs"] != expect["outputs_exact"]:
        problems.append(f"outputs: expected exactly {expect['outputs_exact']!r}, observed {seen['outputs']!r}")
    if "files_written" in expect and seen["files_written"] != expect["files_written"]:
        problems.append(f"files: expected exactly {expect['files_written']!r}, observed {seen['files_written']!r}")
    if "files_written_any_of" in expect and seen["files_written"] not in expect["files_written_any_of"]:
        problems.append(f"files: observed {seen['files_written']!r}, which is none of the constant destinations")
    if "tasks_started" in expect and seen["tasks_started"] != sorted(name(t) for t in expect["tasks_started"]):
        problems.append(f"tasks started: expected {expect['tasks_started']!r}, observed {seen['tasks_started']!r}")
    for task in expect.get("tasks_not_started", []):
        if name(task) in seen["tasks_started"]:
            problems.append(f"`{name(task)}` started and must not have")
    return problems


def rehearse(engine: Engine, candidate: Path, case: dict, rename: dict) -> tuple[list[str], list[dict]]:
    """Run one case (one or several steps) in a fresh directory; return (problems, observations)."""
    doc = yaml.safe_load(candidate.read_text(encoding="utf-8"))
    reason = local_only(doc)
    require(reason is None, f"{candidate.name}: refusing to execute, {reason}")
    stubs = {rename.get(task, task): value for task, value in case.get("stubs", {}).items()}
    steps = case.get("steps") or [{"answers": case.get("answers", {}), "expect": case["expect"]}]
    problems, observations = [], []
    with tempfile.TemporaryDirectory(prefix="complex-behaviour-") as temp:
        directory = Path(temp).resolve()
        fixtures = candidate.parent / "fixtures"
        if fixtures.is_dir():
            shutil.copytree(fixtures, directory / "fixtures")
        (directory / "fixtures").mkdir(exist_ok=True)
        for relative, text in case.get("files", {}).items():
            (directory / relative).write_text(text, encoding="utf-8")
        for relative, payload in case.get("binary_files", {}).items():
            (directory / relative).write_bytes(bytes.fromhex(payload))
        source = yaml.safe_dump(with_stubs(doc, stubs), sort_keys=False, allow_unicode=True)
        workflow = directory / "candidate.nika.yaml"
        trace = None
        for index, step in enumerate(steps):
            for old, new in step.get("mutate", []):
                require(source.count(old) == 1, f"{case['id']}: mutation `{old}` must apply exactly once")
                source = source.replace(old, new)
            workflow.write_text(source, encoding="utf-8")
            before = {p for p in directory.rglob("*") if p.is_file()}
            argv = ["run", workflow.name, "--json"]
            if len(steps) == 1:
                argv.append("--no-trace-file")
            if step.get("resume"):
                require(trace is not None, f"{case['id']}: nothing to resume from")
                argv += ["--resume", str(trace)]
            for key, value in case.get("vars", []):
                argv += ["--var", f"{key}={value}"]
            for task, value in step.get("answers", {}).items():
                argv += ["--answer", f"{rename.get(task, task)}={json.dumps(value)}"]
            seen = observe(engine.call(argv, directory), directory, before)
            traces = sorted((directory / ".nika/traces").glob("*.ndjson")) if (directory / ".nika/traces").is_dir() else []
            trace = traces[-1] if traces else trace
            observations.append(seen)
            problems += [f"step {index + 1}: {p}" if len(steps) > 1 else p for p in compare(step["expect"], seen, rename)]
    return problems, observations


def refused_run(engine: Engine, candidate: Path, spec: dict) -> tuple[list[str], dict]:
    """A REFUSED candidate, run exactly as written: the refusal must hold at run too, before any task,
    and leave nothing behind. An engine that admits the file fails here by running it."""
    reason = local_only(yaml.safe_load(candidate.read_text(encoding="utf-8")))
    require(reason is None, f"{candidate.name}: refusing to execute, {reason}")
    with tempfile.TemporaryDirectory(prefix="complex-refused-") as temp:
        directory = Path(temp).resolve()
        shutil.copy(candidate, directory / "candidate.nika.yaml")  # the original bytes, never a re-serialisation
        before = {p for p in directory.rglob("*") if p.is_file()}
        argv = ["run", "candidate.nika.yaml", "--json", "--no-trace-file"]
        for task, value in spec.get("answers", {}).items():
            argv += ["--answer", f"{task}={json.dumps(value)}"]
        seen = observe(engine.call(argv, directory), directory, before)
    return compare(spec["expect"], seen, {}), seen


def fact_holds(engine: Engine, corpus: dict, fact: dict, root: Path) -> bool:
    """A fact recorded about a retained gap. It is asserted, so that the gap cannot drift unnoticed."""
    if fact["kind"] == "engine_check":
        return engine.check(root / fact["file"]) == fact["verdict"]
    if fact["kind"] == "engine_hint":
        return fact["hint"] in engine.check_report(root / fact["file"])["hints"]
    if fact["kind"] == "behaviour_rejects":
        scenario = next(s for s in corpus["scenarios"] if any(c["id"] == fact["case"] for c in s["behaviour"]))
        case = next(c for c in scenario["behaviour"] if c["id"] == fact["case"])
        problems, _ = rehearse(engine, root / fact["candidate"], case, {})
        return bool(problems) and all(any(needle in p for p in problems) for needle in fact.get("because", []))
    raise JudgeError(f"unknown fact kind {fact['kind']!r}")


def compile_door(engine: Engine, case: dict, root: Path) -> tuple[list[str], dict]:
    expect, problems = case["expect"], []
    with tempfile.TemporaryDirectory(prefix="complex-compile-") as temp:
        directory = Path(temp).resolve()
        for name, source in case.get("existing", {}).items():
            shutil.copy(root / source, directory / name)
        digests = {n: hashlib.sha256((directory / n).read_bytes()).hexdigest() for n in case.get("existing", {})}
        result = engine.call(case["argv"], directory)
        try:
            outcome = json.loads(result.stdout)
        except json.JSONDecodeError:
            outcome = {}
        if result.returncode != expect["exit"]:
            problems.append(f"exit: expected {expect['exit']}, observed {result.returncode}")
        for key in ("status", "candidate", "written"):
            if key in expect and outcome.get(key, "<absent>") != expect[key]:
                problems.append(f"{key}: expected {expect[key]!r}, observed {str(outcome.get(key, '<absent>'))[:80]!r}")
        for name in expect.get("unchanged", []):
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digests[name]:
                problems.append(f"`{name}` was modified")
        for name in expect.get("absent", []):
            if (directory / name).exists():
                problems.append(f"`{name}` was written")
        edit = expect.get("semantic_changes")
        first_line = None
        if edit and (directory / edit["candidate"]).is_file():
            base = yaml.safe_load((directory / edit["base"]).read_text(encoding="utf-8"))
            text = (directory / edit["candidate"]).read_text(encoding="utf-8")
            first_line = text.splitlines()[0] if text else ""
            changed = sorted(semantic_changes(base, yaml.safe_load(text)))
            if changed != sorted(edit["equals"]):
                problems.append(f"semantic changes: expected exactly {edit['equals']}, observed {changed}")
        elif edit:
            problems.append(f"`{edit['candidate']}` was not written")
    return problems, {"exit": result.returncode, "status": outcome.get("status"), "first_line": first_line}


def gap(engine: Engine, corpus: dict, row: dict, door: dict, root: Path) -> bool:
    """True when the EXPECTED behaviour is now observed, i.e. the gap closed."""
    probe = row["reproduce"]
    if probe["kind"] == "engine_check":
        return probe["expect_code"] in engine.check(root / probe["file"])
    if probe["kind"] == "behaviour":
        scenario = next(s for s in corpus["scenarios"] if any(c["id"] == probe["case"] for c in s["behaviour"]))
        case = next(c for c in scenario["behaviour"] if c["id"] == probe["case"])
        problems, _ = rehearse(engine, root / probe["candidate"], case, {})
        return not problems
    if probe["kind"] == "compile_door":
        # Read the expected header FROM the base: a licence tag typed into this corpus would be read by
        # licence scanners as the corpus file's own tag.
        header = (root / probe["expect_first_line_of"]).read_text(encoding="utf-8").splitlines()[0]
        return door[probe["case"]]["first_line"] == header
    raise JudgeError(f"{row['id']}: unknown reproduce kind")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engine", required=True, help="Nika binary path or executable name")
    parser.add_argument("--receipt", type=Path, help="also write the receipt here")
    parser.add_argument("--root", type=Path, default=CORPUS, help="corpus directory (default: this one)")
    args = parser.parse_args()
    root = args.root.resolve()
    corpus = load(root)
    engine = Engine(args.engine)
    failures: list[str] = []
    receipt = {"engine": {"version": engine.version, "sha256": engine.sha256}, "spec_corpus": corpus["corpus"],
               "isolation": "env -i equivalent: HOME is a fresh directory, NIKA_KEYCHAIN=off, PATH=/usr/bin:/bin, "
                            "no provider key, mock/echo only, no network, no program",
               "scenarios": {}, "compile_door": {}, "retained_gaps": {}}
    door: dict[str, dict] = {}
    for scenario in corpus["scenarios"]:
        rows = receipt["scenarios"][scenario["id"]] = {"engine_check": {}, "engine_hints": {}, "refused_runs": {},
                                                       "cases": {}, "static_only": {}}
        for candidate in scenario["candidates"]:
            path = root / candidate["file"]
            report = engine.check_report(path)
            verdict = report["verdict"]
            rows["engine_check"][candidate["file"]] = verdict
            rows["engine_hints"][candidate["file"]] = report["hints"]
            wanted = candidate.get("engine_check", "valid")
            if verdict != wanted:
                failures.append(f"{scenario['id']}/{path.name}: engine check expected {wanted}, observed {verdict}")
            for kind in candidate.get("engine_hints_include", []):
                if kind not in report["hints"]:
                    failures.append(f"{scenario['id']}/{path.name}: the engine gives no `{kind}` advisory; it must at "
                                    "least warn about this candidate")
            for kind in candidate.get("engine_hints_exclude", []):
                if kind in report["hints"]:
                    failures.append(f"{scenario['id']}/{path.name}: the engine gives a `{kind}` advisory on a candidate "
                                    "whose route is closed")
            if "refused_run" in candidate:
                problems, seen = refused_run(engine, path, candidate["refused_run"])
                rows["refused_runs"][candidate["file"]] = {"verdict": "refused, no effect" if not problems else "NOT refused",
                                                          "problems": problems, "observed": seen}
                failures += [f"{scenario['id']}/{path.name}: run as written: {p}" for p in problems]
            reason = local_only(yaml.safe_load(path.read_text(encoding="utf-8")))
            if not candidate.get("behaviour"):
                rows["static_only"][candidate["file"]] = reason or "declared static only"
                continue
            require(reason is None, f"{path.name}: declared runnable, and {reason}")
            rejected = []
            for case in scenario["behaviour"]:
                problems, seen = rehearse(engine, path, case, candidate.get("rename", {}))
                rows["cases"].setdefault(case["id"], {})[candidate["file"]] = {
                    "verdict": "accepts" if not problems else "rejects", "problems": problems, "observed": seen}
                if problems:
                    rejected.append(case["id"])
            declared = sorted(candidate.get("caught_by_behaviour", []))
            if candidate["role"] in ("reference", "variant") and rejected:
                failures.append(f"{scenario['id']}/{path.name}: a correct candidate is rejected by {rejected}")
            if candidate["role"] == "near_miss" and sorted(rejected) != declared:
                failures.append(f"{scenario['id']}/{path.name}: expected rejection by {declared}, observed {sorted(rejected)}")
        for case in scenario.get("compile_door", []):
            problems, seen = compile_door(engine, case, root)
            door[case["id"]] = seen
            receipt["compile_door"][case["id"]] = {"verdict": "accepts" if not problems else "rejects",
                                                  "problems": problems, "observed": seen}
            failures += [f"{case['id']}: {p}" for p in problems]
    for row in corpus["retained_gaps"]:
        closed = gap(engine, corpus, row, door, root)
        facts = [dict(fact, holds=fact_holds(engine, corpus, fact, root)) for fact in row.get("facts", [])]
        receipt["retained_gaps"][row["id"]] = {"expected_behaviour_observed": closed, "baseline": row["baseline"],
                                               "facts": facts}
        if closed:  # a fixed engine must retire its baseline in the same change, or this stays red
            failures.append(f"{row['id']}: the expected behaviour is now observed: retire this gap and qualify its case")
        failures += [f"{row['id']}: a recorded fact no longer holds ({fact['says']}): re-qualify the gap"
                     for fact in facts if not fact["holds"]]
    receipt["failures"] = failures
    receipt["qualification"] = ("offline wiring and deterministic membranes on this one engine build, over a finite set "
                                "of cases; model tasks were replaced by stated outputs; no model quality, connector, HOT "
                                "or comparative claim")
    receipt["compile_capability"] = ("not measured: every rehearsed candidate is hand-authored. Only the compile_door "
                                     "cases exercise the Compile door, in its conservative exact and edit modes")
    text = json.dumps(receipt, indent=2, ensure_ascii=False)
    if args.receipt:
        args.receipt.write_text(text + "\n", encoding="utf-8")
    summary = {"engine": receipt["engine"], "scenarios": len(corpus["scenarios"]),
               "cases_run": sum(len(v) for s in receipt["scenarios"].values() for v in s["cases"].values()),
               "compile_door_cases": len(receipt["compile_door"]),
               "refused_runs": sum(len(s["refused_runs"]) for s in receipt["scenarios"].values()),
               "gap_facts_asserted": sum(len(g["facts"]) for g in receipt["retained_gaps"].values()),
               "retained_gaps_still_red": sum(1 for g in receipt["retained_gaps"].values() if not g["expected_behaviour_observed"]),
               "failures": failures, "qualification": receipt["qualification"],
               "compile_capability": receipt["compile_capability"]}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (JudgeError, KeyError, OSError, subprocess.SubprocessError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"complex behaviour FAIL: {error}", file=sys.stderr)
        sys.exit(1)
