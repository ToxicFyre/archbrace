"""
Purpose:
    Simplicity rules. This increment implements AR040 (Vague Module Name).

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig``.

Outputs:
    Diagnostics for modules whose filename stem matches a configured vague name.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import Diagnostic, ProjectIndex, SourceRange
from .base import Rule


class VagueModuleNameRule(Rule):
    """AR040 - flag modules whose filename stem is a configured vague name."""

    code = "AR040"
    name = "vague-module-name"
    description = "Flag modules whose filename stem matches a configured vague name."
    default_severity = "error"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        vague = set(config.vague_module_names)
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            stem = module.path.stem
            if stem == "__init__":
                continue
            if stem in vague:
                diagnostics.append(
                    Diagnostic(
                        code=self.code,
                        name=self.name,
                        path=module.path,
                        location=SourceRange(line=1, column=1),
                        message=(
                            f"Module `{module.path.name}` has a vague name. "
                            "Name the concrete responsibility."
                        ),
                        severity=self.default_severity,
                        metadata={"symbol": stem},
                    )
                )
        return diagnostics
