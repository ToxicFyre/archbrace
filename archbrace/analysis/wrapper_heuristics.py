"""
Purpose:
    Identify high-confidence wrapper functions using a conservative AST heuristic.

Why is this in this project:
    AR070 flags wrapper chains, not isolated delegation, so wrapper detection must
    stay strict and explainable.

Inputs:
    Function AST nodes, metadata, and a callable index.

Outputs:
    Resolved delegated callee qualified names for wrapper candidates.

Side effects:
    None.

Failure behavior:
    Never raises; non-wrappers return ``None``.
"""

from __future__ import annotations

import ast

from ..models import FunctionInfo, ModuleInfo
from .call_index import CallableIndex
from .call_resolution import expr_name, resolve_call

_DISQUALIFYING_NODES = (
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Match,
)
_COMPREHENSION_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef
_LOG_METHODS = frozenset({"debug", "info", "warning", "error", "critical", "exception"})
_GENERIC_CALLEE_NAMES = frozenset(
    {
        "run",
        "execute",
        "process",
        "handle",
        "manage",
        "orchestrate",
        "delegate",
        "call",
        "invoke",
        "perform",
        "do",
    }
)


def delegated_callee(
    node: _FunctionNode,
    function: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
) -> str | None:
    if has_disqualifying_control_flow(node):
        return None
    if has_rich_transformation(node):
        return None

    delegation = extract_delegation(node)
    if delegation is None:
        return None

    call_node, _preamble = delegation
    resolved = resolve_call(function, call_node, module, index)
    if resolved is None:
        return None

    business_calls = business_local_calls(node, function, module, index, resolved)
    if business_calls:
        return None

    if wrapper_score(node, function, call_node, resolved, business_calls) < 5:
        return None
    return resolved


def wrapper_score(
    node: _FunctionNode,
    function: FunctionInfo,
    call_node: ast.Call,
    resolved: str,
    business_calls: list[str],
) -> int:
    score = 3
    if passes_same_arguments(node, call_node):
        score += 2
    if len(body_statements(node)) <= 3:
        score += 1
    if function.name in _GENERIC_CALLEE_NAMES:
        score += 1
    elif resolved.rsplit(".", 1)[-1] in _GENERIC_CALLEE_NAMES:
        score += 1
    if has_meaningful_docstring(node):
        score -= 2
    if len(business_calls) >= 2:
        score -= 2
    return score


def business_local_calls(
    node: _FunctionNode,
    function: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
    delegated: str,
) -> list[str]:
    incidental = incidental_local_calls(node, function, module, index, delegated)
    return [
        callee
        for callee in resolved_local_calls(node, function, module, index)
        if callee != delegated and callee not in incidental
    ]


def extract_delegation(node: _FunctionNode) -> tuple[ast.Call, tuple[ast.stmt, ...]] | None:
    statements = body_statements(node)
    if not statements:
        return None

    single = single_return_delegation(statements)
    if single is not None:
        return single

    return multi_statement_delegation(statements)


def single_return_delegation(
    statements: list[ast.stmt],
) -> tuple[ast.Call, tuple[ast.stmt, ...]] | None:
    if len(statements) != 1 or not isinstance(statements[0], ast.Return):
        return None
    call = call_from_value(statements[0].value)
    return (call, ()) if call is not None else None


def multi_statement_delegation(
    statements: list[ast.stmt],
) -> tuple[ast.Call, tuple[ast.stmt, ...]] | None:
    *preamble, last = statements
    if not isinstance(last, ast.Return):
        return None

    assign_delegation = delegation_from_assignment(preamble, last)
    if assign_delegation is not None:
        return assign_delegation

    call = call_from_value(last.value)
    if call is None:
        return None
    if all(is_allowed_preamble_statement(statement) for statement in preamble):
        return call, tuple(preamble)
    return None


def delegation_from_assignment(
    preamble: list[ast.stmt],
    last: ast.Return,
) -> tuple[ast.Call, tuple[ast.stmt, ...]] | None:
    if len(preamble) != 1 or not isinstance(preamble[0], ast.Assign):
        return None
    call = call_from_value(preamble[0].value)
    target = assignment_target(preamble[0])
    if call is None or not returns_name(last, target):
        return None
    return call, tuple(preamble)


def body_statements(node: _FunctionNode) -> list[ast.stmt]:
    statements: list[ast.stmt] = []
    for statement in node.body:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            if isinstance(statement.value.value, str):
                continue
        statements.append(statement)
    return statements


