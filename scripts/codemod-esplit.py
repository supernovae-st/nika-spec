#!/usr/bin/env python3
"""C2 e-split codemod — `vars:` -> `inputs:` / `const:` (TEMPORARY tool).

The one official codemod for the E-split window. Line-based and structure-
aware like migrate-w1.py / migrate-w2.py: it preserves comments, blank lines,
anchors and source order byte-for-byte outside the two transformed shapes, and
it is idempotent (a migrated file passes through unchanged). It dies with the
window once the corpus is flipped — the lasting user-facing teaching lives in
the spec prose (the E-split authoring pass) and the engine's `check`.

What it does, per file, in ONE pass:

  1. SPLIT the top-level `vars:` block into `inputs:` and/or `const:` blocks,
     per the deterministic classification (the 3 ratified rules below). A
     single-class file just gets its header renamed (`vars:` -> `const:` or
     `inputs:`) — the block body is left byte-for-byte untouched. A mixed file
     (both classes) is regrouped into `inputs:` then `const:` (caller contract
     first), each entry keeping its exact lines.

  2. REWRITE every `${{ ... vars.<name> ... }}` reference CLASS-AWARE, in the
     same pass: `vars.<name>` -> `inputs.<name>` if `<name>` is classified
     inputs, else `const.<name>`. The name->class map comes from the file's own
     `vars:` block — never a blind rename. References whose name is NOT declared
     in the file (negative fixtures: undeclared / unresolved / unclosed) are
     LEFT ALONE and surfaced. References that live inside a YAML comment are
     LEFT ALONE and surfaced (prose is the authoring pass's job). References
     inside `|` / `>` block scalars ARE rewritten — they are live template
     expressions, not comments.

The classification (converges byte-for-byte with the reference classifier
c2-esplit-classifier-n2.py) applies the operator-ratified rules:

  D-2026-07-19-N1  bare literal (or bare mapping)          -> const
  D-2026-07-19-N1  {..., required: true} without value:    -> inputs
  D-2026-07-19-N2  {type, default} without required:       -> const
                   {type, value} without required:         -> const
  law 15           a credential-shaped name                -> STOP
  law 15           a typed-only decl (no required/default/ -> STOP
                   value), or any other shape

  Anything that STOPs is surfaced and the whole run refuses to write (the flip
  is atomic-or-nothing) — the codemod never guesses.

Exit codes:
  0  clean — no STOP, nothing left to migrate (fully migrated / no-op)
  1  migratable — no STOP, but `vars:` blocks and/or declared refs remain
  3  STOP — at least one entry is outside the 3 ratified rules; on --write
     NOTHING is written (the flip stays atomic)

usage:
  codemod-esplit.py --check [--root DIR]     dry-run report (no writes)
  codemod-esplit.py --write [--root DIR]     apply across the corpus
  codemod-esplit.py --check --file PATH       one file, dry-run
  codemod-esplit.py --write --file PATH       one file, apply
"""

from __future__ import annotations

import glob
import os
import re
import sys

import yaml

CORPUS_GLOBS = (
    "examples/**/*.nika.yaml",
    "templates/**/*.nika.yaml",
    "conformance/**/*.nika.yaml",
)

SECRET_NAME = re.compile(
    r"(secret|api[_-]?key|token|password|passwd|credential|private[_-]?key)", re.I
)
ISLAND = re.compile(r"\$\{\{(.*?)\}\}")
VARREF = re.compile(r"\bvars\.([a-zA-Z_][a-zA-Z0-9_]*)")
VARS_HEADER = re.compile(r"^vars:\s*(#.*)?$")
KEY2 = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_-]*):")
BLOCK_INTRO = re.compile(r":\s*[|>][+\-]?\d*\s*(#.*)?$")

BLOCK_ORDER = ("inputs", "const")


# --------------------------------------------------------------- classification


