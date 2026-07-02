"""Unit tests for configuration loading, validation, and merging (spec Section 5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from archbrace.config import ArchbraceConfig, find_config, load_config
from archbrace.errors import ConfigError


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_when_no_archbrace_table(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname = 'demo'\n")
    config = load_config(None, start=tmp_path)
    assert config.format == "text"
    assert config.fail_on == "error"
    assert config.select == ("AR",)
    assert config.ignore_rules == ()
    assert config.max_function_lines == 40
    assert "utils" in config.vague_module_names
    assert config.root == tmp_path


def test_reads_archbrace_values(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        """
[tool.archbrace]
format = "json"
fail_on = "warning"
select = ["AR0", "AR1"]
ignore_rules = ["AR101"]
max_function_lines = 25
vague_module_names = ["stuff"]
exclude = ["build/**"]

[tool.archbrace.severity]
AR001 = "warning"
""",
    )
    config = load_config(None, start=tmp_path)
    assert config.format == "json"
    assert config.fail_on == "warning"
    assert config.select == ("AR0", "AR1")
    assert config.ignore_rules == ("AR101",)
    assert config.max_function_lines == 25
    assert config.vague_module_names == ("stuff",)
    assert config.severity["AR001"] == "warning"


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        "[tool.archbrace]\nnot_a_real_key = 1\n",
    )
    with pytest.raises(ConfigError, match="not_a_real_key"):
        load_config(None, start=tmp_path)


def test_wrong_type_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[tool.archbrace]\nmax_function_lines = "lots"\n',
    )
    with pytest.raises(ConfigError, match="max_function_lines"):
        load_config(None, start=tmp_path)


def test_invalid_fail_on_value_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[tool.archbrace]\nfail_on = "boom"\n',
    )
    with pytest.raises(ConfigError, match="fail_on"):
        load_config(None, start=tmp_path)


def test_invalid_severity_value_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[tool.archbrace.severity]\nAR001 = "critical"\n',
    )
    with pytest.raises(ConfigError, match="severity"):
        load_config(None, start=tmp_path)


def test_upward_search_finds_nearest(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[tool.archbrace]\nmax_function_lines = 10\n")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    found = find_config(nested)
    assert found == tmp_path / "pyproject.toml"
    config = load_config(None, start=nested)
    assert config.max_function_lines == 10


def test_explicit_config_path_overrides_search(tmp_path: Path) -> None:
    explicit = _write(
        tmp_path / "custom.toml",
        "[tool.archbrace]\nmax_function_lines = 7\n",
    )
    config = load_config(explicit, start=tmp_path)
    assert config.max_function_lines == 7
    assert config.config_path == explicit


def test_missing_explicit_config_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.toml", start=tmp_path)


def test_merge_cli_overrides_select_and_ignore(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[tool.archbrace]\nselect = ["AR"]\nignore_rules = ["AR101"]\n',
    )
    config = load_config(None, start=tmp_path)
    merged = config.merge_cli(select=("AR001",), ignore=("AR040",))
    assert merged.select == ("AR001",)
    assert merged.ignore_rules == ("AR040",)
    # Original config is unchanged (immutability).
    assert config.select == ("AR",)


def test_merge_cli_with_none_keeps_existing(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", '[tool.archbrace]\nselect = ["AR0"]\n')
    config = load_config(None, start=tmp_path)
    merged = config.merge_cli(select=None, ignore=None)
    assert merged.select == ("AR0",)


def test_exclude_spec_matches_patterns(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        '[tool.archbrace]\nexclude = ["tests/**", "*.gen.py"]\n',
    )
    config: ArchbraceConfig = load_config(None, start=tmp_path)
    spec = config.exclude_spec()
    assert spec.match_file("tests/unit/test_x.py")
    assert spec.match_file("pkg/thing.gen.py")
    assert not spec.match_file("pkg/real.py")
