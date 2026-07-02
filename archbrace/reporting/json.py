"""
Purpose:
    Render diagnostics as versioned JSON (schema ``"1"``) (spec Section 8.2).

Why is this in this project:
    Gives CI systems and editors a stable, versioned machine-readable form of
    the same diagnostics the text reporter prints.

Inputs:
    Diagnostics, a base directory for display paths, and the scanned-file count.

Outputs:
    A JSON string with ``version``, ``diagnostics``, and ``summary``.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed diagnostics.
"""

from __future__ import annotations

import json as _json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..models import Diagnostic
from . import count_severities, relative_path, sort_diagnostics

SCHEMA_VERSION = "1"


def _diagnostic_to_dict(diagnostic: Diagnostic, base: Path) -> dict[str, Any]:
    location = diagnostic.location
    return {
        "code": diagnostic.code,
        "name": diagnostic.name,
        "path": relative_path(diagnostic.path, base),
        "line": location.line,
        "column": location.column,
        "end_line": location.end_line,
        "end_column": location.end_column,
        "message": diagnostic.message,
        "severity": diagnostic.severity,
        "metadata": diagnostic.metadata,
    }


def render_json(
    diagnostics: Iterable[Diagnostic],
    *,
    base: Path,
    files_scanned: int,
) -> str:
    """
    Inputs:
        Diagnostics, the base directory for relative paths, and the number of
        files scanned.

    Outputs:
        A pretty-printed JSON string following schema version ``"1"``.

    Side effects:
        None.

    Failure behavior:
        Never raises for well-formed diagnostics.
    """
    ordered = sort_diagnostics(diagnostics, base)
    errors, warnings = count_severities(ordered)
    payload = {
        "version": SCHEMA_VERSION,
        "diagnostics": [_diagnostic_to_dict(d, base) for d in ordered],
        "summary": {
            "files_scanned": files_scanned,
            "errors": errors,
            "warnings": warnings,
        },
    }
    return _json.dumps(payload, indent=2)
