# Per-repo estate rules. The tool is shared and lives in nika-estate;
# these declarations are ours. FILES carries the per-file exceptions,
# PATTERNS the ordered globs that cover everything else.
#
# ROOT, SELF, RULES and CLASSES are injected by the tool into this
# module namespace before it executes. They are therefore undefined as
# far as a linter reading this file alone can tell, hence the noqa: a
# placeholder assignment would satisfy the linter and then OVERWRITE the
# injected value, which is worse than the warning.

# Per-repo estate rules. The tool is shared and lives in nika-estate;
# these declarations are ours. FILES are the per-file exceptions,
# PATTERNS the ordered globs that cover the rest (first match wins).

FILES = [
    {
        "path": SELF,  # noqa: F821
        "class": "pinned-copy",
        "evidence": "the shared estate tool, mirrored byte-for-byte from supernovae-st/nika-estate · editing it here is a lost gesture: change it upstream, bump ESTATE_PIN, re-mirror",
        "derivation": {
            "tool": "curl the tool from nika-estate at the rev named in ESTATE_PIN",
            "gate": "the `mirror` job byte-compares scripts/estate.py against nika-estate@ESTATE_PIN and fails the run on any difference",
            "inputs": ["ESTATE_PIN", "supernovae-st/nika-estate@<ESTATE_PIN>:scripts/estate.py"],
        },
    },
    {
        "path": "ESTATE_PIN",
        "class": "authored-pin",
        "evidence": "its own header: 'Bump deliberately: edit this' \u00b7 the rev the shared estate tool is mirrored from, and the INPUT the mirror gate compares against",
    },
    {
        "path": "SSOT.md",
        "class": "authored",
        "evidence": "the map of where every fact lives — prose and judgments are authored, but it carries ONE generated island (the estate:map markers · §9): scripts/ssot-map-projector.py --write derives the gated-surfaces table from THIS manifest, and --check (exit 5 · conformance.yml 'Projection gates') refuses a hand edit inside the markers — the canon.yaml hybrid, inverted",
    },
    {
        "path": "canon.yaml",
        "class": "generated",
        "evidence": "its own header: 'GENERATED · canon.yaml is a generated projection since the C0 flip — manual edits of a generated surface make CI red (ssot-compiler --check-canon · rc=5)' + a detached body-sha256 self-hash per PAA-006",
        "derivation": {
            "tool": "python3 scripts/ssot-compiler.py --emit-canon (ssot-compiler 0.2.0-sandbox · SSOT-1 §21-23, the canon flip)",
            "gate": ".github/workflows/conformance.yml step 'SSOT gate' → scripts/ssot-compiler.py --check-canon (re-emits from the registries, byte-compares, verifies the GENERATED header · rc=5 on divergence)",
            "inputs": [
                "canon/surface.yaml",
                "canon/builtins.yaml",
                "canon/templates/registry.yaml",
                "canon/diagnostics/registry.yaml",
                "canon/features.yaml",
                "schemas/registries.schema.json (the sealed outcome_class enum)",
                "canon/EXCEPTIONS.md (the §18 exception ledger — the declared-skips mirror)",
            ],
        },
        "note": "hybrid by design: the 15 ledger sections (canon/EXCEPTIONS.md · SSOT-1 §18) stay AUTHORED and are carried verbatim through the regeneration — editing those sections is legal, editing an imported section is rc=5",
    },
    {
        "path": "canon/ssot.lock",
        "class": "generated",
        "evidence": "single-line canonical JSON carrying generator identity ('ssot-compiler' 0.2.0-sandbox + its own source_sha256), the 27 leaf digests and law_count — no human writes a lock",
        "derivation": {
            "tool": "python3 scripts/ssot-compiler.py (write mode · leaf digests only, digest-dag layer 1, own digest DETACHED per PAA-006)",
            "gate": ".github/workflows/conformance.yml step 'SSOT gate' → scripts/ssot-compiler.py --check (regenerate in memory · byte-compare)",
            "inputs": ["canon/laws/*.yaml", "canon/*.yaml registries + canon/{diagnostics,snippets,templates}/registry.yaml", "canon/laws-index.json (leaf-hashed)"],
        },
    },
    {
        "path": "canon/ssot.lock.sha256",
        "class": "generated",
        "evidence": "the lock's own digest, DETACHED into a sidecar per PAA-006 (a file cannot contain its own hash) — written by the compiler alongside the lock",
        "derivation": {
            "tool": "python3 scripts/ssot-compiler.py (write mode · the detached-sidecar emission)",
            "gate": ".github/workflows/conformance.yml step 'SSOT gate' → scripts/ssot-compiler.py --check",
            "inputs": ["canon/ssot.lock"],
        },
    },
    {
        "path": "canon/laws-index.json",
        "class": "generated",
        "evidence": "carries the generator identity block ('ssot-compiler' + source_sha256) · scripts/ssot-compiler.py header: 'emits ONE deterministic projection (canon/laws-index.json, stable sort by law id, canonical JSON, NFC, LF)'",
        "derivation": {
            "tool": "python3 scripts/ssot-compiler.py (write mode)",
            "gate": ".github/workflows/conformance.yml step 'SSOT gate' → scripts/ssot-compiler.py --check",
            "inputs": ["canon/laws/*.yaml (the law registries — law_count lives in the lock, never in prose)", "schemas/law.schema.json", "schemas/registries.schema.json"],
        },
    },
    {
        "path": "llms.txt",
        "class": "generated",
        "evidence": "scripts/llms-projector.py:2 'generates llms.txt + llms-full.txt from the spec sources' · build_llms_txt() interpolates counts from canon.yaml — 'never hand-maintained'",
        "derivation": {
            "tool": "python3 scripts/llms-projector.py --write",
            "gate": ".github/workflows/conformance.yml step 'Projection gates' → scripts/llms-projector.py --check",
            "inputs": ["canon.yaml (the counts)", "README.md + spec/ + stdlib/ + registry/ (the linked reading path)"],
        },
        "note": "carries NO in-file generation marker (llms-full.txt does) — a generated surface that does not self-declare; only the --check gate reveals its provenance",
    },
    {
        "path": "llms-full.txt",
        "class": "generated",
        "evidence": "in-file marker: '<!-- llms-full.txt · GENERATED by scripts/llms-projector.py · do not hand-edit -->'",
        "derivation": {
            "tool": "python3 scripts/llms-projector.py --write",
            "gate": ".github/workflows/conformance.yml step 'Projection gates' → scripts/llms-projector.py --check",
            "inputs": ["README.md · QUICKSTART.md · spec/00-16 · stdlib/ · registry/ · GLOSSARY.md (the ordered normative reading path, concatenated)"],
        },
    },
    {
        "path": "examples/manifest.yaml",
        "class": "generated",
        "evidence": "in-file marker: 'AUTO-GENERATED by scripts/showcase-projector.py from VERSION + examples/ + examples/showcase/ — the versioned pack contract. DO NOT EDIT'",
        "derivation": {
            "tool": "python3 scripts/showcase-projector.py --write",
            "gate": ".github/workflows/conformance.yml step 'Projection gates' → scripts/showcase-projector.py --check",
            "inputs": ["VERSION", "examples/*.nika.yaml"],
        },
        "note": "the engine vendors this manifest into its pack (crates/nika-pack) — downstream it is pinned-copy, here it is the generated original",
    },
    {
        "path": "conformance/type-corpus/corpus.jsonl",
        "class": "generated",
        "evidence": "scripts/gen-type-corpus.py docstring: 'Generates a seeded corpus of v1 type expressions … then writes conformance/type-corpus/corpus.jsonl' — Python judges, Rust must agree",
        "derivation": {
            "tool": "python3 scripts/gen-type-corpus.py --write (seeded · deterministic · judged by conformance/type_core.py)",
            "gate": ".github/workflows/conformance.yml step 'Type corpus' → gen-type-corpus.py --check (byte drift) + --mutate (every broken-judge mutation must be killed)",
            "inputs": ["conformance/type_core.py (the judge)", "the seeded generator grammar in scripts/gen-type-corpus.py"],
        },
    },
    {
        "path": ".github/requirements.txt",
        "class": "generated",
        "evidence": "its own header: 'This file was autogenerated by uv via the following command: uv pip compile /tmp/req.in --generate-hashes --python-version 3.12'",
        "derivation": {
            "tool": "uv pip compile --generate-hashes (the exact command recorded in the file's header)",
            "gate": ".github/workflows/conformance.yml step 'Install runner deps' → pip install --require-hashes (a tampered or stale hash fails the install)",
            "inputs": ["the requirement set (req.in: pyyaml + jsonschema + ruff + their resolved closure)"],
        },
    },
    {
        "path": "conformance/coverage-matrix.tsv",
        "class": "authored",
        "evidence": "conformance/README.md §Scope + coverage: 'Curated 2026-07-08 from the reference engine's private e2e lab (475 workflows → 95 by per-cell best-file selection)' — hand-curated, no script in the tree writes it; empty cells are the declared v0.2 backlog",
    },
    {
        "path": "VERSION",
        "class": "authored",
        "evidence": "hand-set at the v0.1.0-draft spec commit — no lane advances it; the derivations' INPUT (showcase-projector.py reads it as pack_version)",
    },
    {
        "path": "CODE_OF_CONDUCT.md",
        "class": "pinned-copy",
        "evidence": "the Contributor Covenant v2.1 verbatim (its own footer links contributor-covenant.org) — REUSE.toml overrides the blanket to declare its true license: 'The Contributor Covenant is CC-BY-4.0 … the blanket must not misdeclare it'",
        "derivation": {
            "tool": "hand-vendored verbatim from the upstream text (no lane)",
            "gate": ".github/workflows/reuse.yml (reuse lint · REUSE 3.3 compliance · the override annotation keeps the license truthful)",
            "inputs": ["https://www.contributor-covenant.org/version/2/1/code_of_conduct.html (CC-BY-4.0)"],
        },
    },
]

