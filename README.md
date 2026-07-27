# devsync

Back up a development folder (e.g. `C:\Software Development`) to a cloud remote,
across multiple machines, without uploading junk and without blindly dropping
git history that only exists locally.

## What it does

1. **Audits every git repo** under the source and decides, per repo, whether its
   `.git` is safe to skip:
   - No remote configured -> **keep `.git`** (only copy of history).
   - Uncommitted/untracked changes, unpushed commits, stashes, detached HEAD ->
     **keep `.git`** and **warn** (the run proceeds).
   - Clean working tree, all branches pushed -> **exclude `.git`** (re-cloneable).
   Untracked paths that the backup itself excludes (e.g. `.venv`) do not count as
   unsaved work, so clean repos full of build junk still get `.git` dropped.
2. **Generates one rclone filter file** combining `.backupignore` rules, the
   per-repo `.git` decisions, and global junk excludes. Both sync legs use it, so
   the local mirror and the cloud copy stay identical.
3. **Mirrors** source -> a local backup dir.
4. **Syncs** that dir -> `<remote>:<path>/<machine-name>/`, so every machine
   pushes to its own subfolder using the same code.

## Install

Requires Python 3.12+, `git`, and `rclone` on PATH, plus a configured rclone
remote (`rclone config`).

```bash
uv sync                 # install deps + the package
uv run devsync --help
```

Optionally install [`just`](https://github.com/casey/just) to use the
shortcuts in the `justfile` (`just --list` to see them all).

## Usage

```bash
uv run devsync --audit-only        # show the git audit, no syncing
uv run devsync --dry-run           # rclone --dry-run on both legs
uv run devsync                     # real backup
uv run devsync -v                  # verbose (shows rclone commands)
uv run devsync -c path/to/cfg.toml # use a non-default config file
```

Or with `just`:

```bash
just audit          # show the git audit, no syncing
just dry-run        # rclone --dry-run on both legs
just run            # real backup
just run-verbose    # verbose (shows rclone commands)
```

Can also be invoked as `python -m devsync`. Run manually, or wire `devsync`
into Task Scheduler / cron. A lock file prevents overlapping runs.

## Configuration

Edit `config.toml` (validated on load; bad config fails fast with a clear error):

- `paths.source` / `paths.local_destination` — required
- `paths.work_dir` — lock file location (defaults to `<local_destination_parent>/.devsync`)
- `paths.log_dir` — log file location (defaults to `<project_root>/logs`)
- `rclone.enabled` — set to `false` to skip the cloud sync leg entirely (default `true`)
- `rclone.remote_name` — your rclone remote (default `"gdrive"`)
- `rclone.remote_path` — base path on the remote (default `"DevBackups"`)
- `rclone.mode` — `sync` (mirror, deletions propagate) or `copy` (never deletes)
- `[exclude].directories` / `[exclude].files` — global junk patterns (replaces built-in defaults when set)
- `[machine].name` — Drive subfolder (defaults to hostname); normalized to
  lowercase so e.g. `MOMoore-5747` and `momoore-5747` can't end up as two
  separate remote folders

## Per-directory ignores

Drop a `.backupignore` file anywhere to exclude things like `.gitignore` does,
scoped to that directory; use an empty `.backupignore-all` to drop a whole
directory. See `BACKUPIGNORE.md` and `examples/`.

## Project layout

```
src/devsync/
  __main__.py       # enables `python -m devsync`
  cli.py            # arg parsing + entry point
  config.py         # Pydantic config model + validation
  orchestrator.py   # the run pipeline
  lock.py           # single-instance lock
  rclone.py         # command construction + streaming exec
  git/              # porcelain wrappers + backup-safety audit
  filtering/        # .backupignore handling + filter assembly
  infra/
    locate.py       # project root + path discovery
    identity.py     # name/version from installed metadata or pyproject.toml
    log.py          # logging setup + rotation
tests/              # pytest smoke tests
```

## Development

```bash
uv run pytest           # tests
uv run ruff check .     # lint
uv run ruff format .    # format
```

Or with `just`: `just test`, `just lint`, `just format`.