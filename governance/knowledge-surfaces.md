# Knowledge surfaces and documentation projection

Engineering workflow for projections, not a new runtime language law.

## Authority and identity

The spec owns language contracts, schemas and conformance. `nika-docs` owns user explanations and the public documentation taxonomy. `nika.sh` is a marketing surface: importing a page does not make its category or wording normative.

A canonical entity ID may have several projections. A schema field has the ID `language:word:<name>`; each occurrence retains its schema pointer, scope, requirement and declaration. A reference page groups those occurrences without conflating their contracts. Code files, crates, execution artifacts and similarly titled documents retain their separate identities.

## Deterministic source chain

1. Change the owning schema or source template. Runtime contract changes still require their normal review and conformance fixtures.
2. After the source change is committed, run `python3 scripts/knowledge-projector.py --write` in the spec. The exporter retains a valid pin when input bytes are unchanged; otherwise it selects the latest commit affecting the inputs, verifies their bytes against Git, and records hashes. Generated-only commits and squash merges do not advance a content-identical pin. CI fetches the declared pin before checking it.
3. In the docs checkout, run `python3 scripts/knowledge-mirror.py --write --source ../spec/reference/language-index.json` (adjust the checkout path). This produces reference pages, navigation entries and an exact identity manifest.
4. Run `python3 scripts/verify-knowledge-source.py --spec-root ../spec`, the mirror tests, link audit and existing released-engine gates in docs. All declared schema properties and all source-template occurrences must be accounted for. Excerpts remain visibly identified as fragments; complete runnable examples retain the released-binary judge.
5. Publish through each repository's normal review. A locally generated URL is a candidate, not proof of public availability. Keep guide relationships visibly distinct from exact entity references until public availability is verified.

There is no reverse scraping of the marketing site in this chain. Changes to generated prose are rejected by a byte comparison. User-facing enrichment belongs in an authored docs guide, linked to its generated reference; an implementation-specific workaround must not become an undocumented user contract.

## Publication boundary

Public concepts can have user documentation. Private memories, sessions, credentials, internal code paths and unreviewed receipts are not automatically exported. A related public guide describes behavior, not the private contents of an instance. Mixed-source families require review before publication. Failed tests and missing matches remain visible as gaps; they must not be repaired by inventing links or merging nodes by title.

## Drift and freshness

Checks detect a stale derived artifact at the owning repository's commit boundary. Docs checks also validate their snapshot against pinned Git objects. These are separate from freshness against newer upstream changes: a pinned snapshot may be internally consistent and still be old. The refresh sequence is explicit; this mechanism does not claim autonomous cross-repository publication or zero possible drift.

Docs source verification has a `--current-source` mode that compares the pinned input set with the supplied current owner tree, including template additions and deletions. The exporter visits schema-bearing keywords only: `properties` inside an example/default payload does not declare a field. A shared spelling is not evidence of runtime dependence.

Periodic source checks qualify documentation against its declared inputs. They do not rewrite contracts or publish content automatically.