# ── patterns: ordered glob rows — FIRST-MATCH-WINS ──────────────────────────

PATTERNS = [
    {
        "glob": "canon/laws/**",
        "class": "authored",
        "evidence": "the law registries humans edit — every entry schema-validated against schemas/law.schema.json, leaf-hashed into canon/ssot.lock by the ssot-compiler (law_count lives in the lock, never typed here); the compiler CONSUMES these, nothing writes them",
    },
    {
        "glob": "canon/**",
        "class": "authored",
        "evidence": "the registries humans edit (surface · builtins · features · conformance · grammar · types · providers · migrations · projections · tombstones · snippets · templates · diagnostics) + canon/EXCEPTIONS.md (the §18 exception ledger) — the SOURCES the compiler seals; ssot.lock + sidecar excepted in files:",
    },
    {
        "glob": "conformance/tests/runtime/gates/**",
        "class": "generated",
        "evidence": "conformance/tests/runtime/gates/MATRIX.md: 'The gate-v2 observation matrix (generated) … Regenerate: python3 scripts/gen-gate-matrix.py --write' — 35 runtime cells + the 001-always-pattern fixture + MATRIX.md itself, all emitted by the generator",
        "derivation": {
            "tool": "python3 scripts/gen-gate-matrix.py --write (expected statuses come from reference/semantics.py — the model DEFINES the outcome, the script never hand-writes one)",
            "gate": "scripts/gen-gate-matrix.py --check (regenerate into temp · diff every emitted file) · engine proof via --prove <nika-cli>",
            "inputs": ["reference/semantics.py (the executable model)", "the 40-cell matrix grammar in scripts/gen-gate-matrix.py"],
        },
    },
    {
        "glob": "conformance/tests/deep/0??-dead-*/**",
        "class": "generated",
        "evidence": "gen-gate-matrix.py: the 5 STATICALLY DEAD cells (03 §static liveness) land in tests/deep/023-027 expecting NIKA-DAG-006 — 'that refusal IS the cell's semantics' (MATRIX.md points here)",
        "derivation": {
            "tool": "python3 scripts/gen-gate-matrix.py --write",
            "gate": "scripts/gen-gate-matrix.py --check",
            "inputs": ["reference/semantics.py", "the 40-cell matrix grammar in scripts/gen-gate-matrix.py"],
        },
    },
    {
        "glob": "conformance/tests/deep/028-bad-status-literal-vocabulary/**",
        "class": "generated",
        "evidence": "gen-gate-matrix.py DEEP_VOCAB = '028-bad-status-literal-vocabulary' — the NIKA-DAG-007 vocabulary fixture that guards the observation half of the matrix",
        "derivation": {
            "tool": "python3 scripts/gen-gate-matrix.py --write",
            "gate": "scripts/gen-gate-matrix.py --check",
            "inputs": ["the VOCAB_FIXTURE constant in scripts/gen-gate-matrix.py"],
        },
    },
    {
        "glob": "conformance/tests/**",
        "class": "authored",
        "evidence": "the executable law — the 5-tier fixture corpus (core · deep 001-022 · lints · runtime · stdlib): input + expected pairs written at spec-authoring time, consumed by conformance/runner.py; no generation markers",
    },
    {
        "glob": "conformance/.nika/**",
        "class": "testimonial",
        "evidence": "hash-chained NDJSON traces captured from the reference engine executing the corpus (timestamps 2026-07-08 — the curation run) — committed evidence that the corpus RAN, regenerable by no script in this tree",
    },
    {
        "glob": "conformance/out/**",
        "class": "testimonial",
        "evidence": "run.sh: 'Corpus files write ONLY under ./out/<family>/' — the nika:write outputs captured from the reference run of the corpus; evidence of behavior, not law and not regenerable here",
    },
    {
        "glob": "conformance/**",
        "class": "authored",
        "evidence": "the 95-workflow corpus (envelope · variables · verbs · errors · dag · gates · types · yaml-profile · values · composition · decision-goldens frozen at authoring time and consumed by decision_core_selftest.py) + the Python cores/selftests/runner + README/FINDINGS/runner-protocol; type-corpus + coverage-matrix excepted in files:",
    },
    {
        "glob": "proofs/**",
        "class": "testimonial",
        "evidence": "the sealed C0 receipts (PROOFS.md is their authored ledger): determinism runs (run1/run2 byte-identical) · canon-flip and canon-generated receipts · the 57-file mutation-kill battery · pc-light + c1-yaml-profile — captured evidence, frozen, never regenerated",
    },
    {
        "glob": "eval/results/**",
        "class": "testimonial",
        "evidence": "captured eval run outputs (timestamped per provider: haiku · gemini · gpt-4o-mini · ollama-qwen) — REUSE.toml override notes their content embeds whole template files; evidence of model behavior at a date",
    },
    {
        "glob": "eval/authorability/results/**",
        "class": "testimonial",
        "evidence": "captured authorability eval outputs (2026-07-05 qwen35-9b partial) — dated evidence, not law",
    },
    {
        "glob": "eval/**",
        "class": "authored",
        "evidence": "the eval harness humans wrote — run-eval.py · intents.yaml · authorability/{eval.yaml,generate.py,tasks.jsonl} · READMEs; results excepted above",
    },
    {
        "glob": "examples/**",
        "class": "authored",
        "evidence": "the ORIGINALS everything downstream copies (engine pack vendoring · docs/website projections) — 7 foundation + 26 showcase workflows, every one executed by the conformance gate ('examples/ — every shipped example executed as a conformance input'); manifest.yaml excepted in files:",
    },
    {
        "glob": "templates/**",
        "class": "authored",
        "evidence": "the 10 verb-template originals + README — each row in canon/templates/registry.yaml carries 'source_digest is the real sha256 of templates/<id>.nika.yaml · gate: ssot-compiler --check-canon' (the registry digests these, nothing writes them)",
    },
    {
        "glob": "spec/**",
        "class": "authored",
        "evidence": "the normative prose law (00-overview → 16-projections) — THE spec; no generation markers",
        "note": "spec/00-04 · 06-08 carry tool-maintained '<!-- canon:KEY -->N<!-- /canon -->' count markers inside the authored prose (canon-projectors.py TARGET 0 · --check gated) — the class stays authored",
    },
    {
        "glob": "stdlib/**",
        "class": "authored",
        "evidence": "the stdlib contracts (builtins · providers · extract-modes v0.1) + the two authored SSOTs the projectors CONSUME (verb-starters-v0.1.yaml → starters-projector.py · authoring-shapes-v0.1.yaml → authoring-projector.py — 'Values change in the YAML FIRST, then re-project')",
        "note": "the four .md files carry the same canon-projected count markers as spec/ — tool-maintained blocks inside authored prose",
    },
    {
        "glob": "governance/**",
        "class": "authored",
        "evidence": "the NEP process + NEPs + certifications matrix — hand-written governance prose, link-integrity gated by scripts/check-md-refs.py",
    },
    {
        "glob": "adr/**",
        "class": "authored",
        "evidence": "per-decision records authored at decision time (adr-099 · 100 · 104 · 105) — no generation markers",
    },
    {
        "glob": "design/**",
        "class": "authored",
        "evidence": "the design SSOTs (tokens.yaml · motion.yaml — design-projector.py projects them OUTWARD to consumers, nothing writes them here) + v1-constitution.md",
    },
    {
        "glob": "reference/**",
        "class": "authored",
        "evidence": "the executable reference semantics (semantics.py — the model that DEFINES gate-matrix outcomes · values_core.py · differential.py · generate.py · selftest.py) — hand-written Python, ruff-gated",
    },
    {
        "glob": "schemas/**",
        "class": "authored",
        "evidence": "workflow.schema.json's own $comment: 'INTERIM hand-derived schema · prose spec is the single source of truth · regenerate + diff against engine nika-schema at GA' — authored today, generated at GA; law.schema.json + registries.schema.json are the sealed R2 design-pack contracts (consumed as-is, byte-identical per PROOFS.md §P0)",
    },
    {
        "glob": "scripts/**",
        "class": "authored",
        "evidence": "the compiler + projectors humans wrote (ssot-compiler · canon/showcase/llms/starters/authoring/design projectors · gen-gate-matrix · gen-type-corpus · grammar_door + selftest · check-md-refs) — the tools that WRITE the generated surfaces; estate.py excepted in files: (the self row)",
    },
    {
        "glob": "timeline/**",
        "class": "authored",
        "evidence": "timeline.yaml (the SSOT — 'every provable claim … re-proven against its source of truth' per timeline.yml) + verify.py + project-board.py (writes OUTWARD to the org Projects board, never into this tree)",
    },
    {
        "glob": "registry/**",
        "class": "authored",
        "evidence": "registry-v0.1.md — the registry contract prose (entries · trust model · advisories), hand-written",
    },
    {
        "glob": "LICENSES/**",
        "class": "pinned-copy",
        "evidence": "REUSE-convention verbatim license texts (Apache-2.0 · CC-BY-4.0) at the REUSE naming — byte-copies of the SPDX canonical texts",
        "derivation": {
            "tool": "reuse download / hand-vendored verbatim from the SPDX license-list",
            "gate": ".github/workflows/reuse.yml (reuse lint · REUSE 3.3 compliance)",
            "inputs": ["the SPDX license-list canonical texts"],
        },
    },
    {
        "glob": ".github/**",
        "class": "authored",
        "evidence": "6 hand-written SHA-pinned workflows (conformance · timeline · board · codeql · reuse · scorecard) + dependabot config — ZERO in-repo bot lanes: board.yml writes to the org Projects board, timeline.yml verifies read-only, nothing here rewrites tracked files; requirements.txt excepted in files:",
    },
    {
        "glob": "*",
        "class": "authored",
        "evidence": "root prose + config (README · QUICKSTART · GLOSSARY · CONTRIBUTING · CHANGELOG hand-kept per Keep a Changelog · SECURITY · CITATION.cff · CONFORMANT_IMPLEMENTATIONS · PROOFS.md the receipts ledger · LICENSE · REUSE.toml · ruff.toml · .gitignore · .pre-commit-hooks.yaml · .bestpractices.json) — no generation markers; VERSION · llms*.txt · canon.yaml · CODE_OF_CONDUCT.md excepted in files:",
        "note": "README · QUICKSTART · GLOSSARY · CONTRIBUTING · CHANGELOG carry the canon-projected count markers — tool-maintained blocks inside authored prose",
    },
    {
        "glob": "**",
        "class": "authored",
        "evidence": "no evidence gathered — honesty over completeness (the catchall; anything landing here is reported under unverified:)",
        "note": "unverified-default",
    },
]
