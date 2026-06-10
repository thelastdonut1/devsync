"""
Assemble the rclone --filter-from file.

rclone evaluates rules top-to-bottom, first match wins, and anything matching no
rule is INCLUDED by default. Ordering (highest priority first):

  0. User .backupignore patterns     (explicit user intent)
  1. Per-repo .git excludes          (clean/pushed repos only)
  2. Global junk dirs                (node_modules, .venv, etc)
  3. Global junk files               (*.log, .DS_Store, etc)
  4. (implicit) include everything else

No trailing '- **:': the fallthrough-include is intentional so that KEEP repos'
.git (which have no exclude rule) is carried along. Whole-directory drops via
.backupignore-all are handled by --exclude-if-present in the runner, not here.
"""

from pathlib import Path

from devsync.filtering.backupignore import collect_rules

DEFAULT_JUNK_DIRS = [
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".ipynb_checkpoints",
    "target",
    ".gradle",
    ".next",
    ".turbo",
    "dist",
    "build",
    ".cache",
    ".terraform",
]

DEFAULT_JUNK_FILES = [
    "*.pyc",
    "*.pyo",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
    "*.tmp",
    "*.swp",
]
