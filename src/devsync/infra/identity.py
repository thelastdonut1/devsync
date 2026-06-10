import tomllib
from functools import cache
from importlib.metadata import metadata
from importlib.metadata import version as _version
from pathlib import Path

from devsync.infra import locate

__all__ = [
    "DIST_NAME",
    "dist_name",
    "name",
    "version",
    "info",
    "reset_caches",
]

# Per project variables (the only lines you should need to edit)

#: Installed distribution name, e.g. "mhm-data-pipeline".
#: Leave as None to derive it from pyproject.toml [project].name.
DIST_NAME: str | None = None

#: Version reported when neither installed metadata nor pyproject is available.
DEFAULT_VERSION: str = "0.0.0"


# ----- pyproject + distribution metadata -----


@cache
def _pyproject() -> dict:
    """Parsed pyproject.toml at the root, or {} if absent/unreadable."""
    path = locate.root() / "pyproject.toml"

    if not path.is_file():
        return {}

    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _project_table() -> dict:
    """Contents of the [project] table in pyproject.toml, or {} if absent."""
    return _pyproject().get("project", {})


@cache
def dist_name() -> str:
    """The distribution name used for importlib.metadata lookups."""
    if DIST_NAME:
        return DIST_NAME

    if from_toml := _project_table().get("name"):
        return from_toml

    # Fallback to the containing package's directory name
    return Path(__file__).resolve().parent.name


@cache
def name() -> str:
    """Canonical project name: installed metadata first, then pyproject.toml."""
    try:
        return metadata(dist_name())["Name"]
    except Exception:
        pass

    return _project_table().get("name", dist_name())


@cache
def version() -> str:
    """
    Version string: installed metadata first, then pyproject.toml, then DEFAULT_VERSION.

    Note: if you run from a source checkout that is *newer* than the installed
    distribution, installed metadata wins and may be stale. Reinstall the package
    to keep them in sync.
    """
    try:
        return _version(dist_name())
    except Exception:
        pass

    return _project_table().get("version", DEFAULT_VERSION)


def info() -> dict[str, str]:
    """`{'name': ..., 'version': ...}`. Convenience for manifest generation and the like."""
    return {"name": name(), "version": version()}


# ----- Test support -----


def reset_caches() -> None:
    """Clear all memoized values across both locate and identity.

    Needed in tests that monkeypatch environment overrides after these modules
    have already resolved paths, since @cache snapshots the first answer.
    Because identity depends on locate, this clears both so a re-resolved root
    propagates into name()/version() lookups.
    """
    locate.reset_caches()
    for fn in (_pyproject, dist_name, name, version):
        fn.cache_clear()
