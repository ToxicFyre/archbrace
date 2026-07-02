"""Shared pytest fixtures for Archbrace tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from archbrace.analysis.ast_index import build_module_info
from archbrace.config import ArchbraceConfig
from archbrace.models import ProjectIndex
from archbrace.scanner import scan_file

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_root() -> Path:
    return FIXTURES


@pytest.fixture
def index_from() -> Callable[..., ProjectIndex]:
    """Build a ProjectIndex by scanning fixture files under ``tests/fixtures``."""

    def _build(*relpaths: str, root: Path = FIXTURES) -> ProjectIndex:
        modules = tuple(scan_file(root / rel, root) for rel in relpaths)
        return ProjectIndex(
            root=root,
            modules=modules,
            import_graph=None,
            call_graph=None,
            diff=None,
        )

    return _build


@pytest.fixture
def index_from_source() -> Callable[..., ProjectIndex]:
    """Build a ProjectIndex from an in-memory mapping of relative path to source."""

    def _build(files: dict[str, str], root: Path = FIXTURES) -> ProjectIndex:
        modules = tuple(
            build_module_info(
                path=root / rel,
                source=source,
                module_name=rel[:-3].replace("/", "."),
            )
            for rel, source in files.items()
        )
        return ProjectIndex(
            root=root,
            modules=modules,
            import_graph=None,
            call_graph=None,
            diff=None,
        )

    return _build


@pytest.fixture
def base_config() -> Callable[..., ArchbraceConfig]:
    def _make(**kwargs: object) -> ArchbraceConfig:
        return ArchbraceConfig(config_path=None, root=FIXTURES, **kwargs)  # type: ignore[arg-type]

    return _make
