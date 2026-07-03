"""
Purpose:
    Entry-point detection helpers for AR073.

Why is this in this project:
    FLI analysis should start from workflow roots, not private helpers.

Inputs:
    Function metadata, module structure, and configuration.

Outputs:
    Boolean entry-point classification for candidate functions.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import FunctionInfo, ModuleInfo
from .call_graph import has_exempt_decorator, matches_exempt_name
from .fli_models import ENTRY_POINT_NAMES, ROUTE_DECORATORS, EntryPointInfo


def is_entry_point(
    function: FunctionInfo,
    module: ModuleInfo,
    config: ArchbraceConfig,
) -> bool:
    if is_private_helper(function):
        return False
    if is_nested_function(function, module):
        return False
    if is_special_method(function):
        return False
    if has_entry_signal(function, config):
        return True
    return function.is_public and is_top_level_or_method(function, module)


def is_private_helper(function: FunctionInfo) -> bool:
    return function.name.startswith("_")


def is_special_method(function: FunctionInfo) -> bool:
    if function.name.startswith("__") and function.name.endswith("__"):
        return True
    if "property" in function.decorators:
        return True
    return "staticmethod" in function.decorators or "classmethod" in function.decorators


def has_entry_signal(function: FunctionInfo, config: ArchbraceConfig) -> bool:
    if matches_exempt_name(function.name, config.wrapper_chain_exempt_name_patterns):
        return True
    if has_route_decorator(function.decorators):
        return True
    return function.name in ENTRY_POINT_NAMES


def is_top_level_or_method(function: FunctionInfo, module: ModuleInfo) -> bool:
    if function.parent_class is not None:
        return True
    return function.qualified_name == f"{module.module_name}.{function.name}"


def is_nested_function(function: FunctionInfo, module: ModuleInfo) -> bool:
    for top in module.functions:
        if _contains_nested(function, top):
            return True
    for klass in module.classes:
        for method in klass.methods:
            if _contains_nested(function, method):
                return True
    return False


def _contains_nested(target: FunctionInfo, container: FunctionInfo) -> bool:
    for nested in container.nested_functions:
        if nested.qualified_name == target.qualified_name:
            return True
        if _contains_nested(target, nested):
            return True
    return False


def has_route_decorator(decorators: tuple[str, ...]) -> bool:
    return has_exempt_decorator(decorators, ROUTE_DECORATORS)


def matching_route_decorators(decorators: tuple[str, ...]) -> tuple[str, ...]:
    matched: list[str] = []
    for decorator in decorators:
        for route in ROUTE_DECORATORS:
            if decorator == route or decorator.endswith(f".{route.split('.')[-1]}"):
                matched.append(decorator)
                break
    return tuple(matched)


def classify_entry_point(
    function: FunctionInfo,
    module: ModuleInfo,
    config: ArchbraceConfig,
) -> EntryPointInfo:
    signals = _entry_point_signals(function, module, config)
    return EntryPointInfo(
        signals=tuple(signals),
        decorators=matching_route_decorators(function.decorators),
        is_public=function.is_public,
        parent_class=function.parent_class,
    )


def _entry_point_signals(
    function: FunctionInfo,
    module: ModuleInfo,
    config: ArchbraceConfig,
) -> list[str]:
    signals: list[str] = []
    _append_route_signal(function, signals)
    _append_exempt_signal(function, config, signals)
    _append_named_signal(function, signals)
    if signals:
        return signals
    return _fallback_entry_signals(function, module)


def _append_route_signal(function: FunctionInfo, signals: list[str]) -> None:
    if matching_route_decorators(function.decorators):
        signals.append("route_decorator")


def _append_exempt_signal(
    function: FunctionInfo,
    config: ArchbraceConfig,
    signals: list[str],
) -> None:
    if matches_exempt_name(function.name, config.wrapper_chain_exempt_name_patterns):
        signals.append("exempt_name_pattern")


def _append_named_signal(function: FunctionInfo, signals: list[str]) -> None:
    if function.name in ENTRY_POINT_NAMES:
        signals.append("named_entry")


def _fallback_entry_signals(function: FunctionInfo, module: ModuleInfo) -> list[str]:
    if function.parent_class is not None and function.is_public:
        return ["public_method"]
    if function.is_public and is_top_level_or_method(function, module):
        return ["public_api"]
    return []
