"""
Purpose:
    Resolve conservative local callees for wrapper-chain analysis.

Why is this in this project:
    AR070 needs to map call sites to scanned functions without dynamic dispatch
    or runtime import execution.

Inputs:
    Call sites, caller metadata, and a callable index.

Outputs:
    Qualified names of resolvable local callees, if any.

Side effects:
    None.

Failure behavior:
    Never raises; unresolved calls return ``None``.
"""

from __future__ import annotations

import ast

from ..models import FunctionInfo, ModuleInfo
from .call_index import CallableIndex


def expr_name(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = expr_name(node.value)
        return f"{base}.{node.attr}" if base is not None else node.attr
    if isinstance(node, ast.Call):
        return expr_name(node.func)
    return None


def resolve_call(
    caller: FunctionInfo,
    call: ast.Call,
    module: ModuleInfo,
    index: CallableIndex,
) -> str | None:
    callee = expr_name(call.func)
    if callee is None or callee == "super":
        return None

    if "." not in callee:
        return _resolve_simple_name(module, callee, index)

    if callee.startswith("self.") or callee.startswith("cls."):
        return _resolve_method_call(caller, callee.split(".", 1)[1], index)

    return _resolve_prefixed_call(module, callee, index)


def resolve_imported(
    module_name: str,
    local_name: str,
    index: CallableIndex,
) -> str | None:
    target_module = index.import_targets.get(module_name, {}).get(local_name)
    if target_module is None:
        return None

    direct = f"{target_module}.{local_name}"
    if direct in index.callables_by_qualified_name:
        return direct

    if target_module in index.callables_by_qualified_name:
        return target_module

    return None


def _resolve_simple_name(
    module: ModuleInfo,
    callee: str,
    index: CallableIndex,
) -> str | None:
    same_module = f"{module.module_name}.{callee}"
    if same_module in index.callables_by_qualified_name:
        return same_module
    return resolve_imported(module.module_name, callee, index)


def _resolve_method_call(
    caller: FunctionInfo,
    method: str,
    index: CallableIndex,
) -> str | None:
    if caller.parent_class is None:
        return None
    qualified = f"{caller.parent_class}.{method}"
    if qualified in index.callables_by_qualified_name:
        return qualified
    return None


def _resolve_prefixed_call(
    module: ModuleInfo,
    callee: str,
    index: CallableIndex,
) -> str | None:
    prefix, name = callee.split(".", 1)
    module_path = index.import_targets.get(module.module_name, {}).get(prefix)
    if module_path is None:
        return None
    qualified = f"{module_path}.{name}"
    if qualified in index.callables_by_qualified_name:
        return qualified
    return None
