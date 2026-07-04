# nika-spec · language ADRs

Decision records for the **language surface** (CLI contract · trace/event
vocabulary · spec-section lifts). The reference engine's implementation
ADRs live at [supernovae-st/nika](https://github.com/supernovae-st/nika)
`docs/adr/` — **one shared numbering series, two homes**. Before
allocating a number, check BOTH directories (and the engine's
`docs/adr/index.toml` registry, which decides canonical allocation on
collision) for the next free slot, including in-flight branches.

Format · the engine's `docs/adr/TEMPLATE.md` (YAML frontmatter + Context /
Decision / Consequences / Alternatives / Related / Notes). Status law ·
`proposed` while discussing · `accepted` once the implementation ships ·
supersessions update both files in the same commit.

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
| [ADR-099](adr-099-durable-lite-run-resume.md) | Durable-lite run resume · the trace IS the checkpoint | Proposed | 2026-07-05 |
