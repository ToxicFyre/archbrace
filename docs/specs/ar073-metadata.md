# Spec: AR073 Rich Metadata

**Status:** Implemented  
**Rule:** AR073 — `flow-locality-index`  
**Audience:** Archbrace implementers, IDE/CI integrators, AI agents  
**Related code:** `archbrace/rules/flow_locality.py`, `archbrace/analysis/flow_locality.py`,
`archbrace/reporting/json.py`

---

## 1. Summary

This spec defines how AR073 (Flow Locality Index) diagnostics expose **lean text
messages** and **rich, structured metadata** in JSON output. The goal is to make FLI
warnings actionable for humans, IDEs, CI systems, and AI agents without bloating
terminal output.

**Design pattern:** Same as Ruff — concise `message` for the terminal; machine-readable
detail in adjacent JSON fields; static rule documentation fetched on demand via `url`.

---

## 2. Problem statement

AR073 already emits metadata, but consumers struggle to interpret and fix violations
because:

1. **Detail is duplicated in prose** — path blocks, reason strings, and fix advice appear
   in `message` while similar data exists in `metadata`.
2. **`metadata.path` is ambiguous** — it shows the wrapper chain only, not the full
   traversal reach that drives `module_span` and `layer_crossing`.
3. **Score buckets are opaque** — `scores.wrapper_chain: 7` does not reveal that this
   corresponds to wrapper depth 4; `+5 module span` does not say five modules were
   reached.
4. **No actionable guidance in metadata** — fix suggestions live only in the text
   `message`.
5. **Traversal data is discarded** — `traverse_from()` produces reached modules and
   call edges, but only a wrapper path and aggregate counts survive into the finding.
6. **Entry-point classification is invisible** — users do not know why a function was
   treated as an entry point.

---

## 3. Goals and non-goals

### 3.1 Goals

- Keep terminal `message` to a single scannable line.
- Make JSON `metadata` the canonical source of actionable detail for tools.
- Expose raw measurements behind each score bucket.
- Distinguish wrapper path (pass-through chain) from full reach (traversal modules).
- Provide ordered, component-specific fix suggestions in metadata.
- Preserve backward compatibility with existing metadata keys.
- Keep output deterministic, bounded, and stable across runs.

### 3.2 Non-goals

- Auto-fix edits (AR073 is advisory; no `fix` object like Ruff autofix).
- Configurable suggestion templates per project.
- Embedding source code snippets in metadata.
- Changing FLI scoring formulas or thresholds (metadata only).

---

## 4. Design principles

### 4.1 Lean message, rich metadata

| Field | Role | Primary audience |
|-------|------|------------------|
| `message` | One-line, instance-specific summary | Humans in terminal |
| `metadata` | Full structured context | JSON consumers, IDEs, AI agents |
| `url` (top-level JSON) | Link to static rule documentation | LSP, browsers, agents |

Text and JSON share the same `message` string. Multiline path blocks and fix paragraphs
belong in `metadata`, not in `message`.

### 4.2 Derived once, not recomputed

Metadata fields are computed during analysis and stored on the finding. Consumers must
not re-derive dominant components, depths, or layer names from raw scores.

### 4.3 Additive compatibility

Existing keys (`actual`, `limit`, `symbol`, `path`, `scores`, `unresolved_edges`,
`reasons`) remain present. New fields use explicit namespaces. Deprecations are
documented; removals happen no earlier than JSON schema v2.

### 4.4 Deterministic and bounded

All list fields are sorted lexicographically and capped (default 20 items). When capped,
set `truncated: true` on the parent object.

### 4.5 Honest about analysis limits

Metadata must distinguish:

- **Wrapper path** — longest pass-through chain (what users often collapse).
- **Reach** — full module set from traversal (what drives span and layer scores).
- **Unresolved edges** — dynamic calls that may hide additional reach.

---

## 5. Current state

### 5.1 Analysis pipeline

`analyze_entry_point()` in `archbrace/analysis/flow_locality.py`:

```python
reached, _edges, unresolved = traverse_from(...)
scores = compute_scores(...)
path = build_display_path(...)      # wrapper chain only
reasons = format_reasons(...)
```

