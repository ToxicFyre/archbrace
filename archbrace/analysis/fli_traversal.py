"""
Purpose:
    Conservative call-graph traversal for AR073.

Why is this in this project:
    FLI scoring needs depth-limited reachability with unresolved-edge tracking.

Inputs:
    Entry functions, callable indexes, and traversal limits.

Outputs:
    Reached modules, call edges, and unresolved-edge counts.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

import ast

from ..config import ArchbraceConfig
from ..models import FunctionInfo, ModuleInfo
from .call_index import CallableIndex, module_for_function
from .call_resolution import expr_name, resolve_call
from .fli_models import CallEdge, module_domain
from .fli_wrappers import iter_function_calls

_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def traverse_from(
    start: FunctionInfo,
    start_module: ModuleInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> tuple[set[str], list[CallEdge], int]:
    state = _TraversalState(
        reached_modules={start_module.module_name},
        edges=[],
        unresolved=0,
        queue=[(start.qualified_name, 0)],
        visited=set(),
    )
    while state.queue:
        current_name, depth = state.queue.pop(0)
        if current_name in state.visited:
            continue
        state.visited.add(current_name)
        current = index.callables_by_qualified_name.get(current_name)
        module = module_for_function(current, index) if current is not None else None
        node = index.nodes_by_qualified_name.get(current_name)
        if current is None or module is None or node is None:
            continue
        state.reached_modules.add(module.module_name)
        if depth >= config.max_fli_depth:
            continue
        _visit_calls(state, current, module, node, index, depth)
    return state.reached_modules, state.edges, state.unresolved


class _TraversalState:
    def __init__(
        self,
        *,
        reached_modules: set[str],
        edges: list[CallEdge],
        unresolved: int,
        queue: list[tuple[str, int]],
        visited: set[str],
    ) -> None:
        self.reached_modules = reached_modules
        self.edges = edges
        self.unresolved = unresolved
        self.queue = queue
        self.visited = visited


def _visit_calls(
    state: _TraversalState,
    current: FunctionInfo,
    module: ModuleInfo,
    node: _FunctionNode,
    index: CallableIndex,
    depth: int,
) -> None:
    for call in iter_function_calls(node):
        resolved = resolve_call(current, call, module, index)
        if resolved is not None and resolved in index.callables_by_qualified_name:
            _record_resolved_call(state, current, call, module, index, resolved, depth)
        elif is_unresolved_call(call):
            _record_unresolved_call(state, current.qualified_name, call)


def _record_resolved_call(
    state: _TraversalState,
    current: FunctionInfo,
    call: ast.Call,
    module: ModuleInfo,
    index: CallableIndex,
    resolved: str,
    depth: int,
) -> None:
    target = index.callables_by_qualified_name[resolved]
    target_module = module_for_function(target, index)
    if target_module is None:
        return
    state.reached_modules.add(target_module.module_name)
    state.edges.append(
        make_edge(
            current.qualified_name,
            resolved,
            module,
            target_module,
            call_kind(current, call, module, resolved),
            "high",
        )
    )
    state.queue.append((resolved, depth + 1))


def _record_unresolved_call(
    state: _TraversalState,
    caller: str,
    call: ast.Call,
) -> None:
    state.unresolved += 1
    state.edges.append(
        CallEdge(
            caller=caller,
            callee=expr_name(call.func) or "<dynamic>",
            confidence="unresolved",
            same_file=False,
            same_package=False,
            call_kind="unresolved",
        )
    )


def is_unresolved_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Subscript):
        return True
    if isinstance(func, ast.Call):
        return False
    name = expr_name(func)
    if name is None:
        return True
    simple = name.split(".")[0]
    if simple in {"getattr", "callback"}:
        return True
    return simple.endswith("_registry") or simple == "registry"


def make_edge(
    caller: str,
    callee: str,
    caller_module: ModuleInfo,
    callee_module: ModuleInfo,
    call_kind: str,
    confidence: str,
) -> CallEdge:
    same_file = caller_module.path == callee_module.path
    same_package = module_domain(caller_module.module_name) == module_domain(
        callee_module.module_name
    )
    return CallEdge(
        caller=caller,
        callee=callee,
        confidence=confidence,
        same_file=same_file,
        same_package=same_package,
        call_kind=call_kind,
    )


def call_kind(
    caller: FunctionInfo,
    call: ast.Call,
    module: ModuleInfo,
    resolved: str,
) -> str:
    callee = expr_name(call.func)
    if callee is None:
        return "unresolved"
    if callee.startswith("self.") or callee.startswith("cls."):
        return "method"
    if resolved.startswith(f"{module.module_name}."):
        return "direct"
    if "." in callee:
        return "imported"
    return "direct"
