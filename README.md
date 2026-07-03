# Archbrace

An opinionated, deterministic architectural linter for Python. Archbrace complements
Ruff, MyPy, Pytest, Bandit, and Radon by enforcing simplicity, maintainability, and
clear project structure.

Archbrace answers project-structure questions such as:

- Is this file or function carrying too many responsibilities?
- Are modules named after clear responsibilities?
- Are side effects visible?
- Is exception handling silent?
- Are there long chains of pass-through wrapper functions?

## Status

Archbrace ships an end-to-end pipeline (`discover -> parse -> index -> rules -> report`)
and the following rules:

| Code | Rule | Default severity |
|------|------|------------------|
| AR001 | Function too long | error |
| AR002 | File too long | error |
| AR003 | Nesting too deep | error |
| AR020 | Cyclomatic complexity | error |
| AR040 | Vague module name | error |
| AR060 | Module contract | error |
| AR070 | Wrapper chain too deep | warning |
| AR101 | `print()` used instead of logger | error |
| AR102 | Silent broad exception handler | error |

Rule details: [`docs/rules.md`](docs/rules.md). Configuration reference:
[`docs/configuration.md`](docs/configuration.md).

## Installation (development)

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Usage

```bash
archbrace check src/
archbrace check . --format json
archbrace check src/ --select AR001,AR070
archbrace check src/ --ignore AR070
archbrace --version
```

### AR070 example

With the default `max_wrapper_chain_depth = 2`, a chain of three wrapper hops is
reported at the entry function:

```python
def run_job(config):
    return execute_job(config)

def execute_job(config):
    return process_job(config)

def process_job(config):
    return build_report(config)

def build_report(config):
    return config
```

```text
warning[AR070] src/jobs.py:1: Wrapper chain is too deep: run_job -> execute_job ->
process_job -> build_report. Depth is 3; limit is 2. This may be intentional. Consider
collapsing one or more pass-through layers if they do not express a real boundary.
```

See [`docs/rules.md#ar070--wrapper-chain-too-deep`](docs/rules.md#ar070--wrapper-chain-too-deep)
for detection behavior, exemptions, and non-goals.

### Exit codes

| Code | Meaning |
|---:|---|
| `0` | No diagnostics at or above the configured failure severity |
| `1` | One or more diagnostics at or above the configured failure severity |
| `2` | Configuration, parsing, or execution error |

## Configuration

Configuration lives in `pyproject.toml` under `[tool.archbrace]`.

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
wrapper_chain_exempt_decorators = [
  "click.command",
  "app.route",
  "router.get",
  "router.post",
  "celery.task",
]
wrapper_chain_exempt_name_patterns = [
  "main",
  "__enter__",
  "__exit__",
  "__aenter__",
  "__aexit__",
]

[tool.archbrace.severity]
AR070 = "warning"
```

Full key reference: [`docs/configuration.md`](docs/configuration.md).

## Development

Run the full local validation workflow from the repository root:

```bash
ruff check .
mypy archbrace
pytest
archbrace check .
```

If the `archbrace` entry point is not on your `PATH` after an editable install, use
`python3 -m archbrace.cli check .` instead.
