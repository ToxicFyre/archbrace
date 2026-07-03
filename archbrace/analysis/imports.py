"""
Purpose:
    Collect import statements and build local-name to module-path maps for call
    resolution.

Why is this in this project:
    Conservative cross-module call resolution for AR070 depends on import metadata
    without attempting full runtime import semantics.

Inputs:
    Parsed module trees and ``ModuleInfo`` import tuples.

Outputs:
    Import tuples and per-module import lookup maps.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed trees.
"""

from __future__ import annotations

import ast

from ..models import ImportInfo, ModuleInfo, SourceRange


def collect_imports(tree: ast.Module) -> tuple[ImportInfo, ...]:
    imports: list[ImportInfo] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(_import_nodes(node))
        elif isinstance(node, ast.ImportFrom):
            imports.extend(_import_from_nodes(node))
    return tuple(imports)


def build_import_map(module: ModuleInfo) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for imp in module.imports:
        if not imp.names:
            continue
        local_name = imp.names[0]
        if imp.is_relative:
            target_module = resolve_relative_module(module.module_name, imp.module, imp.level)
        else:
            target_module = imp.module
        mapping[local_name] = target_module
    return mapping


def resolve_relative_module(module_name: str, relative: str, level: int) -> str:
    parts = module_name.split(".")
    prefix_parts = parts[: max(len(parts) - level, 0)]
    suffix = relative.lstrip(".")
    if suffix:
        return ".".join(part for part in [*prefix_parts, *suffix.split(".")] if part)
    return ".".join(prefix_parts)


def _import_nodes(node: ast.Import) -> list[ImportInfo]:
    imports: list[ImportInfo] = []
    for alias in node.names:
        local = alias.asname or alias.name.split(".")[0]
        imports.append(
            ImportInfo(
                module=alias.name,
                names=(local,),
                is_relative=False,
                level=0,
                location=SourceRange(line=node.lineno, column=node.col_offset + 1),
            )
        )
    return imports


def _import_from_nodes(node: ast.ImportFrom) -> list[ImportInfo]:
    imports: list[ImportInfo] = []
    module = _relative_module_label(node.module, node.level)
    for alias in node.names:
        if alias.name == "*":
            continue
        local = alias.asname or alias.name
        imports.append(
            ImportInfo(
                module=module,
                names=(local,),
                is_relative=node.level > 0,
                level=node.level,
                location=SourceRange(line=node.lineno, column=node.col_offset + 1),
            )
        )
    return imports


def _relative_module_label(module: str | None, level: int) -> str:
    if level == 0:
        return module or ""
    prefix = "." * level
    return f"{prefix}{module}" if module else prefix
