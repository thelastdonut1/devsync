"""
Command-line interface for devsync.
"""

import argparse
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

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
        default=Path("config.toml"),
        help="Path to config.toml (default: ./config.toml)",
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

    # 1. Try and load config file
    # 2. Setup logging
    # 3. Handle audit-only flag
    # 4. Run the sync

    pass


if __name__ == "__main__":
    sys.exit(main())