| Data | Produced by | Currently stored |
|------|-------------|------------------|
| `reached_modules: set[str]` | `traverse_from` | Discarded |
| `edges: list[CallEdge]` | `traverse_from` | Discarded |
| `unresolved: int` | `traverse_from` | `unresolved_edges` |
| `scores: FliScores` | `compute_scores` | `scores` |
| `path: tuple[str, ...]` | `build_display_path` | `path` |
| `reasons: tuple[str, ...]` | `format_reasons` | `reasons` |
| Entry-point signals | `is_entry_point` | Not recorded |
| Wrapper depth | `longest_wrapper_chain_depth` | Not exposed |
| Generic layers hit | `score_layer_crossing` internals | Not exposed |
| Remote domains hit | `score_remote_domain` internals | Not exposed |

### 5.2 Current metadata shape

```json
{
  "actual": 13,
  "limit": 8,
  "symbol": "create_invoice",
  "path": [
    "invoice/api.py:create_invoice",
    "invoice/handlers.py:CreateInvoiceHandler.handle",
    "invoice/services.py:InvoiceService.execute",
    "invoice/processors.py:InvoiceProcessor.process"
  ],
  "scores": {
    "module_span": 5,
    "layer_crossing": 6,
    "wrapper_chain": 7,
    "remote_domain": 0,
    "unresolved_edge": 0
  },
  "unresolved_edges": 0,
  "reasons": [
    "+5 module span",
    "+6 generic layer crossings",
    "+7 wrapper chain"
  ]
}
```

### 5.3 Current message (to be replaced)

```text
create_invoice has FLI 13, above max 8. Path:
invoice/api.py:create_invoice
 -> invoice/handlers.py:CreateInvoiceHandler.handle
 -> ...
Reasons: +5 module span; +6 generic layer crossings; +7 wrapper chain.
Consider moving the workflow narrative closer to the entry point or inlining
pass-through wrappers.
```

---

## 6. Proposed output shape

### 6.1 Top-level diagnostic JSON

Add `url` to all diagnostics in `archbrace/reporting/json.py`:

```json
{
  "code": "AR073",
  "name": "flow-locality-index",
  "path": "invoice/api.py",
  "line": 4,
  "column": 0,
  "end_line": null,
  "end_column": null,
  "message": "create_invoice: flow locality 13/8 (wrapper chain, depth 4)",
  "severity": "warning",
  "url": "https://github.com/<org>/archbrace/blob/main/docs/rules.md#ar073--flow-locality-index",
  "metadata": { }
}
```

`url` is rule-level (same for every AR073 diagnostic).

### 6.2 Proposed AR073 metadata (full)

```json
{
  "actual": 13,
  "limit": 8,
  "symbol": "create_invoice",
  "entry": "invoice.api.create_invoice",

  "scores": {
    "module_span": 5,
    "layer_crossing": 6,
    "wrapper_chain": 7,
    "remote_domain": 0,
    "unresolved_edge": 0
  },

  "dominant": {
    "component": "wrapper_chain",
    "score": 7,
    "ties": []
  },

  "measurements": {
    "module_count": 5,
    "wrapper_depth": 4,
    "generic_layer_count": 4,
    "remote_domain_count": 0,
    "unresolved_call_count": 0,
    "traversal_depth_limit": 4
  },

  "reach": {
    "modules": [
      "invoice.api",
      "invoice.handlers",
      "invoice.processors",
      "invoice.repositories",
      "invoice.services"
    ],
    "generic_layers": ["handlers", "processors", "repositories", "services"],
    "remote_domains": [],
    "visited_shared_utils": false,
    "truncated": false
  },

  "wrapper_path": {
    "labels": [
      "invoice/api.py:create_invoice",
      "invoice/handlers.py:CreateInvoiceHandler.handle",
      "invoice/services.py:InvoiceService.execute",
      "invoice/processors.py:InvoiceProcessor.process",
      "invoice/repositories.py:InvoiceRepository.save"
    ],
    "qualified_names": [
      "invoice.api.create_invoice",
      "invoice.handlers.CreateInvoiceHandler.handle",
      "invoice.services.InvoiceService.execute",
      "invoice.processors.InvoiceProcessor.process",
      "invoice.repositories.InvoiceRepository.save"
    ],
    "depth": 4
  },

  "entry_point": {
    "signals": ["named_entry"],
    "decorators": [],
    "is_public": true,
    "parent_class": null
  },

  "suggestions": [
    {
      "component": "wrapper_chain",
      "priority": 1,
      "text": "Collapse 4 pass-through hops in the wrapper path, or merge adjacent layers that do not express a real boundary."
    },
    {
      "component": "layer_crossing",
      "priority": 2,
      "text": "Reduce hops through generic folders: handlers, processors, repositories, services."
    },
    {
      "component": "general",
      "priority": 99,
      "text": "This may be intentional if layers express real boundaries. Consider raising max_fli only after reviewing reach."
    }
  ],

  "caveats": [
    "Wrapper path shows pass-through hops only; see reach.modules for full spread."
  ],

  "path": ["invoice/api.py:create_invoice", "..."],
  "reasons": ["+5 module span", "+6 generic layer crossings", "+7 wrapper chain"],
  "unresolved_edges": 0
}
```

