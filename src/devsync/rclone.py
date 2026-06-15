"""
rclone command construction and execution.

One function builds a sync/copy command with the shared filter file and the
.backupignore-all marker; another runs it with real-time output streaming so
progress is visible in logs. Both legs (local mirror and cloud) use this.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from devsync.filtering.backupignore import EXCLUDE_DIR_MARKER

logger = logging.getLogger(__name__)


@dataclass
class SyncJob:
    """Assembled, execution-ready rclone job. Built by the caller from Config."""

    mode: str
    src: str
    dst: str
    filter_file: Path
    dry_run: bool = False
    extra_flags: list[str] = field(default_factory=list)


def build_command(job: SyncJob) -> list[str]:
    """Construct an rclone sync/copy command"""
    cmd = ["rclone"]
    cmd += [job.mode, job.src, job.dst]
    cmd += ["--filter-from", str(job.filter_file)]
    cmd += ["--exclude-if-present", EXCLUDE_DIR_MARKER]
    cmd += ["-v", "--stats", "30s"]

    if job.dry_run:
        cmd.append("--dry-run")

    cmd += job.extra_flags
    return cmd


def run(job: SyncJob, label: str = "sync") -> int:
    """Run rclone, streaming output line-by-line. Returns the exit code."""
    cmd = build_command(job)
    logger.info("[%s] %s %s -> %s%s", label, job.mode, job.src, job.dst, " (dry-run)" if job.dry_run else "")
    logger.debug("[%s] command: %s", label, " ".join(cmd))

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        logger.error("rclone not found on PATH. Install rclone and retry.")
        return 127

    if process.stdout:
        for line in process.stdout:
            line = line.rstrip()

            if line:
                logger.info("[%s] rclone: %s", label, line)

    process.wait()
    code = process.returncode or 0

    if code == 0:
        logger.info("[%s] completed successfully", label)
    else:
        logger.error("[%s] failed with exit code %d", label, code)
    return code
