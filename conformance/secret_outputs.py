# SPDX-License-Identifier: Apache-2.0
"""Bounded Check security rule, not a Core law or transitive taint analysis.

01-envelope §egress forbids direct declared-secret references in output
values even when that secret grants outputs egress. No values are resolved.
"""

import ast

from deep_static import CelError, _tokenize, parse_cel
from interpolation_core import _close_island


def _direct_names(body):
    # Reuse the CEL grammar and tokenizer: quoted prose is never a reference.
    parse_cel(body)
    tokens = _tokenize(body.strip())
    pairs, stack = {}, []
    for i, (_, value) in enumerate(tokens):
        if value in ("(", "["):
            stack.append(i)
        elif value in (")", "]"):
            start = stack.pop()
            pairs[start] = i
            pairs[i] = start
    for i, token in enumerate(tokens):
        if token != ("ident", "secrets") or (i and tokens[i - 1][1] == "."):
            continue
        left, right = i, i + 1
        while right < len(tokens):
            # Parentheses preserve a root; function calls do not.
            if tokens[right][1] == ")" and pairs[right] == left - 1:
                if (left > 1 and tokens[left - 2][0] == "ident"
                        and tokens[left - 2][1] != "in"):
                    break
                left, right = left - 1, right + 1
            elif tokens[right][1] == "." and tokens[right + 1][0] == "ident":
                if tokens[right + 2][1] != "(":
                    yield tokens[right + 1][1]
                break
            elif tokens[right][1] == "[":
                end = pairs[right]
                a, b = right + 1, end
                while a < b and tokens[a][1] == "(" and pairs[a] == b - 1:
                    a, b = a + 1, b - 1
                if b == a + 1 and tokens[a][0] == "string":
                    yield ast.literal_eval(tokens[a][1])
                    break
                # Non-literal indices add no static path segment. Their
                # own secret roots are visited independently by this loop.
                right = end + 1
            else:
                break


def _names(text):
    cursor = 0
    while (start := text.find("${{", cursor)) >= 0:
        if start and text[start - 1] == "\\":
            cursor = start + 3
            continue
        end = _close_island(text, start + 3)
        if end is None:
            return  # Existing interpolation validation owns this refusal.
        try:
            yield from _direct_names(text[start + 3:end - 2])
        except (CelError, ValueError, SyntaxError):
            pass  # Existing CEL validation owns malformed expressions.
        cursor = end


def secret_output_errors(doc):
    """One SEC-007 per output directly reading a declared secret.

    This does not follow task aliases or prove publication masking. Output
    declaration metadata and escaped/literal text are not value references.
    """
    if not isinstance(doc, dict):
        return []
    secrets, outputs = doc.get("secrets"), doc.get("outputs")
    if not isinstance(secrets, dict) or not isinstance(outputs, dict):
        return []
    errors = []
    for name, declaration in outputs.items():
        value = declaration.get("value") if isinstance(declaration, dict) else declaration
        if isinstance(value, str) and any(secret in secrets for secret in _names(value)):
            errors.append({"code": "NIKA-SEC-007", "namespace": "NIKA-SEC",
                           "category": "security_error",
                           "detail": f"outputs.{name}: direct secret output is forbidden even with egress"})
    return errors
