"""
Purpose:
    Default path exclusion patterns for Archbrace discovery.

Why is this in this project:
    Keeps ``config.py`` focused on loading while sharing Ruff-aligned excludes.

Inputs:
    None at import time.

Outputs:
    The ``DEFAULT_EXCLUDE`` pattern tuple.

Side effects:
    None.

Failure behavior:
    Pure constant definitions.
"""

from __future__ import annotations

# Match Ruff's built-in ``exclude`` defaults so ``archbrace check .`` skips the
# same non-project paths without extra configuration.
# https://docs.astral.sh/ruff/configuration/
DEFAULT_EXCLUDE: tuple[str, ...] = (
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".git-rewrite",
    ".hg",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".pyenv",
    ".pytest_cache",
    ".pytype",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    ".vscode",
    "__pypackages__",
    "_build",
    "buck-out",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "venv",
)
