"""Typed configuration model for devsync.

Loads a TOML file into a validated Pydantic model so misconfiguration fails
fast with a clear message instead of surfacing as a confusing rclone error
three stages later. Paths are expanded and resolved at load time; the source
must exist, but destinations may not yet (rclone/robocopy create them).
"""

from __future__ import annotations

import socket
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from devsync.infra import locate


def _expand(p: str | Path) -> Path:
    return Path(p).expanduser()


class PathsConfig(BaseModel):
    """Filesystem locations. source must exist; others are created as needed."""

    source: Path
    local_destination: Path
    work_dir: Path | None = None
    log_dir: Path | None = None

    @field_validator("source", "local_destination", "work_dir", "log_dir", mode="before")
    @classmethod
    def _expand_paths(cls, v: str | Path | None) -> Path | None:
        return _expand(v) if v is not None else None

    @field_validator("source")
    @classmethod
    def _source_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"source folder does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"source is not a directory: {v}")
        return v.resolve()

    def resolved_work_dir(self) -> Path:
        return (self.work_dir or self.local_destination.parent / ".devsync").expanduser()

    def resolved_log_dir(self) -> Path:
        return (self.log_dir or locate.root() / "logs").expanduser()


class RcloneConfig(BaseModel):
    """Cloud leg settings. enabled=False skips the cloud sync entirely."""

    enabled: bool = True
    remote_name: str = "gdrive"
    remote_path: str = "DevBackups"
    dry_run: bool = False

    # rclone sync makes the remote mirror the source (deletions propagate).
    # copy never deletes on the remote. Default sync per user choice.
    mode: str = "sync"

    perf_flags: list[str] = Field(
        default_factory=lambda: [
            "--transfers",
            "16",
            "--checkers",
            "16",
            "--fast-list",
            "--drive-use-trash=false",
            "--drive-chunk-size",
            "16M",
        ]
    )

    @field_validator("mode")
    @classmethod
    def _valid_mode(cls, v: str) -> str:
        if v not in ("sync", "copy"):
            raise ValueError(f"rclone.mode must be 'sync' or 'copy', got {v!r}")
        return v


class ExcludeConfig(BaseModel):
    """Global junk excludes. If a list is set it REPLACES the built-in default."""

    directories: list[str] | None = None
    files: list[str] | None = None


class MachineConfig(BaseModel):
    """Per-machine identity. name defaults to the hostname."""

    name: str | None = None

    def resolved_name(self) -> str:
        return self.name or socket.gethostname()


class Config(BaseModel):
    """Top-level devsync configuration."""

    paths: PathsConfig
    rclone: RcloneConfig = Field(default_factory=RcloneConfig)
    exclude: ExcludeConfig = Field(default_factory=ExcludeConfig)
    machine: MachineConfig = Field(default_factory=MachineConfig)

    @model_validator(mode="after")
    def _no_nested_destination(self) -> Config:
        # Guard against the local mirror living inside the source, which would
        # make rclone try to copy the backup into itself.
        try:
            self.paths.local_destination.resolve().relative_to(self.paths.source)
        except ValueError:
            return self  # not nested, good
        raise ValueError(
            f"local_destination must not be inside source({self.paths.local_destination} is within {self.paths.source})"
        )


def load_config(path: Path | None = None) -> Config:
    """Load and validate a TOML config file into a Config model.

    Defaults to config.toml at the project root when no path is given.
    """
    resolved = path or locate.resource("config.toml")

    if not resolved.exists():
        raise FileNotFoundError(f"config not found: {resolved}")

    with open(resolved, "rb") as f:
        raw = tomllib.load(f)

    return Config.model_validate(raw)
