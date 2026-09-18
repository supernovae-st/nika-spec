#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check candidate corpus integrity and static validity, never HOT quality."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
STATUSES = {
    "CANDIDATE", "COVERED", "FACTORABLE", "NEEDS_PATTERN",
    "READY_FOR_HOT_TEST", "PROMOTED_HOT", "REJECTED_FOR_HOT",
    "OPEN_WORLD", "NEEDS_WARM", "NEEDS_COLD",
}
REQUIRED = {
    "family_id", "domain", "title", "example_intent", "structure_signature",
    "patterns", "bindings", "policy_fields", "effects", "authority_class",
    "promotion_status", "proposed_path",
}


class CorpusError(ValueError):
    """An inventory declaration contradicts its data or source."""


def require(condition: bool, message: str) -> None:
    # The gate must remain active under python -O.
    if not condition:
        raise CorpusError(message)


def read_json(root: Path, name: str) -> dict:
    return json.loads((root / f"{name}.json").read_text())


def unique(rows: list, key: str, label: str) -> set:
    ids = [row[key] for row in rows]
    require(len(ids) == len(set(ids)), f"{label}: duplicate {key}")
    return set(ids)


def validate(root: Path = ROOT) -> dict:
    data = read_json(root, "families")
    families = data["families"]
    ids = unique(families, "family_id", "families")
    require(bool(ids), "families: empty inventory")
    require(data["family_count"] == len(families), "family_count drift")
    counts = dict(Counter(f["promotion_status"] for f in families))
    require(data["counts"] == counts, "status counts drift")
    require(set(data["promotion_status_enum"]) == STATUSES, "status enum drift")
    require(not counts.get("PROMOTED_HOT"), "no PROMOTED_HOT without measured evidence")
    for f in families:
        require(not REQUIRED - f.keys(), f"{f['family_id']}: required field missing")
        require(f["promotion_status"] in STATUSES, f"{f['family_id']}: unknown status")
        for key in ("patterns", "bindings", "policy_fields"):
            require(isinstance(f[key], list), f"{f['family_id']}: {key} must be a list")
        require(not any(x in f["title"].lower() for x in ("gmail-to-slack", "outlook-to-teams")),
                f"{f['family_id']}: provider-specific duplication")

    wave = read_json(root, "first-wave")
    wave_ids = unique(wave["families"], "family_id", "first-wave")
    require(wave["n"] == len(wave_ids), "first-wave count drift")
    require(wave_ids == {f["family_id"] for f in families if f["first_wave"]},
            "first-wave membership drift")
    by_id = {f["family_id"]: f for f in families}
    for row in wave["families"]:
        for key in row.keys() & by_id[row["family_id"]].keys():
            require(row[key] == by_id[row["family_id"]][key],
                    f"first-wave {row['family_id']}: {key} drift")
        require(row["hot_compile_provider_calls_expectation"] == 0 and row["check_must_run"] is True,
                f"first-wave {row['family_id']}: HOT expectation weakened")
    for name in ("families", "first-wave"):
        require(yaml.safe_load((root / f"{name}.yaml").read_text()) == read_json(root, name),
                f"{name}: YAML/JSON drift (JSON owns the data)")

    for name in ("paraphrases", "near-misses"):
        document = read_json(root, name)
        require(document["count"] == len(document["cases"]), f"{name}: count drift")
        for case in document["cases"]:
            require(case["family_id"] in ids, f"{name}: unknown family {case['family_id']}")
    goldens = read_json(root, "goldens")
    golden_ids = set()
    for key in ("positive", "negative", "edits"):
        members = unique(goldens[key], "id", f"goldens/{key}")
        require(not golden_ids & members, "golden IDs collide")
        golden_ids |= members
        require(bool(members), f"goldens/{key}: empty")
    require(goldens["byte_equality"] is False, "goldens use a semantic oracle")
    require(read_json(root, "edits")["cases"] == goldens["edits"], "edit copies drift")
    for name, key in (("patterns", "patterns"), ("composition-fixtures", "fixtures"),
                      ("wave1-decisions", "decisions")):
        unique(read_json(root, name)[key], "id", name)
    for pattern in read_json(root, "patterns")["patterns"]:
        require(set(pattern.get("unlocks", [])) <= ids, f"{pattern['id']}: unknown family")

    registry = yaml.safe_load((REPO / "canon/templates/registry.yaml").read_text())["templates"]
    audit = read_json(root, "skeleton-audit")
    skeletons = audit["skeletons"]
    require(unique(skeletons, "id", "skeleton-audit") == {r["id"] for r in registry},
            "skeleton-audit membership differs from canon registry")
    require(audit["skeleton_count"] == len(registry) == data["skeleton_recount"], "skeleton count drift")
    require(read_json(root, "wave1-decisions")["canon_skeleton_count"] == len(registry),
            "wave1-decisions skeleton count drift")
    registry_by_id = {r["id"]: r for r in registry}
    for row in skeletons:
        require(row["source"] == registry_by_id[row["id"]]["source_path"], "skeleton source drift")
        for key in ("source", "positive_fixture", "negative_fixture", "golden"):
            path = (REPO / row[key]).resolve()
            require(path.is_relative_to(REPO) and path.is_file(), f"{row['id']}: missing {key}")
        digest = "sha256:" + hashlib.sha256((REPO / row["source"]).read_bytes()).hexdigest()
        require(row["sha256_file"] == digest, f"{row['id']}: stale source digest")

    proposed = root / "proposed-skeletons"
    files = sorted(proposed.glob("*.nika.yaml"))
    require(bool(files), "proposed-skeletons: empty")
    for path in files:
        result = subprocess.run([sys.executable, str(REPO / "conformance/runner.py"), "validate", str(path)],
                                capture_output=True, text=True, check=False)
        require(result.returncode == 0, f"{path.name}: static conformance failed\n{result.stdout}{result.stderr}")

    # These are this candidate's declared branch laws, not a second CEL engine.
    # rehearsal.py verifies both cases against the actual Nika runtime.
    fallback = yaml.safe_load((proposed / "known-path-agent-fallback.nika.yaml").read_text())
    for task, op in (("known", "!="), ("investigate", "==")):
        branch = fallback["tasks"][task]
        require(branch.get("with", {}).get("classification") == "${{ tasks.classify.output }}",
                f"{task}: missing classified-state dependency")
        require(branch.get("when") == '${{ with.classification.class ' + op + ' "unknown" }}',
                f"{task}: exceptional-branch gate drift")
    return {"family_count": len(families), "status": counts, "promoted_hot": 0,
            "skeleton_count": len(skeletons), "proposed_static_valid": len(files),
            "qualification": "inventory integrity + static validity; no HOT or model-quality measurement"}


def main() -> int:
    try:
        print(json.dumps(validate(), indent=2))
        return 0
    except (CorpusError, KeyError, TypeError, OSError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"HOT inventory FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