---

## 7. Field reference

### 7.1 Retained keys (backward compatible)

| Key | Type | Description |
|-----|------|-------------|
| `actual` | `int` | Total FLI score (sum of `scores`) |
| `limit` | `int` | Configured `max_fli` threshold |
| `symbol` | `str` | Short function/method name at diagnostic location |
| `scores` | `object` | Component bucket scores (keys unchanged) |
| `unresolved_edges` | `int` | Count of unresolved local-looking calls during traversal |
| `path` | `list[str]` | **Deprecated alias** for `wrapper_path.labels` |
| `reasons` | `list[str]` | **Deprecated** human-readable reason strings |

### 7.2 New keys

#### `entry` — `str`

Fully qualified entry point name (e.g. `invoice.api.create_invoice`). Stable identifier
for deduplication and cross-tool references. Distinct from `symbol` (bare name at
diagnostic location).

#### `dominant` — `object`

Identifies which score component contributed most to the violation.

```json
{
  "component": "wrapper_chain",
  "score": 7,
  "ties": ["layer_crossing"]
}
```

**Selection algorithm:**

1. Consider only components with `score > 0`.
2. Pick the highest score.
3. On tie, prefer in order: `wrapper_chain`, `layer_crossing`, `module_span`,
   `remote_domain`, `unresolved_edge`.
4. List other tied components in `ties`.

Used to drive the one-line `message` suffix and suggestion ordering.

Valid `component` values: `module_span`, `layer_crossing`, `wrapper_chain`,
`remote_domain`, `unresolved_edge`.

#### `measurements` — `object`

Raw measurements behind bucket scores.

| Field | Type | Source function | Bucket mapping |
|-------|------|-----------------|----------------|
| `module_count` | `int` | `len(reached_modules)` | 1→0, 2→1, 3→2, 4→3, 5+→5 |
| `wrapper_depth` | `int` | `longest_wrapper_chain_depth()` | 0–1→0, 2→2, 3→4, 4+→7 |
| `generic_layer_count` | `int` | distinct generic layers in reach | count; +2 if ≥4 layers |
| `remote_domain_count` | `int` | foreign-domain modules in reach | +1 per module; +2 if shared/utils visited |
| `unresolved_call_count` | `int` | same as `unresolved_edges` | 0→0, 1–2→1, 3+→2 |
| `traversal_depth_limit` | `int` | `config.max_fli_depth` | context for depth truncation |

#### `reach` — `object`

Full traversal reach — drives `module_span`, `layer_crossing`, and `remote_domain`.

| Field | Type | Description |
|-------|------|-------------|
| `modules` | `list[str]` | Sorted module names reached within depth limit |
| `generic_layers` | `list[str]` | Sorted generic layer folder names in reached modules |
| `remote_domains` | `list[str]` | Business domains (per `module_domain()`) outside entry domain |
| `visited_shared_utils` | `bool` | Whether reach includes `shared`/`common`/`utils` tokens |
| `truncated` | `bool` | `true` if any list was capped at the limit |

**Caps:** `modules` and `remote_domains` capped at 20 entries. Set `truncated: true`
when the source set exceeds the cap.

#### `wrapper_path` — `object`

Longest wrapper chain from the entry point.

| Field | Type | Description |
|-------|------|-------------|
| `labels` | `list[str]` | `file.py:func` or `file.py:Class.method` display labels |
| `qualified_names` | `list[str]` | Qualified callable name per hop |
| `depth` | `int` | Wrapper hops = `len(labels) - 1` |

Bounded by `max_fli_depth + 1` (already enforced by analysis).

#### `entry_point` — `object`

Explains why this function was analyzed as an entry point.

| Field | Type | Description |
|-------|------|-------------|
| `signals` | `list[str]` | See signal table below |
| `decorators` | `list[str]` | Matching route/task decorators, if any |
| `is_public` | `bool` | From `FunctionInfo.is_public` |
| `parent_class` | `str \| null` | Qualified class name if method |

