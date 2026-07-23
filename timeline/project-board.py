#!/usr/bin/env python3
"""Compatibility entry point for the Nika Project OS reconciler.

The implementation lives in `project_os/`. This path remains stable for the
existing GitHub Actions workflow and for operators who used the original board
projection command.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from project_os.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
