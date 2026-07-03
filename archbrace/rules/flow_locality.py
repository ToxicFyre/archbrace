"""
Purpose:
    Flow locality rule: AR073 (Flow Locality Index).

Why is this in this project:
    Flags public entry points whose behavior is spread across too many files,
    generic layers, and pass-through wrappers.

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig``.

Outputs:
    Diagnostics for entry points whose FLI exceeds ``max_fli``.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..analysis.fli_metadata import format_lean_message
from ..analysis.fli_models import FlowLocalityFinding
from ..analysis.flow_locality import find_flow_locality_violations
from ..config import ArchbraceConfig
from ..models import Diagnostic, FunctionInfo, ModuleInfo, ProjectIndex
from .base import Rule, iter_functions
from .fli_metadata import finding_metadata

DOCUMENTATION_URL = (
    "https://github.com/ToxicFyre/archbrace/blob/main/docs/rules.md"
    "#ar073--flow-locality-index"
)


class FlowLocalityIndexRule(Rule):
    """AR073 - flag entry points whose flow locality index exceeds max_fli."""

    code = "AR073"
    name = "flow-locality-index"
    description = (
        "Flag public entry points whose behavior is spread across too many "
        "files, generic layers, and pass-through wrappers."
    )
    default_severity = "warning"
    documentation_url = DOCUMENTATION_URL

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        return [
            _diagnostic_for(finding, project, config.max_fli)
            for finding in find_flow_locality_violations(project, config)
            if _function_for_qualified_name(project, finding.entry) is not None
            and _module_for_qualified_name(project, finding.entry) is not None
        ]


def _diagnostic_for(
    finding: FlowLocalityFinding,
    project: ProjectIndex,
    limit: int,
) -> Diagnostic:
    function = _function_for_qualified_name(project, finding.entry)
    module = _module_for_qualified_name(project, finding.entry)
    assert function is not None and module is not None
    return Diagnostic(
        code=FlowLocalityIndexRule.code,
        name=FlowLocalityIndexRule.name,
        path=module.path,
        location=function.location,
        message=_finding_message(function.name, finding, limit),
        severity=FlowLocalityIndexRule.default_severity,
        metadata=finding_metadata(function.name, finding, limit),
    )


def _finding_message(name: str, finding: FlowLocalityFinding, limit: int) -> str:
    return format_lean_message(
        name,
        finding.fli,
        limit,
        finding.dominant,
        finding.measurements,
    )


def _function_for_qualified_name(project: ProjectIndex, qualified_name: str) -> FunctionInfo | None:
    for module in project.modules:
        for function in iter_functions(module):
            if function.qualified_name == qualified_name:
                return function
    return None


def _module_for_qualified_name(project: ProjectIndex, qualified_name: str) -> ModuleInfo | None:
    module_prefix = qualified_name.rsplit(".", 1)[0]
    for module in project.modules:
        if module.module_name == module_prefix:
            return module
        if qualified_name.startswith(f"{module.module_name}."):
            return module
    return None
