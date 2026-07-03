# Rules

Archbrace ships a deterministic rule set identified by `AR` codes. Rules are selected
with `[tool.archbrace].select` and can be overridden with `[tool.archbrace.severity]`.

## Implemented rules

| Code | Name | Default severity | Config key |
|------|------|------------------|------------|
| AR001 | `function-too-long` | error | `max_function_lines` |
| AR002 | `file-too-long` | error | `max_file_lines` |
| AR003 | `nesting-too-deep` | error | `max_nesting_depth` |
| AR020 | `cyclomatic-complexity` | error | `max_cyclomatic_complexity` |
| AR040 | `vague-module-name` | error | `vague_module_names` |
| AR060 | `module-contract` | error | `require_module_contract` |
| AR070 | `wrapper-chain-too-deep` | warning | `max_wrapper_chain_depth` |
| AR101 | `print-used` | error | — |
| AR102 | `silent-broad-except` | error | — |

Select all rules with a prefix:

```toml
[tool.archbrace]
select = ["AR"]
```

Select a subset:

```bash
archbrace check src/ --select AR070,AR001
archbrace check src/ --ignore AR070
```

## AR070 — Wrapper chain too deep

**Purpose:** Flag local call chains where multiple consecutive functions are
high-confidence pass-through wrappers, adding comprehension debt without expressing a
real boundary.

**Default severity:** `warning` (does not fail CI when `fail_on = "error"` unless you
override severity).

**What counts as a wrapper chain**

Archbrace builds a conservative local call graph and follows delegated callees while
each hop is a high-confidence wrapper. A chain like:

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

has three wrapper edges before real behavior. With `max_wrapper_chain_depth = 2`, the
diagnostic is emitted at `run_job`.

**What is not flagged**

- Single wrappers or chains within the configured limit
- Functions with branching, loops, try/except policy, or multiple meaningful local calls
- Orchestration that loads, validates, transforms, and persists data
- Unresolved or dynamic calls (`getattr`, registries, callbacks)
- Exempt boundaries (see [configuration](configuration.md#wrapper-chain-exemptions))

**Diagnostic format**

```text
Wrapper chain is too deep: run_job -> execute_job -> process_job -> build_report.
Depth is 3; limit is 2. This may be intentional. Consider collapsing one or more
pass-through layers if they do not express a real boundary.
```

Metadata includes `actual`, `limit`, and the qualified `chain`.

**Related configuration:** `max_wrapper_chain_depth`, `wrapper_chain_exempt_decorators`,
`wrapper_chain_exempt_name_patterns` — see [configuration.md](configuration.md).
