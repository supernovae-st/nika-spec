#!/usr/bin/env sh
# conformance/run.sh — the reference conformance runner (v0.1).
#
# Prove an engine implements `nika: v1` by running every corpus file and
# verdicting it against its DECLARED intent (the `# Expected:` header),
# never against raw exit codes. POSIX sh · zero deps beyond the engine
# binary under test.
#
#   ./run.sh /path/to/your-engine-binary
#
# Verdicts:
#   PASS      the outcome matches the declared intent
#   DRIFT     failed as declared but with a DIFFERENT error code
#   BUG       the outcome contradicts the declared intent
#   DIVERGENT the file documents a spec↔reference-impl divergence (its
#             header carries "DIVERGENCE"): it asserts the SPEC, so it is
#             NEVER a PASS for the reference engine until fixed; a
#             conformant engine that follows the spec turns it green.
#             (v0.1 exemplar: recover-task-ref-no-edge · spec 05 §recover
#             await — tracked at supernovae-st/nika#291.)
#
# Header grammar (see README.md §Headers):
#   # Expected: NIKA-XXX-NNN at CHECK.            negative · at static-check time
#   # Expected: NIKA-XXX-NNN at RUN.              negative · at run time
#   # Expected: NIKA-XXX-NNN (check or run).      negative · either stage
#   # Expected: check-reject (gate verdict).      negative · the static check MUST
#                                                 refuse (nonzero), no specific code
#                                                 required (permits/secrets gates
#                                                 report a verdict, not a wire code)
#   # Expected: exit 0 — …                        positive (incl. recovered-via-on_error)
set -u
ENGINE="${1:-nika}"
command -v "$ENGINE" >/dev/null 2>&1 || [ -x "$ENGINE" ] || { echo "engine binary not found: $ENGINE"; exit 2; }
HERE="$(cd "$(dirname "$0")" && pwd)"

# ── sandbox prep ─────────────────────────────────────────────────────────
# Corpus files write ONLY under ./out/<family>/ (relative to this dir).
# nika:write does not create parent dirs unless asked; shell-redirect
# markers never do. Pre-create the full set so runs are location-agnostic.
for d in cel competitor content ctrlflow data-validation errors fanout research security support; do
  mkdir -p "$HERE/out/$d"
done
# The ONE env secret the corpus uses (envelope/secrets-infer-egress-sanctioned
# declares `source: env · key: FAKE_API_KEY_FOR_TEST` per spec 01 §secrets).
# Dummy value · mock model · never egresses anywhere real.
export FAKE_API_KEY_FOR_TEST="${FAKE_API_KEY_FOR_TEST:-conformance-dummy-secret}"

pass=0; drift=0; bug=0; dvg=0
for wf in "$HERE"/*/*.nika.yaml; do
  rel="${wf#"$HERE"/}"
  header="$(head -30 "$wf" | grep '^#' || true)"
  expected="$(printf '%s\n' "$header" | grep -i '# *Expected:' | head -1 || true)"
  code="$(printf '%s' "$expected" | grep -oE 'NIKA-[A-Z]+(-[A-Z0-9_]+)?-[0-9]+' | head -1 || true)"
  divergent=""; printf '%s' "$header" | grep -qi 'DIVERGENCE' && divergent=1
  stage=RUN
  printf '%s' "$expected" | grep -qiE 'at CHECK|at parse' && stage=CHECK
  printf '%s' "$expected" | grep -qiE 'check or run' && stage=EITHER
  gate=""; printf '%s' "$expected" | grep -qi 'check-reject (gate verdict)' && gate=1
  # negative iff a code is declared and the header does not promise exit 0
  # ('exit 0' alone — recovered-class headers all start "exit 0 — …"; matching
  # bare 'recovered' would false-trip on prose like "Unrecovered failure")
  neg=""; [ -n "$code" ] && ! printf '%s' "$expected" | grep -qiE 'exit 0' && neg=1

  cout="$("$ENGINE" check "$wf" 2>&1)"; cc=$?
  rout=""; rc=0
  if [ $cc -eq 0 ]; then rout="$(cd "$HERE" && "$ENGINE" run "$wf" 2>&1)"; rc=$?; fi

  if [ -n "$divergent" ]; then
    # asserts the SPEC: green (exit 0 + recover honored) = conformant;
    # the reference engine's current behavior reports DIVERGENT.
    if [ $cc -eq 0 ] && [ $rc -eq 0 ]; then v=PASS; pass=$((pass+1))
    else v=DIVERGENT; dvg=$((dvg+1)); fi
  elif [ -n "$gate" ]; then
    # gate-verdict class: the static check must refuse; no code grep.
    if [ $cc -ne 0 ]; then v=PASS; pass=$((pass+1))
    else v=BUG; bug=$((bug+1)); echo "BUG    $rel (expected check-reject gate verdict · check passed)"; fi
  elif [ -n "$neg" ]; then
    hit=""
    case "$stage" in
      CHECK)  [ $cc -ne 0 ] && printf '%s' "$cout" | grep -q "$code" && hit=1 ;;
      EITHER) { [ $cc -ne 0 ] && printf '%s' "$cout" | grep -q "$code"; } || { [ $rc -ne 0 ] && printf '%s' "$rout" | grep -q "$code"; } && hit=1 ;;
      RUN)    if [ $cc -ne 0 ]; then printf '%s' "$cout" | grep -q "$code" && hit=1
              else [ $rc -ne 0 ] && printf '%s' "$rout" | grep -q "$code" && hit=1; fi ;;
    esac
    if [ -n "$hit" ]; then v=PASS; pass=$((pass+1))
    elif [ $cc -ne 0 ] || [ $rc -ne 0 ]; then v=DRIFT; drift=$((drift+1)); echo "DRIFT  $rel (expected $code)"
    else v=BUG; bug=$((bug+1)); echo "BUG    $rel (expected $code · got success)"; fi
  else
    if [ $cc -eq 0 ] && [ $rc -eq 0 ]; then v=PASS; pass=$((pass+1))
    else v=BUG; bug=$((bug+1)); echo "BUG    $rel (positive test failed · cc=$cc rc=$rc)"; fi
  fi
done
echo "conformance v0.1 · PASS=$pass DRIFT=$drift DIVERGENT=$dvg BUG=$bug"
[ $((drift + bug)) -eq 0 ] || exit 1
