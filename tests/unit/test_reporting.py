"""Tests for text and JSON reporting (spec Section 8)."""

from __future__ import annotations

import json
from pathlib import Path

from archbrace.models import Diagnostic, SourceRange
from archbrace.reporting.json import render_json
from archbrace.reporting.text import render_text

BASE = Path("/proj")


def _diag(
    path: str,
    line: int,
    column: int,
    code: str,
    name: str,
    message: str,
    severity: str = "error",
    end_line: int | None = None,
    end_column: int | None = None,
    metadata: dict | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        name=name,
        path=BASE / path,
        location=SourceRange(
            line=line, column=column, end_line=end_line, end_column=end_column
        ),
        message=message,
        severity=severity,  # type: ignore[arg-type]
        metadata=metadata or {},
    )


def _spec_example() -> list[Diagnostic]:
    return [
        _diag("src/core/utils.py", 1, 1, "AR040", "vague-module-name",
              "Module `utils.py` has a vague name."),
        _diag("src/core/process.py", 88, 5, "AR003", "nesting-too-deep",
              "Function `process` has nesting depth 5. Limit is 3."),
        _diag("src/core/report.py", 1, 1, "AR060", "module-contract-required",
              "Missing module contract section: Side effects"),
    ]


def test_text_output_matches_spec_golden() -> None:
    output = render_text(_spec_example(), base=BASE)
    expected = (
        "src/core/process.py:88:5 AR003 Function `process` has nesting depth 5. Limit is 3.\n"
        "src/core/report.py:1:1 AR060 Missing module contract section: Side effects\n"
        "src/core/utils.py:1:1 AR040 Module `utils.py` has a vague name.\n"
        "\n"
        "Found 3 diagnostics: 3 errors, 0 warnings.\n"
    )
    assert output == expected


def test_text_empty_output() -> None:
    assert render_text([], base=BASE) == "Found 0 diagnostics: 0 errors, 0 warnings.\n"


def test_text_pluralization_and_warning_count() -> None:
    diagnostics = [
        _diag("a.py", 1, 1, "AR040", "vague", "one", severity="warning"),
    ]
    output = render_text(diagnostics, base=BASE)
    assert output.endswith("Found 1 diagnostic: 0 errors, 1 warning.\n")


def test_text_is_sorted_by_path_line_column_code_message() -> None:
    diagnostics = [
        _diag("z.py", 1, 1, "AR001", "n", "z"),
        _diag("a.py", 2, 1, "AR001", "n", "a"),
        _diag("a.py", 1, 5, "AR001", "n", "a"),
        _diag("a.py", 1, 1, "AR101", "n", "b"),
        _diag("a.py", 1, 1, "AR001", "n", "b"),
        _diag("a.py", 1, 1, "AR001", "n", "a"),
    ]
    lines = render_text(diagnostics, base=BASE).splitlines()
    body = [line for line in lines if line.startswith(("a.py", "z.py"))]
    assert body == [
        "a.py:1:1 AR001 a",
        "a.py:1:1 AR001 b",
        "a.py:1:1 AR101 b",
        "a.py:1:5 AR001 a",
        "a.py:2:1 AR001 a",
        "z.py:1:1 AR001 z",
    ]


def test_json_schema_and_fields() -> None:
    diagnostics = [
        _diag(
            "src/core/process.py", 88, 5, "AR003", "nesting-too-deep",
            "Function `process` has nesting depth 5. Limit is 3.",
            end_line=121, end_column=1, metadata={"actual": 5, "limit": 3},
        ),
    ]
    data = json.loads(render_json(diagnostics, base=BASE, files_scanned=24))
    assert data["version"] == "1"
    assert data["summary"] == {"files_scanned": 24, "errors": 1, "warnings": 0}
    entry = data["diagnostics"][0]
    assert entry["code"] == "AR003"
    assert entry["name"] == "nesting-too-deep"
    assert entry["path"] == "src/core/process.py"
    assert entry["line"] == 88
    assert entry["column"] == 5
    assert entry["end_line"] == 121
    assert entry["end_column"] == 1
    assert entry["severity"] == "error"
    assert entry["metadata"] == {"actual": 5, "limit": 3}


def test_json_diagnostics_are_sorted() -> None:
    diagnostics = [
        _diag("b.py", 1, 1, "AR001", "n", "m"),
        _diag("a.py", 1, 1, "AR001", "n", "m"),
    ]
    data = json.loads(render_json(diagnostics, base=BASE, files_scanned=2))
    assert [d["path"] for d in data["diagnostics"]] == ["a.py", "b.py"]
