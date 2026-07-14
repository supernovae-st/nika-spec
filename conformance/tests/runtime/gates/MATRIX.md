# The gate-v2 observation matrix (generated)

40 cells · producer state × consumer edge form. 35 run (this
directory) · 5 are statically dead (NIKA-DAG-006 · they live in
`../../deep/023-027`) · vocabulary guard at `../../deep/028`.
Regenerate: `python3 scripts/gen-gate-matrix.py --write` ·
drift gate: `--check` · engine proof: `--prove <nika-cli>`.

| producer \ form | with-value | with-status | with-error | after-succeeded | after-failed | after-skipped | after-terminal | when-true | when-false | no-edge |
|---|---|---|---|---|---|---|---|---|---|---|
| `success` | [010](010-success-x-with-value/) | [014](014-success-x-with-status/) | [018](018-success-x-with-error/) | [022](022-success-x-after-succeeded/) | [025](025-success-x-after-failed/) | `DAG-006` (core) | [029](029-success-x-after-terminal/) | [033](033-success-x-when-true/) | [037](037-success-x-when-false/) | [041](041-success-x-no-edge/) |
| `failure` | [011](011-failure-x-with-value/) | [015](015-failure-x-with-status/) | [019](019-failure-x-with-error/) | [023](023-failure-x-after-succeeded/) | [026](026-failure-x-after-failed/) | `DAG-006` (core) | [030](030-failure-x-after-terminal/) | [034](034-failure-x-when-true/) | [038](038-failure-x-when-false/) | [042](042-failure-x-no-edge/) |
| `skipped` | [012](012-skipped-x-with-value/) | [016](016-skipped-x-with-status/) | [020](020-skipped-x-with-error/) | `DAG-006` (core) | `DAG-006` (core) | [028](028-skipped-x-after-skipped/) | [031](031-skipped-x-after-terminal/) | [035](035-skipped-x-when-true/) | [039](039-skipped-x-when-false/) | [043](043-skipped-x-no-edge/) |
| `cancelled` | [013](013-cancelled-x-with-value/) | [017](017-cancelled-x-with-status/) | [021](021-cancelled-x-with-error/) | [024](024-cancelled-x-after-succeeded/) | [027](027-cancelled-x-after-failed/) | `DAG-006` (core) | [032](032-cancelled-x-after-terminal/) | [036](036-cancelled-x-when-true/) | [040](040-cancelled-x-when-false/) | [044](044-cancelled-x-no-edge/) |
