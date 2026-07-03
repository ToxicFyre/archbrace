"""
Purpose:
    Define the ``Rule`` interface every Archbrace rule implements (spec Section 11).

Why is this in this project:
    Defines the one interface every rule implements so the engine runs them
    uniformly and new rules drop in without engine changes.

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig`` supplied by the engine.

Outputs:
    A list of ``Diagnostic`` objects.

Side effects:
    None. Rules must not mutate source or write to the terminal.

Failure behavior:
    Rules raise on genuinely unexpected conditions; the engine surfaces such
    failures rather than swallowing them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..config import ArchbraceConfig
from ..models import Diagnostic, FunctionInfo, ModuleInfo, ProjectIndex, Severity


def iter_functions(module: ModuleInfo) -> Iterator[FunctionInfo]:
    """Yield every function in a module: top-level, nested, and class methods.

    Shared by the per-function rules (AR001, AR003, AR020) so they analyze the
    same set of functions without each re-implementing the traversal.
    """

    def walk(function: FunctionInfo) -> Iterator[FunctionInfo]:
        yield function
        for nested in function.nested_functions:
            yield from walk(nested)

    for function in module.functions:
        yield from walk(function)
    for klass in module.classes:
        for method in klass.methods:
            yield from walk(method)


class Rule(ABC):
    """Base class for all architectural rules."""

    code: str
    name: str
    description: str
    default_severity: Severity
    documentation_url: str | None = None

    @abstractmethod
    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        """
        Inputs:
            The project index and active configuration.

        Outputs:
            A list of diagnostics produced by this rule.

        Side effects:
            None.

        Failure behavior:
            May raise on unexpected internal errors; the engine converts these
            into ``RuleExecutionError``.
        """
        raise NotImplementedError
