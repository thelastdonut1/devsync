"""
Collect .backupignore files and translate them into rclone filter rules.

Two behaviors mirroring .gitignore:

1. A `.backupignore` file of patterns -> each becomes an rclone exclude rule
   ANCHORED to the directory the file lives in.

2. A `.backupignore-all` file -> the whole directory is dropped via rclone's
   native --exclude-if-present (handled in the runner; collected here)

Pattern translation (gitignore-like, deliberately simple):
  - Blank lines and '#' comments ignored
  - Leading '!' un-ignore is unsupported (warns and skips)
  - Trailing '/' -> directory: emit '<anchor>/<pattern>/**'
  - Pattern containing '/' -> anchored as-is to the file location
  - Bare name/glob -> matches in this dir and any depth below it
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

IGNORE_FILENAME = ".backupignore"
EXCLUDE_DIR_MARKER = ".backupignore-all"


def find_ignore_files(root: Path) -> list[Path]:
    """Recursively find all .backupignore files under root."""
    return sorted(root.rglob(IGNORE_FILENAME))


def _anchor_for(ignore_file: Path, root: Path) -> str:
    relative = ignore_file.parent.relative_to(root).as_posix()
    return "" if relative == "." else f"{relative}/"


def translate_line(line: str, anchor: str) -> list[str]:
    """Translate one .backupignore pattern line into rclone exclude rule(s)."""
    raw = line.strip()

    # Blank lines and comments are ignored
    if not raw or raw.startswith("#"):
        return []

    # Un-ignore patterns (starting with '!') are not supported
    if raw.startswith("!"):
        logger.warning(f"Un-ignore patterns are not supported; skipping: {line}")
        return []

    is_dir = raw.endswith("/")
    pattern = raw.rstrip("/")

    if is_dir:
        return [f"- {anchor}/{pattern}/**"]

    if "/" in pattern:
        return [f"- {anchor}/{pattern}"]

    return [f"- {anchor}/{pattern}", f"- {anchor}/**/{pattern}"]


def collect_rules(root: Path) -> tuple[list[str], list[str]]:
    """Return (exclude_rule_lines, dirs_with_all_marker)"""
    rules: list[str] = []
    marker_dirs: list[str] = []

    for ig in find_ignore_files(root):
        anchor = _anchor_for(ig, root)

        try:
            text = ig.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read {ig}: {e}")
            continue

        for line in text.splitlines():
            rules.extend(translate_line(line, anchor))

    for marker in root.rglob(EXCLUDE_DIR_MARKER):
        marker_dirs.append(marker.parent.relative_to(root).as_posix())

    return rules, marker_dirs
