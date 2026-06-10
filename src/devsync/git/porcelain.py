"""
Thin wrappers around git plumbing/porcelain commands.

Each function shells out to git for a single repo and returns parsed results.
Kept deliberately dumb: no policy decisions here, just data extraction. The
audit module turns this data into backup decisions.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileStatus:
    xy: str
    path: str


@dataclass
class BranchInfo:
    branch: str
    upstream: str
    track: str


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in the given repo and return the CompletedProcess."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def has_remote(repo: Path) -> bool:
    """Return True if the repo has at least one remote configured."""
    result = _git(repo, "remote")
    return result.returncode == 0 and bool(result.stdout.strip())


def is_detached_head(repo: Path) -> bool:
    """Return True if the repo is in a detached HEAD state."""
    # symbolic-ref fails (nonzero) when HEAD is not a branch ref -> detached
    result = _git(repo, "symbolic-ref", "-q", "HEAD")
    return result.returncode != 0


def has_stash(repo: Path) -> bool:
    """Return True if the repo has any stashed changes."""
    return bool(_git(repo, "stash", "list").stdout.strip())


def status_porcelain(repo: Path) -> list[FileStatus]:
    """Return a FileStatus per changed file. xy is the 2-char code; '??' means untracked."""
    out: list[FileStatus] = []

    for line in _git(repo, "status", "--porcelain").stdout.splitlines():
        if len(line) >= 3:
            out.append(FileStatus(xy=line[:2], path=line[3:]))
    return out


def branch_tracking(repo: Path) -> list[BranchInfo]:
    """
    Return a BranchInfo per local branch.

    upstream is '' when no upstream is configured. track contains tokens like
    '[ahead 2]' or '[gone]' from git's %(upstream:track) format.
    """
    result = _git(repo, "for-each-ref", "--format=%(refname:short)%09%(upstream)%09%(upstream:track)", "refs/heads")

    rows: list[BranchInfo] = []

    for line in result.stdout.splitlines():
        parts = line.split("\t")
        name = parts[0] if parts else "?"
        upstream = parts[1] if len(parts) > 1 else ""
        track = parts[2] if len(parts) > 2 else ""
        rows.append(BranchInfo(branch=name, upstream=upstream, track=track))
    return rows
