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
| AR073 | `flow-locality-index` | warning | `max_fli` |
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

## AR073 — Flow locality index

**Purpose:** Flag public entry points whose behavior is spread across too many files,
generic architectural layers, and pass-through wrappers.

**Default severity:** `warning`.

**What is scored**

For each public entry point, Archbrace walks a conservative local call graph (depth
limited by `max_fli_depth`) and computes:

```text
FLI = module_span + layer_crossing + wrapper_chain + remote_domain + unresolved_edge
```

- **Module span** — distinct local modules reached (many files alone is not bad)
- **Layer crossing** — paths through generic folders such as `handlers/`, `services/`,
  `repositories/`, `utils/`
- **Wrapper chain** — longest chain of thin pass-through functions
- **Remote domain** — modules outside the entry point's domain, especially
  `shared/`, `common/`, or `utils/`
- **Unresolved edge penalty** — dynamic calls that were not guessed (`callback()`,
  `getattr`, registries)

**What should pass**

Multiple files in the same business domain with clear roles (for example
`invoice/create.py`, `invoice/models.py`, `invoice/calculations.py`) stay below the
threshold when they are not separated by generic layers and long wrapper chains.

**Diagnostic format (text)**

```text
invoice/api.py:4:0 AR073 create_invoice: flow locality 13/8 (wrapper chain, depth 4)
```

The terminal message is a single scannable line. Detailed context (wrapper path, reach,
measurements, suggestions) lives in JSON metadata — see
[AR073 metadata spec](specs/ar073-metadata.md).

**Diagnostic format (JSON metadata, abbreviated)**

```json
{
  "actual": 13,
  "limit": 8,
  "symbol": "create_invoice",
  "dominant": { "component": "wrapper_chain", "score": 7 },
  "measurements": { "module_count": 5, "wrapper_depth": 4 },
  "wrapper_path": { "labels": ["invoice/api.py:create_invoice", "..."], "depth": 4 },
  "reach": { "modules": ["invoice.api", "invoice.handlers", "..."], "generic_layers": ["handlers", "services"] },
  "suggestions": [{ "component": "wrapper_chain", "priority": 1, "text": "Collapse 4 pass-through hops..." }]
}
```

Legacy keys `path`, `scores`, `reasons`, and `unresolved_edges` remain for compatibility.
Full field reference: [specs/ar073-metadata.md](specs/ar073-metadata.md).

**Related configuration:** `max_fli`, `max_fli_depth`, `fli_ignore_tests` — see
[configuration.md](configuration.md).
