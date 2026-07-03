"""
Purpose:
    Build a conservative local call graph and detect wrapper chains for AR070.

Why is this in this project:
    Wrapper-chain detection needs cross-function resolution and chain following
    beyond per-function metadata alone.

Inputs:
    A ``ProjectIndex`` and wrapper-chain configuration values.

Outputs:
    Wrapper-chain findings whose depth exceeds the configured limit.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes; cycles are handled safely.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import ArchbraceConfig
from ..models import FunctionInfo, ModuleInfo, ProjectIndex
from .call_index import CallableIndex, build_callable_index, module_for_function
from .wrapper_heuristics import delegated_callee as analyze_delegated_callee

_TEST_FILE_PATTERN = re.compile(r"(^test_.*|.*_test\.py$|conftest\.py$)")


@dataclass(frozen=True)
class WrapperChainFinding:
    """A wrapper chain whose depth exceeds the configured limit."""

    start: str
    chain: tuple[str, ...]
    depth: int


def find_wrapper_chains(
    project: ProjectIndex,
    config: ArchbraceConfig,
) -> list[WrapperChainFinding]:
    index = build_callable_index(project)
    findings: list[WrapperChainFinding] = []

    for qualified_name, function in index.callables_by_qualified_name.items():
        module = module_for_function(function, index)
        if module is None or is_exempt(function, module, config):
            continue

        chain, depth = follow_wrapper_chain(function, index, config)
        if depth > config.max_wrapper_chain_depth:
            findings.append(
                WrapperChainFinding(start=qualified_name, chain=chain, depth=depth)
            )

    return findings


def delegated_callee(
    function: FunctionInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> str | None:
    module = module_for_function(function, index)
    if module is None or is_exempt(function, module, config):
        return None

    node = index.nodes_by_qualified_name.get(function.qualified_name)
    if node is None:
        return None

    return analyze_delegated_callee(node, function, module, index)


def follow_wrapper_chain(
    start: FunctionInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> tuple[tuple[str, ...], int]:
    chain = [start.qualified_name]
    visited = {start.qualified_name}
    depth = 0
    current = start

    while True:
        delegated = delegated_callee(current, index, config)
        if delegated is None:
            break
        if delegated in visited:
            chain.append(delegated)
            break

        chain.append(delegated)
        visited.add(delegated)

        next_function = index.callables_by_qualified_name.get(delegated)
        if next_function is None:
            break

        depth += 1
        if delegated_callee(next_function, index, config) is None:
            break

        current = next_function

    return tuple(chain), depth


def is_exempt(
    function: FunctionInfo,
    module: ModuleInfo,
    config: ArchbraceConfig,
) -> bool:
    if is_test_file(module.path):
        return True
    if function.name.startswith("__") and function.name.endswith("__"):
        return True
    if "property" in function.decorators:
        return True
    if "staticmethod" in function.decorators or "classmethod" in function.decorators:
        return True
    if matches_exempt_name(function.name, config.wrapper_chain_exempt_name_patterns):
        return True
    return has_exempt_decorator(function.decorators, config.wrapper_chain_exempt_decorators)


def matches_exempt_name(name: str, patterns: tuple[str, ...]) -> bool:
    return any(name == pattern or fnmatch.fnmatch(name, pattern) for pattern in patterns)


def has_exempt_decorator(
    decorators: tuple[str, ...],
    exempt_decorators: tuple[str, ...],
) -> bool:
    for decorator in decorators:
        for exempt in exempt_decorators:
            if decorator == exempt or decorator.endswith(f".{exempt.split('.')[-1]}"):
                return True
    return False


def is_test_file(path: Path) -> bool:
    return _TEST_FILE_PATTERN.match(path.name) is not None
