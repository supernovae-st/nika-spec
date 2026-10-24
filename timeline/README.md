# Timeline proof boundaries

`timeline.yaml` owns the dated record; entries remain append-only.
`verify.py` rechecks the evidence class each entry declares.

For `github-release`, HTTP success alone is insufficient. The JSON must name
the exact tag, explicitly carry `draft: false`, and contain a valid publication
timestamp. The verifier prints that observed timestamp. Historical entry dates
remain recorded chronology; this check does not assert their equality.

This proves publication state, not complete assets, binary bytes, signatures,
registry convergence or installation. The engine's release barrier owns those
checks; this timeline does not implement another release verifier.

## Gates and their amendments

A gate states conditions, never a date. When its standing changes, the gate
is not rewritten: it gains a dated `amended:` note, `YYYY-MM-DD · <note>`,
appended after the earlier ones. `verify.py` refuses a note whose date is not
a calendar day, comes before the previous note, or lies ahead of today, since
a future date would turn a condition into a schedule.

Since 2026-10-23 (the entry `reference-release-maintenance`), engine 0.123.0
is the maintained reference release and no gate is scheduled; each gate that
planned a 1.0 carries a note saying so.

```sh
python3 -m unittest discover -s timeline -p 'test_*.py'
python3 timeline/verify.py
python3 timeline/verify.py --offline
```

Offline mode labels external claims `SKIPPED-OFFLINE`, never `PROVED`.
Its final summary also says those claims remain unproved; exit zero means
no local check failed, not that skipped network proofs passed.
The regression suite uses controlled API responses; the following live pass
is still required to re-prove actual public records.

An optional `GH_TOKEN` avoids GitHub's anonymous API quota; CI supplies its
read-only token. It is sent only to `https://api.github.com`, and authenticated
redirects off that exact origin fail. Crates.io requests never carry this token.
An unavailable or rate-limited API is `FAILED`, not successful offline evidence.
