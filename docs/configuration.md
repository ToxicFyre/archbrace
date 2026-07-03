# Configuration

Archbrace reads settings from `[tool.archbrace]` in the nearest `pyproject.toml` (searched
upward from the path you pass to `archbrace check`).

CLI flags override file values where supported:

```bash
archbrace check src/ --select AR070,AR001
archbrace check src/ --ignore AR070
```

## Path exclusions

Archbrace applies the same built-in path exclusions as
[Ruff](https://docs.astral.sh/ruff/configuration/) (for example `.venv`, `.git`,
`node_modules`, `build`, and `dist`).

```toml
[tool.archbrace]
# Replace Ruff-like defaults entirely
exclude = ["vendor/**"]

# Append project-specific patterns (recommended)
extend_exclude = ["tests/**"]
```

## Rule selection and severity

```toml
[tool.archbrace]
select = ["AR"]
ignore_rules = []

[tool.archbrace.severity]
AR070 = "warning"
```

- `select` — rule codes or prefixes (`"AR"`, `"AR07"`, `"AR070"`)
- `ignore_rules` — explicit suppressions; always wins over `select`
- `severity` — per-rule override (`error` or `warning`)

## Size and complexity thresholds

| Key | Default | Used by |
|-----|---------|---------|
| `max_function_lines` | `40` | AR001 |
| `max_file_lines` | `300` | AR002 |
| `max_nesting_depth` | `3` | AR003 |
| `max_cyclomatic_complexity` | `8` | AR020 |
| `max_wrapper_chain_depth` | `2` | AR070 |
| `max_fli` | `8` | AR073 |
| `max_fli_depth` | `4` | AR073 |
| `fli_ignore_tests` | `true` | AR073 |

## Flow locality index (AR073)

```toml
[tool.archbrace]
max_fli = 8
max_fli_depth = 4
fli_ignore_tests = true
```

### `max_fli`

Maximum Flow Locality Index before a public entry point is flagged. FLI combines
module span, generic layer crossings, wrapper chains, remote-domain hops, and
unresolved-edge penalties.

### `max_fli_depth`

Maximum call-graph depth to traverse from each entry point when computing FLI. This
limits how far Archbrace follows conservative local callees.

### `fli_ignore_tests`

When `true`, test modules (`test_*.py`, `*_test.py`, `conftest.py`) are not analyzed
as FLI entry points.

## Wrapper chain (AR070)

```toml
[tool.archbrace]
max_wrapper_chain_depth = 2
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
```

### `max_wrapper_chain_depth`

Maximum number of consecutive high-confidence wrapper edges before real behavior.
Chains at the limit pass; chains **above** the limit are flagged at the first function
in the chain.

Example with limit `2`:

- `run -> execute -> work` — passes (2 edges)
- `run -> execute -> process -> work` — flags `run` (3 edges)

### Wrapper chain exemptions

Archbrace never flags wrapper chains starting from:

- Test files (`test_*.py`, `*_test.py`, `conftest.py`)
- Dunder methods, `@property` getters/setters, `@staticmethod`, `@classmethod`
- Functions whose names match `wrapper_chain_exempt_name_patterns`
- Functions decorated with names listed in `wrapper_chain_exempt_decorators`

Decorator matching is suffix-aware: `router.get` matches `@router.get(...)`.

## Module naming and contracts

```toml
[tool.archbrace]
vague_module_names = ["utils", "helpers", "common", "misc", "shared"]
require_module_contract = true
```

See [rules.md](rules.md) for which rules consume these keys.

## Output and failure behavior

```toml
[tool.archbrace]
format = "text"   # or "json"
fail_on = "error" # or "warning"
```

| Exit code | Meaning |
|----------:|---------|
| `0` | No diagnostics at or above `fail_on` |
| `1` | One or more diagnostics at or above `fail_on` |
| `2` | Configuration, parsing, or execution error |
