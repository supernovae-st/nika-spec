---
name: nika-project-os-ui
description: Verify and repair the browser-only presentation layer of the public Nika GitHub Project from project/project-os.yaml. Use when Codex must audit, restore, or screenshot the eight Project views and six Insights charts, investigate UI drift that GitHub's API cannot expose, or run the scheduled Nika Project OS UI guardian. Never use it to edit Project items, field values, field options, workflows, repository links, dates, descriptions, or SSOT content.
---

<!-- SPDX-License-Identifier: Apache-2.0 -->

# Nika Project OS UI Guardian

Treat `project/project-os.yaml` as the only UI contract. Repair GitHub's
browser-only projection without becoming a second data writer.

## Resolve the repository

Use the current repository when it contains `project/project-os.yaml`.
Otherwise locate the canonical `nika-spec` checkout from the current Nika
venture. Never hard-code a temporary worktree path.

## Prove before touching Chrome

1. Read `project/project-os.yaml`.
2. Run:

   ```bash
   nika check project/project-os-audit.nika.yaml
   ```

3. For an explicitly armed Codex automation, run the deterministic preflight:

   ```bash
   nika run project/project-os-audit.nika.yaml --max-cost-usd 0
   ```

   The workflow contains no model task. Outside an armed automation, propose
   this line and let the human run it.

Stop without UI mutation if any preflight fails. Do not hide projector or
SSOT drift with browser edits.

## Audit the API-visible shell

Use authenticated `gh api graphql` read calls to verify:

- the Project title and number;
- exactly the declared view names and layouts;
- the existence of every field referenced by a view or Insight;
- the native `Status` vocabulary.

The API snapshot is evidence, not the browser-only truth. GitHub does not
expose all filters, grouping, sorting, field visibility, roadmap settings, or
Insight configuration.

## Audit and repair the browser-only layer

Use the Computer Use skill with Chrome. Re-query the current app state before
every action because element indices are ephemeral.

For each declared view, compare the manifest with the live UI:

- name and layout;
- filter;
- grouping or board columns;
- complete sort order and direction;
- visible fields in order;
- roadmap start, target, markers, and zoom.

Then compare all declared Insights:

- chart name and type;
- X axis;
- group-by field.

Repair only observed drift. Save every changed view or chart immediately.
Prefer rename and reconfiguration over deletion or recreation. After a
repair, reload the Project and re-check the changed surface.

## Hard boundaries

Never:

- edit, add, remove, or reorder Project items;
- edit field values, field options, project README, description, or links;
- create a field;
- set any date on a gate;
- touch Project workflows;
- delete a view or Insight unless the manifest explicitly replaces it and the
  human authorizes deletion;
- infer a configuration when Chrome is unauthenticated or the UI cannot be
  read reliably.

Treat `views` and `insights` as the only repairable surfaces.
Treat `built_in_workflows` as observe-and-report only.

## Receipt

Stay quiet when everything matches. When drift is found, report:

- surfaces inspected;
- exact before and after values;
- saved repairs;
- unresolved blockers;
- screenshots of changed surfaces.

Always include the Nika preflight verdict and finish with a second inspection
of every changed surface.
