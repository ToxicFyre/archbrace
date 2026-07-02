"""Unit tests for source scanning and project-index assembly (spec Section 6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from archbrace.config import ArchbraceConfig
from archbrace.errors import AnalysisError
from archbrace.project import build_project_index
from archbrace.scanner import module_name_for, scan_file


def _config(root: Path) -> ArchbraceConfig:
    return ArchbraceConfig(config_path=None, root=root, exclude=())


def _make_repo(root: Path) -> None:
    (root / "pkg" / "sub").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "a.py").write_text("def one():\n    return 1\n", encoding="utf-8")
    (root / "pkg" / "sub" / "mod.py").write_text("VALUE = 2\n", encoding="utf-8")


def test_module_name_for_regular_module(tmp_path: Path) -> None:
    assert module_name_for(tmp_path / "pkg" / "a.py", tmp_path) == "pkg.a"


def test_module_name_for_package_init(tmp_path: Path) -> None:
    assert module_name_for(tmp_path / "pkg" / "__init__.py", tmp_path) == "pkg"


def test_module_name_for_nested(tmp_path: Path) -> None:
    assert module_name_for(tmp_path / "pkg" / "sub" / "mod.py", tmp_path) == "pkg.sub.mod"


def test_scan_file_builds_module_info(tmp_path: Path) -> None:
    path = tmp_path / "thing.py"
    path.write_text("def go():\n    return 0\n", encoding="utf-8")
    module = scan_file(path, tmp_path)
    assert module.module_name == "thing"
    assert [f.name for f in module.functions] == ["go"]


def test_scan_file_missing_raises_analysis_error(tmp_path: Path) -> None:
    with pytest.raises(AnalysisError):
        scan_file(tmp_path / "nope.py", tmp_path)


def test_build_project_index_collects_sorted_modules(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    index = build_project_index([tmp_path], _config(tmp_path))
    names = [m.module_name for m in index.modules]
    assert names == ["pkg", "pkg.a", "pkg.sub.mod"]
    assert [m.path for m in index.modules] == sorted(m.path for m in index.modules)


def test_project_index_graph_fields_are_deferred(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    index = build_project_index([tmp_path], _config(tmp_path))
    assert index.root == tmp_path
    assert index.import_graph is None
    assert index.call_graph is None
    assert index.diff is None
