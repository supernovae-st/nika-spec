#!/usr/bin/env bash
# render.sh — render a spec tape against the released engine in a staged
# corpus copy. Sibling of the engine's render-tape.sh · same honesty
# contract: every verdict is the binary's own, nothing global is touched.
# Usage: bash scripts/media/render.sh [tape-name]   (default: law-in-action)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAME="${1:-law-in-action}"
TAPE="$ROOT/scripts/media/$NAME.tape"
[ -f "$TAPE" ] || { echo "no tape at $TAPE" >&2; exit 1; }
command -v vhs >/dev/null || { echo "vhs not installed (brew install vhs)" >&2; exit 1; }
command -v nika >/dev/null || { echo "nika not on PATH" >&2; exit 1; }

# The staged corpus copy the tape's `cd /tmp/spec-demo` enters — the two
# trifecta fixtures, verbatim from conformance/ (never edited for camera).
rm -rf /tmp/spec-demo
mkdir -p /tmp/spec-demo/envelope
cp "$ROOT"/conformance/envelope/trifecta-*.nika.yaml /tmp/spec-demo/envelope/

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK" /tmp/spec-demo' EXIT
cp "$TAPE" "$WORK/$NAME.tape"
(cd "$WORK" && vhs "$NAME.tape")

mkdir -p "$ROOT/media"
OUT="$ROOT/media/$NAME.gif"
if command -v gifsicle >/dev/null; then
  gifsicle -O3 --lossy=40 "$WORK/$NAME.gif" -o "$OUT"
else
  cp "$WORK/$NAME.gif" "$OUT"
fi
SIZE_MB=$(du -m "$OUT" | cut -f1)
[ "$SIZE_MB" -le 8 ] || { echo "✖ $OUT is ${SIZE_MB}MB (budget 8MB)" >&2; exit 1; }
echo "→ $OUT (${SIZE_MB}MB · budget 8MB)"
