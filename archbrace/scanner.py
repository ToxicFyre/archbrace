"""
Purpose:
    Read a single Python source file from disk and turn it into a ``ModuleInfo``,
    deriving its dotted module name from its path relative to the project root.

Why is this in this project:
    Concentrates the file-read-and-parse boundary so I/O and parse-error handling
    stay consistent for every module.

Inputs:
    A file path and the project root directory.

Outputs:
    A populated ``ModuleInfo``.

Side effects:
    Reads the source file from disk.

Failure behavior:
    Raises ``AnalysisError`` when the file cannot be read or parsed.
"""

from __future__ import annotations

import os
from pathlib import Path

from .analysis.ast_index import build_module_info
from .errors import AnalysisError
from .models import ModuleInfo


def module_name_for(path: Path, root: Path) -> str:
    """
    Inputs:
        A ``.py`` file path and the project root.

    Outputs:
        A dotted module name relative to ``root`` (``pkg/__init__.py`` becomes
        ``pkg``); paths outside ``root`` fall back to the file stem.

    Side effects:
        None.

    Failure behavior:
        Never raises.
    """
    try:
        relative = Path(os.path.relpath(path.resolve(), root.resolve()))
    except ValueError:
        return path.stem

    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else path.stem


def scan_file(path: Path, root: Path) -> ModuleInfo:
    """
    Inputs:
        A ``.py`` file path and the project root.

    Outputs:
        A ``ModuleInfo`` describing the file.

    Side effects:
        Reads the file from disk.

    Failure behavior:
        Raises ``AnalysisError`` when the file cannot be read (spec Section 9.4)
        or contains a syntax error.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AnalysisError(f"{path}: could not read file: {exc}") from exc

    return build_module_info(
        path=path,
        source=source,
        module_name=module_name_for(path, root),
    )
