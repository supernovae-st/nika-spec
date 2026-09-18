#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the consent lane's SURE-SKIP reading (spec 10 · NEP-0020 · NIKA-SEC-014).

The classical walk stops at a gate the refusal closes. That is one hop short:
03 §edge roles admits that a `with:` value edge PASSES on a skipped producer
and reads defined-`null`, so a task that only reads the value of a stage the
refusal skips still reaches its verb, and the effect is attempted on « no ».

A finite table, one shape per row, every row a small change to ONE base
workflow. Nothing here keys on a task id or a file name. A row is either

    SEC014    the reader is a PROVEN witness: the stage certainly skips, the
              reader is certainly admitted and certainly reaches its verb
    NO_CLAIM  anything less: the route is cancelled, or the proof rests on a
              verb succeeding, an expression not erroring, a fan-out iterating.
              The reference oracle only ever refuses what it proves.

The four mutants at the end neuter one guard each and must flip exactly the
rows that guard exists for; a guard no row depends on is decoration.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import deep_static  # noqa: E402
from deep_static import consent_errors  # noqa: E402

SEC014, NO_CLAIM = "SEC014", "NO_CLAIM"
ANSWER = "${{ tasks.ask.output }}"
STAGED = "${{ tasks.stage.output }}"


def base() -> dict:
    """A confirm gate, a stage the refusal skips, and a write that only READS the stage."""
    return {
        "nika": "t",
        "permits": {"tools": ["nika:prompt", "nika:jq", "nika:write"], "fs": {"write": ["./out/report.md"]}},
        "tasks": {
            "ask": {"invoke": {"tool": "nika:prompt", "args": {"message": "Publish?"}}},
            "stage": {"with": {"go": ANSWER}, "when": "${{ with.go == true }}",
                      "invoke": {"tool": "nika:jq", "args": {"input": "shown", "expression": "."}}},
            "publish": {"with": {"staged": STAGED},
                        "invoke": {"tool": "nika:write",
                                   "args": {"path": "./out/report.md", "content": "Report: ${{ with.staged }}"}}},
        },
    }


def jq(value="ok", **keys) -> dict:
    return {**keys, "invoke": {"tool": "nika:jq", "args": {"input": value, "expression": "."}}}


CASES: dict[str, tuple[dict, str]] = {}


def case(name: str, expect: str, change=None, permits=None) -> None:
    """Every shape stays a workflow an engine admits for every OTHER law, so the same
    table can be shown to an engine and only the consent verdict is under test."""
    doc = base()
    if change is not None:
        change(doc["tasks"])
    doc["permits"].update(permits or {})
    CASES[name] = (doc, expect)


def put(tasks: dict, name: str, task: dict, before: str = "publish") -> None:
    """Insert a task before `before`, keeping the authored order readable."""
    items = list(tasks.items())
    index = [key for key, _ in items].index(before)
    items.insert(index, (name, task))
    tasks.clear()
    tasks.update(items)


# ── the proven witness ───────────────────────────────────────────────────────
case("a value read of a certainly skipped stage reaches its verb", SEC014)
case("a defaulted confirm gate is the same law", SEC014,
     lambda t: t["ask"]["invoke"]["args"].update(mode="confirm", default=False))
case("an exec reader is a sink too", SEC014,
     lambda t: t.update(publish={"with": {"staged": STAGED}, "exec": {"command": ["touch", "./fired"]}}),
     permits={"exec": ["touch"]})
case("a stage that fans out is still skipped: when: is read once, before the fan-out", SEC014,
     lambda t: t["stage"].update({"with": {"go": ANSWER, "items": ["a", "b"]},
                                  "for_each": {"items": "${{ with.items }}", "max_parallel": 2}}))
case("a false LEFT operand decides before the right one is read", SEC014,
     lambda t: t["stage"].update({"with": {"go": ANSWER, "n": 3}, "when": "${{ with.go == true && with.n > 0 }}"}))
case("a chain of stages the refusal skips: the reader of the last one still runs", SEC014,
     lambda t: (put(t, "second", jq(**{"with": {"go": ANSWER, "staged": STAGED}, "when": "${{ with.go == true }}"})),
                t["publish"].update({"with": {"staged": "${{ tasks.second.output }}"}})))
case("a skip handler that also READS the value is certainly admitted", SEC014,
     lambda t: t["publish"].update(after={"stage": "skipped"}))
case("an all-four edge from an independent task closes nothing", SEC014,
     lambda t: (put(t, "other", jq()), t["publish"].update(after={"other": "terminal"})))
case("a gate that has its own success prerequisite was still answered: it is a fact", SEC014,
     lambda t: (put(t, "build", jq(), before="ask"), t["ask"].update(after={"build": "success"})))
case("a gate that only runs after a failure was still answered: it is a fact", SEC014,
     lambda t: (put(t, "build", jq(), before="ask"), t["ask"].update(after={"build": "failure"})))

# ── the route is cancelled: silence ──────────────────────────────────────────
case("a success edge on the SAME producer cancels the reader", NO_CLAIM,
     lambda t: t["publish"].update(after={"stage": "success"}))
