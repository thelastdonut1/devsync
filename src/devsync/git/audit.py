"""Decide, per git repo, whether its .git directory needs backing up.

The question for each repo: if this machine died right now, would excluding
.git lose anything not safely on a remote?

  - No remote configured        -> KEEP .git (only copy of history)
  - Detached HEAD                -> KEEP .git (conservative)
  - Remote, but local work ahead -> KEEP .git + WARN (unpushed/uncommitted)
  - Remote, clean, fully pushed  -> EXCLUDE .git (re-cloneable)

"Local work ahead" conservatively covers: uncommitted tracked changes,
untracked files (excluding paths the backup itself ignores, like .venv),
branches with commits not on their upstream or with no upstream, and stashes.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from . import porcelain


class GitDecision(Enum):
    EXCLUDE_GIT = "exclude_git"
    KEEP_GIT = "keep_git"


@dataclass
class RepoStatus:
    path: Path
    decision: GitDecision
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    has_remote: bool = False

    @property
    def needs_attention(self) -> bool:
        return bool(self.warnings)


def _untracked_is_ignorable(path: str, ignore_globs: list[str]) -> bool:
    base = path.rstrip("/")
    name = base.split("/")[-1]
    for g in ignore_globs:
        gg = g.rstrip("/*").rstrip("/")
        if fnmatch.fnmatch(name, g) or fnmatch.fnmatch(base, g) or name == gg:
            return True
    return False


def _dirtiness(repo: Path, ignore_untracked_globs: list[str]) -> list[str]:
    """Blocking reasons from the working tree, or empty if effectively clean."""
    entries = porcelain.status_porcelain(repo)
    if not entries:
        return []
    tracked = [e.path for e in entries if e.xy != "??"]
    untracked = [e.path for e in entries if e.xy == "??"]

    reasons: list[str] = []
    if tracked:
        reasons.append("uncommitted tracked changes")
    real_untracked = [p for p in untracked if not _untracked_is_ignorable(p, ignore_untracked_globs)]
    if real_untracked:
        reasons.append("untracked files present")
    return reasons


def _unpushed(repo: Path) -> list[str]:
    problems: list[str] = []
    for b in porcelain.branch_tracking(repo):
        if not b.upstream:
            problems.append(f"{b.branch} (no upstream)")
        elif "ahead" in b.track or "gone" in b.track:
            problems.append(f"{b.branch} {b.track}".strip())
    return problems


def classify_repo(repo: Path, ignore_untracked_globs: list[str] | None = None) -> RepoStatus:
    ignore_untracked_globs = ignore_untracked_globs or []
    status = RepoStatus(path=repo, decision=GitDecision.KEEP_GIT)
    status.has_remote = porcelain.has_remote(repo)

    if not status.has_remote:
        status.reasons.append("no remote configured")
        status.warnings.append("No remote: .git is the only copy of history")
        return status

    if porcelain.is_detached_head(repo):
        status.reasons.append("detached HEAD")
        status.warnings.append("Detached HEAD: keeping .git to be safe")
        return status

    blocking = _dirtiness(repo, ignore_untracked_globs)
    unpushed = _unpushed(repo)
    if unpushed:
        blocking.append("unpushed branches: " + ", ".join(unpushed))
    if porcelain.has_stash(repo):
        blocking.append("stash entries present")

    if blocking:
        status.reasons.extend(blocking)
        status.warnings.append("Local work not on remote (" + "; ".join(blocking) + ")")
    else:
        status.decision = GitDecision.EXCLUDE_GIT
        status.reasons.append("clean working tree, all branches pushed")
    return status


def find_repos(root: Path) -> list[Path]:
    """Find all dirs containing a .git entry, recursing into nested repos."""
    repos: list[Path] = []

    def walk(d: Path) -> None:
        try:
            entries = list(d.iterdir())
        except (PermissionError, OSError):
            return
        if any(e.name == ".git" for e in entries):
            repos.append(d)
        for e in entries:
            if e.is_dir() and e.name != ".git" and not e.is_symlink():
                walk(e)

    walk(root)
    return repos


def audit_tree(root: Path, ignore_untracked_globs: list[str] | None = None) -> list[RepoStatus]:
    return [classify_repo(r, ignore_untracked_globs) for r in find_repos(root)]
