"""
Purpose:
    Select which rules run, execute them against the project index, and apply
    configured severity overrides (spec Sections 5.2, 9.4, 11).

Why is this in this project:
    Centralizes rule selection, execution, and severity resolution so individual
    rules stay small and free of orchestration concerns.

Inputs:
    A collection of rules, the project index, and the active configuration.

Outputs:
    An aggregated list of diagnostics with severities resolved.

Side effects:
    None.

Failure behavior:
    Wraps any exception raised by a rule in ``RuleExecutionError`` so failures
    are surfaced rather than silently swallowed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace

from ..config import ArchbraceConfig
from ..errors import RuleExecutionError
from ..models import Diagnostic, ProjectIndex, Severity
from .base import Rule


def _matches(code: str, patterns: Iterable[str]) -> bool:
    return any(code.startswith(pattern) for pattern in patterns)


def select_rules(
    rules: Iterable[Rule],
    *,
    select: Sequence[str],
    ignore: Sequence[str],
) -> list[Rule]:
    """
    Inputs:
        Candidate rules, the ``select`` patterns, and the ``ignore`` patterns
        (each a full code or a prefix).

    Outputs:
        The rules whose code matches a select pattern and no ignore pattern. An
        explicit ignore always wins over a selecting prefix.

    Side effects:
        None.

    Failure behavior:
        Never raises.
    """
    return [
        rule
        for rule in rules
        if _matches(rule.code, select) and not _matches(rule.code, ignore)
    ]


def apply_severity(
    diagnostics: Iterable[Diagnostic],
    overrides: Mapping[str, Severity],
) -> list[Diagnostic]:
    """
    Inputs:
        Diagnostics and a mapping of rule code to overriding severity.

    Outputs:
        New diagnostics with severities replaced where an override exists.

    Side effects:
        None.

    Failure behavior:
        Never raises.
    """
    resolved: list[Diagnostic] = []
    for diagnostic in diagnostics:
        override = overrides.get(diagnostic.code)
        if override is not None and override != diagnostic.severity:
            resolved.append(replace(diagnostic, severity=override))
        else:
            resolved.append(diagnostic)
    return resolved


def run_rules(
    rules: Iterable[Rule],
    project: ProjectIndex,
    config: ArchbraceConfig,
) -> list[Diagnostic]:
    """
    Inputs:
        Candidate rules, the project index, and the active configuration.

    Outputs:
        Aggregated diagnostics from selected rules with severity overrides
        applied. Ordering is left to the reporting layer.

    Side effects:
        None.

    Failure behavior:
        Raises ``RuleExecutionError`` if any rule raises during ``check``.
    """
    selected = select_rules(
        rules, select=config.select, ignore=config.ignore_rules
    )
    diagnostics: list[Diagnostic] = []
    for rule in selected:
        try:
            diagnostics.extend(rule.check(project, config))
        except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
            raise RuleExecutionError(
                f"Rule {rule.code} failed during execution: {exc}"
            ) from exc
    return apply_severity(diagnostics, config.severity)
