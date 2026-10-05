# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Closed assertions on journaled harness-image receipts, never a blob/file oracle.

The native verifier still owns the chain verdict. This reader inspects the same
frozen bytes, like the prologue assertions; it never opens a reported path or CAS
locator. A stored receipt is evidence of the observed store answer, not proof
that the blob remains available, is an image, or was produced by a named model.
"""
import re

SOURCE = {"session_config", "confirmed_selection", "accepted_request", "unspecified"}
IMAGE_KEYS = {"schema", "source", "tool_call_id", "mime_type", "received_bytes", "blob",
              "storage", "storage_failure", "received_sha256", "reported_saved_path",
              "file_verified", "permission_evidence"}
MODEL_KEYS = {"model_reported", "model_reported_source", "model_served"}


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def nullable_text(value):
    return value is None or isinstance(value, str)


def image_valid(image):
    """A well-typed receipt; a bare savedPath or missing blob cannot mean stored."""
    if not isinstance(image, dict) or set(image) != IMAGE_KEYS:
        return False
    if image["schema"] != "nika/harness-image-observation@1" \
            or image["source"] != "harness_reported" or image["file_verified"] is not False \
            or image["permission_evidence"] != "separate permit_checked frames" \
            or not isinstance(image["tool_call_id"], str):
        return False
    for key in ("mime_type", "storage_failure", "reported_saved_path"):
        if not nullable_text(image[key]):
            return False
    state, size, blob = image["storage"], image["received_bytes"], image["blob"]
    if state == "none":
        return size is None and blob is None and image["received_sha256"] is None \
            and image["storage_failure"] is None
    if not integer(size) or not isinstance(image["received_sha256"], str) \
            or not re.fullmatch(r"[0-9a-f]{64}", image["received_sha256"]):
        return False
    if state == "failed":
        return blob is None and isinstance(image["storage_failure"], str)
    if state == "unconfirmed":
        return blob is None and image["storage_failure"] is None
    return state == "stored" and image["storage_failure"] is None \
        and isinstance(blob, dict) and set(blob) == {"hash", "size", "mime_type"} \
        and isinstance(blob["hash"], str) and re.fullmatch(r"blake3:[0-9a-f]{64}", blob["hash"]) \
        and integer(blob["size"]) and blob["size"] == size \
        and isinstance(blob["mime_type"], str) and bool(blob["mime_type"]) \
        and (image["mime_type"] is None or image["mime_type"] == blob["mime_type"])


def row_valid(row):
    return isinstance(row, dict) and set(row) == {"attempt", "iteration", "image"} \
        and integer(row["attempt"], 1) \
        and (row["iteration"] is None or integer(row["iteration"])) \
        and image_valid(row["image"])


def validate_expected(expected):
    """Fixture mistakes refuse before the first engine command, including unknown keys."""
    if not isinstance(expected, dict) or not expected:
        raise ValueError("harness_media must be a nonempty task map")
    for task, claim in expected.items():
        if not isinstance(task, str) or not task or not isinstance(claim, dict) \
                or set(claim) != {"observations", "terminal_count", "complete", "model"}:
            raise ValueError("harness_media task requires observations, terminal_count, complete, model")
        rows, count = claim["observations"], claim["terminal_count"]
        if not isinstance(rows, list) or any(row is not None and not row_valid(row) for row in rows):
            raise ValueError("harness_media observations must be receipt rows or null for malformed frames")
        if count is not None and not integer(count):
            raise ValueError("harness_media terminal_count must be a nonnegative integer or null")
        if type(claim["complete"]) is not bool:
            raise ValueError("harness_media complete must be a boolean")
        if claim["complete"] and (count != len(rows) or any(row is None for row in rows)):
            raise ValueError("complete media requires an exact terminal count and well-formed observations")
        model = claim["model"]
        if not isinstance(model, dict) or set(model) != MODEL_KEYS \
                or not all(nullable_text(model[key]) for key in MODEL_KEYS) \
                or model["model_reported_source"] not in SOURCE | {None} \
                or model["model_served"] is not None:
            raise ValueError("harness model assertions preserve reports and require served identity absent")


def fields_of(event):
    fields = event.get("fields")
    if not isinstance(fields, list):
        raise ValueError("event fields must be an array")
    result = {}
    for field in fields:
        if not isinstance(field, dict) or set(field) != {"key", "value"} \
                or not isinstance(field["key"], str) or field["key"] in result:
            raise ValueError("malformed or duplicate event field")
        result[field["key"]] = field["value"]
    return result


def compare_journal(raw, expected, loads, equal):
    """Compare explicit facts, with no path access, pricing, permission or model inference."""
    states = {}
    try:
        for line in raw.splitlines():
            if not line.strip():
                continue
            event = loads(line.decode("utf-8"))
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
            kind = event.get("kind")
            fields = fields_of(event)
            if kind == "workflow_started":
                states.clear()
                continue
            task = fields.get("task")
            if not isinstance(task, str) or task not in expected:
                continue
            if kind in {"task_started", "task_cache_hit"}:
                states[task] = {"observations": [], "terminal_count": None, "model": {},
                                "started": True, "terminal": False, "bad": False}
                continue
            state = states.setdefault(task, {"observations": [], "terminal_count": None,
                                             "model": {}, "started": False,
                                             "terminal": False, "bad": True})
            if kind == "agent_image_observed":
                state["bad"] |= state["terminal"]
                image = fields.get("harness_image")
                try:
                    image = loads(image) if isinstance(image, str) \
                        and len(image.encode("utf-8")) <= 64 * 1024 else None
                except (ValueError, TypeError):
                    image = None
                row = {"image": image, "attempt": fields.get("attempt"),
                       "iteration": fields.get("iteration")}
                state["observations"].append(row if row_valid(row) else None)
            elif kind in {"task_completed", "task_failed", "task_skipped"}:
                state["bad"] |= state["terminal"]
                state["terminal"] = True
                count = fields.get("harness_media_count")
                state["terminal_count"] = count if integer(count) else None
                state["model"] = {key: fields.get(key) for key in MODEL_KEYS}
        differences = []
        for task, wanted in expected.items():
            state = states.get(task)
            if state is None:
                differences.append(f"harness_media {task}: task evidence absent")
                continue
            rows, count = state["observations"], state["terminal_count"]
            got = {"observations": rows, "terminal_count": count, "model": state["model"],
                   "complete": state["started"] and state["terminal"] and not state["bad"]
                   and count == len(rows) and all(row is not None for row in rows)}
            if not equal(got, wanted):
                differences.append(f"harness_media {task}: journal receipts differ from expectation")
        return differences
    except (ValueError, TypeError, UnicodeError) as error:
        return [f"harness_media: unreadable journal evidence ({error})"]
