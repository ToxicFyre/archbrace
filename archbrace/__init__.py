"""
Purpose:
    Archbrace is a deterministic architectural linter for Python. This package
    exposes the analysis engine, rule catalog, reporting, and command-line entry
    point.

Inputs:
    Python source files and ``pyproject.toml`` configuration.

Outputs:
    Architectural diagnostics rendered as text or JSON.

Side effects:
    None at import time.

Failure behavior:
    Submodules raise ``ArchbraceError`` subclasses for configuration, parsing,
    and execution failures.
"""

from __future__ import annotations

__all__ = ["__version__"]


def _resolve_version() -> str:
    """
    Inputs:
        None.

    Outputs:
        The installed distribution version string, or ``"0.0.0"`` when the
        package is not installed (for example, running from a source checkout
        without an editable install).

    Side effects:
        None.

    Failure behavior:
        Never raises; falls back to ``"0.0.0"`` when metadata is unavailable.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("archbrace")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _resolve_version()
