#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Offline selftest of the reference-engine adapter (nika-engine.py).

A synthetic SPY stands in for the engine binary: it records the argv, cwd,
environment and project files it was handed, then prints a canned report.
The spy proves ROUTING and ISOLATION — the final argument, the staged bytes,
the fixture context, the closed project, the clean HOME and environment —
never a fixture's verdict: no real checker runs here, no network, no
provider. The main scenario goes through the real protocol door
(`runner.py run <fixture> --engine "<adapter>"`), from two unrelated working
directories that each carry a hostile project and registry.

    python3 conformance/adapters/nika_engine_selftest.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER = HERE / "nika-engine.py"
RUNNER = HERE.parent / "runner.py"
TESTS = HERE.parent / "tests"
F003 = TESTS / "core" / "verbs-shape" / "003-agent-with-schema-valid"
F012 = TESTS / "core" / "verbs-shape" / "012-mcp-digit-server-valid"
F_COMP = TESTS / "deep" / "composition" / "009-valid-composition"
SENTINEL = "nika-selftest-sentinel-credential"
CHECKS: list[tuple[str, bool]] = []


def law(name: str, ok: bool) -> None:
    CHECKS.append((name, bool(ok)))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


SPY = """#!{python}
import hashlib, json, os, sys, time
def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
def listing(top, limit=200):
    out = []
    for root, _dirs, names in os.walk(top):
        out += [os.path.join(root, n) for n in names]
        if len(out) > limit:
            return None  # an unbounded ambient tree is itself the finding
    return out
cwd = os.getcwd()
files = {{os.path.relpath(p, cwd): sha(p) for p in listing(cwd) or []}}
home = os.environ.get("HOME", "")
home_files = None
if home and os.path.isdir(home):
    found = listing(home)
    home_files = None if found is None else [os.path.relpath(p, home) for p in found]
target = sys.argv[-1]
rec = {{"argv": sys.argv, "cwd": cwd, "env": dict(os.environ), "files": files,
       "home_files": home_files,
       "target_sha": sha(target) if os.path.isfile(target) else None}}
with open({log!r}, "a") as fh:
    fh.write(json.dumps(rec) + "\\n")
mode = open({mode!r}).read().strip()
if mode == "clean":
    print(json.dumps({{"clean": True, "conformance": [], "findings": []}}))
elif mode == "finding":
    print(json.dumps({{"clean": False, "findings": [
        {{"code": "NIKA-SEC-004", "message": "spy finding"}}]}}))
elif mode == "nojson":
    print("no report here")
elif mode == "sleep":
    time.sleep(30)
"""


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nika-adapter-selftest-") as tmp:
        tmp = Path(tmp).resolve()
        log, mode = tmp / "spy.log", tmp / "spy.mode"
        spy = tmp / "spy-nika"
        spy.write_text(SPY.format(python=sys.executable, log=str(log), mode=str(mode)))
        spy.chmod(0o755)

        def set_mode(m: str) -> None:
            mode.write_text(m)

        def records() -> list[dict]:
            if not log.exists():
                return []
            return [json.loads(line) for line in log.read_text().splitlines()]

        # The hostile ambient world: two unrelated cwds and a HOME, each with
        # a project boundary and a registry naming a server no fixture uses.
        hostile_home = tmp / "hostile-home"
        evil = json.dumps({"mcp_servers_format": 1,
                           "servers": {"evil": {"command": "evil", "args": []}}})
        cwds = [tmp / "cwd-a", tmp / "cwd-b" / "deeper"]
        for d in (*cwds, hostile_home):
            (d / ".nika").mkdir(parents=True)
            (d / ".nika" / "mcp_servers.json").write_text(evil)
            (d / "nika.yaml").write_text("name: hostile-project\n")
            (d / "input.nika").write_text("nika: decoy\ntasks: {}\n")
        hostile_bin = tmp / "hostile-bin"
        hostile_bin.mkdir()
        env = dict(os.environ)
        # The hostile HOME hides a user site-packages; keep the suite's own
        # dependencies importable for the runner and adapter (never the spy's).
        import jsonschema
        import yaml
        deps = {str(Path(m.__file__).resolve().parents[1]) for m in (yaml, jsonschema)}
        env["PYTHONPATH"] = os.pathsep.join(
            sorted(deps) + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        env.update({"NIKA_BIN": str(spy), "HOME": str(hostile_home),
                    "PATH": f"{hostile_bin}{os.pathsep}{env.get('PATH', '')}",
                    "OPENAI_API_KEY": SENTINEL, "ANTHROPIC_API_KEY": SENTINEL,
                    "MISTRAL_API_KEY": SENTINEL, "NIKA_CONFIG": SENTINEL,
                    "XDG_CONFIG_HOME": str(hostile_home)})
        engine = f"{shlex.quote(sys.executable)} -B {shlex.quote(str(ADAPTER))}"
        corpus = [F003, F012, F_COMP]
        corpus_before = {str(f): tree(f) for f in corpus}

        def via_runner(fixture: Path, cwd: Path) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-B", str(RUNNER), "run", str(fixture), "--engine", engine],
                cwd=cwd, env=env, capture_output=True, text=True, timeout=120)

        # ── the protocol door, from two unrelated cwds ──────────────────
        set_mode("clean")
        for cwd in cwds:
            for fixture in corpus:
                n = len(records())
                proc = via_runner(fixture, cwd)
                tag = f"{fixture.name} from {cwd.name}"
                law(f"runner PASS with a clean spy report · {tag}",
                    proc.returncode == 0 and "PASS" in proc.stdout)
                new = records()[n:]
                law(f"the engine ran exactly once · {tag}", len(new) == 1)
                if len(new) != 1:
                    continue
                r = new[0]
                target = Path(r["argv"][-1])
                project = Path(os.path.realpath(r["cwd"]))
                law(f"argv is check --json <absolute .nika> · {tag}",
                    r["argv"][1:4] == ["check", "--json", r["argv"][-1]]
                    and len(r["argv"]) == 4 and target.is_absolute()
                    and target.name == "input.nika")
                law(f"cwd is the staged project, never the caller's · {tag}",
                    Path(os.path.realpath(target)).parent == project
                    and project != Path(os.path.realpath(cwd))
                    and fixture.resolve() not in (project, *project.parents))
                law(f"staged input bytes == fixture input.yaml bytes · {tag}",
                    r["target_sha"] == sha(fixture / "input.yaml"))
                law(f"an EMPTY nika.yaml closes the project · {tag}",
                    r["files"].get("nika.yaml") == hashlib.sha256(b"").hexdigest())
                home = r["env"].get("HOME", "")
                law(f"HOME is a fresh empty dir, not the ambient one · {tag}",
                    home and Path(home).is_absolute()
                    and os.path.realpath(home) != str(hostile_home)
                    and r["home_files"] == [])
                law(f"no credential or config sentinel reaches the engine · {tag}",
                    SENTINEL not in json.dumps(r["env"])
                    and "XDG_CONFIG_HOME" not in r["env"]
                    and str(hostile_bin) not in r["env"].get("PATH", "")
                    and r["env"].get("NIKA_KEYCHAIN") == "off")
                law(f"the expected verdict never reaches the engine · {tag}",
                    "expected.json" not in r["files"])
                aux = {k: v for k, v in tree(fixture).items()
                       if k not in ("input.yaml", "expected.json")}
                staged = {k: v for k, v in r["files"].items()
                          if k not in ("input.nika", "nika.yaml")}
                law(f"exactly the fixture's auxiliaries, byte-exact · {tag}",
                    staged == aux)
                law(f"the scratch is gone after the call · {tag}",
                    not project.exists())

        law("012 stages exactly the declared 21st registry",
            (F012 / ".nika" / "mcp_servers.json").is_file())
        law("the corpus is byte-unchanged",
            {str(f): tree(f) for f in corpus} == corpus_before)

        # ── the verdict mapping and the harness errors stay as they were ─
        def direct(path: Path, m: str) -> subprocess.CompletedProcess:
            set_mode(m)
            return subprocess.run([sys.executable, "-B", str(ADAPTER), str(path)],
                                  cwd=cwds[0], env=env, capture_output=True,
                                  text=True, timeout=120)

        proc = direct(F012 / "input.yaml", "finding")
        try:
            v = json.loads(proc.stdout)
        except json.JSONDecodeError:
            v = {}
        law("a finding maps to valid:false + its code + registry category",
            proc.returncode == 0 and v.get("valid") is False
            and v.get("errors", [{}])[0].get("code") == "NIKA-SEC-004"
            and v["errors"][0].get("category") == "security_error")
        law("no JSON from the engine is exit 3 (the runner's harness_error)",
            direct(F012 / "input.yaml", "nojson").returncode == 3)
        set_mode("nojson")
        proc = via_runner(F012, cwds[1])
        law("the runner reports the silent engine as a RUNNER harness error",
            proc.returncode == 1 and "RUNNER" in proc.stdout)

        # ── synthetic fixtures: no invented registry · refusals ──────────
        synth = tmp / "synthetic"
        no_reg = synth / "no-registry"
        no_reg.mkdir(parents=True)
        (no_reg / "input.yaml").write_text(
            "nika: t\npermits:\n  tools: [\"mcp:other/do\"]\n"
            "tasks:\n  a:\n    invoke: { tool: \"mcp:other/do\" }\n")
        n = len(records())
        proc = direct(no_reg / "input.yaml", "clean")
        new = records()[n:]
        law("a mentioned server is never invented into a registry",
            proc.returncode == 0 and len(new) == 1
            and not any(k.startswith(".nika") for k in new[0]["files"]))
        linked = synth / "symlinked"
        linked.mkdir()
        (linked / "input.yaml").write_text("nika: t\ntasks: {}\n")
        (linked / "child.nika").symlink_to(hostile_home / "input.nika")
        n = len(records())
        law("a symlink in the fixture is refused before the engine runs",
            direct(linked / "input.yaml", "clean").returncode == 3
            and len(records()) == n)
        project_file = synth / "has-project"
        project_file.mkdir()
        (project_file / "input.yaml").write_text("nika: t\ntasks: {}\n")
        (project_file / "nika.yaml").write_text("name: authored\n")
        n = len(records())
        law("a fixture's own nika.yaml is a reported collision, never overwritten",
            direct(project_file / "input.yaml", "clean").returncode == 3
            and len(records()) == n)

        # ── a hung engine is bounded (in process · short timeout) ────────
        spec = importlib.util.spec_from_file_location("nika_engine_adapter", ADAPTER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        law("the adapter exposes its check timeout", hasattr(mod, "CHECK_TIMEOUT_S"))
        if hasattr(mod, "CHECK_TIMEOUT_S"):
            mod.CHECK_TIMEOUT_S = 1
            set_mode("sleep")
            saved = dict(os.environ)
            os.environ.clear()
            os.environ.update(env)
            try:
                n = len(records())
                rc = mod.main(["nika-engine.py", str(F012 / "input.yaml")])
            finally:
                os.environ.clear()
                os.environ.update(saved)
            new = records()[n:]
            law("a hung engine is exit 3 (harness_error), scratch removed",
                rc == 3 and len(new) == 1
                and not Path(new[0]["cwd"]).exists())

    bad = [name for name, ok in CHECKS if not ok]
    print(f"nika-engine adapter selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
    for name in bad:
        print(f"  ✗ {name}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
