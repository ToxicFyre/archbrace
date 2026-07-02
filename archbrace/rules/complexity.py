"""
Purpose:
    Complexity rules. This increment implements AR020 (Cyclomatic Complexity
    Too High) over Radon's measured complexity.

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig``.

Outputs:
    Diagnostics for functions whose Radon cyclomatic complexity exceeds
    ``max_cyclomatic_complexity``.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import Diagnostic, ProjectIndex
from .base import Rule, iter_functions


class CyclomaticComplexityRule(Rule):
    """AR020 - flag a function whose Radon cyclomatic complexity is too high."""

    code = "AR020"
    name = "cyclomatic-complexity-too-high"
    description = (
        "Flag a function or method whose Radon cyclomatic complexity exceeds "
        "max_cyclomatic_complexity."
    )
    default_severity = "error"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        limit = config.max_cyclomatic_complexity
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            for function in iter_functions(module):
                complexity = function.cyclomatic_complexity
                if complexity > limit:
                    diagnostics.append(
                        Diagnostic(
                            code=self.code,
                            name=self.name,
                            path=module.path,
                            location=function.location,
                            message=(
                                f"Function `{function.name}` has cyclomatic "
                                f"complexity {complexity}. Limit is {limit}."
                            ),
                            severity=self.default_severity,
                            metadata={
                                "actual": complexity,
                                "limit": limit,
                                "symbol": function.name,
                            },
                        )
                    )
        return diagnostics
