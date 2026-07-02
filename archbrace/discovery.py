"""
Purpose:
    Discover the Python source files Archbrace should analyze, honoring the
    configured exclusion patterns.

Why is this in this project:
    Decides exactly which files a run analyzes, keeping exclusion and path
    handling in one place instead of scattered across rules.

Inputs:
    One or more filesystem paths (files or directories) and an
    ``ArchbraceConfig`` providing exclusion patterns and the project root.

Outputs:
    A sorted, de-duplicated list of ``.py`` file paths to analyze.

Side effects:
    Reads directory listings from disk.

Failure behavior:
    Never raises for missing entries; non-existent or non-Python paths simply
    contribute nothing.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from pathlib import Path

import pathspec

from .config import ArchbraceConfig


def discover_python_files(
    paths: Iterable[Path],
    config: ArchbraceConfig,
) -> list[Path]:
    """
    Inputs:
        Paths to scan and the active configuration.

    Outputs:
        A sorted, de-duplicated list of resolved ``.py`` files not matched by any
        exclusion pattern.

    Side effects:
        Walks the filesystem beneath directory paths.

    Failure behavior:
        Never raises; unreadable directory entries are skipped by ``rglob``.
    """
    spec = config.exclude_spec()
    root = config.root.resolve()

    collected: set[Path] = set()
    for entry in paths:
        for candidate in _candidate_files(entry.resolve()):
            if not _is_excluded(candidate, root, spec):
                collected.add(candidate)

    return sorted(collected)


def _candidate_files(resolved: Path) -> Iterator[Path]:
    """Yield the ``.py`` files a single path contributes: a directory's tree, or
    the file itself when it is a Python source file."""
    if resolved.is_dir():
        yield from (
            candidate
            for candidate in resolved.rglob("*.py")
            if candidate.is_file()
        )
    elif resolved.is_file() and resolved.suffix == ".py":
        yield resolved


def _is_excluded(path: Path, root: Path, spec: pathspec.PathSpec) -> bool:
    relative = os.path.relpath(path, root)
    posix = Path(relative).as_posix()
    return spec.match_file(posix)