**Entry-point signals** (mirrors `archbrace/analysis/fli_entry.py`):

| Signal | Condition |
|--------|-----------|
| `route_decorator` | Has decorator in `ROUTE_DECORATORS` |
| `exempt_name_pattern` | Name matches `wrapper_chain_exempt_name_patterns` |
| `named_entry` | Name in `ENTRY_POINT_NAMES` |
| `public_method` | Public method on a class |
| `public_api` | Public top-level function (fallback) |

#### `suggestions` — `list[object]`

Ordered, component-specific fix guidance.

```json
{
  "component": "wrapper_chain",
  "priority": 1,
  "text": "Collapse 4 pass-through hops in the wrapper path, or merge adjacent layers that do not express a real boundary."
}
```

**Generation rules:**

1. Emit one suggestion per component with `score > 0`, ordered by score descending
   (ties use dominant tie-break order).
2. Text is a deterministic template function of `measurements` and `reach`/`wrapper_path`.
3. Always append a low-priority general suggestion when any score is non-zero:

```json
{
  "component": "general",
  "priority": 99,
  "text": "This may be intentional if layers express real boundaries. Consider raising max_fli only after reviewing reach."
}
```

**Template catalog:**

| Component | Template |
|-----------|----------|
| `wrapper_chain` | `Collapse {wrapper_depth} pass-through hop(s) in the wrapper path, or merge adjacent layers that do not express a real boundary.` |
| `layer_crossing` | `Reduce hops through generic folders: {generic_layers joined}.` |
| `module_span` | `{module_count} modules are involved; consider a vertical slice in the same domain instead of horizontal layers.` |
| `remote_domain` | `Entry point reaches {remote_domain_count} other domain(s): {remote_domains joined}. Move shared logic closer or narrow entry scope.` |
| `unresolved_edge` | `{unresolved_call_count} dynamic/unresolved call(s) may hide additional reach; use explicit calls where possible.` |

#### `caveats` — `list[str]`

Human-readable disclaimers. Empty list when none apply.

| Condition | Text |
|-----------|------|
| `unresolved_edges > 0` | `FLI may be underestimated due to {n} unresolved local-looking call(s).` |
| Traversal stopped at depth limit | `Traversal stopped at depth {max_fli_depth}; actual reach may be larger.` |
| `module_count > wrapper_path.depth + 1` | `Wrapper path shows pass-through hops only; see reach.modules for full spread.` |

---

## 8. Lean message contract

Replace multiline `_finding_message()` with a single line derived from metadata:

```text
{symbol}: flow locality {actual}/{limit} ({dominant_summary})
```

**`dominant_summary` fragments:**

| Dominant component | Fragment |
|--------------------|----------|
| `wrapper_chain` | `wrapper chain, depth {wrapper_depth}` |
| `layer_crossing` | `{generic_layer_count} generic layers` |
| `module_span` | `{module_count} modules` |
| `remote_domain` | `{remote_domain_count} remote domains` |
| `unresolved_edge` | `unresolved calls` |
| Multiple tied | `{comp1} + {comp2}` (use short names) |

**Example:**

```text
invoice/api.py:4:0 AR073 create_invoice: flow locality 13/8 (wrapper chain, depth 4)
```

No path blocks, reason strings, or fix paragraphs in `message`.

---

## 9. Implementation plan

### 9.1 Extend analysis models

Add to `archbrace/analysis/fli_models.py`:

```python
@dataclass(frozen=True)
class FliMeasurements:
    module_count: int
    wrapper_depth: int
    generic_layer_count: int
    remote_domain_count: int
    unresolved_call_count: int
    traversal_depth_limit: int

@dataclass(frozen=True)
class DominantComponent:
    component: str
    score: int
    ties: tuple[str, ...]

@dataclass(frozen=True)
class EntryPointInfo:
    signals: tuple[str, ...]
    decorators: tuple[str, ...]
    is_public: bool
    parent_class: str | None

@dataclass(frozen=True)
class FliSuggestion:
    component: str
    priority: int
    text: str
```

Extend `FlowLocalityFinding` with:

- `reached_modules: tuple[str, ...]`
- `measurements: FliMeasurements`
- `dominant: DominantComponent`
- `entry_point: EntryPointInfo`
- `suggestions: tuple[FliSuggestion, ...]`
- `caveats: tuple[str, ...]`
- `wrapper_qualified_names: tuple[str, ...]`
- `generic_layers: tuple[str, ...]`
- `remote_domains: tuple[str, ...]`
- `visited_shared_utils: bool`

