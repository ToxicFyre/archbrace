"""
Purpose:
    Compute Flow Locality Index (FLI) scores from conservative call-graph walks.

Why is this in this project:
    AR073 flags public entry points whose behavior is spread across too many
    files, generic layers, and pass-through wrappers.

Inputs:
    A ``ProjectIndex`` and FLI configuration values.

Outputs:
    FLI findings for entry points whose score exceeds ``max_fli``.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes; cycles are handled safely.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import FunctionInfo, ModuleInfo, ProjectIndex
from ..rules.base import iter_functions
from .call_graph import is_test_file
from .call_index import CallableIndex, build_callable_index
from .fli_assembly import build_flow_locality_finding
from .fli_entry import is_entry_point
from .fli_models import FlowLocalityFinding
from .fli_traversal import traverse_from

__all__ = [
    "FlowLocalityFinding",
    "analyze_entry_point",
    "find_flow_locality_violations",
]


def find_flow_locality_violations(
    project: ProjectIndex,
    config: ArchbraceConfig,
) -> list[FlowLocalityFinding]:
    index = build_callable_index(project)
    findings: list[FlowLocalityFinding] = []

    for module in project.modules:
        if config.fli_ignore_tests and is_test_file(module.path):
            continue
        for function in iter_functions(module):
            if not is_entry_point(function, module, config):
                continue
            finding = analyze_entry_point(function, module, index, config)
            if finding is not None and finding.fli > config.max_fli:
                findings.append(finding)

    return findings


def analyze_entry_point(
    function: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> FlowLocalityFinding | None:
    if function.qualified_name not in index.nodes_by_qualified_name:
        return None

    reached, _edges, unresolved, depth_limited = traverse_from(
        function, module, index, config
    )
    return build_flow_locality_finding(
        function,
        module,
        reached,
        unresolved,
        depth_limited,
        index,
        config,
    )
