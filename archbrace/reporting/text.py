"""
Purpose:
    Render diagnostics as Ruff-like text output with a summary line (spec 8.1).

Inputs:
    Diagnostics, a base directory for display paths, and formatting options.

Outputs:
    A single text string ending with a newline.

Side effects:
    Reads source files only when ``show_source`` is enabled.

Failure behavior:
    Never raises for well-formed diagnostics; unreadable source lines are
    skipped when showing source.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ..models import Diagnostic
from . import count_severities, relative_path, sort_diagnostics

_RESET = "\033[0m"
_RED = "\033[31m"
_YELLOW = "\033[33m"


def _plural(count: int, singular: str) -> str:
    return singular if count == 1 else f"{singular}s"


def _summary(total: int, errors: int, warnings: int) -> str:
    return (
        f"Found {total} {_plural(total, 'diagnostic')}: "
        f"{errors} {_plural(errors, 'error')}, "
        f"{warnings} {_plural(warnings, 'warning')}."
    )


def _colorize(code: str, severity: str, color: bool) -> str:
    if not color:
        return code
    tint = _RED if severity == "error" else _YELLOW
    return f"{tint}{code}{_RESET}"


def _source_line(path: Path, line: int) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return None


def render_text(
    diagnostics: Iterable[Diagnostic],
    *,
    base: Path,
    show_source: bool = False,
    color: bool = False,
) -> str:
    """
    Inputs:
        Diagnostics, the base directory for relative paths, and options for
        source display and coloring.

    Outputs:
        The formatted report text (diagnostic lines, a blank line, and a summary).

    Side effects:
        Reads source files when ``show_source`` is enabled.

    Failure behavior:
        Never raises for well-formed diagnostics.
    """
    ordered = sort_diagnostics(diagnostics, base)
    errors, warnings = count_severities(ordered)

    lines: list[str] = []
    for diagnostic in ordered:
        location = diagnostic.location
        rel = relative_path(diagnostic.path, base)
        code = _colorize(diagnostic.code, diagnostic.severity, color)
        lines.append(
            f"{rel}:{location.line}:{location.column} {code} {diagnostic.message}"
        )
        if show_source:
            source = _source_line(diagnostic.path, location.line)
            if source is not None:
                lines.append(f"    {source}")

    summary = _summary(len(ordered), errors, warnings)
    if not ordered:
        return summary + "\n"
    return "\n".join(lines) + "\n\n" + summary + "\n"
