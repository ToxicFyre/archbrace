"""Tests for AR040 Vague Module Name (spec Section 7.3)."""

from __future__ import annotations

from archbrace.rules.simplicity import VagueModuleNameRule


def test_flags_vague_module_name(index_from, base_config) -> None:
    project = index_from("ar040/utils.py")
    config = base_config()
    diagnostics = VagueModuleNameRule().check(project, config)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR040"
    assert diagnostic.name == "vague-module-name"
    assert diagnostic.location.line == 1
    assert diagnostic.location.column == 1
    assert "utils.py" in diagnostic.message


def test_ignores_concrete_module_name(index_from, base_config) -> None:
    project = index_from("ar040/report_formatter.py")
    assert VagueModuleNameRule().check(project, base_config()) == []


def test_init_module_is_exempt(index_from, base_config) -> None:
    project = index_from("ar040/__init__.py")
    assert VagueModuleNameRule().check(project, base_config()) == []


def test_vague_names_are_configurable(index_from_source, base_config) -> None:
    project = index_from_source({"widgets.py": "x = 1\n"})
    config = base_config(vague_module_names=("widgets",))
    diagnostics = VagueModuleNameRule().check(project, config)
    assert [d.metadata["symbol"] for d in diagnostics] == ["widgets"]
