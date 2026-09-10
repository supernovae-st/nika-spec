#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the declared template inventory; optionally refresh only source hashes."""
import argparse
import hashlib
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]


def project(root=ROOT):
    path = root / "canon/templates/registry.yaml"
    text = path.read_text()
    rows = yaml.safe_load(text)["templates"]
    seen, sources, changes = set(), set(), []
    for row in rows:
        identity, source = row["id"], row["source_path"]
        if identity in seen or source in sources:
            raise ValueError("Duplicate template identity or source: " + identity)
        seen.add(identity)
        sources.add(source)
        if source != "templates/" + identity + ".nika.yaml" or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identity):
            raise ValueError("Invalid template source: " + source)
        file = root / source
        if file.is_symlink():
            raise ValueError("Template source must not be a symlink: " + source)
        actual = "sha256:" + hashlib.sha256(file.read_bytes()).hexdigest()
        if actual != row["source_digest"]:
            changes.append((identity, row["source_digest"], actual))
    files = {file.relative_to(root).as_posix() for file in (root / "templates").glob("*.nika.yaml")}
    if sources != files:
        raise ValueError("Template inventory differs from sources: " + str(sorted(sources ^ files)))
    for identity, old, new in changes:
        # Preserve comments and formatting. Scope each replacement to its declared row.
        pattern = r"(  - id: " + re.escape(identity) + r"\n(?:(?!  - id: ).)*?source_digest: )" + re.escape(old)
        text, count = re.subn(pattern, lambda match: match[1] + new, text, flags=re.S)
        if count != 1:
            raise ValueError("Unsupported registry layout: " + identity)
    return text, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    text, changes = project()
    if changes and not args.write:
        raise SystemExit("Template registry digest drift: " + ", ".join(row[0] for row in changes) + ". Run scripts/template-registry.py --write after reviewing source changes.")
    if args.write and changes:
        (ROOT / "canon/templates/registry.yaml").write_text(text)
    print(f"Template registry verified; {len(changes)} hashes {'updated' if args.write else 'divergent'}.")


if __name__ == "__main__":
    main()
