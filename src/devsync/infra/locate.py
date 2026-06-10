import os
import sys
from functools import cache
from pathlib import Path

__all__ = [
    "ENV_PREFIX",
    "is_frozen",
    "root",
    "settings_dir",
    "settings_file",
    "assets_dir",
    "asset",
    "resource",
    "validate",
    "reset_caches",
]


# Per project variables (the only lines you should need to edit)

#: Prefix for environment variable overrides. With "MYAPP" you get
#: MYAPP_ROOT, MYAPP_SETTINGS_DIR, MYAPP_SETTINGS_FILE, etc.
#: Prefixing avoids the collision you'd get if two projects on one
#: machine both used ROOT, SETTINGS_DIR, etc.
ENV_PREFIX: str = "MYAPP"

#: Files/dirs whose presence indicates the project root. Order matters: first hit
#: while walking upwards wins. Deliberately excludes README.md (too common in
#: subdirectories to be a reliable anchor).
ROOT_MARKERS: tuple[str, ...] = ("pyproject.toml", ".git")


# ----- Internals -----


def _env(suffix: str) -> str | None:
    """Read a namespaced override, e.g. _env('ROOT') -> $MYAPP_ROOT."""
    return os.environ.get(f"{ENV_PREFIX}_{suffix}")


def is_frozen() -> bool:
    """True when running inside a PyInstaller (or similar) frozen executable."""
    return bool(getattr(sys, "frozen", False))


# ----- Root discovery -----


@cache
def root() -> Path:
    """
    Resolve the project root, in priority order:

    1. `$<ENV_PREFIX>_ROOT` override (CI, containers, tests)
    2. Frozen build: `sys._MEIPASS` (one-file) or the executable's directory (one-folder)
    3. Walk upward from this file looking for ROOT_MARKERS
    4. src-layout heuristic: `.../src/<project>/locate.py` -> parent of `src`
    5. Last resort: this file's directory
    """
    if override := _env("ROOT"):
        return Path(override).resolve()

    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)

        if meipass is not None:
            return Path(meipass)
        return Path(sys.executable).resolve().parent

    here = Path(__file__).resolve()

    for parent in here.parents:
        if any((parent / marker).exists() for marker in ROOT_MARKERS):
            return parent

    for parent in here.parents:
        if parent.name == "src":
            return parent.parent

    return here.parent


# ----- Well-known paths -----


def _named_dir(env_suffix: str, default_name: str) -> Path:
    if override := _env(env_suffix):
        return Path(override)
    return root() / default_name


def settings_dir() -> Path:
    """<root>/settings (override: $<ENV_PREFIX>_SETTINGS_DIR)"""
    return _named_dir("SETTINGS_DIR", "settings")


def settings_file() -> Path:
    """<settings_dir>/settings.json (override: $<ENV_PREFIX>_SETTINGS_FILE)"""
    if override := _env("SETTINGS_FILE"):
        return Path(override)
    return settings_dir() / "settings.json"


def assets_dir() -> Path:
    """<root>/assets (override: $<ENV_PREFIX>_ASSETS_DIR)"""
    return _named_dir("ASSETS_DIR", "assets")


def asset(relative: str) -> Path:
    """Path to a bundled asset, e.g. asset("logo.png")"""
    return assets_dir() / relative


def resource(*parts: str) -> Path:
    """Generic root-relative path, e.g. `resource("data", "schema.sql")`."""
    return root().joinpath(*parts)


# ----- Validation (explicit, not import-time) -----


def validate(*paths: Path) -> None:
    """
    Raise RuntimeError if any of the given paths is missing.

    Call this once in your application entry point to get fail-fast
    validation of critical resources without import-time side effects.
    for tests and tooling.

    Example:

        def main():
            validate(settings_file(), asset("logo.png"))

    """
    missing = [str(p) for p in paths if not p.exists()]

    if missing:
        raise RuntimeError(f"Required project paths not found (root={root()}): " + ", ".join(missing))


# ----- Test support -----


def reset_caches() -> None:
    """
    Clear memoized values owned by this module.

    Needed in tests that monkeypatch environment overrides after this module
    has already resolved paths, since @cache snapshots the first answer.
    """
    root.cache_clear()
