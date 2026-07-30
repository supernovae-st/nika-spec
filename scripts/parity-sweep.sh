#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# The static oracle-parity sweep, one command — the replay behind the
# runner-protocol.md parity numbers (200/215 → 213/217 → …). Drives the
# reference runner in third-party mode with the engine adapter over the
# six static tiers and prints one line per tier + the total. POSIX sh,
# no pipes on any verdict rc.
#
#   NIKA_BIN=/path/to/nika sh scripts/parity-sweep.sh
#
# Exit 0 iff every tier's runner exits 0 (full parity) — a non-zero
# tier keeps sweeping (the total is the point) and the worst rc wins.

set -u
SPEC_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ADAPTER="python3 $SPEC_ROOT/conformance/adapters/nika-engine.py"
total_pass=0
total_all=0
worst=0

for tier in tests/core tests/deep tests/stdlib values types gates; do
  log=$(mktemp)
  python3 "$SPEC_ROOT/conformance/runner.py" run "$SPEC_ROOT/conformance/$tier" \
    --engine "$ADAPTER" > "$log" 2>&1
  rc=$?
  [ "$rc" -gt "$worst" ] && worst=$rc
  summary=$(grep '^Summary' "$log")
  pass=$(printf '%s' "$summary" | sed -E 's|Summary · ([0-9]+)/([0-9]+).*|\1|')
  all=$(printf '%s' "$summary" | sed -E 's|Summary · ([0-9]+)/([0-9]+).*|\2|')
  total_pass=$((total_pass + ${pass:-0}))
  total_all=$((total_all + ${all:-0}))
  printf '%s: %s/%s (rc=%s)\n' "$tier" "${pass:-?}" "${all:-?}" "$rc"
  rm -f "$log"
done

printf 'parity-sweep · %s/%s\n' "$total_pass" "$total_all"
exit "$worst"
