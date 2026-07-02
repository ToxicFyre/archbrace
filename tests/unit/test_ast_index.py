"""Unit tests for the AST index builder (spec Sections 6, 7.1, 10)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from archbrace.analysis import radon_metrics
from archbrace.analysis.ast_index import build_module_info
from archbrace.errors import AnalysisError

SRC = '''\
"""Module doc."""
import os


@decorator
def outer(a, b, *args, **kwargs):
    """Docstring."""
    x = 1
    y = 2
    if a:
        for i in range(3):
            z = i
    def inner(c):
        return c
    return x


class Widget(Base):
    """Class doc."""

    def method(self):
        return 1

    def _private(self):
        pass
'''


def _module():
    return build_module_info(
        path=Path("pkg/example.py"),
        source=SRC,
        module_name="pkg.example",
    )


def test_module_docstring_and_tree() -> None:
    module = _module()
    assert module.module_docstring == "Module doc."
    assert isinstance(module.tree, ast.Module)
    assert module.module_name == "pkg.example"


def test_imports_are_deferred_to_empty_tuple() -> None:
    # Import resolution is a follow-up; this increment reports no imports.
    assert _module().imports == ()


def test_only_top_level_functions_are_listed() -> None:
    module = _module()
    assert [f.name for f in module.functions] == ["outer"]


def test_nested_function_is_captured_under_parent() -> None:
    outer = _module().functions[0]
    assert [f.name for f in outer.nested_functions] == ["inner"]
    inner = outer.nested_functions[0]
    assert inner.return_count == 1
    assert inner.nesting_depth == 0
    assert inner.qualified_name == "pkg.example.outer.inner"


def test_function_parameters_and_flags() -> None:
    outer = _module().functions[0]
    assert outer.parameters == ("a", "b", "args", "kwargs")
    assert outer.has_docstring is True
    assert outer.is_public is True


def test_function_span_includes_decorator() -> None:
    outer = _module().functions[0]
    # Decorator is line 5; the function ends at ``return x`` on line 15.
    assert outer.location.line == 5
    assert outer.location.end_line == 15


def test_function_metrics_are_computed() -> None:
    outer = _module().functions[0]
    assert outer.return_count == 1
    assert outer.nesting_depth == 2
    assert outer.local_variable_count == 4


def test_cyclomatic_complexity_comes_from_radon() -> None:
    outer = _module().functions[0]
    expected = radon_metrics.complexity_map(SRC)[6]  # ``def outer`` is on line 6.
    assert outer.cyclomatic_complexity == expected


def test_classes_methods_and_bases() -> None:
    module = _module()
    assert [c.name for c in module.classes] == ["Widget"]
    widget = module.classes[0]
    assert widget.bases == ("Base",)
    assert [m.name for m in widget.methods] == ["method", "_private"]
    assert widget.methods[0].is_public is True
    assert widget.methods[1].is_public is False
    assert widget.methods[0].qualified_name == "pkg.example.Widget.method"


def test_raw_metrics_and_maintainability_populated() -> None:
    module = _module()
    assert module.raw_metrics.sloc > 0
    assert module.maintainability_index > 0


def test_syntax_error_raises_analysis_error() -> None:
    with pytest.raises(AnalysisError):
        build_module_info(
            path=Path("bad.py"),
            source="def broken(:\n    pass\n",
            module_name="bad",
        )
