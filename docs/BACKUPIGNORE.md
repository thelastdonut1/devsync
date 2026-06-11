# .backupignore — a .gitignore for your backup

Drop a `.backupignore` file in any directory under your source folder to control
what gets backed up, scoped to that directory and below — like `.gitignore`, but
for the backup.

## Two tools

### 1. `.backupignore` — pattern excludes (scoped)

Glob patterns, one per line, anchored to the file's directory:

```
# personal/api-investigation/.backupignore
derived/          # exclude this whole subdir
ghidra/
*.rep             # exclude these anywhere below here
*.gpr
```

Rules:
- Blank lines and `#` comments are ignored.
- Trailing `/` means "this directory and everything in it."
- A pattern containing `/` is anchored to the `.backupignore` location.
- A bare name/glob (`*.log`, `__pycache__`) matches at any depth below.
- `!` un-ignore patterns are NOT supported (they make rclone ordering
  surprising); you get a warning if you use one.

### 2. `.backupignore-all` — drop a whole directory

An empty marker file named `.backupignore-all` excludes its entire directory via
rclone's native `--exclude-if-present`, which has priority over all other rules
and skips traversal entirely:

```bash
touch "data/datasets/Stack Overflow Developer Surveys/.backupignore-all"
```

## Precedence (first match wins)

1. `.backupignore-all` markers (whole-dir, highest priority)
2. `.backupignore` patterns
3. Per-repo `.git` audit decisions
4. Global junk defaults
5. Everything else is INCLUDED

## Always dry-run after changing ignores

```bash
uv run devsync --dry-run -v
```

rclone's real filter engine prints exactly what's included/excluded.