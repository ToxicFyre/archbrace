"""Integration tests for the ``archbrace`` command-line interface (spec Section 4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from archbrace import __version__
from archbrace.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


_CALC_MODULE = (
    '"""\n'
    "Purpose:\n"
    "    Add numbers.\n\n"
    "Why is this in this project:\n"
    "    Provides the arithmetic used by the example package.\n\n"
    "Inputs:\n"
    "    Two addends.\n\n"
    "Outputs:\n"
    "    Their sum.\n\n"
    "Side effects:\n"
    "    None.\n\n"
    "Failure behavior:\n"
    "    Never raises.\n"
    '"""\n\n\n'
    "def add(a, b):\n"
    "    return a + b\n"
)


def _clean_project(root: Path) -> None:
    _write(root / "pyproject.toml", "[tool.archbrace]\n")
    _write(root / "pkg" / "__init__.py", "")
    _write(root / "pkg" / "calc.py", _CALC_MODULE)


def _dirty_project(root: Path, *, severity: str = "error") -> None:
    severity_table = ""
    if severity == "warning":
        severity_table = (
            "\n[tool.archbrace.severity]\n"
            'AR040 = "warning"\n'
            'AR060 = "warning"\n'
            'AR101 = "warning"\n'
        )
    _write(root / "pyproject.toml", f"[tool.archbrace]\n{severity_table}")
    _write(root / "utils.py", '"""Stuff."""\n\n\ndef show(x):\n    print(x)\n')


def test_version_reports_metadata(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"archbrace {__version__}"


def test_check_clean_project_exit_zero(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    _clean_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", "."])
    assert result.exit_code == 0
    assert "Found 0 diagnostics" in result.output


def test_check_reports_diagnostics_and_exits_one(
    runner: CliRunner, tmp_path: Path, monkeypatch
) -> None:
    _dirty_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", "."])
    assert result.exit_code == 1
    assert "AR040" in result.output
    assert "AR101" in result.output
    assert "utils.py" in result.output


def test_check_json_format(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    _dirty_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", ".", "--format", "json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["version"] == "1"
    codes = {d["code"] for d in data["diagnostics"]}
    assert {"AR040", "AR101"} <= codes
    assert data["summary"]["files_scanned"] >= 1


def test_select_limits_rules(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    _dirty_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", ".", "--select", "AR040"])
    assert "AR040" in result.output
    assert "AR101" not in result.output


def test_ignore_suppresses_rule(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    _dirty_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", ".", "--ignore", "AR101"])
    assert "AR040" in result.output
    assert "AR101" not in result.output


def test_fail_on_error_ignores_warnings(
    runner: CliRunner, tmp_path: Path, monkeypatch
) -> None:
    _dirty_project(tmp_path, severity="warning")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", "."])
    # All diagnostics are warnings; default fail_on=error must not fail the run.
    assert result.exit_code == 0
    assert "AR040" in result.output


def test_fail_on_warning_fails_on_warnings(
    runner: CliRunner, tmp_path: Path, monkeypatch
) -> None:
    _dirty_project(tmp_path, severity="warning")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", ".", "--fail-on", "warning"])
    assert result.exit_code == 1


def test_config_error_exits_two(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path / "pyproject.toml", "[tool.archbrace]\nbogus_key = 1\n")
    _write(tmp_path / "m.py", "x = 1\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", "."])
    assert result.exit_code == 2


def test_syntax_error_exits_two(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path / "pyproject.toml", "[tool.archbrace]\n")
    _write(tmp_path / "broken.py", "def broken(:\n    pass\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["check", "."])
    assert result.exit_code == 2
