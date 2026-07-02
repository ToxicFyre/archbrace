"""Unit tests for the core Archbrace data models (spec Section 10)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from archbrace.models import (
    CallRef,
    ClassInfo,
    Diagnostic,
    FunctionInfo,
    ImportInfo,
    ModuleInfo,
    ProjectIndex,
    RawMetrics,
    SourceRange,
)


def _source_range() -> SourceRange:
    return SourceRange(line=1, column=0, end_line=5, end_column=10)


def test_source_range_defaults() -> None:
    location = SourceRange(line=3, column=4)
    assert location.line == 3
    assert location.column == 4
    assert location.end_line is None
    assert location.end_column is None


def test_diagnostic_defaults_metadata_to_empty_dict() -> None:
    diagnostic = Diagnostic(
        code="AR001",
        name="function-too-long",
        path=Path("src/foo.py"),
        location=_source_range(),
        message="Function is too long.",
        severity="error",
    )
    assert diagnostic.metadata == {}


def test_diagnostic_is_frozen() -> None:
    diagnostic = Diagnostic(
        code="AR001",
        name="function-too-long",
        path=Path("src/foo.py"),
        location=_source_range(),
        message="Function is too long.",
        severity="error",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        diagnostic.code = "AR002"  # type: ignore[misc]


def test_function_info_fields() -> None:
    call = CallRef(callee="print", location=_source_range())
    func = FunctionInfo(
        qualified_name="mod.build",
        name="build",
        location=_source_range(),
        parameters=("a", "b"),
        return_count=1,
        local_variable_count=2,
        nesting_depth=1,
        cyclomatic_complexity=3,
        has_docstring=True,
        is_public=True,
        calls=(call,),
    )
    assert func.parameters == ("a", "b")
    assert func.calls[0].callee == "print"
    assert func.is_public is True


def test_class_info_fields() -> None:
    method = FunctionInfo(
        qualified_name="mod.Widget.render",
        name="render",
        location=_source_range(),
        parameters=(),
        return_count=0,
        local_variable_count=0,
        nesting_depth=0,
        cyclomatic_complexity=1,
        has_docstring=False,
        is_public=True,
        calls=(),
    )
    cls = ClassInfo(
        qualified_name="mod.Widget",
        name="Widget",
        location=_source_range(),
        methods=(method,),
        bases=("Base",),
        decorators=("dataclass",),
    )
    assert cls.methods[0].name == "render"
    assert cls.bases == ("Base",)


def test_module_info_and_project_index() -> None:
    raw = RawMetrics(
        loc=10,
        lloc=8,
        sloc=9,
        comments=1,
        multi=0,
        blank=1,
        single_comments=1,
    )
    imp = ImportInfo(
        module="os",
        names=("path",),
        is_relative=False,
        level=0,
        location=_source_range(),
    )
    module = ModuleInfo(
        path=Path("src/foo.py"),
        module_name="src.foo",
        source="import os\n",
        layer=None,
        imports=(imp,),
        functions=(),
        classes=(),
        module_docstring=None,
        raw_metrics=raw,
        maintainability_index=72.5,
    )
    index = ProjectIndex(
        root=Path("."),
        modules=(module,),
        import_graph=None,
        call_graph=None,
        diff=None,
    )
    assert index.modules[0].module_name == "src.foo"
    assert index.modules[0].raw_metrics.sloc == 9
    assert index.diff is None
