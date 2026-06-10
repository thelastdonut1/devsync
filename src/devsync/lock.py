"""
Cross-platform single-instance lock.

Prevents two devsync processes from syncing the same remote concurrently, which can
corrupt the destination. Uses fcntl ob POSIX and msvcrt on Windows.
"""
# ruff: noqa: SIM115

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path


class LockError(Exception):
    """Raised when the lock is already held by another process."""


@contextmanager
def single_instance_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        import msvcrt

        try:
            f = open(lock_path, "w")
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as e:
            f.close()
            raise LockError(f"Another devsync process is in progress ({lock_path})") from e

        try:
            yield
        finally:
            with suppress(OSError):
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            f.close()

    else:
        import fcntl

        try:
            f = open(lock_path, "w")
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            f.close()
            raise LockError(f"Another devsync process is in progress ({lock_path})") from e

        try:
            f.write(str(os.getpid()))
            f.flush()
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
