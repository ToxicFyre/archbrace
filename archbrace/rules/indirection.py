"""
Purpose:
    Indirection rules: AR070 (Wrapper Chain Too Deep).

Why is this in this project:
    Flags long chains of low-value pass-through functions that increase
    inter-function comprehension debt.

Inputs:
    A ``ProjectIndex`` and an ``ArchbraceConfig``.

Outputs:
    Diagnostics for wrapper chains deeper than ``max_wrapper_chain_depth``.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..analysis.call_graph import find_wrapper_chains
from ..config import ArchbraceConfig
from ..models import Diagnostic, FunctionInfo, ModuleInfo, ProjectIndex
from .base import Rule


class WrapperChainTooDeepRule(Rule):
    """AR070 - flag a local wrapper chain deeper than max_wrapper_chain_depth."""

    code = "AR070"
    name = "wrapper-chain-too-deep"
    description = (
        "Flag a call chain of high-confidence wrapper functions deeper than "
        "max_wrapper_chain_depth."
    )
    default_severity = "warning"

    def check(
        self,
        project: ProjectIndex,
        config: ArchbraceConfig,
    ) -> list[Diagnostic]:
        limit = config.max_wrapper_chain_depth
        diagnostics: list[Diagnostic] = []

        for finding in find_wrapper_chains(project, config):
            start_function = _function_for_qualified_name(project, finding.start)
            if start_function is None:
                continue
            module = _module_for_qualified_name(project, finding.start)
            if module is None:
                continue

            chain_display = " -> ".join(name.rsplit(".", 1)[-1] for name in finding.chain)
            diagnostics.append(
                Diagnostic(
                    code=self.code,
                    name=self.name,
                    path=module.path,
                    location=start_function.location,
                    message=(
                        f"Wrapper chain is too deep: {chain_display}. "
                        f"Depth is {finding.depth}; limit is {limit}. "
                        "This may be intentional. Consider collapsing one or more "
                        "pass-through layers if they do not express a real boundary."
                    ),
                    severity=self.default_severity,
                    metadata={
                        "actual": finding.depth,
                        "limit": limit,
                        "chain": list(finding.chain),
                        "symbol": start_function.name,
                    },
                )
            )

        return diagnostics


def _function_for_qualified_name(project: ProjectIndex, qualified_name: str) -> FunctionInfo | None:
    from .base import iter_functions

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
