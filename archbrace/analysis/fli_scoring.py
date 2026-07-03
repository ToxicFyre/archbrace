"""
Purpose:
    FLI scoring helpers for AR073.

Why is this in this project:
    AR073 combines module span, layer crossings, wrapper chains, and domain hops.

Inputs:
    Traversal results, entry metadata, and configuration limits.

Outputs:
    Component scores, display paths, and reason strings.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import FunctionInfo, ModuleInfo
from .call_index import CallableIndex, module_for_function
from .fli_models import GENERIC_LAYERS, SHARED_DOMAIN_TOKENS, FliScores, module_domain
from .fli_wrappers import fli_delegated_callee


def compute_scores(
    entry: FunctionInfo,
    entry_module: ModuleInfo,
    reached_modules: set[str],
    unresolved: int,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> FliScores:
    return FliScores(
        module_span=score_module_span(reached_modules),
        layer_crossing=score_layer_crossing(reached_modules),
        wrapper_chain=score_wrapper_chain(entry, index, config),
        remote_domain=score_remote_domain(entry_module, reached_modules),
        unresolved_edge=score_unresolved(unresolved),
    )


def score_module_span(reached_modules: set[str]) -> int:
    count = len(reached_modules)
    if count <= 1:
        return 0
    if count == 2:
        return 1
    if count == 3:
        return 2
    if count == 4:
        return 3
    return 5


def score_layer_crossing(reached_modules: set[str]) -> int:
    layers = {layer for module in reached_modules if (layer := module_generic_layer(module))}
    score = len(layers)
    if len(layers) >= 4:
        score += 2
    return score


def module_generic_layer(module_name: str) -> str | None:
    for token in module_name.split("."):
        if token in GENERIC_LAYERS:
            return token
    return None


def score_wrapper_chain(
    entry: FunctionInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> int:
    depth = longest_wrapper_chain_depth(entry, index, config)
    if depth <= 1:
        return 0
    if depth == 2:
        return 2
    if depth == 3:
        return 4
    return 7


def longest_wrapper_chain_depth(
    start: FunctionInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> int:
    best = 0
    stack: list[tuple[str, int, set[str]]] = [(start.qualified_name, 0, set())]
    while stack:
        name, depth, visited = stack.pop()
        delegated = _next_wrapper(name, visited, index)
        if delegated is None:
            best = max(best, depth)
            continue
        best = max(best, depth + 1)
        if depth + 1 < config.max_fli_depth:
            stack.append((delegated, depth + 1, visited | {name}))
    return best


def _next_wrapper(
    name: str,
    visited: set[str],
    index: CallableIndex,
) -> str | None:
    function = index.callables_by_qualified_name.get(name)
    module = module_for_function(function, index) if function is not None else None
    node = index.nodes_by_qualified_name.get(name) if function is not None else None
    if function is None or module is None or node is None:
        return None
    delegated = fli_delegated_callee(node, function, module, index)
    if delegated is None or delegated in visited:
        return None
    return delegated


def score_remote_domain(entry_module: ModuleInfo, reached_modules: set[str]) -> int:
    entry_domain = module_domain(entry_module.module_name)
    score = 0
    visited_shared = False
    for module_name in reached_modules:
        if module_name == entry_module.module_name:
            continue
        if module_domain(module_name) != entry_domain:
            score += 1
        if uses_shared_utils(module_name):
            visited_shared = True
    if visited_shared:
        score += 2
    return score


def uses_shared_utils(module_name: str) -> bool:
    return bool(set(module_name.split(".")) & SHARED_DOMAIN_TOKENS)


def score_unresolved(unresolved: int) -> int:
    if unresolved == 0:
        return 0
    if unresolved <= 2:
        return 1
    return 2


def build_display_path(
    entry: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> tuple[str, ...]:
    path = [path_label(entry, module)]
    current = entry
    visited = {entry.qualified_name}
    while len(path) <= config.max_fli_depth:
        next_hop = _next_wrapper(current.qualified_name, visited, index)
        if next_hop is None:
            break
        next_function = index.callables_by_qualified_name.get(next_hop)
        next_module = module_for_function(next_function, index) if next_function else None
        if next_function is None or next_module is None:
            break
        path.append(path_label(next_function, next_module))
        visited.add(next_hop)
        current = next_function
    return tuple(path)


def path_label(function: FunctionInfo, module: ModuleInfo) -> str:
    rel = module.path.as_posix()
    if function.parent_class is None:
        return f"{rel}:{function.name}"
    class_name = function.parent_class.rsplit(".", 1)[-1]
    return f"{rel}:{class_name}.{function.name}"


def format_reasons(scores: FliScores, unresolved: int) -> tuple[str, ...]:
    reasons: list[str] = []
    if scores.module_span:
        reasons.append(f"+{scores.module_span} module span")
    if scores.layer_crossing:
        reasons.append(f"+{scores.layer_crossing} generic layer crossings")
    if scores.wrapper_chain:
        reasons.append(f"+{scores.wrapper_chain} wrapper chain")
    if scores.remote_domain:
        reasons.append(f"+{scores.remote_domain} remote domain")
    if scores.unresolved_edge:
        reasons.append(f"+{scores.unresolved_edge} unresolved edges")
    return tuple(reasons)
