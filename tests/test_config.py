"""Smoke test for config loading and validation."""
# ruff: noqa: F811

from pathlib import Path

import pytest
from pydantic import ValidationError

from devsync.config import load_config


def test_valid_config(valid_config: Path) -> None:
    config = load_config(valid_config)

    assert config.paths.source.exists()
    assert config.rclone.mode == "copy"
    assert config.machine.resolved_name() == "test-machine"


def test_missing_source_fails(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text('[paths]\nsource = "/does/not/exist"\nlocal_destination = "/also/does/not/exist"\n')

    with pytest.raises(ValidationError):
        load_config(config_file)


def test_destination_in_source_fails(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f'[paths]\nsource = "{source.as_posix()}"\nlocal_destination = "{(source / "mirror").as_posix()}"\n'
    )

    with pytest.raises(ValidationError):
        load_config(config_file)
