# List available recipes
default:
    @just --list

# Install dependencies + the package
sync:
    uv sync

# Show the git audit, no syncing
audit:
    uv run devsync --audit-only

# rclone --dry-run on both legs
dry-run:
    uv run devsync --dry-run

# Run the real backup
run:
    uv run devsync

# Run the real backup with verbose output
run-verbose:
    uv run devsync -v

# Run tests
test:
    uv run pytest

# Lint
lint:
    uv run ruff check .

# Format
format:
    uv run ruff format .
