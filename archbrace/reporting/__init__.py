"""
Purpose:
    Shared reporting helpers: relative path normalization, deterministic
    diagnostic ordering, and severity counting (spec Section 8).

Why is this in this project:
    Shares ordering, path, and severity helpers so the text and JSON reporters
    stay consistent with each other.

Inputs:
    Diagnostics and a base directory for display paths.

Outputs:
    Normalized paths, sorted diagnostics, and severity counts.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed diagnostics.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from ..models import Diagnostic


def relative_path(path: Path, base: Path) -> str:
    """
    Inputs:
        An absolute (or relative) diagnostic path and a base directory.

    Outputs:
        A POSIX-style path relative to ``base`` when possible, else the path's
        POSIX string.

    Side effects:
        None.

    Failure behavior:
        Never raises.
    """
    try:
        return Path(os.path.relpath(path, base)).as_posix()
    except ValueError:
        return path.as_posix()


def sort_diagnostics(
    diagnostics: Iterable[Diagnostic],
    base: Path,
) -> list[Diagnostic]:
    """
    Inputs:
        Diagnostics and the base directory used for path normalization.

    Outputs:
        Diagnostics sorted by normalized path, line, column, code, then message
        (spec Section 8.1).

    Side effects:
        None.

    Failure behavior:
        Never raises.
    """
    return sorted(
        diagnostics,
        key=lambda diagnostic: (
            relative_path(diagnostic.path, base),
            diagnostic.location.line,
            diagnostic.location.column,
            diagnostic.code,
            diagnostic.message,
        ),
    )


def count_severities(diagnostics: Iterable[Diagnostic]) -> tuple[int, int]:
    """
    Inputs:
        Diagnostics.

    Outputs:
        A ``(errors, warnings)`` tuple.

    Side effects:
        None.

    Failure behavior:
        Never raises.
    """
    errors = 0
    warnings = 0
    for diagnostic in diagnostics:
        if diagnostic.severity == "error":
            errors += 1
        elif diagnostic.severity == "warning":
            warnings += 1
    return errors, warnings
