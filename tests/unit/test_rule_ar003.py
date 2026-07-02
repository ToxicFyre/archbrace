"""Tests for AR003 Nesting Too Deep (spec Section 7.1)."""

from __future__ import annotations

from archbrace.rules.size import NestingTooDeepRule


def test_flags_deeply_nested_function(index_from_source, base_config) -> None:
    source = (
        "def deep():\n"
        "    if a:\n"
        "        for x in y:\n"
        "            while z:\n"
        "                with m:\n"
        "                    pass\n"
    )
    project = index_from_source({"deep.py": source})
    config = base_config(max_nesting_depth=3)
    diagnostics = NestingTooDeepRule().check(project, config)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR003"
    assert diagnostic.name == "nesting-too-deep"
    assert diagnostic.severity == "error"
    assert diagnostic.metadata["symbol"] == "deep"
    assert diagnostic.metadata["limit"] == 3
    assert diagnostic.metadata["actual"] == 4


def test_ignores_shallow_function(index_from_source, base_config) -> None:
    source = (
        "def shallow():\n"
        "    if a:\n"
        "        for x in y:\n"
        "            return x\n"
        "    return 0\n"
    )
    project = index_from_source({"shallow.py": source})
    config = base_config(max_nesting_depth=3)
    assert NestingTooDeepRule().check(project, config) == []


def test_elif_chain_counts_as_single_level(index_from_source, base_config) -> None:
    source = (
        "def branchy():\n"
        "    if a:\n"
        "        pass\n"
        "    elif b:\n"
        "        pass\n"
        "    elif c:\n"
        "        pass\n"
        "    else:\n"
        "        pass\n"
    )
    project = index_from_source({"branchy.py": source})
    # An elif chain is one nesting level; if it were counted as nested
    # ``else: if`` blocks the depth would exceed a limit of 1.
    config = base_config(max_nesting_depth=1)
    assert NestingTooDeepRule().check(project, config) == []


def test_boolean_operators_do_not_add_depth(index_from_source, base_config) -> None:
    source = (
        "def guard():\n"
        "    if (a and b) or (c and d):\n"
        "        return 1\n"
        "    return 0\n"
    )
    project = index_from_source({"guard.py": source})
    # A single ``if`` is depth 1 regardless of the boolean expression inside it.
    config = base_config(max_nesting_depth=1)
    assert NestingTooDeepRule().check(project, config) == []


def test_nested_functions_analyzed_separately(index_from_source, base_config) -> None:
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        if a:\n"
        "            for x in y:\n"
        "                while z:\n"
        "                    with m:\n"
        "                        return z\n"
        "    return inner\n"
    )
    project = index_from_source({"nested.py": source})
    config = base_config(max_nesting_depth=3)
    flagged = {d.metadata["symbol"] for d in NestingTooDeepRule().check(project, config)}
    # ``inner`` (depth 4 in its own body) is analyzed as its own function.
    assert "inner" in flagged
