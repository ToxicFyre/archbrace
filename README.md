# Archbrace

An opinionated, deterministic architectural linter for Python. Archbrace complements
Ruff, MyPy, Pytest, Bandit, and Radon by enforcing simplicity, maintainability, and
clear project structure.

Archbrace answers project-structure questions such as:

- Is this file or function carrying too many responsibilities?
- Are modules named after clear responsibilities?
- Are side effects visible?
- Is exception handling silent?

See [`Archbrace_Project_Spec_Final.md`](Archbrace_Project_Spec_Final.md) for the full
specification.

## Status

This is the first implementation increment (a "walking skeleton"). It ships an
end-to-end pipeline (`discover -> parse -> index -> rules -> report`) wired to a small
starter set of rules:

| Code | Rule |
|---|---|
| AR001 | Function too long |
| AR040 | Vague module name |
| AR070 | Wrapper chain too deep |
| AR101 | `print()` used instead of logger |
| AR102 | Silent broad exception handler |

## Installation (development)

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Usage

```bash
archbrace check src/
archbrace check . --format json
archbrace check src/ --select AR001,AR040
archbrace check src/ --ignore AR101
archbrace --version
```

### Exit codes

| Code | Meaning |
|---:|---|
| `0` | No diagnostics at or above the configured failure severity |
| `1` | One or more diagnostics at or above the configured failure severity |
| `2` | Configuration, parsing, or execution error |

## Configuration

Configuration lives in `pyproject.toml` under `[tool.archbrace]`. See the specification
for the full set of keys. The keys used by this increment include:

Archbrace applies the same built-in path exclusions as
[Ruff](https://docs.astral.sh/ruff/configuration/) (for example `.venv`, `.git`,
`node_modules`, `build`, and `dist`) without requiring you to list them. Use
`extend_exclude` to add project-specific patterns on top of those defaults; setting
`exclude` replaces the defaults entirely.

```toml
[tool.archbrace]
format = "text"
fail_on = "error"
select = ["AR"]
ignore_rules = []
extend_exclude = ["tests/**"]
max_function_lines = 40
max_wrapper_chain_depth = 2
vague_module_names = ["utils", "helpers", "common", "misc", "shared"]
wrapper_chain_exempt_decorators = ["click.command", "app.route", "router.get"]
wrapper_chain_exempt_name_patterns = ["main", "__enter__", "__exit__"]

[tool.archbrace.severity]
AR021 = "warning"
```

## Development

Run the full local validation workflow from the repository root:

```bash
ruff check .
mypy archbrace
pytest
python3 -m archbrace.cli check .
archbrace check .
```
