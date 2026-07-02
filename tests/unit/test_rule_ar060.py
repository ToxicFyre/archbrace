"""Tests for AR060 Module Contract Required (spec Section 7.4)."""

from __future__ import annotations

from collections.abc import Sequence

from archbrace.rules.documentation import ModuleContractRule

DEFAULT_SECTIONS = (
    "Purpose",
    "Why is this in this project",
    "Inputs",
    "Outputs",
    "Side effects",
    "Failure behavior",
)


def _module_with_sections(sections: Sequence[str], *, code: str = "value = 1\n") -> str:
    lines = ['"""']
    for section in sections:
        lines.append(f"{section}:")
        lines.append("    Detail.")
        lines.append("")
    lines.append('"""')
    docstring = "\n".join(lines)
    return f"{docstring}\n{code}"


def test_compliant_module_passes(index_from_source, base_config) -> None:
    source = _module_with_sections(DEFAULT_SECTIONS)
    project = index_from_source({"good.py": source})
    assert ModuleContractRule().check(project, base_config()) == []


def test_flags_single_missing_section(index_from_source, base_config) -> None:
    source = _module_with_sections(
        [s for s in DEFAULT_SECTIONS if s != "Side effects"]
    )
    project = index_from_source({"partial.py": source})
    diagnostics = ModuleContractRule().check(project, base_config())
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR060"
    assert diagnostic.name == "module-contract-required"
    assert diagnostic.severity == "error"
    assert diagnostic.message == "Missing module contract section: Side effects"
    assert diagnostic.location.line == 1
    assert diagnostic.location.column == 1
    assert diagnostic.metadata["section"] == "Side effects"
    assert diagnostic.metadata["symbol"] == "partial"


def test_missing_docstring_flags_all_sections(index_from_source, base_config) -> None:
    project = index_from_source({"nodoc.py": "value = 1\n"})
    diagnostics = ModuleContractRule().check(project, base_config())
    assert [d.metadata["section"] for d in diagnostics] == list(DEFAULT_SECTIONS)


def test_headings_match_case_insensitively(index_from_source, base_config) -> None:
    source = (
        '"""\n'
        "PURPOSE:\n"
        "    Detail.\n"
        "why is this in this project:\n"
        "    Detail.\n"
        "inputs :\n"
        "    Detail.\n"
        "  Outputs:\n"
        "    Detail.\n"
        "SIDE EFFECTS:\n"
        "    Detail.\n"
        "failure behavior:\n"
        "    Detail.\n"
        '"""\n'
        "value = 1\n"
    )
    project = index_from_source({"cased.py": source})
    assert ModuleContractRule().check(project, base_config()) == []


def test_sections_are_configurable(index_from_source, base_config) -> None:
    source = _module_with_sections(["Purpose", "Contract"])
    project = index_from_source({"custom.py": source})
    passing = base_config(module_contract_sections=("Purpose", "Contract"))
    assert ModuleContractRule().check(project, passing) == []

    failing = base_config(module_contract_sections=("Rationale",))
    diagnostics = ModuleContractRule().check(project, failing)
    assert [d.metadata["section"] for d in diagnostics] == ["Rationale"]


def test_toggle_disables_rule(index_from_source, base_config) -> None:
    project = index_from_source({"nodoc.py": "value = 1\n"})
    config = base_config(require_module_contract=False)
    assert ModuleContractRule().check(project, config) == []


def test_empty_module_is_exempt(index_from_source, base_config) -> None:
    project = index_from_source({"__init__.py": ""})
    assert ModuleContractRule().check(project, base_config()) == []


def test_docstring_only_module_is_exempt(index_from_source, base_config) -> None:
    source = '"""Just a marker docstring."""\n'
    project = index_from_source({"marker.py": source})
    assert ModuleContractRule().check(project, base_config()) == []
