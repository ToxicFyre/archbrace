"""Unit tests for rule selection, severity overrides, and execution (spec 5.2, 9.4, 11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from archbrace.config import ArchbraceConfig
from archbrace.errors import RuleExecutionError
from archbrace.models import Diagnostic, ProjectIndex, SourceRange
from archbrace.rules import Rule, apply_severity, run_rules, select_rules


def _project() -> ProjectIndex:
    return ProjectIndex(
        root=Path("."), modules=(), import_graph=None, call_graph=None, diff=None
    )


def _config(**kwargs: object) -> ArchbraceConfig:
    return ArchbraceConfig(config_path=None, root=Path("."), **kwargs)  # type: ignore[arg-type]


def _diag(code: str, severity: str = "error") -> Diagnostic:
    return Diagnostic(
        code=code,
        name=code.lower(),
        path=Path("m.py"),
        location=SourceRange(line=1, column=1),
        message="msg",
        severity=severity,  # type: ignore[arg-type]
    )


class _FixedRule(Rule):
    def __init__(self, code: str) -> None:
        self.code = code
        self.name = code.lower()
        self.description = "test rule"
        self.default_severity = "error"

    def check(self, project: ProjectIndex, config: ArchbraceConfig) -> list[Diagnostic]:
        return [_diag(self.code)]


class _BoomRule(_FixedRule):
    def check(self, project: ProjectIndex, config: ArchbraceConfig) -> list[Diagnostic]:
        raise ValueError("kaboom")


def test_select_by_prefix() -> None:
    rules = [_FixedRule("AR001"), _FixedRule("AR040"), _FixedRule("AR101")]
    selected = select_rules(rules, select=("AR0",), ignore=())
    assert {r.code for r in selected} == {"AR001", "AR040"}


def test_explicit_ignore_beats_prefix_select() -> None:
    rules = [_FixedRule("AR001"), _FixedRule("AR040")]
    selected = select_rules(rules, select=("AR",), ignore=("AR040",))
    assert {r.code for r in selected} == {"AR001"}


def test_full_code_select() -> None:
    rules = [_FixedRule("AR001"), _FixedRule("AR040")]
    selected = select_rules(rules, select=("AR001",), ignore=())
    assert {r.code for r in selected} == {"AR001"}


def test_apply_severity_overrides() -> None:
    diagnostics = [_diag("AR001", "error"), _diag("AR040", "error")]
    result = apply_severity(diagnostics, {"AR001": "warning"})
    by_code = {d.code: d.severity for d in result}
    assert by_code == {"AR001": "warning", "AR040": "error"}


def test_run_rules_aggregates_and_applies_severity() -> None:
    rules = [_FixedRule("AR001"), _FixedRule("AR040")]
    config = _config(select=("AR",), severity={"AR040": "warning"})
    diagnostics = run_rules(rules, _project(), config)
    by_code = {d.code: d.severity for d in diagnostics}
    assert by_code == {"AR001": "error", "AR040": "warning"}


def test_run_rules_respects_selection() -> None:
    rules = [_FixedRule("AR001"), _FixedRule("AR040")]
    config = _config(select=("AR001",))
    diagnostics = run_rules(rules, _project(), config)
    assert [d.code for d in diagnostics] == ["AR001"]


def test_rule_failure_is_not_silently_swallowed() -> None:
    rules = [_BoomRule("AR999")]
    config = _config(select=("AR",))
    with pytest.raises(RuleExecutionError, match="AR999"):
        run_rules(rules, _project(), config)
