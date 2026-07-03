"""
Purpose:
    Define Archbrace's core, immutable data models: source locations,
    diagnostics, function/class/module descriptors, and the project index that
    rules consume.

Why is this in this project:
    Central immutable data contracts shared by analysis, rules, and reporting so
    those layers stay decoupled and pass structured values, not ad-hoc dicts.

Inputs:
    Values produced by the analysis adapters (AST index, Radon metrics).

Outputs:
    Frozen dataclasses used across the rule engine and reporting layers.

Side effects:
    None.

Failure behavior:
    Pure data definitions; construction raises ``TypeError`` only on misuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class SourceRange:
    """A 1-based line / 0-based column span within a source file."""

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True)
class Diagnostic:
    """A single rule finding at a specific location."""

    code: str
    name: str
    path: Path
    location: SourceRange
    message: str
    severity: Severity
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CallRef:
    """A conservative reference to a call made inside a function body."""

    callee: str
    location: SourceRange


@dataclass(frozen=True)
class ImportInfo:
    """A resolved-or-raw import statement in a module."""

    module: str
    names: tuple[str, ...]
    is_relative: bool
    level: int
    location: SourceRange


@dataclass(frozen=True)
class RawMetrics:
    """Radon raw line-count metrics for a module (spec Section 6)."""

    loc: int
    lloc: int
    sloc: int
    comments: int
    multi: int
    blank: int
    single_comments: int


@dataclass(frozen=True)
class FunctionInfo:
    """Structural metadata for a top-level or nested function/method.

    ``nested_functions`` preserves the function tree so per-function rules (for
    example AR001) can analyze inner functions separately, while
    ``ModuleInfo.functions`` continues to list only top-level functions.

    ``code_lines`` is the count of source lines of code the function spans
    (Radon SLOC semantics: docstrings, comments, blank lines, and decorators are
    excluded). ``location`` still describes the full physical span for reporting.
    """

    qualified_name: str
    name: str
    location: SourceRange
    parameters: tuple[str, ...]
    return_count: int
    local_variable_count: int
    nesting_depth: int
    cyclomatic_complexity: int
    has_docstring: bool
    is_public: bool
    calls: tuple[CallRef, ...]
    nested_functions: tuple[FunctionInfo, ...] = ()
    code_lines: int = 0
    decorators: tuple[str, ...] = ()
    is_async: bool = False
    parent_class: str | None = None


@dataclass(frozen=True)
class ClassInfo:
    """Structural metadata for a top-level class."""

    qualified_name: str
    name: str
    location: SourceRange
    methods: tuple[FunctionInfo, ...]
    bases: tuple[str, ...]
    decorators: tuple[str, ...]


@dataclass(frozen=True)
class ModuleInfo:
    """A parsed, indexed Python module."""

    path: Path
    module_name: str
    source: str
    layer: str | None
    imports: tuple[ImportInfo, ...]
    functions: tuple[FunctionInfo, ...]
    classes: tuple[ClassInfo, ...]
    module_docstring: str | None
    raw_metrics: RawMetrics
    maintainability_index: float
    # Parsed syntax tree, retained so structural rules can inspect the module
    # without re-parsing. Excluded from equality/repr because AST nodes are not
    # hashable and are noisy to print.
    tree: Any = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class ProjectIndex:
    """The single index built per Archbrace run (spec Section 6)."""

    root: Path
    modules: tuple[ModuleInfo, ...]
    import_graph: Any
    call_graph: Any
    diff: Any
