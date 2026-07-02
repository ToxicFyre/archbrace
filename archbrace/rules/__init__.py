"""
Purpose:
    Expose the rule interface, the execution engine, and the registry of all
    rules shipped in this Archbrace release.

Inputs:
    None at import time; ``get_all_rules`` instantiates the concrete rules on
    demand.

Outputs:
    The ``Rule`` base class, engine helpers, and ``get_all_rules``.

Side effects:
    None.

Failure behavior:
    ``get_all_rules`` raises ``ImportError`` only if a rule module is missing.
"""

from __future__ import annotations

from .base import Rule
from .engine import apply_severity, run_rules, select_rules

__all__ = [
    "Rule",
    "apply_severity",
    "run_rules",
    "select_rules",
    "get_all_rules",
]


def get_all_rules() -> list[Rule]:
    """
    Inputs:
        None.

    Outputs:
        A fresh list of every rule instance shipped in this release, ordered by
        rule code.

    Side effects:
        None.

    Failure behavior:
        Never raises for the bundled rule set.
    """
    from .logging_rules import PrintUsedRule, SilentBroadExceptRule
    from .simplicity import VagueModuleNameRule
    from .size import FunctionTooLongRule

    rules: list[Rule] = [
        FunctionTooLongRule(),
        VagueModuleNameRule(),
        PrintUsedRule(),
        SilentBroadExceptRule(),
    ]
    return sorted(rules, key=lambda rule: rule.code)
