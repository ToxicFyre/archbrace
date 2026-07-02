"""Tests for AR101 print() Used Instead of Logger (spec Section 7.6)."""

from __future__ import annotations

from archbrace.rules.logging_rules import PrintUsedRule


def test_flags_direct_print_call(index_from, base_config) -> None:
    project = index_from("ar101_print.py")
    diagnostics = PrintUsedRule().check(project, base_config())
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR101"
    assert diagnostic.name == "print-used"
    assert diagnostic.severity == "error"
    assert diagnostic.location.line == 5


def test_ignores_logger_usage(index_from, base_config) -> None:
    project = index_from("ar101_logger.py")
    assert PrintUsedRule().check(project, base_config()) == []


def test_module_level_print_is_flagged(index_from_source, base_config) -> None:
    project = index_from_source({"top.py": "print('hi')\n"})
    diagnostics = PrintUsedRule().check(project, base_config())
    assert [d.location.line for d in diagnostics] == [1]


def test_aliased_print_is_not_flagged(index_from_source, base_config) -> None:
    # Resolution through an alias is uncertain, so it must not be reported.
    source = "p = print\n\n\ndef go():\n    p('x')\n"
    project = index_from_source({"alias.py": source})
    assert PrintUsedRule().check(project, base_config()) == []
