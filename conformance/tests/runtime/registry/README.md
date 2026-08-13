# Registry admission contracts · LIVE (engine-consumed)

The admission half of [registry-v0.1 §3b](../../../registry/registry-v0.1.md)
(NEP-0016): a real cache record (`record.meta.json` · written by a
conformant client at fetch) plus the operator policy in force, and what
the resolve MUST do. The static gate ignores this tier (no
`input.yaml`); the executable proof is any verb that resolves a
`registry:` reference.

## Contract shape

```
tests/runtime/registry/<NNN-name>/
├── record.meta.json    the cache record under judgment (digest · tier · signed)
├── policy.toml         the operator floor · ABSENT means the default
└── expected.json       { "admitted": bool, "tier": …, "code"?: …, "exit"?: …, "note": … }
```

`policy.toml` being absent is a real fixture state, not a missing file:
the law says an absent policy means `floor = "unprovenanced"`, which is
today's behaviour said out loud instead of assumed.

## Why a pair, and why the records are byte-identical

The two records are the SAME bytes. Only the policy differs, and the
outcomes are opposite: admitted at the default floor, refused at a
raised one. That is the whole of law 4 — **the cache does not
grandfather** — and it is also what makes `001`'s `admitted: true` a
certificate: an admission that survived a raised floor would be proving
nothing about the floor at all.

## Reproducing without touching the host

The cache root is `~/.nika/registry/`. Point `HOME` at a scratch copy
rather than editing the real one — the policy file is operator data and
a floor left behind would refuse that operator's next resolve:

```sh
cp -R ~/.nika/registry "$TMP/.nika/registry"
HOME=$TMP nika check registry:<owner>/<name>@<version>
```