def classify_entry(name: str, val) -> tuple[str, str]:
    """Return (klass, reason). klass in inputs | const | STOP."""
    if SECRET_NAME.search(name):
        return "STOP", "name signals a credential (belongs in secrets: with source:)"
    if not isinstance(val, dict):
        return "const", "bare literal default (D-N1)"
    keys = set(val.keys())
    decl = keys & {"type", "required", "default", "value", "description"}
    if not decl:
        return "const", "bare mapping literal (D-N1)"
    req = val.get("required") is True
    has_value = "value" in val
    has_default = "default" in val
    if has_value and not req:
        return "const", "typed + value: fixed (author authority)"
    if req and not has_value:
        return "inputs", "required:true caller-provided (D-N1)"
    if has_default and not req:
        return "const", "typed + default: no required (D-N2)"
    if "type" in val and not (req or has_value or has_default):
        return "STOP", "typed declaration with no required/default/value (law 15)"
    return "STOP", f"shape not decided by the ratified rules (keys={sorted(keys)})"


# --------------------------------------------------------------- comment / block scalar


def comment_col(line: str) -> int:
    """Column where a YAML comment starts on `line`, or -1. Aware of single /
    double quotes AND `${{ ... }}` islands (a '#' inside either is literal). A
    '#' opens a comment only when it is at column 0 or preceded by whitespace."""
    in_s = in_d = False
    depth = 0
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if in_s:
            if c == "'":
                if i + 1 < n and line[i + 1] == "'":
                    i += 2
                    continue
                in_s = False
        elif in_d:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_d = False
        elif depth > 0:
            if c == "}" and line[i - 1] == "}":
                depth -= 1
        else:
            if c == "'":
                in_s = True
            elif c == '"':
                in_d = True
            elif c == "$" and line[i : i + 3] == "${{":
                depth += 1
                i += 3
                continue
            elif c == "#" and (i == 0 or line[i - 1] in " \t"):
                return i
        i += 1
    return -1


def block_scalar_body(lines: list[str]) -> set[int]:
    """0-based indices of lines inside a `|` / `>` block scalar body."""
    body: set[int] = set()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if BLOCK_INTRO.search(line):
            intro = len(line) - len(line.lstrip(" "))
            j = i + 1
            while j < n:
                lj = lines[j]
                if lj.strip() == "" or (len(lj) - len(lj.lstrip(" "))) > intro:
                    body.add(j)
                    j += 1
                    continue
                break
            i = j
            continue
        i += 1
    return body


# --------------------------------------------------------------- planning


class Plan:
    def __init__(self):
        self.entries: list[tuple[str, str, str]] = []  # (name, klass, reason)
        self.name2class: dict[str, str] = {}
        self.has_vars = False

    @property
    def stops(self):
        return [(n, r) for n, k, r in self.entries if k == "STOP"]

    @property
    def counts(self):
        c = {"inputs": 0, "const": 0, "STOP": 0}
        for _n, k, _r in self.entries:
            c[k] += 1
        return c


def plan_file(text: str) -> Plan:
    p = Plan()
    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return p  # parse-fail: skipped (the R11 negatives)
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        block = doc.get("vars")
        if not isinstance(block, dict) or not block:
            continue
        p.has_vars = True
        for name, val in block.items():
            klass, reason = classify_entry(name, val)
            p.entries.append((name, klass, reason))
            if klass in ("inputs", "const"):
                p.name2class[name] = klass
    return p


def scan_refs(text: str, name2class: dict[str, str]):
    """Return (expr, comment, undeclared) lists of (lineno1, name)."""
    lines = text.split("\n")
    body = block_scalar_body(lines)
    expr, comment, undeclared = [], [], []
    for idx, line in enumerate(lines):
        ccol = -1 if idx in body else comment_col(line)
        for m in ISLAND.finditer(line):
            for vm in VARREF.finditer(m.group(1)):
                name = vm.group(1)
                if name not in name2class:
                    undeclared.append((idx + 1, name))
                elif ccol != -1 and m.start() >= ccol:
                    comment.append((idx + 1, name))
                else:
                    expr.append((idx + 1, name))
    return expr, comment, undeclared


# --------------------------------------------------------------- surgery


