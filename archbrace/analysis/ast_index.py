"""
Purpose:
    Parse a Python module into Archbrace's structural models: the module
    docstring, top-level functions (with their nested functions), classes and
    their methods, and per-function metrics.

Inputs:
    A file path, its source text, and the dotted module name.

Outputs:
    A ``ModuleInfo`` populated from the AST and the Radon adapter.

Side effects:
    None.

Failure behavior:
    Raises ``AnalysisError`` when the source cannot be parsed.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ..errors import AnalysisError
from ..models import (
    CallRef,
    ClassInfo,
    FunctionInfo,
    ModuleInfo,
    SourceRange,
)
from . import radon_metrics

_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef
_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_NESTING_STMT = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Match,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
)


def build_module_info(
    path: Path,
    source: str,
    module_name: str,
    layer: str | None = None,
) -> ModuleInfo:
    """
    Inputs:
        The module path, source text, dotted name, and optional layer.

    Outputs:
        A ``ModuleInfo`` describing the module's structure and metrics.

    Side effects:
        None.

    Failure behavior:
        Raises ``AnalysisError`` on syntax errors.
    """
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise AnalysisError(f"{path}: could not parse source: {exc}") from exc

    complexity = radon_metrics.complexity_map(source)
    code_lines = radon_metrics.code_line_numbers(source)

    functions = tuple(
        _build_function(node, module_name, complexity, code_lines)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    classes = tuple(
        _build_class(node, module_name, complexity, code_lines)
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    )

    return ModuleInfo(
        path=path,
        module_name=module_name,
        source=source,
        layer=layer,
        imports=(),
        functions=functions,
        classes=classes,
        module_docstring=ast.get_docstring(tree),
        raw_metrics=radon_metrics.raw_metrics(source),
        maintainability_index=radon_metrics.maintainability_index(source),
        tree=tree,
    )


def _build_function(
    node: _FunctionNode,
    prefix: str,
    complexity: dict[int, int],
    code_lines: frozenset[int],
) -> FunctionInfo:
    qualified_name = f"{prefix}.{node.name}"
    nested = tuple(
        _build_function(child, qualified_name, complexity, code_lines)
        for child in _collect_direct_functions(node)
    )
    return FunctionInfo(
        qualified_name=qualified_name,
        name=node.name,
        location=_span(node),
        parameters=_parameter_names(node.args),
        return_count=_count_returns(node),
        local_variable_count=_count_local_variables(node),
        nesting_depth=_nesting_depth(node),
        cyclomatic_complexity=complexity.get(node.lineno, 1),
        has_docstring=ast.get_docstring(node) is not None,
        is_public=not node.name.startswith("_"),
        calls=_collect_calls(node),
        nested_functions=nested,
        code_lines=_count_code_lines(node, code_lines),
    )


def _build_class(
    node: ast.ClassDef,
    module_name: str,
    complexity: dict[int, int],
    code_lines: frozenset[int],
) -> ClassInfo:
    qualified_name = f"{module_name}.{node.name}"
    methods = tuple(
        _build_function(child, qualified_name, complexity, code_lines)
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    bases = tuple(
        name for base in node.bases if (name := _expr_name(base)) is not None
    )
    decorators = tuple(
        name
        for decorator in node.decorator_list
        if (name := _expr_name(decorator)) is not None
    )
    return ClassInfo(
        qualified_name=qualified_name,
        name=node.name,
        location=_span(node),
        methods=methods,
        bases=bases,
        decorators=decorators,
    )


def _count_code_lines(node: _FunctionNode, code_lines: frozenset[int]) -> int:
    # Count from ``def``/``async def`` (``node.lineno``), so decorators are
    # excluded; ``code_lines`` already omits docstrings, comments, and blanks.
    # Nested functions remain inside the parent's range and are also measured
    # separately as their own ``FunctionInfo``.
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    return sum(1 for line in code_lines if node.lineno <= line <= end)


def _span(node: _FunctionNode | ast.ClassDef) -> SourceRange:
    start_line = node.lineno
    if node.decorator_list:
        start_line = min(decorator.lineno for decorator in node.decorator_list)
    end_column = None if node.end_col_offset is None else node.end_col_offset + 1
    return SourceRange(
        line=start_line,
        column=node.col_offset + 1,
        end_line=node.end_lineno,
        end_column=end_column,
    )


def _parameter_names(args: ast.arguments) -> tuple[str, ...]:
    names: list[str] = [arg.arg for arg in args.posonlyargs]
    names.extend(arg.arg for arg in args.args)
    if args.vararg is not None:
        names.append(args.vararg.arg)
    names.extend(arg.arg for arg in args.kwonlyargs)
    if args.kwarg is not None:
        names.append(args.kwarg.arg)
    return tuple(names)


def _count_returns(node: _FunctionNode) -> int:
    return sum(1 for owned in _iter_own_nodes(node) if isinstance(owned, ast.Return))


def _count_local_variables(node: _FunctionNode) -> int:
    names: set[str] = set()
    for owned in _iter_own_nodes(node):
        names |= _names_introduced_by(owned)
    names -= set(_parameter_names(node.args))
    return len(names)


def _collect_calls(node: _FunctionNode) -> tuple[CallRef, ...]:
    calls: list[CallRef] = []
    for owned in _iter_own_nodes(node):
        if isinstance(owned, ast.Call):
            callee = _expr_name(owned.func)
            if callee is not None:
                calls.append(
                    CallRef(
                        callee=callee,
                        location=SourceRange(line=owned.lineno, column=owned.col_offset + 1),
                    )
                )
    return tuple(calls)


def _collect_direct_functions(node: _FunctionNode) -> list[_FunctionNode]:
    result: list[_FunctionNode] = []
    for stmt in node.body:
        _gather_functions(stmt, result)
    return result


def _gather_functions(node: ast.AST, result: list[_FunctionNode]) -> None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        result.append(node)
        return
    if isinstance(node, (ast.Lambda, ast.ClassDef)):
        return
    for child in ast.iter_child_nodes(node):
        _gather_functions(child, result)


def _iter_own_nodes(node: _FunctionNode):  # type: ignore[no-untyped-def]
    for stmt in node.body:
        yield from _walk_own(stmt)


def _walk_own(node: ast.AST):  # type: ignore[no-untyped-def]
    if isinstance(node, _SCOPE_NODES):
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _walk_own(child)


def _names_introduced_by(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Assign):
        names: set[str] = set()
        for target in node.targets:
            names |= _names_from_target(target)
        return names
    if isinstance(node, ast.AnnAssign):
        return _names_from_target(node.target)
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return _names_from_target(node.target)
    if isinstance(node, (ast.With, ast.AsyncWith)):
        names = set()
        for item in node.items:
            if item.optional_vars is not None:
                names |= _names_from_target(item.optional_vars)
        return names
    if isinstance(node, ast.ExceptHandler):
        return {node.name} if node.name else set()
    if isinstance(node, ast.comprehension):
        return _names_from_target(node.target)
    if isinstance(node, ast.MatchAs):
        return {node.name} if node.name else set()
    if isinstance(node, ast.MatchStar):
        return {node.name} if node.name else set()
    if isinstance(node, ast.MatchMapping):
        return {node.rest} if node.rest else set()
    return set()


def _names_from_target(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, ast.Starred):
        return _names_from_target(target.value)
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names |= _names_from_target(element)
        return names
    return set()


def _nesting_depth(node: _FunctionNode) -> int:
    return _block_depth(node.body)


def _block_depth(statements: list[ast.stmt]) -> int:
    return max((_statement_depth(statement) for statement in statements), default=0)


def _statement_depth(statement: ast.stmt) -> int:
    inner = max((_block_depth(block) for block in _child_blocks(statement)), default=0)
    if isinstance(statement, _NESTING_STMT):
        return 1 + inner
    return inner


def _child_blocks(statement: ast.stmt) -> list[list[ast.stmt]]:
    if isinstance(statement, ast.If):
        blocks = [statement.body]
        orelse = statement.orelse
        # Flatten ``elif`` chains so they count as one nesting level, not many.
        while len(orelse) == 1 and isinstance(orelse[0], ast.If):
            blocks.append(orelse[0].body)
            orelse = orelse[0].orelse
        if orelse:
            blocks.append(orelse)
        return blocks
    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        return [statement.body, statement.orelse]
    if isinstance(statement, (ast.With, ast.AsyncWith)):
        return [statement.body]
    if isinstance(statement, ast.Try):
        blocks = [statement.body, statement.orelse, statement.finalbody]
        blocks.extend(handler.body for handler in statement.handlers)
        return blocks
    if isinstance(statement, ast.Match):
        return [case.body for case in statement.cases]
    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [statement.body]
    return []


def _expr_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_name(node.value)
        return f"{base}.{node.attr}" if base is not None else node.attr
    if isinstance(node, ast.Call):
        return _expr_name(node.func)
    return None
