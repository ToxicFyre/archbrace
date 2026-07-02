"""
Purpose:
    Thin adapter over Radon's public API so the rest of Archbrace consumes
    internal models (``RawMetrics``, floats, line maps) instead of Radon objects.
    Archbrace never re-implements Radon's calculations (spec Sections 7.1/7.2).

Inputs:
    Python source text.

Outputs:
    Radon raw metrics, the Maintainability Index, and a line-keyed cyclomatic
    complexity map.

Side effects:
    None.

Failure behavior:
    Propagates ``SyntaxError`` from Radon; callers parse first and translate
    failures into ``AnalysisError``.
"""

from __future__ import annotations

import io
import tokenize

from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze

from ..models import RawMetrics

# Radon's harvesters treat multiline strings as comments by default.
_COUNT_MULTILINE_AS_COMMENTS = True

# Token types that never constitute a source line of code: comments, string
# literals (including docstrings), the various newline/indentation markers, and
# the stream sentinels. A physical line counts as code only when it carries a
# token outside this set. This mirrors Radon's SLOC definition, which excludes
# blank lines, comments, and docstrings (spec Sections 7.1/7.2).
_NON_CODE_TOKENS = frozenset(
    {
        tokenize.COMMENT,
        tokenize.STRING,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
)


def raw_metrics(source: str) -> RawMetrics:
    """
    Inputs:
        Python source text.

    Outputs:
        A ``RawMetrics`` carrying Radon's measured line counts verbatim.

    Side effects:
        None.

    Failure behavior:
        Propagates ``SyntaxError`` for unparsable source.
    """
    module = analyze(source)
    return RawMetrics(
        loc=module.loc,
        lloc=module.lloc,
        sloc=module.sloc,
        comments=module.comments,
        multi=module.multi,
        blank=module.blank,
        single_comments=module.single_comments,
    )


def maintainability_index(source: str) -> float:
    """
    Inputs:
        Python source text.

    Outputs:
        Radon's Maintainability Index for the module.

    Side effects:
        None.

    Failure behavior:
        Propagates ``SyntaxError`` for unparsable source.
    """
    return mi_visit(source, _COUNT_MULTILINE_AS_COMMENTS)


def code_line_numbers(source: str) -> frozenset[int]:
    """
    Inputs:
        Python source text.

    Outputs:
        The set of 1-based physical line numbers that hold source code, matching
        Radon's SLOC definition: blank lines, comment-only lines, and docstring /
        multiline-string lines are excluded. ``len(code_line_numbers(src))``
        equals ``raw_metrics(src).sloc``.

    Side effects:
        None.

    Failure behavior:
        Propagates ``tokenize.TokenError`` / ``SyntaxError`` for unparsable
        source; callers parse first and translate failures into ``AnalysisError``.
    """
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return frozenset(
        token.start[0]
        for token in tokens
        if token.type not in _NON_CODE_TOKENS
    )


def complexity_map(source: str) -> dict[int, int]:
    """
    Inputs:
        Python source text.

    Outputs:
        A mapping from each analyzed block's starting ``def``/``class`` line to
        its Radon cyclomatic complexity.

    Side effects:
        None.

    Failure behavior:
        Propagates ``SyntaxError`` for unparsable source.
    """
    return {block.lineno: block.complexity for block in cc_visit(source)}
