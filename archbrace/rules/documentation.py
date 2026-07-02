"""
Purpose:
    Documentation contract rules. This increment implements AR060 (Module
    Contract Required, spec Section 7.4).

Why is this in this project:
    Enforces the module documentation contract, Archbrace's core guarantee that
    every module states its purpose and interface.

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig``.

Outputs:
    Diagnostics for code-bearing modules missing a required contract heading.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import Diagnostic, ProjectIndex, SourceRange
from .base import Rule


def _normalize(text: str) -> str:
    return text.strip().rstrip(":").strip().casefold()


def _present_headings(docstring: str | None) -> set[str]:
    if docstring is None:
        return set()
    return {_normalize(line.split(":", 1)[0]) for line in docstring.splitlines()}


class ModuleContractRule(Rule):
    """AR060 - require a module docstring with the configured contract headings."""

    code = "AR060"
    name = "module-contract-required"
    description = (
        "Require a module docstring containing the configured contract headings."
    )
    default_severity = "error"

    DEFAULT_SECTIONS = (
        "Purpose",
        "Why is this in this project",
        "Inputs",
        "Outputs",
        "Side effects",
        "Failure behavior",
    )

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        if not config.require_module_contract:
            return []
        sections = config.module_contract_sections or self.DEFAULT_SECTIONS
        diagnostics: list[Diagnostic] = []
        for module in project.modules:
            if module.raw_metrics.sloc == 0:
                continue
            present = _present_headings(module.module_docstring)
            for section in sections:
                if _normalize(section) in present:
                    continue
                diagnostics.append(
                    Diagnostic(
                        code=self.code,
                        name=self.name,
                        path=module.path,
                        location=SourceRange(line=1, column=1),
                        message=f"Missing module contract section: {section}",
                        severity=self.default_severity,
                        metadata={"symbol": module.path.stem, "section": section},
                    )
                )
        return diagnostics
