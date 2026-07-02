"""Tests for AR002 File Too Long (spec Section 7.1)."""

from __future__ import annotations

from archbrace.rules.size import FileTooLongRule


def test_flags_file_over_limit(index_from_source, base_config) -> None:
    source = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6\n"
    project = index_from_source({"big.py": source})
    config = base_config(max_file_lines=5)
    diagnostics = FileTooLongRule().check(project, config)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR002"
    assert diagnostic.name == "file-too-long"
    assert diagnostic.severity == "error"
    assert diagnostic.metadata["symbol"] == "big"
    assert diagnostic.metadata["limit"] == 5
    assert diagnostic.metadata["actual"] == 6
    assert diagnostic.location.line == 1


def test_ignores_file_within_limit(index_from_source, base_config) -> None:
    source = "a = 1\nb = 2\n"
    project = index_from_source({"small.py": source})
    config = base_config(max_file_lines=40)
    assert FileTooLongRule().check(project, config) == []


def test_docstrings_and_blanks_not_counted(index_from_source, base_config) -> None:
    source = (
        '"""\n'
        "Purpose line one.\n"
        "Purpose line two.\n"
        "Purpose line three.\n"
        "Purpose line four.\n"
        '"""\n'
        "\n"
        "a = 1\n"
        "b = 2\n"
    )
    project = index_from_source({"documented.py": source})
    # Nine physical lines, but Radon SLOC counts only ``a = 1`` and ``b = 2``.
    config = base_config(max_file_lines=5)
    assert FileTooLongRule().check(project, config) == []
