"""
Purpose:
    Size and shape rules. This increment implements AR001 (Function Too Long).

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig``.

Outputs:
    Diagnostics for functions whose source lines of code exceed
    ``max_function_lines``.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..config import ArchbraceConfig
from ..models import Diagnostic, FunctionInfo, ModuleInfo, ProjectIndex
from .base import Rule


def _iter_all_functions(module: ModuleInfo) -> Iterator[FunctionInfo]:
    """Yield every function in a module: top-level, nested, and class methods."""

    def walk(function: FunctionInfo) -> Iterator[FunctionInfo]:
        yield function
        for nested in function.nested_functions:
            yield from walk(nested)

    for function in module.functions:
        yield from walk(function)
    for klass in module.classes:
        for method in klass.methods:
            yield from walk(method)


class FunctionTooLongRule(Rule):
    """AR001 - flag a function or method with too many source lines of code."""

    code = "AR001"
    name = "function-too-long"
    description = (
        "Flag a function or method whose source lines of code exceed "
        "max_function_lines."
    )
    default_severity = "error"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        limit = config.max_function_lines
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            for function in _iter_all_functions(module):
                code_lines = function.code_lines
                if code_lines > limit:
                    diagnostics.append(
                        Diagnostic(
                            code=self.code,
                            name=self.name,
                            path=module.path,
                            location=function.location,
                            message=(
                                f"Function `{function.name}` has {code_lines} "
                                f"code lines. Limit is {limit}."
                            ),
                            severity=self.default_severity,
                            metadata={
                                "actual": code_lines,
                                "limit": limit,
                                "symbol": function.name,
                            },
                        )
                    )
        return diagnostics
