"""Dogfood integration test: Archbrace must report no diagnostics on itself.

Archbrace's own package is written to satisfy every implemented rule, so running
the full rule set over ``archbrace/`` is a meaningful, non-trivial invariant: it
fails the moment production code (or a rule) regresses the project's standards.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from archbrace.config import load_config
from archbrace.models import Diagnostic
from archbrace.project import build_project_index
from archbrace.rules import get_all_rules, run_rules

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "archbrace"


def _describe(diagnostics: Iterable[Diagnostic]) -> str:
    return "\n".join(
        f"{d.code} {d.path}:{d.location.line} {d.message}" for d in diagnostics
    )


def test_archbrace_source_is_self_clean() -> None:
    config = load_config(REPO_ROOT / "pyproject.toml")
    project = build_project_index([PACKAGE], config)
    diagnostics = run_rules(get_all_rules(), project, config)
    assert diagnostics == [], _describe(diagnostics)
