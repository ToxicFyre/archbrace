"""
Purpose:
    Logging and error-visibility rules. This increment implements AR101
    (print used instead of a logger) and AR102 (silent broad exception handler).

Why is this in this project:
    Houses the observability checks that keep failures visible instead of printed
    or silently swallowed.

Inputs:
    A ``ProjectIndex`` (whose modules carry parsed ASTs) and an
    ``ArchbraceConfig``.

Outputs:
    Diagnostics for direct ``print()`` calls and silent broad handlers.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from ..config import ArchbraceConfig
from ..models import Diagnostic, ProjectIndex, SourceRange
from .base import Rule

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_LOG_METHODS = frozenset(
    {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
)
_BROAD_NAMES = frozenset({"Exception", "BaseException"})


class PrintUsedRule(Rule):
    """AR101 - flag direct ``print()`` calls in production modules."""

    code = "AR101"
    name = "print-used"
    description = "Flag direct print() calls in production modules."
    default_severity = "error"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            if module.tree is None:
                continue
            for node in ast.walk(module.tree):
                if isinstance(node, ast.Call) and _is_print_name(node.func):
                    diagnostics.append(
                        Diagnostic(
                            code=self.code,
                            name=self.name,
                            path=module.path,
                            location=SourceRange(
                                line=node.lineno, column=node.col_offset + 1
                            ),
                            message="`print()` used instead of a logger.",
                            severity=self.default_severity,
                            metadata={},
                        )
                    )
        return diagnostics


class SilentBroadExceptRule(Rule):
    """AR102 - flag broad exception handlers that swallow the error."""

    code = "AR102"
    name = "silent-broad-except"
    description = (
        "Flag bare/broad exception handlers that neither log, re-raise, raise a "
        "replacement, nor return a documented sentinel."
    )
    default_severity = "error"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            if module.tree is None:
                continue
            for node in ast.walk(module.tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                if _is_broad(node) and not _has_visible_action(node):
                    diagnostics.append(
                        Diagnostic(
                            code=self.code,
                            name=self.name,
                            path=module.path,
                            location=SourceRange(
                                line=node.lineno, column=node.col_offset + 1
                            ),
                            message=(
                                "Broad exception handler silently swallows errors. "
                                "Log, re-raise, or return a documented value."
                            ),
                            severity=self.default_severity,
                            metadata={"handler": _handler_label(node)},
                        )
                    )
        return diagnostics


def _is_print_name(func: ast.expr) -> bool:
    return isinstance(func, ast.Name) and func.id == "print"


def _is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Tuple):
        return False
    return _last_name(handler.type) in _BROAD_NAMES


def _handler_label(handler: ast.ExceptHandler) -> str:
    if handler.type is None:
        return "bare"
    return _last_name(handler.type) or "unknown"


def _last_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _has_visible_action(handler: ast.ExceptHandler) -> bool:
    for node in _walk_scope(handler.body):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Return) and node.value is not None:
            return True
        if isinstance(node, ast.Call) and _is_log_call(node):
            return True
    return False


def _is_log_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr in _LOG_METHODS


def _walk_scope(statements: list[ast.stmt]) -> Iterator[ast.AST]:
    for statement in statements:
        yield from _walk_node(statement)


def _walk_node(node: ast.AST) -> Iterator[ast.AST]:
    if isinstance(node, _SCOPE_NODES):
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _walk_node(child)
