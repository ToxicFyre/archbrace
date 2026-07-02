"""Unit tests for the Radon adapter (spec Sections 7.1/7.2, 9.1).

These tests assert Archbrace reports Radon's own measured value rather than a
separately calculated one.
"""

from __future__ import annotations

from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze

from archbrace.analysis import radon_metrics
from archbrace.models import RawMetrics

SOURCE = (
    "def f(x):\n"
    "    # a comment\n"
    "    if x > 0:\n"
    "        return x\n"
    "    return -x\n"
    "\n"
    "\n"
    "def g(y):\n"
    "    return y\n"
)


def test_raw_metrics_match_radon() -> None:
    expected = analyze(SOURCE)
    result = radon_metrics.raw_metrics(SOURCE)
    assert isinstance(result, RawMetrics)
    assert result.loc == expected.loc
    assert result.lloc == expected.lloc
    assert result.sloc == expected.sloc
    assert result.comments == expected.comments
    assert result.multi == expected.multi
    assert result.blank == expected.blank
    assert result.single_comments == expected.single_comments


def test_maintainability_index_matches_radon() -> None:
    expected = mi_visit(SOURCE, True)
    assert radon_metrics.maintainability_index(SOURCE) == expected


def test_complexity_map_matches_radon_by_line() -> None:
    expected = {block.lineno: block.complexity for block in cc_visit(SOURCE)}
    result = radon_metrics.complexity_map(SOURCE)
    assert result == expected
    # ``f`` starts on line 1 and has one branch, so complexity is 2.
    assert result[1] == 2


DOC_HEAVY_SOURCE = (
    "def f(x):\n"
    '    """\n'
    "    A docstring\n"
    "    spanning several lines.\n"
    '    """\n'
    "    # a comment\n"
    "    y = x + 1\n"
    "\n"
    "    return y\n"
)


def test_code_line_numbers_size_matches_radon_sloc() -> None:
    # The count of code lines must equal Radon's own SLOC measurement, so AR001
    # and AR002 share one definition of "a line of code".
    result = radon_metrics.code_line_numbers(DOC_HEAVY_SOURCE)
    assert len(result) == radon_metrics.raw_metrics(DOC_HEAVY_SOURCE).sloc


def test_code_line_numbers_excludes_docstrings_comments_and_blanks() -> None:
    # Only the ``def``, the assignment, and the ``return`` are code lines;
    # the docstring (2-5), the comment (6), and the blank (8) are excluded.
    result = radon_metrics.code_line_numbers(DOC_HEAVY_SOURCE)
    assert result == frozenset({1, 7, 9})
