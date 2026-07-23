# NEP-0006 · The data-as-code sink: a fetch of a code-bearing artifact is never innocent

- **NEP**: 0006 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit)
- **Title**: The contract distinguishes inert reads from code-bearing reads: a fetch whose artifact class can execute is refused, unless the read is declared inert
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-23

## Abstract

NEP-0003 sealed the absent boundary, NEP-0004 the values flowing under
it, NEP-0005 the environment plane. This NEP closes the verb-choice
hole: acquiring an artifact whose LOAD executes code · a serialized
object whose deserializer runs arbitrary code, a script, an executable
binary · through an innocent-looking `fetch` hides an execution sink
from review. The static judge sees « the workflow fetches a host »; the
kill chain sees « the workflow imports a loader ». The contract now
distinguishes the two reads. A `nika:fetch` whose RESOLVED URL path
names a code-bearing class is refused at check (`NIKA-SEC-008`); the
repair is to model the acquisition as the `exec` it feeds
(program-permitted · reviewable) or to declare the read inert
(`inert: "<because>"` · the honest door · one greppable line). At run,
the same class refuses on the resolved URL in defense in depth
(`NIKA-SEC-004`), honoring the same declared door.

## Motivation

HF incident vector n°1: the loader RCE (arXiv:2601.14163 · code
execution on ML hosting through artifact loads). The dangerous act is
not the network read · it is that some artifact CLASSES execute at
load: the pickle-format family deserializes by running opcodes
(`.pkl`, and the torch checkpoint family that embeds the same
mechanism), scripts exist to be run, binaries and executable modules
are code by definition. A workflow that models « load this dataset »
as a bare `fetch` under a permitted host carries an execution sink no
reviewer sees and no permit names. Nothing today forces the author to
model that load as the `exec` it is · this NEP makes the mismatch a
check-time refusal with a one-line repair in either honest direction.

## Specification

Definitions (normative · closed):

- **CODE-BEARING CLASS (v1)** · three classes, each justified by a
  named RCE mechanism, matched CASE-INSENSITIVELY on the final
  extension of the resolved URL's PATH:
  - *serialized-executable* (the deserializer executes at load):
    `.pkl` `.pickle` `.dill` `.joblib` `.pt` `.pth` `.ckpt`
  - *script/interpreter* (the artifact is a program):
    `.py` `.sh` `.bash` `.zsh` `.ps1` `.bat` `.cmd` `.rb` `.pl`
    `.php` `.js` `.mjs` `.ipynb`
  - *executable binary/module*:
    `.exe` `.dll` `.so` `.dylib` `.wasm` `.jar`
  The list is CLOSED and normative; only a NEP amends it. Deliberate
  exclusions: `.safetensors` (the safe tensor format · its existence
  is the argument), `.npy`/`.npz` (the loader does not execute by
  default since numpy 1.16.3), archives (`.zip`/`.tar.*` · every
  dataset is a tarball; the INNER artifact is judged at its consumer ·
  declared residual), templates (the extension signal is too weak ·
  declared residual).
- **RESOLVED URL** · the `nika:fetch` `url` argument, literal, or
  resolved at check through the NEP-0004 rules (a `${{ }}` island over
  `const.*`, or over `inputs.*`/`config.*` carrying a declared
  default). A URL not resolvable at check DEFERS to the run-time
  twin · never a static refusal.
- **THE INERT DOOR** · the task-level `inert: "<because>"` key
  (non-empty string · the justification). Authored, check-visible,
  greppable. It lifts THIS law only.

The law (MUST):

1. An engine MUST refuse at check a `nika:fetch` whose resolved URL
   path names a code-bearing class · `NIKA-SEC-008` (security_error ·
   blocking) · the diagnostic names the class, the extension, and both
   repairs.
2. The task-level `inert: "<because>"` declaration lifts law 1 for its
   task. It never lifts the `net.http` boundary, the SSRF floor, or
   the NEP-0004 taint re-gate · the door declares the READ inert, it
   widens nothing.