case("a control-only success edge was always closed", NO_CLAIM,
     lambda t: t.update(publish={"after": {"stage": "success"},
                                 "invoke": {"tool": "nika:write", "args": {"path": "./out/report.md", "content": "x"}}}))
case("a cancelled intermediate cancels what reads it", NO_CLAIM,
     lambda t: (put(t, "mid", jq(**{"after": {"stage": "success"}, "with": {"staged": STAGED}})),
                t["publish"].update({"with": {"staged": "${{ tasks.mid.output }}"}})))
case("a success edge from ANOTHER stage the refusal skips cancels the reader", NO_CLAIM,
     lambda t: (put(t, "approved", jq(**{"with": {"go": ANSWER}, "when": "${{ with.go == true }}"})),
                t["publish"].update(after={"approved": "success"})))
case("a reader that gates on the answer itself is the house pattern", NO_CLAIM,
     lambda t: t["publish"].update({"with": {"staged": STAGED, "go": ANSWER}, "when": "${{ with.go == true }}"}))

# ── the proof would rest on something not proven: no claim (decision A) ──────
case("a laundering hop by success edge: the intermediate's success is never assumed", NO_CLAIM,
     lambda t: (put(t, "mid", jq(**{"with": {"staged": STAGED}})),
                t["publish"].update({"after": {"mid": "success"}, "with": {"staged": "${{ tasks.mid.output }}"}})))
case("a laundering hop by value edge: same", NO_CLAIM,
     lambda t: (put(t, "mid", jq(**{"with": {"staged": STAGED}})),
                t["publish"].update({"with": {"staged": "${{ tasks.mid.output }}"}})))
case("an independent success prerequisite may fail", NO_CLAIM,
     lambda t: (put(t, "other", jq()), t["publish"].update(after={"other": "success"})))
case("an independent failure prerequisite may succeed", NO_CLAIM,
     lambda t: (put(t, "idle", jq()), t["publish"].update(after={"idle": "failure"})))
case("a stage that also reads a verb that merely ran may be cancelled instead of skipped", NO_CLAIM,
     lambda t: (put(t, "merge", jq(), before="stage"),
                t["stage"].update({"with": {"go": ANSWER, "report": "${{ tasks.merge.output }}"}})))
case("a stage whose binding navigates may error before its when: is read", NO_CLAIM,
     lambda t: (put(t, "merge", jq(), before="stage"),
                t["stage"].update({"with": {"go": ANSWER, "report": "${{ tasks.merge.output.report }}"}})))
case("a stage that navigates the gate's own answer may error before its when: is read", NO_CLAIM,
     lambda t: t["stage"].update({"with": {"go": ANSWER, "why": "${{ tasks.ask.output.reason }}"}}))
case("an undecided LEFT operand is not a proven skip, whatever the right one says", NO_CLAIM,
     lambda t: t["stage"].update({"with": {"go": ANSWER, "n": 3}, "when": "${{ with.n > 0 && with.go == true }}"}))
case("a comparison across two classes errors at run: not a proven skip", NO_CLAIM,
     lambda t: t["stage"].update(when="${{ with.go == 'yes' }}"))
case("a reader that fans out over the null fails instead of running", NO_CLAIM,
     lambda t: (t["publish"].update(for_each={"items": "${{ with.staged }}", "max_parallel": 1}),
                t["publish"]["invoke"]["args"].update(path="./out/item-${{ index }}.md", content="${{ item }}")),
     permits={"fs": {"write": ["./out/*"]}})
case("a reader behind a condition on the skipped value is not evaluated here", NO_CLAIM,
     lambda t: t["publish"].update(when="${{ with.staged == null }}"))
case("a reader whose binding navigates the null is not a proven witness", NO_CLAIM,
     lambda t: t["publish"].update({"with": {"staged": "${{ tasks.stage.output.path }}"}}))
case("a reader behind a guard the fragment cannot decide", NO_CLAIM,
     lambda t: t["publish"].update(when="${{ size(with.staged) > 0 }}"))
case("a sink that waits for a success the gate's own world excludes", NO_CLAIM,
     lambda t: (put(t, "build", jq(), before="ask"), t["ask"].update(after={"build": "failure"}),
                t["publish"].update(after={"build": "success"})))

# ── outside this reading: no claim, stated rather than guessed ───────────────
case("a reader that is not egress-capable is not a sink", NO_CLAIM,
     lambda t: t.update(publish=jq(**{"with": {"staged": STAGED}})))
case("a choice-mode gate is another contract", NO_CLAIM,
     lambda t: t["ask"]["invoke"]["args"].update(mode="choice", choices=["yes", "no"]))
case("an observation of the skipped stage is not a value read", NO_CLAIM,
     lambda t: t["publish"].update({"with": {"staged": "${{ tasks.stage.status }}"}}))
case("a skip handler that reads nothing is not a value read either", NO_CLAIM,
     lambda t: t.update(publish={"after": {"stage": "skipped"},
                                 "invoke": {"tool": "nika:write", "args": {"path": "./out/report.md", "content": "x"}}}))