def _find_vars_span(lines: list[str]):
    """(header_idx, end_exclusive) of the top-level vars: block, or None. `end`
    excludes trailing blank lines (they belong after the block)."""
    for i, line in enumerate(lines):
        if VARS_HEADER.match(line):
            j = i + 1
            last = i
            while j < len(lines):
                lj = lines[j]
                if lj.strip() == "":
                    j += 1
                    continue
                if lj.startswith((" ", "\t")):
                    last = j
                    j += 1
                    continue
                break
            return i, last + 1
    return None


def _parse_block_entries(body: list[str]):
    """Parse a vars-block body into [(lead_lines, entry_lines, key_name)]."""
    entries = []
    lead: list[str] = []
    i = 0
    while i < len(body):
        line = body[i]
        indent = len(line) - len(line.lstrip(" "))
        if line.strip() == "" or (line.lstrip().startswith("#") and indent <= 2):
            lead.append(line)
            i += 1
            continue
        if indent == 2 and KEY2.match(line):
            name = KEY2.match(line).group(1)
            ent = [line]
            i += 1
            while i < len(body):
                lj = body[i]
                jindent = len(lj) - len(lj.lstrip(" "))
                if lj.strip() == "":
                    # a blank inside a value only if a deeper line follows
                    k = i + 1
                    while k < len(body) and body[k].strip() == "":
                        k += 1
                    if k < len(body) and (len(body[k]) - len(body[k].lstrip(" "))) > 2:
                        ent.extend(body[i:k])
                        i = k
                        continue
                    break
                if jindent > 2:
                    ent.append(lj)
                    i += 1
                    continue
                break
            entries.append((lead, ent, name))
            lead = []
        else:
            lead.append(line)
            i += 1
    return entries, lead


def _split_block(lines: list[str], name2class: dict[str, str]) -> list[str]:
    """Rename (single-class) or regroup (mixed) the top-level vars: block."""
    span = _find_vars_span(lines)
    if span is None:
        return lines
    hdr, end = span
    classes = {name2class[n] for n in name2class}
    out = lines[:hdr]
    if len(classes) <= 1:
        # single class: rename header, keep body byte-for-byte
        only = next(iter(classes)) if classes else "const"
        comment = ""
        mh = VARS_HEADER.match(lines[hdr])
        if mh and mh.group(1):
            comment = " " + mh.group(1)
        out.append(f"{only}:{comment}")
        out.extend(lines[hdr + 1 : end])
        out.extend(lines[end:])
        return out
    # mixed: regroup into inputs: then const:
    body = lines[hdr + 1 : end]
    entries, _tail = _parse_block_entries(body)
    grouped: dict[str, list] = {"inputs": [], "const": []}
    for lead, ent, name in entries:
        klass = name2class.get(name, "const")
        grouped[klass].append((lead, ent))
    for klass in BLOCK_ORDER:
        if not grouped[klass]:
            continue
        out.append(f"{klass}:")
        for lead, ent in grouped[klass]:
            out.extend(lead)
            out.extend(ent)
    out.extend(lines[end:])
    return out


def _rewrite_refs(lines: list[str], name2class: dict[str, str]) -> list[str]:
    body = block_scalar_body(lines)

    def repl(m):
        name = m.group(1)
        klass = name2class.get(name)
        return f"{klass}.{name}" if klass else m.group(0)

    out = []
    for idx, line in enumerate(lines):
        ccol = -1 if idx in body else comment_col(line)

        def island_sub(mo, ccol=ccol):
            if ccol != -1 and mo.start() >= ccol:
                return mo.group(0)
            return "${{" + VARREF.sub(repl, mo.group(1)) + "}}"

        out.append(ISLAND.sub(island_sub, line))
    return out


def transform(text: str, plan: Plan) -> str:
    """Split the vars block + rewrite refs. Caller guarantees no STOP."""
    trailing_nl = text.endswith("\n")
    lines = text.split("\n")
    lines = _split_block(lines, plan.name2class)
    lines = _rewrite_refs(lines, plan.name2class)
    result = "\n".join(lines)
    if trailing_nl and not result.endswith("\n"):
        result += "\n"
    return result


# --------------------------------------------------------------- driver


