# SPDX-License-Identifier: Apache-2.0
"""Lexical Nika source-name owner (spec 01 §File naming).

Pure basename classification: no filesystem I/O, no grant, no case folding.
Callers own path shape (relative vs absolute), regular-file checks, and
root/symlink policy. Off-disk source (stdin, HTTP, SDK string, pack blob)
never goes through this module.

Canonical program suffix is lowercase ``.nika`` with a nonempty stem.
``nika.yaml`` is project configuration. ``.nika/`` is runtime state.
``.nika.yaml`` / ``.nika.yml`` are retired live program paths.
"""

from __future__ import annotations

from pathlib import Path

CANONICAL_SUFFIX = ".nika"
RETIRED_SUFFIXES: tuple[str, ...] = (".nika.yaml", ".nika.yml")
PROJECT_BASENAME = "nika.yaml"
RUNTIME_DIRNAME = ".nika"
PROGRAM_GLOB = "*.nika"

KIND_PROGRAM = "program"
KIND_PROJECT = "project"
KIND_RETIRED = "retired"
KIND_NOT_PROGRAM = "not-program"


def _has_illegal_chars(name: str) -> bool:
    return any(ord(c) < 32 or c == "\x7f" for c in name)


def path_basename(name: str) -> str:
    """Final path component, slash-normalized. Empty when the input is a dir."""
    text = name.replace("\\", "/").rstrip("/")
    if not text:
        return ""
    return text.rsplit("/", 1)[-1]


def classify_basename(name: str) -> str:
    """Classify a single path component. Exact lowercase suffix matching."""
    if not name or _has_illegal_chars(name) or "/" in name or "\\" in name:
        return KIND_NOT_PROGRAM
    if name == PROJECT_BASENAME:
        return KIND_PROJECT
    if name == RUNTIME_DIRNAME:
        return KIND_NOT_PROGRAM
    for retired in RETIRED_SUFFIXES:
        if name.endswith(retired):
            return KIND_RETIRED
    if name.endswith(CANONICAL_SUFFIX):
        stem = name[: -len(CANONICAL_SUFFIX)]
        if stem:
            return KIND_PROGRAM
        return KIND_NOT_PROGRAM
    return KIND_NOT_PROGRAM


def classify_path(path: str) -> str:
    """Classify a path string by its basename. No I/O, no traversal policy."""
    if _has_illegal_chars(path):
        return KIND_NOT_PROGRAM
    normalized = path.replace("\\", "/")
    if normalized.endswith("/"):
        return KIND_NOT_PROGRAM
    return classify_basename(path_basename(normalized))


def logical_stem(name: str) -> str | None:
    """Stem of a canonical program basename. ``support.v2.nika`` → ``support.v2``."""
    if classify_basename(name) != KIND_PROGRAM:
        return None
    return name[: -len(CANONICAL_SUFFIX)]


def program_filename(stem: str) -> str:
    if not stem or _has_illegal_chars(stem) or "/" in stem or "\\" in stem:
        raise ValueError("program stem must be a nonempty path component")
    return stem + CANONICAL_SUFFIX


def template_source_path(identity: str) -> str:
    return "templates/" + program_filename(identity)


def is_runtime_dir_part(part: str) -> bool:
    return part == RUNTIME_DIRNAME


def is_under_runtime_dir(path: Path) -> bool:
    return any(is_runtime_dir_part(part) for part in path.parts)


def iter_program_files(directory: Path, *, recursive: bool = False):
    """Yield regular files whose basename is a canonical program name.

    Directories named ``*.nika`` are skipped. Paths under a ``.nika/``
    runtime directory are skipped. Lexical only beyond ``is_file()``.
    """
    if not directory.is_dir():
        return
    paths = directory.rglob(PROGRAM_GLOB) if recursive else directory.glob(PROGRAM_GLOB)
    for path in sorted(paths):
        if not path.is_file():
            continue
        if is_under_runtime_dir(path.relative_to(directory) if recursive else Path(path.name)):
            continue
        if classify_basename(path.name) == KIND_PROGRAM:
            yield path
