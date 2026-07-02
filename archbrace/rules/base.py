"""
Purpose:
    Define the ``Rule`` interface every Archbrace rule implements (spec Section 11).

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

from ..config import ArchbraceConfig
from ..models import Diagnostic, ProjectIndex, Severity


class Rule(ABC):
    """Base class for all architectural rules."""

    code: str
    name: str
    description: str
    default_severity: Severity

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