def call_from_value(value: ast.expr | None) -> ast.Call | None:
    if value is None:
        return None
    if isinstance(value, ast.Call):
        return value
    if isinstance(value, ast.Await) and isinstance(value.value, ast.Call):
        return value.value
    return None


def returns_name(ret: ast.Return, name: str | None) -> bool:
    if name is None or ret.value is None:
        return False
    return isinstance(ret.value, ast.Name) and ret.value.id == name


def assignment_target(statement: ast.Assign) -> str | None:
    if len(statement.targets) != 1:
        return None
    target = statement.targets[0]
    return target.id if isinstance(target, ast.Name) else None


def incidental_local_calls(
    node: _FunctionNode,
    function: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
    delegated: str,
) -> set[str]:
    incidental: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        resolved = resolve_call(function, child, module, index)
        if resolved is None or resolved == delegated:
            continue
        if is_logger_call(child) or is_simple_validation_call(child):
            incidental.add(resolved)
    return incidental


def is_allowed_preamble_statement(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return is_logger_call(statement.value) or is_simple_validation_call(statement.value)
    if isinstance(statement, ast.If):
        return is_guard_clause(statement)
    return isinstance(statement, ast.Assert)


def is_logger_call(call: ast.Call) -> bool:
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "logger"
        and func.attr in _LOG_METHODS
    )


def is_simple_validation_call(call: ast.Call) -> bool:
    name = expr_name(call.func)
    if name is None:
        return False
    simple = name.rsplit(".", 1)[-1]
    return simple.startswith("validate") or simple.startswith("check_")


def is_guard_clause(statement: ast.If) -> bool:
    if statement.orelse or len(statement.body) != 1:
        return False
    return isinstance(statement.body[0], ast.Raise)


def has_disqualifying_control_flow(node: _FunctionNode) -> bool:
    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(child, _DISQUALIFYING_NODES):
            return True
        if isinstance(child, ast.If) and not is_guard_clause(child):
            if if_has_alternate_returns(child):
                return True
        if isinstance(child, _COMPREHENSION_NODES):
            return True
    return False


def if_has_alternate_returns(statement: ast.If) -> bool:
    returns = _returns_in_blocks(statement.body) + _returns_in_blocks(statement.orelse)
    if len(returns) < 2:
        return False
    return len({_normalize_return(value) for value in returns}) > 1


def _returns_in_blocks(block: list[ast.stmt]) -> list[ast.expr | None]:
    return [item.value for item in block if isinstance(item, ast.Return)]


def _normalize_return(value: ast.expr | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, ast.Call):
        return expr_name(value.func)
    if isinstance(value, ast.Await) and isinstance(value.value, ast.Call):
        return expr_name(value.value.func)
    if isinstance(value, ast.Name):
        return value.id
    return expr_name(value)


def has_rich_transformation(node: _FunctionNode) -> bool:
    for statement in body_statements(node):
        if isinstance(statement, ast.Return):
            continue
        if isinstance(statement, ast.AugAssign):
            return True
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Call):
            call_name = expr_name(statement.value.func)
            if call_name and looks_like_domain_construction(call_name):
                return True
    return False


def looks_like_domain_construction(name: str) -> bool:
    simple = name.rsplit(".", 1)[-1]
    return simple[:1].isupper() or simple.endswith("Command")


def resolved_local_calls(
    node: _FunctionNode,
    function: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
) -> list[str]:
    resolved: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            callee = resolve_call(function, child, module, index)
            if callee is not None:
                resolved.append(callee)
    return resolved


def passes_same_arguments(node: _FunctionNode, call: ast.Call) -> bool:
    positional_params = _positional_parameter_names(node)
    if not positional_params:
        return len(call.args) == 0 and len(call.keywords) == 0
    if len(call.args) != len(positional_params) or call.keywords:
        return False
    return all(
        isinstance(arg, ast.Name) and arg.id == param
        for param, arg in zip(positional_params, call.args, strict=True)
    )


def _positional_parameter_names(node: _FunctionNode) -> list[str]:
    params = list(node.args.posonlyargs) + list(node.args.args)
    return [arg.arg for arg in params if arg.arg not in {"self", "cls"}]


def has_meaningful_docstring(node: _FunctionNode) -> bool:
    docstring = ast.get_docstring(node)
    if not docstring:
        return False
    return len(docstring.strip()) >= 40 or "." in docstring
