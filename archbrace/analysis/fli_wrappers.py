"""
Purpose:
    Wrapper detection helpers for AR073 scoring.

Why is this in this project:
    FLI wrapper-chain scoring uses a simpler pass-through heuristic than AR070.

Inputs:
    Function AST nodes, metadata, and callable indexes.

Outputs:
    Delegated callee names for thin wrapper candidates.

Side effects:
    None.

Failure behavior:
    Never raises; non-wrappers return ``None``.
"""

from __future__ import annotations

import ast
import math

from ..models import FunctionInfo, ModuleInfo
from .call_index import CallableIndex
from .wrapper_heuristics import body_statements, call_from_value, resolved_local_calls

_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def iter_function_calls(node: _FunctionNode) -> list[ast.Call]:
    return [child for child in ast.walk(node) if isinstance(child, ast.Call)]


def fli_delegated_callee(
    node: _FunctionNode,
    function: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
) -> str | None:
    statements = body_statements(node)
    if len(statements) > 3:
        return None
    resolved = resolved_local_calls(node, function, module, index)
    if len(resolved) != 1:
        return None
    call_node = single_delegation_call(node)
    if call_node is None or not forwards_to_call(node, call_node):
        return None
    if not passes_parameter_threshold(node, call_node):
        return None
    return resolved[0]


def single_delegation_call(node: _FunctionNode) -> ast.Call | None:
    statements = body_statements(node)
    if not statements:
        return None
    if len(statements) == 1 and isinstance(statements[0], ast.Return):
        return call_from_value(statements[0].value)
    if isinstance(statements[-1], ast.Return):
        return call_from_value(statements[-1].value)
    return None


def forwards_to_call(node: _FunctionNode, call: ast.Call) -> bool:
    statements = body_statements(node)
    if len(statements) == 1 and isinstance(statements[0], ast.Return):
        return call_from_value(statements[0].value) is call
    if isinstance(statements[-1], ast.Return):
        return call_from_value(statements[-1].value) is call
    return False


def passes_parameter_threshold(node: _FunctionNode, call: ast.Call) -> bool:
    params = [
        arg.arg
        for arg in list(node.args.posonlyargs) + list(node.args.args)
        if arg.arg not in {"self", "cls"}
    ]
    if not params:
        return True
    required = math.ceil(0.7 * len(params))
    matched = 0
    for index, param in enumerate(params):
        if index >= len(call.args):
            break
        argument = call.args[index]
        if isinstance(argument, ast.Name) and argument.id == param:
            matched += 1
    return matched >= required
