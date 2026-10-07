---
name: nika-project-os-ui
description: Inspect the historical Nika GitHub Project without restoring its retired kanban. Use for old Project links or archive questions; current planning is in Linear.
---

<!-- SPDX-License-Identifier: Apache-2.0 -->

# Historical Nika Project

Current priorities and tasks belong to [Linear](https://linear.app/nika-supernovae).
GitHub issues remain public contribution intake; pull requests, CI and releases
remain the code and publication evidence. This Project is an archive.

Read `project/project-os.yaml` from current `nika-spec` to establish retirement.
Its fields and views describe historical records, not a repair target. An old
scheduled guardian invocation does not authorize restoring the board. Do not
reopen it, rebuild views, reconcile cards or enable its former publisher.

For an archive question, inspect the requested existing record read-only and
state its date. Do not infer current work status from historical cards. The
supported local audit is `python3 project/verify.py --offline`; the projector
CLI and live drift audit are retired. For current priorities, use Linear.
