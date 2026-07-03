"""
Purpose:
    Build project-level callable lookup tables for conservative call resolution.

Why is this in this project:
    Wrapper-chain analysis needs qualified-name and import maps shared by call
    resolution and wrapper heuristics.

Inputs:
    A ``ProjectIndex``.

Outputs:
    Callable lookup tables and AST nodes keyed by qualified name.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass

from ..models import FunctionInfo, ModuleInfo, ProjectIndex
from ..rules.base import iter_functions
from .imports import build_import_map

_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class CallableIndex:
    """Project-level lookup tables for conservative call resolution."""

    callables_by_qualified_name: dict[str, FunctionInfo]
    callables_by_simple_name: dict[str, tuple[str, ...]]
    module_by_name: dict[str, ModuleInfo]
    import_targets: dict[str, dict[str, str]]
    nodes_by_qualified_name: dict[str, _FunctionNode]


def build_callable_index(project: ProjectIndex) -> CallableIndex:
    callables_by_qualified_name: dict[str, FunctionInfo] = {}
    callables_by_simple_name: dict[str, list[str]] = defaultdict(list)
    module_by_name: dict[str, ModuleInfo] = {}
    import_targets: dict[str, dict[str, str]] = {}
    nodes_by_qualified_name: dict[str, _FunctionNode] = {}

    for module in project.modules:
        module_by_name[module.module_name] = module
        import_targets[module.module_name] = build_import_map(module)
        for node, qualified_name, _parent_class in iter_function_nodes(module):
            function = function_for_qualified_name(module, qualified_name)
            if function is None:
                continue
            callables_by_qualified_name[qualified_name] = function
            callables_by_simple_name[function.name].append(qualified_name)
            nodes_by_qualified_name[qualified_name] = node

    return CallableIndex(
        callables_by_qualified_name=callables_by_qualified_name,
        callables_by_simple_name={
            name: tuple(names) for name, names in callables_by_simple_name.items()
        },
        module_by_name=module_by_name,
        import_targets=import_targets,
        nodes_by_qualified_name=nodes_by_qualified_name,
    )


def module_for_function(function: FunctionInfo, index: CallableIndex) -> ModuleInfo | None:
    module_prefix = function.qualified_name.rsplit(".", 1)[0]
    if module_prefix in index.module_by_name:
        return index.module_by_name[module_prefix]
    for module in index.module_by_name.values():
        if function.qualified_name.startswith(f"{module.module_name}."):
            return module
    return None


def function_for_qualified_name(
    module: ModuleInfo,
    qualified_name: str,
) -> FunctionInfo | None:
    for function in iter_functions(module):
        if function.qualified_name == qualified_name:
            return function
    return None


def iter_function_nodes(
    module: ModuleInfo,
) -> list[tuple[_FunctionNode, str, str | None]]:
    tree = module.tree
    if tree is None:
        return []

    collected: list[tuple[_FunctionNode, str, str | None]] = []
    _collect_function_nodes(tree.body, module.module_name, None, collected)
    return collected


def _collect_function_nodes(
    statements: list[ast.stmt],
    prefix: str,
    parent_class: str | None,
    collected: list[tuple[_FunctionNode, str, str | None]],
) -> None:
    for statement in statements:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _append_function_node(statement, prefix, parent_class, collected)
        elif isinstance(statement, ast.ClassDef):
            _append_class_methods(statement, prefix, collected)


def _append_function_node(
    node: _FunctionNode,
    prefix: str,
    parent_class: str | None,
    collected: list[tuple[_FunctionNode, str, str | None]],
) -> None:
    qualified_name = f"{prefix}.{node.name}"
    collected.append((node, qualified_name, parent_class))
    _collect_function_nodes(
        _nested_function_nodes(node),
        qualified_name,
        parent_class,
        collected,
    )


def _append_class_methods(
    class_node: ast.ClassDef,
    prefix: str,
    collected: list[tuple[_FunctionNode, str, str | None]],
) -> None:
    class_name = f"{prefix}.{class_node.name}"
    for child in class_node.body:
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        method_name = f"{class_name}.{child.name}"
        collected.append((child, method_name, class_name))
        _collect_function_nodes(
            _nested_function_nodes(child),
            method_name,
            class_name,
            collected,
        )


def _nested_function_nodes(node: _FunctionNode) -> list[ast.stmt]:
    nested: list[ast.stmt] = []
    for statement in node.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nested.append(statement)
            continue
        nested.extend(_functions_in_statement(statement))
    return nested


def _functions_in_statement(statement: ast.stmt) -> list[ast.stmt]:
    found: list[ast.stmt] = []
    for block in _statement_blocks(statement):
        for child in block:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append(child)
    return found


def _statement_blocks(statement: ast.stmt) -> list[list[ast.stmt]]:
    if isinstance(statement, ast.If):
        return [statement.body, statement.orelse]
    if isinstance(statement, (ast.With, ast.AsyncWith)):
        return [statement.body]
    if isinstance(statement, ast.Try):
        blocks = [statement.body, statement.orelse, statement.finalbody]
        blocks.extend(handler.body for handler in statement.handlers)
        return blocks
    return []
