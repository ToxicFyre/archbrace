"""Tests for AR102 Silent Broad Exception Handler (spec Section 7.6)."""

from __future__ import annotations

from archbrace.rules.logging_rules import SilentBroadExceptRule


def test_flags_silent_broad_handler(index_from, base_config) -> None:
    project = index_from("ar102_silent.py")
    diagnostics = SilentBroadExceptRule().check(project, base_config())
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR102"
    assert diagnostic.name == "silent-broad-except"
    assert diagnostic.severity == "error"


def test_ignores_logged_and_reraised_handler(index_from, base_config) -> None:
    project = index_from("ar102_handled.py")
    assert SilentBroadExceptRule().check(project, base_config()) == []


def test_flags_bare_except(index_from_source, base_config) -> None:
    source = "def run():\n    try:\n        risky()\n    except:\n        pass\n"
    project = index_from_source({"bare.py": source})
    diagnostics = SilentBroadExceptRule().check(project, base_config())
    assert len(diagnostics) == 1


def test_ignores_specific_exception(index_from_source, base_config) -> None:
    source = (
        "def run():\n"
        "    try:\n"
        "        risky()\n"
        "    except ValueError:\n"
        "        pass\n"
    )
    project = index_from_source({"specific.py": source})
    assert SilentBroadExceptRule().check(project, base_config()) == []


def test_returned_sentinel_is_allowed(index_from_source, base_config) -> None:
    source = (
        "def run():\n"
        "    try:\n"
        "        return risky()\n"
        "    except Exception:\n"
        "        return None\n"
    )
    project = index_from_source({"sentinel.py": source})
    assert SilentBroadExceptRule().check(project, base_config()) == []
