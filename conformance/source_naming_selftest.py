#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Table-driven selftest for the lexical source-name owner.

Proves the 01 §File naming matrix, the project schema's arm[].workflow
references, and the on-disk positive fixtures.
Does no filesystem I/O inside classify_basename / logical_stem.
Exit 0 green · 1 red.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
from source_naming import (  # noqa: E402
    CANONICAL_SUFFIX,
    KIND_NOT_PROGRAM,
    KIND_PROGRAM,
    classify_basename,
    classify_path,
    iter_program_files,
    logical_stem,
    program_filename,
    template_source_path,
)

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


cases = yaml.safe_load((HERE / "source-naming" / "cases.yaml").read_text())["cases"]
law("declarative case table is non-empty", len(cases) >= 16)

for row in cases:
    name = row["name"]
    want = row["kind"]
    got = classify_path(name)
    law(f"classify {name!r} → {want}", got == want)
    if want == KIND_PROGRAM:
        stem = row.get("stem")
        base = name.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        law(f"stem {name!r} → {stem}", logical_stem(base) == stem)
    elif "/" not in name and not name.endswith("/") and "://" not in name:
        law(f"no stem for {name!r}", logical_stem(name) is None)

# The full project schema must apply the same lexical naming contract to
# workflow references. Filesystem existence and owned-relative admission
# remain the engine's job, as they do for classify_path above.
project_schema = json.loads((HERE.parent / "schemas" / "project.schema.json").read_text())
Draft202012Validator.check_schema(project_schema)
project_validator = Draft202012Validator(project_schema)

for row in cases:
    project = {
        "nika": "schema-test",
        "arm": [{"workflow": row["name"], "cadence": "0 9 * * *"}],
    }
    errors = list(project_validator.iter_errors(project))
    valid = row["kind"] == KIND_PROGRAM
    law(f"project arm workflow {row['name']!r} valid={valid}", (not errors) == valid)
    if not valid:
        law(f"project refusal targets workflow name {row['name']!r}",
            len(errors) == 1 and list(errors[0].absolute_path) == ["arm", 0, "workflow"]
            and errors[0].validator == "pattern")

law("nika.yaml remains a valid project configuration without beats",
    project_validator.is_valid({"nika": "schema-test", "traces": {"keep": "30d"}}))
for data_path in ("nika.yaml", "data.yaml", "data.yml"):
    law(f"project inputs preserve YAML data path {data_path!r}",
        project_validator.is_valid({
            "nika": "schema-test",
            "arm": [{"workflow": "workflows/nightly.nika", "cadence": "0 9 * * *",
                     "inputs": {"source": data_path}}],
        }))

law("canonical suffix is lowercase .nika", CANONICAL_SUFFIX == ".nika")
law("program_filename keeps extra dots", program_filename("support.v2") == "support.v2.nika")
law("template path uses canonical suffix", template_source_path("chain") == "templates/chain.nika")
try:
    program_filename("")
    law("empty stem refused", False)
except ValueError:
    law("empty stem refused", True)

# Hostile bytes stay not-program without being decoded as allowed names.
law("embedded NUL is not a program", classify_basename("foo.nika\x00") == KIND_NOT_PROGRAM)
law("DEL is not a program", classify_basename("foo.nika\x7f") == KIND_NOT_PROGRAM)
law("uppercase suffix is not a program", classify_basename("foo.NIKA") == KIND_NOT_PROGRAM)
law("project basename is not a program", classify_basename("nika.yaml") != KIND_PROGRAM)
law("URI is not a filename", classify_path("file:///tmp/foo.nika") == KIND_NOT_PROGRAM)
law("HTTP URI is not a filename", classify_path("https://example.com/foo.nika") == KIND_NOT_PROGRAM)
law("owned-relative policy is not this module", classify_path("../foo.nika") == KIND_PROGRAM)
law("absolute lexical program is still a basename program", classify_path("/absolute/foo.nika") == KIND_PROGRAM)

positive = HERE / "source-naming" / "positive"
found = {p.name: p for p in iter_program_files(positive)}
law("on-disk canonical.nika is a program file", "canonical.nika" in found)
law("on-disk support.v2.nika is a program file", "support.v2.nika" in found)
law("support.v2 stem does not drop v2", logical_stem("support.v2.nika") == "support.v2")
law("positive dir yields only program files", all(classify_basename(n) == KIND_PROGRAM for n in found))
law("iter_program_files skips directories", all(p.is_file() for p in found.values()))

# Parser fixtures must remain input.yaml and must not be harvested as programs.
core_envelope = HERE / "tests" / "core" / "envelope" / "001-valid-minimal"
law("static parser fixture stays input.yaml", (core_envelope / "input.yaml").is_file())
law("parser fixture is not a program filename", classify_basename("input.yaml") == KIND_NOT_PROGRAM)

bad = [n for n, ok in CHECKS if not ok]
print(f"source-naming selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