3. An engine MUST refuse the same class at run on the RESOLVED URL
   (`NIKA-SEC-004` · defense in depth · the dynamic case the static
   judge defers), honoring the same declared door.
4. Classification reads the URL PATH only · query and fragment carry
   no verdict (a `?file=x.py` query is not a `.py` path · declared).
   Byte-sniffing and magic-byte classification are out of scope in v1
   (declared residual · a future NEP may harden the run-time twin).
5. The grammar gains exactly one optional task-level key (`inert:`) ·
   additive · no version marker.

Registry and prose touched:

- **LAW-AUTH-0327** is added to `canon/laws/authority.yaml` (status
  active) · the machine row of this law.
- `spec/10-authority.md` gains « The data-as-code sink (normative) » ·
  `stdlib/builtins-v0.1.md` §nika:fetch gains the class pointer.
- `canon/diagnostics/registry.yaml` gains `NIKA-SEC-008` (the slot the
  F-O1 analysis confirmed free · the flow family carries the sink).
- `schemas/workflow.schema.json` gains the task `inert` key.
- Implementation surfaces: the schema parser (the door key) · the
  check (the classifier · the deferral) · the fetch builtin (the
  run-time twin) · the reference oracle (the same closed list ·
  engine/reference differential per LAW-AUTH-0319).

## Conformance test

Five static pairs ship in `conformance/tests/core/authority/`
(018-022, continuing the NEP-0005 suite) plus one behavioral contract
(`runtime/permits/007` · the deferred dynamic case). One fixture per
class keeps the two mirrored lists honest.

## Compatibility impact

Additive for every file in the reference corpora (census at engine
7cf8d2ba7 and spec aa96468: zero conformance, example, or template
workflow fetches a code-bearing URL). The one flip is deliberate and
inside the engine's own adversarial suite: the `f1-02` attack fixture
fetches `install.sh` and is exactly what this law now catches at
check · the fixture's expected verdict gains the static finding (the
attack is refused EARLIER, the same reclassification story as F-O1's
f3-03).

## Migration plan

**What changes for you.** A `fetch` of a `.pkl`, a `.sh`, a `.py`, an
executable · refused at check with both repairs in the error:

```
error[NIKA-SEC-008]: task `grab` fetches a code-bearing artifact (script class · `.sh`)
  · https://news.example/install.sh is a program, not data · the read hides an execution sink
  · fix: model the acquisition as the exec it feeds (exec: + a program permit) · reviewable authority
  · or declare the read inert on the task: inert: "archived for provenance · never loaded or run"
```

When the read genuinely never feeds an interpreter (archival ·
scanning · provenance), declare it:

```yaml
tasks:
  grab:
    invoke:
      tool: nika:fetch
      args: { url: "https://data.example.com/legacy-model.pkl" }
    inert: "archived for provenance · never loaded by any child of this workflow"
```

One greppable line; review sees every declared exception. Nothing else
changes: hosts still bind under `net.http`, the SSRF floor still
refuses, dynamic URLs still re-gate at run.

## Rejected alternatives

- **Classify by Content-Type** · rejected: the header is
  server-controlled · the attacker names their own class.
- **Classify at extract-time** · rejected: too late, the bytes landed;
  check-time is where review happens.
- **An allowlist of inert extensions** · rejected: the inert world is
  unbounded; the code-bearing set is the small closed one.
- **Auto-reclassify the fetch as exec** · rejected: a verb that
  silently changes meaning is magic; the author declares, the engine
  refuses.
- **A per-URL door (`inert_urls:` list)** · rejected: the task is the
  reviewable unit; one fetch per task is already the shape the taint
  laws assume.
- **Extending the law to `nika:notify`** · rejected: notify is egress
  (it posts OUT); the sink this NEP names is the read.
