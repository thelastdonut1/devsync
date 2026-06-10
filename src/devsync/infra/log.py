"""Logging setup: console + timestamped file handler, with log rotation and retention."""

import contextlib
import logging
import sys
from datetime import datetime
from pathlib import Path

KEEP_LOGS = 5


def setup_logging(log_dir: Path, verbose: bool) -> Path:
    """Configure root logging and prune old logs. Returns the active log file."""
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"devsync_{ts}.log"

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    logs = sorted(log_dir.glob("devsync_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)

    for old_log in logs[KEEP_LOGS:]:
        with contextlib.suppress(OSError):
            old_log.unlink()

    return log_file
