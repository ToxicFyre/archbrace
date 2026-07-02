"""Unit tests for Python file discovery and exclusion (spec Sections 5.1 / 9.3)."""

from __future__ import annotations

from pathlib import Path

from archbrace.config import DEFAULT_EXCLUDE, ArchbraceConfig
from archbrace.discovery import discover_python_files


def _config(root: Path, exclude: tuple[str, ...]) -> ArchbraceConfig:
    return ArchbraceConfig(config_path=root / "pyproject.toml", root=root, exclude=exclude)


def _make_tree(root: Path) -> None:
    (root / "pkg" / "sub").mkdir(parents=True)
    (root / "excluded").mkdir()
    (root / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "pkg" / "sub" / "b.py").write_text("y = 2\n", encoding="utf-8")
    (root / "excluded" / "c.py").write_text("z = 3\n", encoding="utf-8")
    (root / "pkg" / "thing.gen.py").write_text("g = 4\n", encoding="utf-8")
    (root / "pkg" / "notes.txt").write_text("hi\n", encoding="utf-8")


def test_discovers_python_files_recursively(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    config = _config(tmp_path, exclude=())
    found = discover_python_files([tmp_path], config)
    names = {p.name for p in found}
    assert names == {"a.py", "b.py", "c.py", "thing.gen.py"}


def test_results_are_sorted_and_deduplicated(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    config = _config(tmp_path, exclude=())
    found = discover_python_files([tmp_path, tmp_path / "pkg"], config)
    assert found == sorted(found)
    assert len(found) == len(set(found))


def test_exclusion_patterns_are_applied(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    config = _config(tmp_path, exclude=("excluded/**", "*.gen.py"))
    found = discover_python_files([tmp_path], config)
    names = {p.name for p in found}
    assert names == {"a.py", "b.py"}


def test_single_file_path_is_supported(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    config = _config(tmp_path, exclude=())
    found = discover_python_files([tmp_path / "pkg" / "a.py"], config)
    assert [p.name for p in found] == ["a.py"]


def test_excluded_single_file_is_dropped(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    config = _config(tmp_path, exclude=("*.gen.py",))
    found = discover_python_files([tmp_path / "pkg" / "thing.gen.py"], config)
    assert found == []


def test_non_python_file_is_ignored(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    config = _config(tmp_path, exclude=())
    found = discover_python_files([tmp_path / "pkg" / "notes.txt"], config)
    assert found == []


def test_default_excludes_skip_common_non_project_paths(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "site.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.py").write_text("z = 3\n", encoding="utf-8")

    config = _config(tmp_path, exclude=DEFAULT_EXCLUDE)
    found = discover_python_files([tmp_path], config)
    assert [p.name for p in found] == ["app.py"]
