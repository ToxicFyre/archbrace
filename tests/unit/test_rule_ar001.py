"""Tests for AR001 Function Too Long (spec Section 7.1)."""

from __future__ import annotations

from archbrace.rules.size import FunctionTooLongRule


def test_flags_function_over_limit(index_from, base_config) -> None:
    project = index_from("ar001_long.py")
    config = base_config(max_function_lines=5)
    diagnostics = FunctionTooLongRule().check(project, config)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR001"
    assert diagnostic.name == "function-too-long"
    assert diagnostic.severity == "error"
    assert diagnostic.metadata["symbol"] == "long_function"
    assert diagnostic.metadata["limit"] == 5
    assert diagnostic.metadata["actual"] > 5


def test_ignores_function_within_limit(index_from, base_config) -> None:
    project = index_from("ar001_ok.py")
    config = base_config(max_function_lines=40)
    assert FunctionTooLongRule().check(project, config) == []


def test_docstring_not_counted(index_from_source, base_config) -> None:
    source = (
        "def documented():\n"
        '    """\n'
        "    Line one.\n"
        "    Line two.\n"
        "    Line three.\n"
        "    Line four.\n"
        "    Line five.\n"
        "    Line six.\n"
        '    """\n'
        "    return 1\n"
    )
    project = index_from_source({"doc.py": source})
    config = base_config(max_function_lines=5)
    # ``def`` + ``return`` are the only code lines; the docstring must not count.
    assert FunctionTooLongRule().check(project, config) == []


def test_comments_and_blanks_not_counted(index_from_source, base_config) -> None:
    source = (
        "def spaced():\n"
        "    # comment one\n"
        "    a = 1\n"
        "\n"
        "    # comment two\n"
        "    b = 2\n"
        "\n"
        "    # comment three\n"
        "    return a + b\n"
    )
    project = index_from_source({"spaced.py": source})
    config = base_config(max_function_lines=4)
    # Only ``def``, ``a = 1``, ``b = 2``, and ``return`` count: 4 code lines,
    # exactly the limit, so nothing is flagged.
    assert FunctionTooLongRule().check(project, config) == []


def test_decorators_not_counted(index_from_source, base_config) -> None:
    source = (
        "@first\n"
        "@second\n"
        "@third\n"
        "def wrapped():\n"
        "    return 1\n"
    )
    project = index_from_source({"deco.py": source})
    config = base_config(max_function_lines=2)
    # Five physical lines, but only ``def`` and ``return`` are code lines, so the
    # two decorators do not push the function over the limit of 2.
    assert FunctionTooLongRule().check(project, config) == []


def test_nested_functions_analyzed_separately(index_from_source, base_config) -> None:
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        a = 1\n"
        "        b = 2\n"
        "        c = 3\n"
        "        d = 4\n"
        "        return a + b + c + d\n"
        "    return inner\n"
    )
    project = index_from_source({"nested.py": source})
    config = base_config(max_function_lines=5)
    flagged = {d.metadata["symbol"] for d in FunctionTooLongRule().check(project, config)}
    # ``inner`` spans 6 lines and is analyzed separately from ``outer``.
    assert "inner" in flagged