### 9.2 New builder functions

| Function | Module | Responsibility |
|----------|--------|----------------|
| `classify_entry_point()` | `fli_entry.py` | Return `EntryPointInfo` |
| `compute_measurements()` | `fli_scoring.py` | Raw counts from reach + scores |
| `select_dominant()` | `fli_scoring.py` | Pick dominant component |
| `build_reach_summary()` | `fli_scoring.py` | Modules, layers, domains |
| `build_suggestions()` | `fli_scoring.py` | Ordered suggestion list |
| `build_caveats()` | `fli_scoring.py` | Disclaimer strings |
| `build_wrapper_path()` | `fli_scoring.py` | Labels + qualified names + depth |

### 9.3 Pipeline update

In `analyze_entry_point()`:

```python
reached, edges, unresolved = traverse_from(...)
scores = compute_scores(...)
labels, qualified = build_wrapper_path(...)
measurements = compute_measurements(reached, scores, unresolved, config)
dominant = select_dominant(scores)
entry_info = classify_entry_point(function, module, config)
reach = build_reach_summary(reached, entry_module)
suggestions = build_suggestions(scores, measurements, reach, wrapper_path)
caveats = build_caveats(measurements, unresolved, config, reach, wrapper_path)
```

In `_finding_metadata()` (`flow_locality.py` rule): map finding fields to JSON shape.
In `_finding_message()`: format single line from `dominant` + `measurements`.

In `_diagnostic_to_dict()` (`json.py`): add `url` from rule registry.

### 9.4 Files to modify

| File | Change |
|------|--------|
| `archbrace/analysis/fli_models.py` | New dataclasses; extend `FlowLocalityFinding` |
| `archbrace/analysis/fli_scoring.py` | Measurement, dominant, reach, suggestions builders |
| `archbrace/analysis/fli_entry.py` | `classify_entry_point()` |
| `archbrace/analysis/flow_locality.py` | Wire new builders into `analyze_entry_point()` |
| `archbrace/rules/flow_locality.py` | Lean message; expanded `_finding_metadata()` |
| `archbrace/reporting/json.py` | Top-level `url` field |
| `docs/rules.md` | Link to this spec; update diagnostic format section |

---

## 10. Scope by version

### 10.1 v1 (this spec)

- All fields in §6.2 except `edges`
- Top-level `url`
- Lean `message`
- Backward-compatible `path`, `reasons`, `unresolved_edges`

### 10.2 v2 (deferred)

**`edges` in metadata** — call-edge list for graph visualization:

```json
{
  "caller": "invoice.api.create_invoice",
  "callee": "invoice.handlers.CreateInvoiceHandler.handle",
  "confidence": "high",
  "call_kind": "imported",
  "same_package": true
}
```

Cap at 50 edges; omit key when empty. Useful for IDE graph views; not required for
AI fix guidance in v1.

**`archbrace rule AR073` command** — static rule docs on demand (separate spec).

**`--verbose` text flag** — expand path and suggestions in terminal output.

---

## 11. JSON schema versioning

Reporter schema remains `"version": "1"`. This change is **additive** — new metadata
keys only; optional top-level `url`.

Keys in §7 are public API. Breaking changes require schema version bump.

---

## 12. Worked examples

### 12.1 Layered invoice flow (primary regression fixture)

Source layout: `api → handlers → services → processors → repositories`.

**Message:**

```text
create_invoice: flow locality 13/8 (wrapper chain, depth 4)
```

**Key metadata:**

```json
{
  "dominant": { "component": "wrapper_chain", "score": 7, "ties": [] },
  "measurements": {
    "module_count": 5,
    "wrapper_depth": 4,
    "generic_layer_count": 4
  },
  "reach": {
    "generic_layers": ["handlers", "processors", "repositories", "services"]
  }
}
```

### 12.2 Same-domain vertical slice (passes — no diagnostic)

Source layout: `create.py`, `models.py`, `calculations.py`, `pdf.py` in `invoice/`.

No diagnostic emitted. Documented in tests as the contrast case.

### 12.3 Remote domain + shared utils

**Message:**

```text
create_invoice: flow locality 6/3 (remote domain, 2 domains)
```

**Key metadata:**

