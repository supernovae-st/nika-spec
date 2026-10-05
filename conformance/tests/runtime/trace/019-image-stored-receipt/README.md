# 019-image-stored-receipt

Law: [17 §Harness image observations](../../../../../spec/17-trace.md#harness-image-observations-additive).

This is an explicitly synthetic additive variant of the real chained golden001.
It asserts one journal receipt and its terminal count, not a model call or a stored file.
`complete: true` describes the observation sequence; even a complete
sequence with `storage: none/failed/unconfirmed` proves no successful storage.
The stored case checks the receipt's metadata link, never current blob availability.
A path claim is not opened; no byte payload is inline. `provenance.json` records construction.

The declared clean native walk still requires execution against an integrated media engine.
Offline reader tests do not qualify that engine or its TUI/CLI projection.
