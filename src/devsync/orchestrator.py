"""
The backup pipeline: audit -> filter -> local mirror -> cloud.

This module owns the run sequence and nothing else. Each stage lives in its own
module; the orchestrator wires them together and handles stage-level control
flow (stop on failure, skip disabled cloud leg, report the audit).
"""

from __future__ import annotations

import logging
import time

import devsync.rclone as rclone
from devsync.config import Config
from devsync.filtering import DEFAULT_JUNK_DIRS, build_filter_lines, write_filter_file
from devsync.git import GitDecision, RepoStatus, audit_tree

logger = logging.getLogger(__name__)


def report_audit(statuses: list[RepoStatus]) -> None:
    excl = [s for s in statuses if s.decision == GitDecision.EXCLUDE_GIT]
    keep = [s for s in statuses if s.decision == GitDecision.KEEP_GIT]
    logger.info(
        "Git audit: %d repos | %d .git excluded | %d .git kept",
        len(statuses),
        len(excl),
        len(keep),
    )
    attention = [s for s in statuses if s.needs_attention]
    if attention:
        logger.warning("%d repo(s) need attention (backing up their .git anyway):", len(attention))
        for s in attention:
            logger.warning("  %s -> %s", s.path.name, s.warnings[0])


def run_audit(config: Config, junk_dirs: list[str]) -> list[RepoStatus]:
    logger.info("Auditing git repositories under %s ...", config.paths.source)
    statuses = audit_tree(config.paths.source, ignore_untracked_globs=junk_dirs)
    report_audit(statuses)
    return statuses


def run_pipeline(config: Config, dry_run_override: bool | None = None) -> int:
    source = config.paths.source
    local_dest = config.paths.local_destination
    dry_run = dry_run_override if dry_run_override is not None else config.rclone.dry_run
    junk_dirs = config.exclude.directories or DEFAULT_JUNK_DIRS
    junk_files = config.exclude.files

    statuses = run_audit(config, junk_dirs)

    work_dir = config.paths.resolved_work_dir()
    work_dir.mkdir(parents=True, exist_ok=True)
    filter_file = work_dir / "filter.txt"
    write_filter_file(
        filter_file,
        build_filter_lines(
            source,
            statuses,
            junk_dirs=junk_dirs,
            junk_files=junk_files,
        ),
    )
    logger.info("Filter written to %s", filter_file)

    # Local mirror leg (local->local; always sync to mirror exactly).
    t0 = time.perf_counter()
    job = rclone.SyncJob(
        mode="sync",
        src=str(source),
        dst=str(local_dest),
        filter_file=filter_file,
        dry_run=dry_run,
        extra_flags=["--checkers", "16", "--transfers", "16"],
    )
    code = rclone.run(job, label="local")
    logger.info("Local mirror leg: %.1fs", time.perf_counter() - t0)
    if code != 0:
        return code

    if not config.rclone.enabled:
        logger.info("Cloud leg disabled in config; done.")
        return 0

    if dry_run and not local_dest.exists():
        logger.info("Cloud leg skipped in dry-run: local mirror %s does not exist yet.", local_dest)
        return 0

    remote_dst = f"{config.rclone.remote_name}:{config.rclone.remote_path}/{config.machine.resolved_name()}"
    t1 = time.perf_counter()
    job = rclone.SyncJob(
        mode=config.rclone.mode,
        src=str(local_dest),
        dst=remote_dst,
        filter_file=filter_file,
        dry_run=dry_run,
        extra_flags=config.rclone.perf_flags,
    )
    code = rclone.run(job, label="cloud")
    logger.info("Cloud leg: %.1fs", time.perf_counter() - t1)
    return code
