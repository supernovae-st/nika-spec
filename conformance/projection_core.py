# SPDX-License-Identifier: Apache-2.0
#
# The reference projection surface (spec 16-projections.md · W7). Stdlib-only.
#
# The oracle surface is a READ-model, not an evaluator — so this reference
# is a SHAPE VALIDATOR, not a semantic judge. It pins the normative,
# algorithm-independent laws of the projection:
#   · semantic_document_format is present and is the surface's OWN version
#   · reason is a closed one-word vocabulary, present IFF graph is absent
#   · a healthy document carries no reason key (presence is the signal)
#   · the projection is structure-only (no secret/env material leaks in)
#   · additive forward-compat: an unknown field is IGNORED, never rejected
#
# It validates the shape the engine's `nika inspect` / LSP / MCP all serve;
# the triangle byte-parity is proven engine-side (one producer), the shape
# law is proven here (both evaluators agree on what a valid surface IS).

from __future__ import annotations

SEMANTIC_DOCUMENT_FORMAT = 1
# closed one-word vocabulary (spec 16 · a new reason bumps the format)
REASONS = ("parse", "findings")
# keys the v1 surface defines; the additive arc grows this under a format bump
KNOWN_FIELDS = {"semantic_document_format", "graph", "reason", "spans"}
# fields that must never appear — a projection is structure-only (spec 10 · 16)
FORBIDDEN_SUBSTRINGS = ("secret", "env_value", "resolved_secret", "api_key")


class ProjectionError(Exception):
    """A projection-surface law (spec 16) is violated."""


def validate(doc: dict) -> None:
    """Refuse a malformed semantic document. The laws are structural —
    the projection ALWAYS answers, so an invalid SHAPE (not an invalid
    workflow) is what this catches."""
    if not isinstance(doc, dict):
        raise ProjectionError("semantic document · must be an object")

    fmt = doc.get("semantic_document_format")
    if fmt != SEMANTIC_DOCUMENT_FORMAT:
        raise ProjectionError(
            f"semantic_document_format must be {SEMANTIC_DOCUMENT_FORMAT} (the surface's own "
            f"version · not the nested graph_format) · got {fmt!r}")

    has_graph = doc.get("graph") is not None
    has_reason = "reason" in doc

    # reason present IFF graph absent (presence is the signal · no sentinel)
    if has_graph and has_reason:
        raise ProjectionError(
            "a healthy document (graph present) MUST omit `reason` — presence is the signal")
    if not has_graph and not has_reason:
        raise ProjectionError(
            "an unbuildable document (graph absent) MUST name a one-word `reason`")
    if has_reason:
        r = doc["reason"]
        if r not in REASONS:
            raise ProjectionError(
                f"reason {r!r} is not in the closed vocabulary {REASONS} "
                "(a new reason bumps semantic_document_format)")

    # the nested graph, when present, names ITS own version (graph_format)
    if has_graph:
        g = doc["graph"]
        if not (isinstance(g, dict) and "graph_format" in g):
            raise ProjectionError(
                "graph, when present, is the canonical projection carrying its own graph_format")

    # spans: task id → range, always an object (possibly empty)
    spans = doc.get("spans")
    if not isinstance(spans, dict):
        raise ProjectionError("spans must be an object (task id → range · possibly empty)")

    # structure-only: no secret/env material anywhere in the surface
    _refuse_secret_material(doc)


def _refuse_secret_material(v) -> None:
    """A projection carries structure, never resolved material (spec 10 · 16).
    A key or string that smells of a secret sink is a refusal."""
    if isinstance(v, dict):
        for k, val in v.items():
            kl = str(k).lower()
            if any(s in kl for s in FORBIDDEN_SUBSTRINGS):
                raise ProjectionError(f"projection carries forbidden material at key {k!r} "
                                      "(structure only · no secret/env leaks)")
            _refuse_secret_material(val)
    elif isinstance(v, list):
        for item in v:
            _refuse_secret_material(item)


def accepts_unknown_additive_field(doc: dict) -> bool:
    """Additive forward-compat: a consumer IGNORES a field it does not know,
    never fails on it. A valid document with an extra unknown key is still
    valid (the format-bump discipline · spec 16 §the additive arc)."""
    try:
        validate(doc)
        return True
    except ProjectionError:
        return False
