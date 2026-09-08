# Open defect: classification can read unstaged evidence

Confirmed on `09f5283` and still present after the targeted provenance
hardening: content hashes and tracked membership describe the index, but
`_load_rules()` imports `scripts/estate_rules.py` from disk and gives the
module the working-tree `ROOT`. Those rules are arbitrary Python. Rules
which inspect a marker with `(ROOT / path).read_text()` classify disk bytes
even when the manifest hashes a different, staged blob.

An unstaged rules edit can likewise change the emitted classification. The
warning about unstaged files is useful, but it does not establish a single
snapshot for the manifest's evidence and hashes. A clean worktree avoids
this particular discrepancy; a dirty worktree is not fully deterministic
with respect to the index alone.

## Reproduce without changing this checkout

From the repository root, on a stock Python interpreter:

```sh
python3 - <<'PY'
import importlib.util
import pathlib
import sys
import tempfile

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("estate_selftest", "scripts/selftest.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
with tempfile.TemporaryDirectory(prefix="estate-open-defect-") as tmp:
    root = pathlib.Path(tmp) / "repo"
    fixture.build(root)
    before = fixture.sh("git", "write-tree", cwd=root, check=True).stdout
    (root / "snippets/projected.md").write_text("plain body\n")
    after = fixture.sh("git", "write-tree", cwd=root, check=True).stdout
    rc, output = fixture.check(root)
    print(f"same index: {before == after}; check exit: {rc}")
    print(output, end="")
    assert before == after and rc == 5
PY
```

Observed: `same index: True; check exit: 5`. The staged marker and content
hash have not changed, but the disk read has changed the row from `generated`
to `authored`. A full index-snapshot guarantee would keep the manifest in
sync and report only the unstaged edit.

## Bounded follow-up

Inventory the actual file, directory and subprocess reads in each carrier's
rules before choosing the rules interface. Then make both the rules source
and its evidence reads use the same staged snapshot. A shared staged-read
helper is one possible migration, but exposing it alone does not fix callers
which still use filesystem reads. A temporary index checkout is another
option whose cost and compatibility with existing rule helpers need proof.

Close the defect with regressions for unstaged marker edits and deletion,
unstaged rule edits, staged counterparts, and generator bootstrap, plus a
clean-carrier comparison that accounts for every manifest change. Keep the
existing per-repo ownership of rules and update mirrored tools through their
declared pin lane. The current patch does not change that interface or any
downstream mirror.
