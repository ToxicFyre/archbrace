"""
Purpose:
    Size and shape rules: AR001 (Function Too Long), AR002 (File Too Long), and
    AR003 (Nesting Too Deep).

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig``.

Outputs:
    Diagnostics for functions that exceed ``max_function_lines`` or
    ``max_nesting_depth``, and modules that exceed ``max_file_lines``.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import Diagnostic, ProjectIndex, SourceRange
from .base import Rule, iter_functions


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
            for function in iter_functions(module):
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


class FileTooLongRule(Rule):
    """AR002 - flag a module whose Radon source-line count is too high."""

    code = "AR002"
    name = "file-too-long"
    description = (
        "Flag a module whose Radon source-line count exceeds max_file_lines."
    )
    default_severity = "error"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        limit = config.max_file_lines
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            sloc = module.raw_metrics.sloc
            if sloc > limit:
                diagnostics.append(
                    Diagnostic(
                        code=self.code,
                        name=self.name,
                        path=module.path,
                        location=SourceRange(line=1, column=1),
                        message=(
                            f"File `{module.path.name}` has {sloc} source "
                            f"lines. Limit is {limit}."
                        ),
                        severity=self.default_severity,
                        metadata={
                            "actual": sloc,
                            "limit": limit,
                            "symbol": module.module_name,
                        },
                    )
                )
        return diagnostics


class NestingTooDeepRule(Rule):
    """AR003 - flag a function whose structural nesting is too deep."""

    code = "AR003"
    name = "nesting-too-deep"
    description = (
        "Flag a function whose maximum structural nesting exceeds "
        "max_nesting_depth."
    )
    default_severity = "error"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        limit = config.max_nesting_depth
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            for function in iter_functions(module):
                depth = function.nesting_depth
                if depth > limit:
                    diagnostics.append(
                        Diagnostic(
                            code=self.code,
                            name=self.name,
                            path=module.path,
                            location=function.location,
                            message=(
                                f"Function `{function.name}` has nesting depth "
                                f"{depth}. Limit is {limit}."
                            ),
                            severity=self.default_severity,
                            metadata={
                                "actual": depth,
                                "limit": limit,
                                "symbol": function.name,
                            },
                        )
                    )
        return diagnostics
