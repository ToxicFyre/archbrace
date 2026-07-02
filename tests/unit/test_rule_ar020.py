"""Tests for AR020 Cyclomatic Complexity Too High (spec Section 7.2).

The reported complexity must be Radon's own measured value, not a separately
calculated one.
"""

from __future__ import annotations

from archbrace.analysis import radon_metrics
from archbrace.rules.complexity import CyclomaticComplexityRule

BRANCHY = (
    "def branchy(x):\n"
    "    if x == 1:\n"
    "        return 1\n"
    "    elif x == 2:\n"
    "        return 2\n"
    "    elif x == 3:\n"
    "        return 3\n"
    "    elif x == 4:\n"
    "        return 4\n"
    "    return 0\n"
)


def test_flags_high_complexity(index_from_source, base_config) -> None:
    project = index_from_source({"branchy.py": BRANCHY})
    expected = radon_metrics.complexity_map(BRANCHY)[1]  # ``def branchy`` on line 1
    config = base_config(max_cyclomatic_complexity=expected - 1)
    diagnostics = CyclomaticComplexityRule().check(project, config)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR020"
    assert diagnostic.name == "cyclomatic-complexity-too-high"
    assert diagnostic.severity == "error"
    assert diagnostic.metadata["symbol"] == "branchy"
    assert diagnostic.metadata["limit"] == expected - 1
    # Archbrace reports Radon's measured complexity verbatim.
    assert diagnostic.metadata["actual"] == expected


def test_ignores_simple_function(index_from_source, base_config) -> None:
    source = "def simple(x):\n    return x + 1\n"
    project = index_from_source({"simple.py": source})
    config = base_config(max_cyclomatic_complexity=8)
    assert CyclomaticComplexityRule().check(project, config) == []
