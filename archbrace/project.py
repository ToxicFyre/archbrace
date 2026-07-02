"""
Purpose:
    Assemble the single ``ProjectIndex`` for a run by discovering Python files,
    scanning each into a ``ModuleInfo``, and collecting them in a deterministic
    order (spec Sections 6, 9.3).

Inputs:
    Paths to analyze and the active ``ArchbraceConfig``.

Outputs:
    A ``ProjectIndex`` containing all analyzed modules.

Side effects:
    Reads source files from disk via the scanner.

Failure behavior:
    Propagates ``AnalysisError`` from the scanner for unreadable or unparsable
    files (spec Section 9.4). Import/call graphs and diff metadata are deferred
    to later increments and remain ``None``.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .config import ArchbraceConfig
from .discovery import discover_python_files
from .models import ProjectIndex
from .scanner import scan_file


def build_project_index(
    paths: Iterable[Path],
    config: ArchbraceConfig,
) -> ProjectIndex:
    """
    Inputs:
        Paths to scan and the active configuration.

    Outputs:
        A ``ProjectIndex`` with modules sorted by path and no graph/diff data
        (deferred to later increments).

    Side effects:
        Reads discovered source files from disk.

    Failure behavior:
        Raises ``AnalysisError`` when a discovered file cannot be read or parsed.
    """
    files = discover_python_files(paths, config)
    modules = tuple(scan_file(path, config.root) for path in files)
    return ProjectIndex(
        root=config.root,
        modules=modules,
        import_graph=None,
        call_graph=None,
        diff=None,
    )