```json
{
  "dominant": { "component": "remote_domain", "score": 3, "ties": [] },
  "reach": {
    "remote_domains": ["core", "shared"],
    "visited_shared_utils": true
  }
}
```

### 12.4 Unresolved dynamic calls

**Message:**

```text
run: flow locality 3/8 (unresolved calls)
```

**Key metadata:**

```json
{
  "unresolved_edges": 1,
  "measurements": { "unresolved_call_count": 1 },
  "caveats": [
    "FLI may be underestimated due to 1 unresolved local-looking call(s)."
  ]
}
```

Unresolved info appears in `measurements`, `caveats`, and `scores.unresolved_edge` —
not duplicated as a separate entry in `reasons`.

---

## 13. Consumer guide

### 13.1 Human in terminal

Read the one-line `message`. For detail:

```bash
archbrace check src/ --format json | jq '.diagnostics[] | select(.code=="AR073")'
```

### 13.2 IDE / LSP

1. Display `message` inline.
2. Set `code_description.href` from `url`.
3. Show fix panel from `metadata.suggestions`.
4. Navigate call chain via `metadata.wrapper_path.qualified_names`.

### 13.3 AI agent workflow

```
1. archbrace check . --format json
2. Filter diagnostics where code == "AR073"
3. Read metadata.dominant.component → choose fix strategy
4. Read metadata.wrapper_path + metadata.reach → open relevant files
5. Follow metadata.suggestions[0].text as primary guidance
6. Optional: fetch diagnostic.url for static rule context
7. Re-run check; verify metadata.actual <= metadata.limit
```

Agents must prefer JSON `metadata` over parsing `message` prose.

---

## 14. Testing requirements

### 14.1 Unit tests (`tests/unit/test_rule_ar073.py`)

| Test | Assertion |
|------|-----------|
| `test_metadata_includes_dominant` | `dominant.component` matches highest score |
| `test_measurements_match_score_buckets` | raw counts map to bucket scores |
| `test_wrapper_path_matches_legacy_path` | `path == wrapper_path.labels` |
| `test_reach_modules_covers_traversal` | all modules from bad invoice fixture |
| `test_suggestions_ordered_by_score` | priorities ascending |
| `test_entry_point_signals` | route decorator → `route_decorator` signal |
| `test_caveats_when_unresolved` | underestimate caveat present |
| `test_message_is_single_line` | no `\n` in message |
| `test_reach_truncated_when_large` | synthetic large reach sets `truncated: true` |

### 14.2 Reporting tests (`tests/unit/test_reporting.py`)

- JSON output includes `url` for AR073
- Metadata round-trips through `render_json` unchanged

### 14.3 Documentation

- `docs/rules.md` § AR073 links to this spec and shows example JSON
- Note `path` deprecation in favor of `wrapper_path.labels`

---

## 15. Migration and rollout

| Phase | Deliverable |
|-------|-------------|
| 1 | Extend finding model + analysis builders |
| 2 | Expand metadata; shorten message |
| 3 | Add `url` to JSON reporter |
| 4 | Update `docs/rules.md`; link this spec |
| 5 | `archbrace rule AR073` command (separate work) |
| 6 | Optional `--verbose` text expansion |

**Deprecation:** `path` and `reasons` marked deprecated in docs at phase 4; removed no
earlier than schema v2.

---

## 16. Open questions

1. Include `edges` in v1? **Recommendation:** no; defer to v2.
2. Cap `reach.modules` at 20 or 50? **Recommendation:** 20 with `truncated` flag.
3. Formal JSON Schema file? **Recommendation:** optional; inline docs sufficient for v1.
4. Should scoring formulas be documented in metadata? **Recommendation:** no; link to
   `docs/rules.md` via `url`.

---

## 17. Acceptance criteria

- [x] AR073 `message` is a single line with no embedded path or fix prose
- [x] Metadata includes `dominant`, `measurements`, `reach`, `wrapper_path`,
      `entry_point`, `suggestions`, `caveats`
- [x] `path` remains and equals `wrapper_path.labels`
- [x] Raw measurements explain every non-zero score bucket
- [x] `reach.modules` reflects full traversal, not wrapper path alone
- [x] Unresolved edge info is not duplicated across `reasons` and `caveats`
- [x] All new fields are deterministic and covered by unit tests
- [x] `docs/rules.md` documents the metadata contract and links here
- [x] Full validation passes: pytest, ruff, mypy, archbrace check .
