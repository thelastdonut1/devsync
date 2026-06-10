from pathlib import Path

import pytest


@pytest.fixture
def valid_config(tmp_path: Path) -> Path:
    template = Path(__file__).parent / "data" / "valid_config.toml"

    source = tmp_path / "src"
    source.mkdir()

    dest = tmp_path / "dest"

    body = template.read_text()
    body = body.replace("__SOURCE__", source.as_posix())
    body = body.replace("__DEST__", dest.as_posix())

    config_file = tmp_path / "config.toml"
    config_file.write_text(body)
    return config_file
