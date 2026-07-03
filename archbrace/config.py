"""
Purpose:
    Load, validate, and normalize Archbrace configuration from ``pyproject.toml``
    ``[tool.archbrace]`` tables, and merge command-line overrides on top.

Why is this in this project:
    Single source of truth for thresholds and toggles so rule behavior is
    configurable per project while staying deterministic.

Inputs:
    A ``pyproject.toml`` file (located by upward search or an explicit path) and
    optional CLI ``--select`` / ``--ignore`` overrides.

Outputs:
    A validated, immutable ``ArchbraceConfig``.

Side effects:
    Reads configuration files from disk.

Failure behavior:
    Raises ``ConfigError`` for missing files, unknown keys, or invalid value
    types (mapped to exit code 2 by the CLI).
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pathspec

from .errors import ConfigError
from .models import Severity

_VALID_SEVERITIES: frozenset[str] = frozenset({"error", "warning"})
_VALID_FORMATS: frozenset[str] = frozenset({"text", "json"})

# Nested ``[tool.archbrace.*]`` tables handled explicitly (spec Section 5).
_KNOWN_TABLES: frozenset[str] = frozenset(
    {"severity", "module_contract", "io_contract", "layers"}
)

# Match Ruff's built-in ``exclude`` defaults so ``archbrace check .`` skips the
# same non-project paths without extra configuration.
# https://docs.astral.sh/ruff/configuration/
DEFAULT_EXCLUDE: tuple[str, ...] = (
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".git-rewrite",
    ".hg",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".pyenv",
    ".pytest_cache",
    ".pytype",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    ".vscode",
    "__pypackages__",
    "_build",
    "buck-out",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "venv",
)

_RESOLVED_EXCLUDE_KEYS: frozenset[str] = frozenset({"exclude", "extend_exclude"})


@dataclass(frozen=True)
class ArchbraceConfig:
    """Validated Archbrace configuration for a single run."""

    config_path: Path | None
    root: Path

    target_python: str = "3.11"
    format: str = "text"
    fail_on: Severity = "error"

    select: tuple[str, ...] = ("AR",)
    ignore_rules: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE

    max_function_lines: int = 40
    max_file_lines: int = 300
    max_nesting_depth: int = 3
    max_parameters: int = 5
    max_classes_per_file: int = 3
    max_public_functions_per_file: int = 12

    max_cyclomatic_complexity: int = 8
    min_maintainability_index: float = 65.0
    max_returns: int = 5
    max_local_variables: int = 15

    max_wrapper_chain_depth: int = 2
    wrapper_chain_exempt_decorators: tuple[str, ...] = (
        "click.command",
        "app.route",
        "router.get",
        "router.post",
        "celery.task",
    )
    wrapper_chain_exempt_name_patterns: tuple[str, ...] = (
        "main",
        "__enter__",
        "__exit__",
        "__aenter__",
        "__aexit__",
    )
    max_changed_files: int = 8
    max_changed_lines: int = 400
    max_new_functions: int = 12
    max_new_classes: int = 3
    max_new_modules: int = 5

    require_module_contract: bool = True
    require_io_docstrings: bool = True
    require_orchestrator_step_comments: bool = False
    require_orchestrator_logging: bool = True

    vague_module_names: tuple[str, ...] = (
        "utils",
        "helpers",
        "common",
        "misc",
        "shared",
    )
    suspicious_class_suffixes: tuple[str, ...] = (
        "Manager",
        "Service",
        "Processor",
        "Handler",
        "Engine",
        "Coordinator",
        "Controller",
        "Orchestrator",
        "Helper",
        "Utility",
    )
    io_call_patterns: tuple[str, ...] = ()

    severity: dict[str, Severity] = field(default_factory=dict)
    module_contract_sections: tuple[str, ...] = ()
    io_contract_sections: tuple[str, ...] = ()
    layers: dict[str, Any] = field(default_factory=dict)

    def merge_cli(
        self,
        *,
        select: tuple[str, ...] | None,
        ignore: tuple[str, ...] | None,
    ) -> ArchbraceConfig:
        """
        Inputs:
            Optional CLI ``select`` / ``ignore`` tuples.

        Outputs:
            A new ``ArchbraceConfig`` with CLI values overriding file values when
            provided, leaving the original instance unchanged.

        Side effects:
            None.

        Failure behavior:
            Never raises.
        """
        changes: dict[str, Any] = {}
        if select is not None:
            changes["select"] = tuple(select)
        if ignore is not None:
            changes["ignore_rules"] = tuple(ignore)
        if not changes:
            return self
        return replace(self, **changes)

    def exclude_spec(self) -> pathspec.PathSpec:
        """
        Inputs:
            None.

        Outputs:
            A PathSpec compiled from the configured ``exclude`` patterns using
            Git-style wildmatch semantics.

        Side effects:
            None.

        Failure behavior:
            Never raises for valid pattern strings.
        """
        return pathspec.PathSpec.from_lines("gitignore", self.exclude)


# Scalar / list keys and the validator each requires.
_INT_KEYS: frozenset[str] = frozenset(
    {
        "max_function_lines",
        "max_file_lines",
        "max_nesting_depth",
        "max_parameters",
        "max_classes_per_file",
        "max_public_functions_per_file",
        "max_cyclomatic_complexity",
        "max_returns",
        "max_local_variables",
        "max_wrapper_chain_depth",
        "max_changed_files",
        "max_changed_lines",
        "max_new_functions",
        "max_new_classes",
        "max_new_modules",
    }
)
_FLOAT_KEYS: frozenset[str] = frozenset({"min_maintainability_index"})
_BOOL_KEYS: frozenset[str] = frozenset(
    {
        "require_module_contract",
        "require_io_docstrings",
        "require_orchestrator_step_comments",
        "require_orchestrator_logging",
    }
)
_STR_LIST_KEYS: frozenset[str] = frozenset(
    {
        "select",
        "ignore_rules",
        "vague_module_names",
        "suspicious_class_suffixes",
        "io_call_patterns",
        "wrapper_chain_exempt_decorators",
        "wrapper_chain_exempt_name_patterns",
    }
)


def find_config(start: Path) -> Path | None:
    """
    Inputs:
        A directory (or file) to begin searching from.

    Outputs:
        The nearest ``pyproject.toml`` found by walking upward, or ``None``.

    Side effects:
        Reads directory metadata from disk.

    Failure behavior:
        Never raises; returns ``None`` when no file is found.
    """
    current = start if start.is_dir() else start.parent
    current = current.resolve()
    for directory in (current, *current.parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def load_config(
    config_path: Path | None,
    *,
    start: Path | None = None,
) -> ArchbraceConfig:
    """
    Inputs:
        An explicit config path (or ``None`` to search upward) and the directory
        to search from.

    Outputs:
        A validated ``ArchbraceConfig``.

    Side effects:
        Reads a ``pyproject.toml`` file from disk.

    Failure behavior:
        Raises ``ConfigError`` when the explicit path is missing, the file is not
        valid TOML, an unknown key is present, or a value has the wrong type.
    """
    start = (start or Path.cwd()).resolve()

    if config_path is not None:
        resolved = config_path.resolve()
        if not resolved.is_file():
            raise ConfigError(f"Configuration file not found: {config_path}")
    else:
        found = find_config(start)
        if found is None:
            # No configuration is a valid state: use defaults rooted at ``start``.
            return ArchbraceConfig(config_path=None, root=start)
        resolved = found

    try:
        raw = tomllib.loads(resolved.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigError(f"Could not read configuration {resolved}: {exc}") from exc

    table = raw.get("tool", {}).get("archbrace", {})
    if not isinstance(table, dict):
        raise ConfigError("[tool.archbrace] must be a table.")

    return _build_config(table, config_path=resolved, root=resolved.parent)


def _build_config(
    table: dict[str, Any],
    *,
    config_path: Path,
    root: Path,
) -> ArchbraceConfig:
    values: dict[str, Any] = {"config_path": config_path, "root": root}

    for key, value in table.items():
        if key in _KNOWN_TABLES or key in _RESOLVED_EXCLUDE_KEYS:
            continue
        values[key] = _coerce_value(key, value)

    values["exclude"] = _resolve_exclude(table)
    values["severity"] = _parse_severity(table.get("severity", {}))
    values["module_contract_sections"] = _parse_sections(
        "module_contract", table.get("module_contract", {})
    )
    values["io_contract_sections"] = _parse_sections(
        "io_contract", table.get("io_contract", {})
    )
    values["layers"] = _parse_layers(table.get("layers", {}))

    return ArchbraceConfig(**values)


def _as_int(key: str, value: Any) -> int:
    # ``bool`` is a subclass of ``int``; reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"Configuration key {key!r} must be an integer.")
    return value


def _as_float(key: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"Configuration key {key!r} must be a number.")
    return float(value)


def _as_bool(key: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"Configuration key {key!r} must be a boolean.")
    return value


def _as_str(key: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"Configuration key {key!r} must be a string.")
    return value


def _as_choice(key: str, value: Any, choices: frozenset[str]) -> str:
    text = _as_str(key, value)
    if text not in choices:
        allowed = ", ".join(sorted(choices))
        raise ConfigError(f"Configuration key {key!r} must be one of: {allowed}.")
    return text


def _as_str_tuple(key: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"Configuration key {key!r} must be a list of strings.")
    return tuple(value)


def _resolve_exclude(table: dict[str, Any]) -> tuple[str, ...]:
    if "exclude" in table:
        base = _as_str_tuple("exclude", table["exclude"])
    else:
        base = DEFAULT_EXCLUDE

    if "extend_exclude" in table:
        return base + _as_str_tuple("extend_exclude", table["extend_exclude"])
    return base


# Scalar/list keys grouped by the validator that coerces them.
_SCALAR_VALIDATORS: tuple[tuple[frozenset[str], Callable[[str, Any], Any]], ...] = (
    (_INT_KEYS, _as_int),
    (_FLOAT_KEYS, _as_float),
    (_BOOL_KEYS, _as_bool),
    (_STR_LIST_KEYS, _as_str_tuple),
)


def _coerce_value(key: str, value: Any) -> Any:
    for keyset, validator in _SCALAR_VALIDATORS:
        if key in keyset:
            return validator(key, value)
    if key == "target_python":
        return _as_str(key, value)
    if key == "format":
        return _as_choice(key, value, _VALID_FORMATS)
    if key == "fail_on":
        return _as_choice(key, value, _VALID_SEVERITIES)
    raise ConfigError(f"Unknown configuration key: [tool.archbrace] {key!r}")


def _parse_severity(value: Any) -> dict[str, Severity]:
    if not isinstance(value, dict):
        raise ConfigError("[tool.archbrace.severity] must be a table.")
    result: dict[str, Severity] = {}
    for code, level in value.items():
        if not isinstance(level, str) or level not in _VALID_SEVERITIES:
            raise ConfigError(
                f"[tool.archbrace.severity] {code} must be 'error' or 'warning'."
            )
        result[code] = level  # type: ignore[assignment]
    return result


def _parse_sections(table_name: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict):
        raise ConfigError(f"[tool.archbrace.{table_name}] must be a table.")
    if not value:
        return ()
    sections = value.get("required_sections", [])
    if not isinstance(sections, list) or not all(
        isinstance(item, str) for item in sections
    ):
        raise ConfigError(
            f"[tool.archbrace.{table_name}].required_sections must be a list of strings."
        )
    return tuple(sections)


def _parse_layers(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError("[tool.archbrace.layers] must be a table.")
    return dict(value)
