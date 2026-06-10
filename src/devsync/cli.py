"""
Command-line interface for devsync.
"""

import argparse
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from devsync.config import Config, load_config
from devsync.git import GitDecision, audit_tree
from devsync.infra import setup_logging
from devsync.lock import LockError, single_instance_lock
from devsync.orchestrator import report_audit, run_pipeline

logger = logging.getLogger("devsync")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devsync",
        description="Backup a development folder to a cloud remote, safely.",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Path to config.toml (default: <project root>/config.toml)",
    )

    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=None,
        help="Preview only; pass --dry-run to rclone on both legs.",
    )

    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Run the git audit only and print the report, no syncing.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config: Config = load_config(args.config)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except ValidationError as e:
        print(f"Invalid configuration in {args.config}:\n{e}", file=sys.stderr)
        return 2

    log_file = setup_logging(config.paths.resolved_log_dir(), verbose=args.verbose)
    logger.debug("Logging to %s", log_file)

    if args.audit_only:
        junk = config.exclude.directories
        statuses = audit_tree(config.paths.source, ignore_untracked_globs=junk)
        report_audit(statuses)
        for s in statuses:
            mark = "EXCLUDE" if s.decision == GitDecision.EXCLUDE_GIT else "KEEP"
            logger.info("  [%s] %s :: %s", mark, s.path, "; ".join(s.reasons))
        return 0

    lock_file = config.paths.resolved_work_dir() / ".devsync.lock"

    try:
        with single_instance_lock(lock_file):
            return run_pipeline(config, args.dry_run)
    except LockError as e:
        logger.error(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