def discover(root: str) -> list[str]:
    files: list[str] = []
    for g in CORPUS_GLOBS:
        files += glob.glob(os.path.join(root, g), recursive=True)
    return sorted(set(files))


def run(files, root, write):
    reports = []
    tally = {"inputs": 0, "const": 0, "STOP": 0}
    tot_expr = tot_comment = tot_undeclared = 0
    parse_skips = []
    stop_files = []
    changes = []  # (path, new_text)
    for path in files:
        text = open(path, encoding="utf-8").read()
        rel = os.path.relpath(path, root)
        try:
            list(yaml.safe_load_all(text))
        except yaml.YAMLError as e:
            parse_skips.append((rel, str(e).splitlines()[0]))
            continue
        p = plan_file(text)
        expr, comment, undeclared = scan_refs(text, p.name2class)
        if not p.has_vars and not expr and not comment and not undeclared:
            continue
        c = p.counts
        for k in tally:
            tally[k] += c[k]
        tot_expr += len(expr)
        tot_comment += len(comment)
        tot_undeclared += len(undeclared)
        if p.stops:
            stop_files.append((rel, p.stops))
        reports.append((rel, c, len(expr), len(comment), len(undeclared)))
        if not p.stops and (p.has_vars or expr):
            new_text = transform(text, p)
            if new_text != text:
                changes.append((path, new_text))

    stop = bool(stop_files)
    if write and not stop:
        for path, new_text in changes:
            open(path, "w", encoding="utf-8").write(new_text)

    _print_report(reports, tally, tot_expr, tot_comment, tot_undeclared,
                  parse_skips, stop_files, changes, write, stop)

    if stop:
        return 3
    if changes:
        return 1
    return 0


def _print_report(reports, tally, tot_expr, tot_comment, tot_undeclared,
                  parse_skips, stop_files, changes, write, stop):
    mode = "WRITE" if write else "CHECK"
    print(f"=== C2 E-SPLIT CODEMOD ({mode}) ===")
    total = tally["inputs"] + tally["const"] + tally["STOP"]
    print(
        f"files with vars/refs: {len(reports)} · entries: {total} "
        f"(inputs={tally['inputs']} const={tally['const']} config=0 secrets=0 "
        f"STOP={tally['STOP']})"
    )
    print(
        f"refs · expr(rewrite)={tot_expr} · comment(skip)={tot_comment} · "
        f"undeclared(leave)={tot_undeclared}"
    )
    print(f"parse-skips (R11 negatives): {len(parse_skips)}")
    for rel, e in parse_skips:
        print(f"    skip {rel}: {e[:70]}")
    print("--- per file ---")
    for rel, c, ne, ncm, nud in sorted(reports):
        extra = ""
        if ncm:
            extra += f" · comment-refs:{ncm}"
        if nud:
            extra += f" · undeclared-refs:{nud}"
        if c["STOP"]:
            extra += f" · STOP:{c['STOP']}"
        print(
            f"  {rel} :: entries {c['inputs'] + c['const'] + c['STOP']} "
            f"(inputs={c['inputs']} const={c['const']}) · refs:{ne}{extra}"
        )
    if stop_files:
        print(f"--- STOP-LIST ({sum(len(s) for _r, s in stop_files)} entries · atomic-abort) ---")
        for rel, stops in stop_files:
            for name, reason in stops:
                print(f"  {rel} :: vars.{name} · {reason}")
    if write and not stop:
        print(f"--- WROTE {len(changes)} files ---")
    elif not write:
        verb = "would change" if changes else "nothing to migrate"
        print(f"--- {len(changes)} files {verb} ---")


def main() -> int:
    args = sys.argv[1:]
    write = "--write" in args
    check = "--check" in args
    root = "."
    if "--root" in args:
        root = args[args.index("--root") + 1]
    single = None
    if "--file" in args:
        single = args[args.index("--file") + 1]
    if not write and not check:
        print(__doc__)
        return 2
    if single:
        # one file: report its path relative to the cwd for readability
        files = [single]
        root = os.getcwd()
    else:
        files = discover(root)
    return run(files, root, write)


if __name__ == "__main__":
    raise SystemExit(main())
