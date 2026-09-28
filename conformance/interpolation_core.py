# SPDX-License-Identifier: Apache-2.0
"""04-variables: reject single-brace dotted Nika reference lookalikes."""

import re

# Unicode White_Space, unlike Python's broader str.isspace (U+001C..001F).
SPACE = r"[\x09-\x0d\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]"
HEAD = re.compile(rf"{SPACE}*(?:inputs|const|secrets|with|tasks|group|item|index){SPACE}*\.")


def _close_island(text, start):
    quote = None
    i = start
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif text.startswith("}}", i):
            return i + 2
        i += 1
    return None


def has_reference_lookalike(text):
    """Only real double-brace islands mask their bodies, including CEL strings."""
    return _scan_text(text)[0]


def _scan_text(text):
    cursor = 0
    scan = 0
    found = False
    while (start := text.find("${{", scan)) >= 0:
        if start > 0 and text[start - 1] == "\\":
            scan = start + 3
            continue
        found |= _gap_has_head(text[cursor:start])
        end = _close_island(text, start + 3)
        if end is None:
            return found, True
        cursor = scan = end
    return found or _gap_has_head(text[cursor:]), False


def _gap_has_head(text):
    return any(HEAD.match(text, match.end()) for match in re.finditer(r"\$\{(?!\{)", text))


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _surfaces(doc):
    yield "model", doc.get("model")
    outputs = doc.get("outputs")
    for name, value in outputs.items() if isinstance(outputs, dict) else []:
        yield f"outputs.{name}", value.get("value") if isinstance(value, dict) else value
    tasks = doc.get("tasks")
    for name, task in tasks.items() if isinstance(tasks, dict) else []:
        if not isinstance(task, dict):
            continue
        for field in ("with", "when", "for_each"):
            yield f"tasks.{name}.{field}", task.get(field)
        recovery = task.get("on_error")
        if isinstance(recovery, dict):
            yield f"tasks.{name}.on_error.recover", recovery.get("recover")
        for verb, fields in {
            "infer": ("prompt", "system", "model", "vision"),
            "agent": ("prompt", "system", "model"),
            "exec": ("command", "shell", "cwd", "stdin", "env"),
            "invoke": ("tool", "args"),
        }.items():
            action = task.get(verb)
            if isinstance(action, dict):
                for field in fields:
                    yield f"tasks.{name}.{verb}.{field}", action.get(field)


def interpolation_errors(doc):
    if not isinstance(doc, dict):
        return []
    errors = []
    for where, value in _surfaces(doc):
        flags = [_scan_text(text) for text in _strings(value)]
        for index, code, detail in [
            (0, "NIKA-VAR-005", "use a double-brace reference or a quoted CEL string for literal text"),
            (1, "NIKA-VAR-008", "unterminated real interpolation island"),
        ]:
            if any(flag[index] for flag in flags):
                errors.append({"code": code, "category": "validation_error", "detail": f"{where}: {detail}"})
    return errors
