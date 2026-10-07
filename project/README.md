# Nika planning has moved to Linear

[Linear](https://linear.app/nika-supernovae) owns current priorities and tasks.
The former GitHub Project is a historical archive, not a second kanban.
Public contributions remain welcome through GitHub issues and pull requests;
code, review, CI and releases remain in their owning repositories.

`project-os.yaml` records the archived fields, source identities and views.
Their old status values are historical observations, not current progress.
The reconciliation publisher, source-event triggers, schedule and browser
repair instructions have been retired. The CLI refuses both `--apply` and
`--check` before connecting to GitHub, including when a token is available.
Do not recreate the board from an old checkout or scheduled UI guardian.

The source normalization and reconciliation libraries remain available for
reading historical exports and their regression tests. They are not installed
as a planning integration. Public release history and conditions remain in
`timeline/timeline.yaml`; its existing validation and publication are separate
from the retired Project.

Run the retained offline checks:

```bash
python3 project/verify.py --offline
python3 timeline/verify.py --offline
python3 -m unittest discover -s project -t . -p "test_*.py"
```

The `project-archive-audit` workflow runs these checks on relevant changes and
manual dispatch. It has no Project token, scheduler or mutation job. The
historical `.nika` audit remains an offline example.