case("the cleanup of a stage that never ran never fires", NO_CLAIM,
     lambda t: t["publish"].update(after={"stage": "unwind"}))
case("a closer confirm gate owns its own closure", NO_CLAIM,
     lambda t: (put(t, "again", {"with": {"staged": STAGED},
                                 "invoke": {"tool": "nika:prompt", "args": {"message": "Really? ${{ with.staged }}"}}}),
                t["publish"].update({"with": {"staged": STAGED, "go": "${{ tasks.again.output }}"},
                                     "when": "${{ with.go == true }}"})))


def verdict(doc: dict) -> str:
    found = [e for e in consent_errors(copy.deepcopy(doc)) if e.get("code") == "NIKA-SEC-014"]
    return SEC014 if found else NO_CLAIM


def wrong_rows() -> list[str]:
    return sorted(name for name, (doc, expect) in CASES.items() if verdict(doc) != expect)


CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def main() -> int:
    for name, (doc, expect) in CASES.items():
        law(f"{expect:<8} · {name}", verdict(doc) == expect)

    # ── the witness is named once, with the stage that was skipped ───────────────
    core = consent_errors(base())
    law("the core shape is reported exactly once", len(core) == 1)
    law("the finding names the gate, the skipped stage and the sink",
        bool(core) and all(word in core[0]["detail"] for word in ("'ask'", "'stage'", "'publish'")))
    law("no new wire code: the finding is NIKA-SEC-014 · security_error",
        bool(core) and (core[0]["code"], core[0]["category"]) == ("NIKA-SEC-014", "security_error"))

    # ── the classical walk did not move ──────────────────────────────────────────
    FIXTURES = Path(__file__).parent / "tests" / "core" / "consent"
    for folder, expected in (("001-bare-after-refused", SEC014), ("002-affirmative-clean", NO_CLAIM),
                             ("003-status-gate-is-not-consent", SEC014)):
        law(f"the committed fixture {folder} keeps its verdict",
            verdict(yaml.safe_load((FIXTURES / folder / "input.yaml").read_text(encoding="utf-8"))) == expected)
    plain = yaml.safe_load((FIXTURES / "001-bare-after-refused" / "input.yaml").read_text(encoding="utf-8"))
    law("a plain route keeps its own wording",
        any("never consumes the answer" in error["detail"] for error in consent_errors(plain)))

    # ── each guard is load-bearing: neuter it and exactly its rows flip ──────────
    MUTANTS = {
        "the ordered total reading of when: (a Kleene reading proves skips that may error)": (
            "_consent_eval_total", lambda real: deep_static._consent_eval,
            {"an undecided LEFT operand is not a proven skip, whatever the right one says",
             "a comparison across two classes errors at run: not a proven skip"}),
        "the certainty of every edge into a task (a verb that merely ran is assumed to succeed)": (
            "_consent_admission", lambda real: (lambda task, gate, skipped: "certain"),
            {"a success edge on the SAME producer cancels the reader",
             "a success edge from ANOTHER stage the refusal skips cancels the reader",
             "an independent success prerequisite may fail", "an independent failure prerequisite may succeed",
             "a stage that also reads a verb that merely ran may be cancelled instead of skipped",
             "a sink that waits for a success the gate's own world excludes",
             "the cleanup of a stage that never ran never fires"}),
        "the totality of with: bindings (a navigating read is assumed not to error)": (
            "_consent_total_binding", lambda real: (lambda value: True),
            # the stage that navigates a verb that merely ran is NOT here: the edge guard protects it too
            {"a stage that navigates the gate's own answer may error before its when: is read",
             "a reader whose binding navigates the null is not a proven witness"}),
        "the fan-out guard on the READER (a fan-out over null is assumed to iterate)": (
            "_consent_reader_fans_out", lambda real: (lambda task: False),
            {"a reader that fans out over the null fails instead of running"}),
    }
    law("the table is green before any guard is neutered", wrong_rows() == [])
    for guard, (attribute, mutate, expected_flips) in MUTANTS.items():
        real = getattr(deep_static, attribute, None)
        if real is None:
            law(f"guard exists · {guard}", False)
            continue
        setattr(deep_static, attribute, mutate(real))
        try:
            flipped = set(wrong_rows())
        finally:
            setattr(deep_static, attribute, real)
        law(f"neutered · {guard} · flips exactly {len(expected_flips)} row(s)", flipped == expected_flips)
        if flipped != expected_flips:
            print(f"    mutant {attribute}: unexpected {sorted(flipped ^ expected_flips)}")

    failed = [name for name, holds in CHECKS if not holds]
    for name, holds in CHECKS:
        print(("  ✓ " if holds else "  ✗ ") + name)
    print(f"\nconsent_core_selftest {'PASS' if not failed else 'FAIL'} · {len(CHECKS) - len(failed)}/{len(CHECKS)} laws · "
          f"{len(CASES)} shapes · {len(MUTANTS)} neutered guards")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
